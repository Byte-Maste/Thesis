"""MechQA pilot: vector (A), graph (B), and hybrid (C) on 200 validation questions.

The gold paragraph is indexed with the other pilot paragraphs. It is not pasted
into the prompt unless retrieval returns it. Raw rows stay under data/processed/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import string
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
CONFIG_PATH = ROOT / "configs" / "mechqa_pilot.json"
PROCESSED = ROOT / "data" / "processed" / "mechqa"
PROMPT = """Answer the question using only the context below.
If the context is insufficient, say so.
End with the line: Result: <short answer>

Context:
{context}

Question: {question}
"""


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def post_json(url: str, payload: dict, headers: dict[str, str]) -> dict:
    data = json.dumps(payload).encode("utf-8")
    for attempt in range(8):
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:400]
            if exc.code == 429 and attempt < 7:
                time.sleep(21)
                continue
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    raise RuntimeError("rate limit retries exhausted")


def cohere_embed(api_key: str, model: str, texts: list[str], input_type: str) -> list[list[float]]:
    body = post_json(
        "https://api.cohere.com/v2/embed",
        {"model": model, "texts": texts, "input_type": input_type, "embedding_types": ["float"]},
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    vectors = body.get("embeddings", {})
    if isinstance(vectors, dict):
        vectors = vectors.get("float")
    if not isinstance(vectors, list):
        raise RuntimeError("Unexpected embed response")
    time.sleep(3.2)
    return vectors


def cohere_chat(api_key: str, model: str, prompt: str) -> str:
    body = post_json(
        "https://api.cohere.com/v2/chat",
        {"model": model, "temperature": 0, "messages": [{"role": "user", "content": prompt}]},
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    parts = body.get("message", {}).get("content", [])
    text = "\n".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
    if not text:
        raise RuntimeError("Empty chat response")
    time.sleep(3.2)
    return text


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


def select_pilot(rows: list[dict], quotas: dict[str, int]) -> list[dict]:
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


def cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def extract_triples(api_key: str, model: str, chunks: list[dict]) -> list[dict]:
    instruction = (
        "Extract mechanical-property facts as a JSON array only. "
        "Each item has material, property, value, and a short evidence quote. "
        "property must be one of: yield strength, ultimate tensile strength, "
        "fracture strength, Young's modulus, ductility. "
        "No more than 8 items. If none, return [].\n\n"
    )
    triples: list[dict] = []
    for index, chunk in enumerate(chunks, start=1):
        if index == 1 or index % 10 == 0:
            print(f"triple {index}/{len(chunks)}", flush=True)
        raw = cohere_chat(api_key, model, instruction + chunk["text"][:4000])
        match = re.search(r"\[.*\]", raw, re.S)
        if not match:
            continue
        try:
            items = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
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


def top_chunks(query_vector: list[float], chunks: list[dict], vectors: list[list[float]], k: int) -> list[dict]:
    ranked = []
    for chunk, vector in zip(chunks, vectors):
        ranked.append({**chunk, "score": cosine(query_vector, vector)})
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:k]


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    PROCESSED.mkdir(parents=True, exist_ok=True)
    pilot_path = PROCESSED / "pilot_200.jsonl"
    chunks_path = PROCESSED / "chunks.json"
    vectors_path = PROCESSED / "vectors.json"
    triples_path = PROCESSED / "triples.json"

    if not pilot_path.exists():
        print("loading validation split")
        rows = load_validation()
        pilot = select_pilot(rows, config["quotas"])
        pilot_path.write_text("".join(json.dumps(row) + "\n" for row in pilot), encoding="utf-8")
        chunks = []
        seen = set()
        for row in pilot:
            if row["context_id"] in seen:
                continue
            seen.add(row["context_id"])
            chunks.append({"id": row["context_id"], "doi": row["doi"], "text": row["context"]})
        chunks_path.write_text(json.dumps(chunks), encoding="utf-8")
        print(f"pilot={len(pilot)} unique_contexts={len(chunks)}")
    else:
        pilot = [json.loads(line) for line in pilot_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
        print(f"cached pilot={len(pilot)} unique_contexts={len(chunks)}")

    if args.prepare_only:
        return

    env = load_env(ENV_PATH)
    api_key = env.get("cohere_api_key") or env.get("COHERE_API_KEY")
    if not api_key:
        raise SystemExit("Missing cohere_api_key")

    if vectors_path.exists():
        vectors = json.loads(vectors_path.read_text(encoding="utf-8"))
    else:
        vectors = []
        texts = [chunk["text"][:8000] for chunk in chunks]
        for start in range(0, len(texts), 96):
            print(f"embed {start}/{len(texts)}")
            vectors.extend(cohere_embed(api_key, config["embedder"], texts[start : start + 96], "search_document"))
        vectors_path.write_text(json.dumps(vectors), encoding="utf-8")

    if triples_path.exists():
        triples = json.loads(triples_path.read_text(encoding="utf-8"))
    else:
        print(f"extract triples for {len(chunks)} chunks")
        triples = extract_triples(api_key, config["generator"], chunks)
        triples_path.write_text(json.dumps(triples), encoding="utf-8")
    print(f"triples={len(triples)}")

    answers_path = PROCESSED / "answers.jsonl"
    done = {}
    if answers_path.exists():
        for line in answers_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                done[(item["id"], item["condition"])] = item

    conditions = {"A": (True, False), "B": (False, True), "C": (True, True)}
    with answers_path.open("a", encoding="utf-8") as handle:
        for row in pilot:
            query_vector = None
            passages = None
            graph = None
            for condition, (use_text, use_graph) in conditions.items():
                if (row["id"], condition) in done:
                    continue
                if use_text and passages is None:
                    query_vector = cohere_embed(api_key, config["embedder"], [row["question"]], "search_query")[0]
                    passages = top_chunks(query_vector, chunks, vectors, config["top_k"])
                if use_graph and graph is None:
                    graph = top_triples(row["question"], triples, config["top_k"])
                context = format_context(passages if use_text else None, graph if use_graph else None)
                answer = cohere_chat(api_key, config["generator"], PROMPT.format(context=context, question=row["question"]))
                record = {
                    "id": row["id"],
                    "qa_type": row["qa_type"],
                    "record_type": row["record_type"],
                    "condition": condition,
                    "gold_answer": row["gold_answer"],
                    "correct": exact_match(row["gold_answer"], answer),
                    "gold_context_id": row["context_id"],
                    "passages": [
                        {"id": item["id"], "score": round(item["score"], 3)} for item in (passages or [])
                    ] if use_text else [],
                    "graph": [
                        f"{item['material']} | {item['property']} | {item['value']}" for item in (graph or [])
                    ] if use_graph else [],
                    "hit_gold_context": any(item["id"] == row["context_id"] for item in (passages or [])) if use_text else None,
                    "answer": answer,
                }
                handle.write(json.dumps(record) + "\n")
                handle.flush()
                done[(row["id"], condition)] = record
                print(f"{row['id']} {condition} {record['correct']}")

    summary: dict[str, dict[str, float]] = {}
    for qa_type in config["quotas"]:
        summary[qa_type] = {}
        for condition in conditions:
            subset = [item for item in done.values() if item["qa_type"] == qa_type and item["condition"] == condition]
            summary[qa_type][condition] = sum(item["correct"] for item in subset) / len(subset) if subset else 0.0
    overall = {}
    hit_rate = {}
    for condition in conditions:
        subset = [item for item in done.values() if item["condition"] == condition]
        overall[condition] = sum(item["correct"] for item in subset) / len(subset) if subset else 0.0
        hits = [item["hit_gold_context"] for item in subset if item["hit_gold_context"] is not None]
        hit_rate[condition] = sum(bool(item) for item in hits) / len(hits) if hits else None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "results" / "mechqa" / "pilot" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "config": config,
        "corpus": "unique contexts of the 200 pilot questions only",
        "score": "SQuAD exact match on the Result line",
        "summary_by_qa_type": summary,
        "overall_exact_match": overall,
        "gold_context_hit_rate": hit_rate,
        "rows": list(done.values()),
    }
    (out_dir / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"overall_exact_match": overall, "gold_context_hit_rate": hit_rate, "by_type": summary}, indent=2))
    print(out_dir / "results.json")


if __name__ == "__main__":
    main()
