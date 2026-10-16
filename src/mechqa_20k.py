"""MechQA on 20,000 validation questions with local Ollama models.

Condition A is vector retrieval, B is graph triples, C is both.
The gold paragraph is indexed with the other passages. It is not pasted
into the prompt unless retrieval returns it.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import re
import string
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "mechqa_20k.json"
OUT = ROOT / "data" / "processed" / "mechqa20k"
PROMPT = """Answer the question using only the context below.
If the context is insufficient, say so.
End with the line: Result: <short answer>

Context:
{context}

Question: {question}
"""
TRIPLE_INSTRUCTION = (
    "Extract mechanical-property facts as a JSON array only. "
    "Each item has material, property, value, and a short evidence quote. "
    "property must be one of: yield strength, ultimate tensile strength, "
    "fracture strength, Young's modulus, ductility. "
    "No more than 8 items. If none, return [].\n\n"
)


_thread_state = threading.local()


def post_json(url: str, payload: dict) -> dict:
    hostport = url.split("://", 1)[1].split("/", 1)[0]
    host, port_text = hostport.split(":")
    port = int(port_text)
    path = "/" + url.split("://", 1)[1].split("/", 1)[1]
    data = json.dumps(payload).encode("utf-8")
    for attempt in range(8):
        try:
            connection = getattr(_thread_state, "connection", None)
            if connection is None or getattr(_thread_state, "target", None) != (host, port):
                connection = http.client.HTTPConnection(host, port, timeout=300)
                _thread_state.connection = connection
                _thread_state.target = (host, port)
            connection.request("POST", path, body=data, headers={"Content-Type": "application/json"})
            response = connection.getresponse()
            raw = response.read().decode("utf-8")
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}: {raw[:400]}")
            return json.loads(raw)
        except Exception as exc:
            _thread_state.connection = None
            if attempt < 7:
                time.sleep(1 + attempt)
                continue
            raise RuntimeError(str(exc)) from exc
    raise RuntimeError("request retries exhausted")


def ollama_embed(base: str, model: str, texts: list[str]) -> list[list[float]]:
    body = post_json(
        f"{base}/api/embed",
        {"model": model, "input": texts, "keep_alive": "30m"},
    )
    vectors = body.get("embeddings")
    if not isinstance(vectors, list) or len(vectors) != len(texts):
        raise RuntimeError("Unexpected embed response")
    return vectors


def ollama_chat(base: str, model: str, prompt: str, num_predict: int) -> str:
    body = post_json(
        f"{base}/api/chat",
        {
            "model": model,
            "stream": False,
            "keep_alive": "30m",
            "options": {"temperature": 0, "num_predict": num_predict},
            "messages": [{"role": "user", "content": prompt}],
        },
    )
    text = body.get("message", {}).get("content", "").strip()
    if not text:
        raise RuntimeError("Empty chat response")
    return text


def complete(config: dict, prompt: str, num_predict: int) -> str:
    if config.get("vllm_url"):
        body = post_json(
            config["vllm_url"],
            {
                "model": config["generator"],
                "temperature": 0,
                "max_tokens": num_predict,
                "messages": [{"role": "user", "content": prompt}],
                "chat_template_kwargs": {"enable_thinking": False},
            },
        )
        message = body["choices"][0]["message"]
        text = message.get("content") or message.get("reasoning") or ""
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    else:
        text = ollama_chat(config["ollama_url"], config["generator"], prompt, num_predict)
    if not text:
        raise RuntimeError("Empty chat response")
    return text


def complete_many(config: dict, prompts: list[str], num_predict: int) -> list[str]:
    workers = 24 if config.get("vllm_url") and len(prompts) > 1 else 1
    if workers == 1:
        return [complete(config, prompt, num_predict) for prompt in prompts]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda prompt: complete(config, prompt, num_predict), prompts))


def squad_normalize(text: str) -> str:
    text = text.lower()
    text = "".join(ch for ch in text if ch not in set(string.punctuation))
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    return " ".join(text.split())


def exact_match(gold: str, answer: str) -> bool:
    match = re.search(r"result\s*:\s*(.+)", answer, flags=re.I)
    predicted = match.group(1).strip() if match else answer.strip().splitlines()[-1]
    return squad_normalize(predicted) == squad_normalize(gold)


def context_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def select_rows(rows: list[dict], quotas: dict[str, int]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["qa_type"]].append(row)
    chosen: list[dict] = []
    for qa_type, quota in quotas.items():
        pool = grouped.get(qa_type, [])
        pool.sort(key=lambda item: hashlib.sha256(str(item["id"]).encode("utf-8")).hexdigest())
        if len(pool) < quota:
            raise SystemExit(f"Not enough rows for {qa_type}: {len(pool)} < {quota}")
        chosen.extend(pool[:quota])
    return chosen


def load_validation() -> list[dict]:
    from datasets import load_dataset

    dataset = load_dataset("mz516/MechQA-dataset", split="validation")
    rows = []
    for index, row in enumerate(dataset):
        answers = row["answers"]
        texts = answers["text"] if isinstance(answers, dict) else []
        gold = texts[0] if texts else ""
        context = row["context"]
        rows.append(
            {
                "id": str(row["id"]),
                "doi": row["DOI"],
                "question": row["question"],
                "context": context,
                "context_id": context_id(context),
                "gold_answer": gold,
                "qa_type": row["qa_type"],
                "record_type": row["Record Type"],
                "source_index": index,
            }
        )
    return rows


def embed_all(base: str, model: str, texts: list[str], path: Path, batch: int) -> np.ndarray:
    done = 0
    stored: list[np.ndarray] = []
    if path.exists():
        stored_arr = np.load(path)
        done = int(stored_arr.shape[0])
        stored.append(stored_arr.astype(np.float32))
        print(f"resume embed {path.name} {done}/{len(texts)}", flush=True)
    while done < len(texts):
        chunk = texts[done : done + batch]
        vectors = ollama_embed(base, model, [text[:1800] for text in chunk])
        stored.append(np.asarray(vectors, dtype=np.float32))
        done += len(chunk)
        if done % (batch * 5) == 0 or done == len(texts):
            np.save(path, np.vstack(stored))
            print(f"embed {path.name} {done}/{len(texts)}", flush=True)
    matrix = np.vstack(stored)
    if matrix.shape[0] != len(texts):
        raise RuntimeError(f"embed count mismatch for {path.name}")
    np.save(path, matrix)
    return matrix


def normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def top_indices(query: np.ndarray, docs: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    scores = docs @ query
    if k >= len(scores):
        order = np.argsort(-scores)
    else:
        pick = np.argpartition(-scores, k)[:k]
        order = pick[np.argsort(-scores[pick])]
    return order, scores[order]


def parse_triples(raw: str, chunk: dict) -> list[dict]:
    match = re.search(r"\[.*\]", raw, re.S)
    if not match:
        return []
    try:
        items = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    triples = []
    for item in items:
        if not isinstance(item, dict):
            continue
        material = str(item.get("material", "")).strip()
        prop = str(item.get("property", "")).strip()
        value = str(item.get("value", "")).strip()
        if material and prop and value:
            triples.append(
                {
                    "material": material,
                    "property": prop,
                    "value": value,
                    "context_id": chunk["id"],
                    "doi": chunk["doi"],
                }
            )
    return triples


def extract_triples(config: dict, chunks: list[dict], path: Path) -> list[dict]:
    done_ids = set()
    triples: list[dict] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            done_ids.add(item["context_id"])
            if item.get("triples"):
                triples.extend(item["triples"])
        print(f"resume triples {len(done_ids)}/{len(chunks)}", flush=True)
    pending = [chunk for chunk in chunks if chunk["id"] not in done_ids]
    with path.open("a", encoding="utf-8") as handle:
        for start in range(0, len(pending), 48):
            group = pending[start : start + 48]
            raws = complete_many(
                config,
                [TRIPLE_INSTRUCTION + chunk["text"][:2500] for chunk in group],
                160,
            )
            for chunk, raw in zip(group, raws):
                found = parse_triples(raw, chunk)
                handle.write(json.dumps({"context_id": chunk["id"], "triples": found}) + "\n")
                triples.extend(found)
            handle.flush()
            print(f"triple {len(done_ids) + start + len(group)}/{len(chunks)} kept={len(triples)}", flush=True)
    return triples


def top_triples(question: str, triples: list[dict], k: int) -> list[dict]:
    words = {word for word in re.findall(r"[a-z0-9.+-]+", question.lower()) if len(word) > 2}
    scored = []
    for triple in triples:
        blob = f"{triple['material']} {triple['property']} {triple['value']}".lower()
        overlap = sum(1 for word in words if word in blob)
        if overlap:
            scored.append({**triple, "score": overlap})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:k]


def format_context(passages: list[dict] | None, triples: list[dict] | None) -> str:
    lines: list[str] = []
    if passages:
        lines.extend(f"[{item['id']} DOI:{item['doi']}] {item['text']}" for item in passages)
    if triples:
        lines.append("Graph facts:")
        lines.extend(
            f"- {item['material']} --has_property--> {item['property']} --has_value--> {item['value']} (chunk {item['context_id']})"
            for item in triples
        )
    return "\n".join(lines) if lines else "No retrieved context."


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_summary(config: dict, rows: list[dict], done: dict, out_path: Path, include_rows: bool = True) -> dict:
    conditions = config["conditions"]
    summary: dict[str, dict[str, float]] = {}
    counts: dict[str, dict[str, int]] = {}
    for qa_type in config["quotas"]:
        summary[qa_type] = {}
        counts[qa_type] = {}
        for condition in conditions:
            subset = [
                item
                for item in done.values()
                if item["qa_type"] == qa_type and item["condition"] == condition
            ]
            counts[qa_type][condition] = len(subset)
            summary[qa_type][condition] = (
                sum(item["correct"] for item in subset) / len(subset) if subset else 0.0
            )
    overall = {}
    hit_rate = {}
    for condition in conditions:
        subset = [item for item in done.values() if item["condition"] == condition]
        overall[condition] = sum(item["correct"] for item in subset) / len(subset) if subset else 0.0
        hits = [item["hit_gold_context"] for item in subset if item["hit_gold_context"] is not None]
        hit_rate[condition] = sum(bool(item) for item in hits) / len(hits) if hits else None
    payload = {
        "config": config,
        "questions": len(rows),
        "answered_records": len(done),
        "expected_records": len(rows) * len(conditions),
        "corpus": "unique contexts of the 20000 validation questions",
        "score": "SQuAD exact match on the Result line",
        "models": {"generator": config["generator"], "embedder": config["embedder"]},
        "summary_by_qa_type": summary,
        "counts_by_qa_type": counts,
        "overall_exact_match": overall,
        "gold_context_hit_rate": hit_rate,
        "rows": list(done.values()) if include_rows else [],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def print_table(payload: dict, table_path: Path | None = None) -> None:
    conditions = payload["config"]["conditions"]
    headers = ["qa_type", *conditions, "n"]
    lines = [
        "exact match",
        " | ".join(headers),
        " | ".join("---" for _ in headers),
    ]
    for qa_type, scores in payload["summary_by_qa_type"].items():
        count = payload["counts_by_qa_type"][qa_type]["A"]
        cells = [qa_type] + [f"{scores[cond] * 100:.2f}%" for cond in conditions] + [str(count)]
        lines.append(" | ".join(cells))
    overall = payload["overall_exact_match"]
    lines.append(
        " | ".join(
            ["Overall"] + [f"{overall[cond] * 100:.2f}%" for cond in conditions] + [str(payload["questions"])]
        )
    )
    hit = payload["gold_context_hit_rate"]
    lines.append("")
    lines.append("gold context in top-k")
    lines.append(" | ".join(["metric", *conditions]))
    lines.append(
        " | ".join(
            ["hit rate"]
            + [f"{(hit[cond] or 0) * 100:.2f}%" if hit[cond] is not None else "-" for cond in conditions]
        )
    )
    table = "\n".join(lines)
    print(table, flush=True)
    (table_path or (OUT / "table.md")).write_text(table + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qa-type", default="")
    parser.add_argument("--answers", default="answers.jsonl")
    args = parser.parse_args()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    rows_path = OUT / "questions.jsonl"
    chunks_path = OUT / "chunks.json"
    doc_vec_path = OUT / "doc_vectors.npy"
    query_vec_path = OUT / "query_vectors.npy"
    triples_path = OUT / "triples.jsonl"
    answers_path = OUT / args.answers
    summary_name = "results_property.json" if args.qa_type else "results.json"
    table_path = OUT / ("table_property.md" if args.qa_type else "table.md")
    summary_path = OUT / summary_name
    base = config["ollama_url"]

    if not rows_path.exists():
        print("loading validation split", flush=True)
        selected = select_rows(load_validation(), config["quotas"])
        rows_path.write_text("".join(json.dumps(row) + "\n" for row in selected), encoding="utf-8")
        chunks = []
        seen = set()
        for row in selected:
            if row["context_id"] in seen:
                continue
            seen.add(row["context_id"])
            chunks.append({"id": row["context_id"], "doi": row["doi"], "text": row["context"]})
        chunks_path.write_text(json.dumps(chunks), encoding="utf-8")
        print(f"questions={len(selected)} unique_contexts={len(chunks)}", flush=True)
    rows = load_jsonl(rows_path)
    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    print(f"questions={len(rows)} unique_contexts={len(chunks)}", flush=True)

    doc_matrix = normalize(
        embed_all(base, config["embedder"], [chunk["text"] for chunk in chunks], doc_vec_path, 16)
    )
    query_matrix = normalize(
        embed_all(base, config["embedder"], [row["question"] for row in rows], query_vec_path, 32)
    )
    triples = extract_triples(config, chunks, triples_path)
    print(f"triples={len(triples)}", flush=True)

    done = {}
    if answers_path.exists():
        for item in load_jsonl(answers_path):
            done[(item["id"], item["condition"])] = item
        print(f"resume answers {len(done)}", flush=True)

    conditions = {"A": (True, False), "B": (False, True), "C": (True, True)}
    jobs = []
    selected = list(enumerate(rows))
    if args.qa_type:
        selected = [(index, row) for index, row in selected if row["qa_type"] == args.qa_type]
        print(f"qa_type={args.qa_type} questions={len(selected)}", flush=True)
    for index, row in selected:
        pending = [cond for cond in conditions if (row["id"], cond) not in done]
        if not pending:
            continue
        order, scores = top_indices(query_matrix[index], doc_matrix, config["top_k"])
        passages = []
        for rank, score in zip(order, scores):
            chunk = chunks[int(rank)]
            passages.append({**chunk, "score": float(score)})
        graph = top_triples(row["question"], triples, config["top_k"])
        for condition in pending:
            use_text, use_graph = conditions[condition]
            context = format_context(passages if use_text else None, graph if use_graph else None)
            jobs.append(
                {
                    "row": row,
                    "condition": condition,
                    "use_text": use_text,
                    "use_graph": use_graph,
                    "passages": passages,
                    "graph": graph,
                    "prompt": PROMPT.format(context=context, question=row["question"]),
                }
            )
    print(f"pending generations={len(jobs)}", flush=True)
    started = time.perf_counter()
    written = 0
    with answers_path.open("a", encoding="utf-8") as handle:
        for start in range(0, len(jobs), 48):
            group = jobs[start : start + 48]
            answers = complete_many(config, [job["prompt"] for job in group], 64)
            for job, answer in zip(group, answers):
                row = job["row"]
                record = {
                    "id": row["id"],
                    "qa_type": row["qa_type"],
                    "record_type": row["record_type"],
                    "condition": job["condition"],
                    "gold_answer": row["gold_answer"],
                    "correct": exact_match(row["gold_answer"], answer),
                    "gold_context_id": row["context_id"],
                    "passages": [
                        {"id": item["id"], "score": round(item["score"], 3)} for item in job["passages"]
                    ]
                    if job["use_text"]
                    else [],
                    "graph": [
                        f"{item['material']} | {item['property']} | {item['value']}" for item in job["graph"]
                    ]
                    if job["use_graph"]
                    else [],
                    "hit_gold_context": any(item["id"] == row["context_id"] for item in job["passages"])
                    if job["use_text"]
                    else None,
                    "answer": answer,
                }
                handle.write(json.dumps(record) + "\n")
                done[(row["id"], job["condition"])] = record
                written += 1
            handle.flush()
            elapsed = time.perf_counter() - started
            print(f"answers {len(done)}/{len(rows) * 3} rate={written / elapsed:.2f}/s", flush=True)
            if written % 480 == 0:
                print_table(
                    write_summary(config, rows, done, summary_path, include_rows=False),
                    table_path,
                )

    payload = write_summary(config, rows, done, summary_path)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stamped = ROOT / "results" / "mechqa" / "n20000" / stamp / "results.json"
    stamped.parent.mkdir(parents=True, exist_ok=True)
    stamped.write_text(json.dumps(payload), encoding="utf-8")
    print_table(payload, table_path)
    print(summary_path)
    print(stamped)


if __name__ == "__main__":
    main()
