"""Chapter 10 pilot: vector-only (A) vs hybrid (C) on the draft question files.

Reads keys from .env. Does not print them. Caches chunks, embeddings, and triples
under data/processed/, which is gitignored along with the textbook PDF.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
CONFIG_PATH = ROOT / "configs" / "b1_pilot.json"
QUESTIONS_DIR = ROOT / "data" / "benchmarks" / "b1"
PROCESSED = ROOT / "data" / "processed"
PDF_NAME = "238673958-Fundamentals-of-Modern-Manufacturing-4th-Edition-by-Mikell-p-Groover.pdf"

PROMPT = """You answer a manufacturing question using only the context below.
If the context is insufficient, say so.
For a calculation, end with the line: Result: <number> <units>
For a multiple-choice question, end with the line: Answer: <letter>
Keep the answer short.

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
    for attempt in range(6):
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            if exc.code == 429 and attempt < 5:
                time.sleep(20)
                continue
            raise RuntimeError(f"HTTP {exc.code} from {url.split('?')[0]}: {body}") from exc
    raise RuntimeError(f"HTTP 429 from {url.split('?')[0]}")


def find_pdf() -> Path:
    candidates = [ROOT / PDF_NAME, ROOT / "data" / "raw" / PDF_NAME]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("Groover PDF not found in the thesis folder or data/raw/")


def extract_chapter(pdf_path: Path, start: int, end: int) -> str:
    import fitz

    document = fitz.open(pdf_path)
    parts: list[str] = []
    for index in range(start - 1, end):
        parts.append(f"\n\n===== PDF_PAGE {index + 1} =====\n{document[index].get_text()}")
    return "".join(parts)


def chunk_text(text: str, size: int, overlap: int) -> list[dict]:
    chunks: list[dict] = []
    page = "?"
    for block in re.split(r"(===== PDF_PAGE \d+ =====)", text):
        match = re.fullmatch(r"===== PDF_PAGE (\d+) =====", block.strip())
        if match:
            page = match.group(1)
            continue
        words = block.split()
        if not words:
            continue
        window: list[str] = []
        length = 0
        for word in words:
            window.append(word)
            length += len(word) + 1
            if length >= size:
                chunks.append({"id": f"c{len(chunks):03d}", "page": page, "text": " ".join(window)})
                keep = []
                kept = 0
                for previous in reversed(window):
                    if kept >= overlap:
                        break
                    keep.append(previous)
                    kept += len(previous) + 1
                window = list(reversed(keep))
                length = sum(len(item) + 1 for item in window)
        if window and length > 80:
            chunks.append({"id": f"c{len(chunks):03d}", "page": page, "text": " ".join(window)})
    return chunks


def cohere_embed(api_key: str, model: str, texts: list[str], input_type: str) -> list[list[float]]:
    body = post_json(
        "https://api.cohere.com/v2/embed",
        {
            "model": model,
            "texts": texts,
            "input_type": input_type,
            "embedding_types": ["float"],
        },
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    vectors = body.get("embeddings", {})
    if isinstance(vectors, dict):
        vectors = vectors.get("float") or vectors.get("embeddings")
    if not isinstance(vectors, list):
        raise RuntimeError("Unexpected Cohere embed response")
    time.sleep(3.2)
    return vectors


def cohere_chat(api_key: str, model: str, prompt: str, temperature: float) -> str:
    body = post_json(
        "https://api.cohere.com/v2/chat",
        {
            "model": model,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        },
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    content = body.get("message", {}).get("content", [])
    texts = [part.get("text", "") for part in content if isinstance(part, dict)]
    answer = "\n".join(text for text in texts if text).strip()
    if not answer:
        raise RuntimeError("Empty Cohere chat response")
    time.sleep(3.2)
    return answer


def gemini_text(api_key: str, model: str, prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = post_json(
        url,
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0},
        },
        {"Content-Type": "application/json", "x-goog-api-key": api_key},
    )
    parts = body["candidates"][0]["content"]["parts"]
    return "".join(part.get("text", "") for part in parts).strip()


def pages_of(chunks: list[dict]) -> list[tuple[str, str]]:
    grouped: dict[str, list[str]] = {}
    for chunk in chunks:
        grouped.setdefault(chunk["page"], []).append(chunk["text"])
    return [(page, " ".join(texts)) for page, texts in grouped.items()]


def extract_triples(complete, pages: list[tuple[str, str]]) -> list[dict]:
    triples: list[dict] = []
    instruction = (
        "Extract manufacturing facts as JSON. Return only a JSON array. "
        "Each item has subject, relation, object, and a short evidence quote. "
        "Use relations such as part_of, causes, requires, freezes_after, measured_by, "
        "defined_as. No more than 12 items. If nothing is useful, return [].\n\n"
    )
    for page, text in pages:
        raw = complete(instruction + text[:7000])
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
            subject = str(item.get("subject", "")).strip()
            relation = str(item.get("relation", "")).strip()
            obj = str(item.get("object", "")).strip()
            if subject and relation and obj:
                triples.append(
                    {
                        "subject": subject,
                        "relation": relation,
                        "object": obj,
                        "page": page,
                        "evidence": str(item.get("evidence", ""))[:240],
                    }
                )
        time.sleep(0.3)
    return triples


def cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def top_chunks(query_vector: list[float], chunks: list[dict], vectors: list[list[float]], k: int) -> list[dict]:
    ranked = sorted(
        ({"id": chunk["id"], "page": chunk["page"], "text": chunk["text"], "score": cosine(query_vector, vector)} for chunk, vector in zip(chunks, vectors)),
        key=lambda item: item["score"],
        reverse=True,
    )
    return ranked[:k]


def top_triples(question: str, triples: list[dict], k: int) -> list[dict]:
    words = {word for word in re.findall(r"[a-z0-9]+", question.lower()) if len(word) > 3}
    scored: list[dict] = []
    for triple in triples:
        blob = f"{triple['subject']} {triple['relation']} {triple['object']}".lower()
        overlap = sum(1 for word in words if word in blob)
        if overlap:
            scored.append({**triple, "score": overlap})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:k]


def format_context(passages: list[dict], triples: list[dict] | None) -> str:
    lines = [f"[{item['id']} p.{item['page']}] {item['text']}" for item in passages]
    if triples:
        lines.append("Graph facts:")
        lines.extend(
            f"- {item['subject']} --{item['relation']}--> {item['object']} (p.{item['page']})"
            for item in triples
        )
    return "\n".join(lines)


def score_answer(question: dict, answer: str) -> bool:
    if "gold_value" in question:
        numbers = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", answer.replace(",", ""))]
        target = float(question["gold_value"])
        return any(abs(number - target) / max(abs(target), 1e-6) <= 0.03 for number in numbers)
    if "gold_choice" in question:
        match = re.search(r"answer\s*:\s*([a-d])", answer, re.I)
        choice = match.group(1).lower() if match else ""
        if not choice:
            match = re.search(r"\b([a-d])\b", answer.lower())
            choice = match.group(1) if match else ""
        return choice == question["gold_choice"]
    return False


def score_rq_overlap(question: dict, answer: str) -> bool:
    """Provisional check used only because the Gemini judge account has no credits."""
    stop = {"which", "their", "there", "about", "after", "before", "where", "while", "during", "other", "these", "those", "from", "with", "that", "this", "into", "than"}
    words = [word for word in re.findall(r"[a-z]{5,}", question["gold_answer"].lower()) if word not in stop]
    if not words:
        return False
    answer_words = set(re.findall(r"[a-z]{5,}", answer.lower()))
    return sum(word in answer_words for word in words) / len(words) >= 0.45


def load_questions() -> list[dict]:
    questions: list[dict] = []
    for path in sorted(QUESTIONS_DIR.glob("*.jsonl")):
        if path.name == "questions.jsonl":
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                questions.append(json.loads(line))
    if not questions:
        raise SystemExit(f"No question files in {QUESTIONS_DIR}")
    return questions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("dev", "test", "all"), default="dev")
    args = parser.parse_args()
    env = load_env(ENV_PATH)
    cohere_key = env.get("cohere_api_key") or env.get("COHERE_API_KEY")
    gemini_key = env.get("gemini_api_key") or env.get("GEMINI_API_KEY")
    if not cohere_key or not gemini_key:
        raise SystemExit("Missing cohere_api_key or gemini_api_key in .env")

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    questions = load_questions()
    if args.split != "all":
        questions = [item for item in questions if item["split"] == args.split]
    PROCESSED.mkdir(parents=True, exist_ok=True)

    chapter_path = PROCESSED / "ch10.txt"
    if not chapter_path.exists():
        start, end = config["pdf_pages"]
        chapter_path.write_text(extract_chapter(find_pdf(), start, end), encoding="utf-8")
    chunks_path = PROCESSED / "ch10_chunks.json"
    if chunks_path.exists():
        chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    else:
        chunks = chunk_text(chapter_path.read_text(encoding="utf-8"), config["chunk_size"], config["chunk_overlap"])
        chunks_path.write_text(json.dumps(chunks), encoding="utf-8")

    vectors_path = PROCESSED / "ch10_vectors.json"
    if vectors_path.exists():
        vectors = json.loads(vectors_path.read_text(encoding="utf-8"))
    else:
        vectors = []
        batch = 96
        texts = [chunk["text"] for chunk in chunks]
        for start in range(0, len(texts), batch):
            vectors.extend(cohere_embed(cohere_key, config["embedder"], texts[start : start + batch], "search_document"))
        vectors_path.write_text(json.dumps(vectors), encoding="utf-8")

    triples_path = PROCESSED / "ch10_triples.json"
    if triples_path.exists():
        triples = json.loads(triples_path.read_text(encoding="utf-8"))
    else:
        # Gemini returned HTTP 402 (prepayment credits depleted), so extraction uses Cohere.
        triples = extract_triples(
            lambda prompt: cohere_chat(cohere_key, config["generator"], prompt, 0),
            pages_of(chunks),
        )
        triples_path.write_text(json.dumps(triples), encoding="utf-8")

    print(f"chunks={len(chunks)} triples={len(triples)} questions={len(questions)}")
    rows = []
    for question in questions:
        query_vector = cohere_embed(cohere_key, config["embedder"], [question["question"]], "search_query")[0]
        passages = top_chunks(query_vector, chunks, vectors, config["top_k"])
        graph = top_triples(question["question"], triples, config["top_k"] * 2)
        answers = {}
        for condition, use_graph in (("A", False), ("C", True)):
            context = format_context(passages, graph if use_graph else None)
            prompt = PROMPT.format(context=context, question=question["question"])
            answer = cohere_chat(cohere_key, config["generator"], prompt, config["temperature"])
            if question["category"] == "RQ":
                correct = score_rq_overlap(question, answer)
            else:
                correct = score_answer(question, answer)
            answers[condition] = {"answer": answer, "correct": correct}
            time.sleep(0.2)
        rows.append(
            {
                "id": question["id"],
                "category": question["category"],
                "A_correct": answers["A"]["correct"],
                "C_correct": answers["C"]["correct"],
                "passages": [{"id": item["id"], "page": item["page"], "score": round(item["score"], 3)} for item in passages],
                "graph": [f"{item['subject']} --{item['relation']}--> {item['object']}" for item in graph],
                "A_answer": answers["A"]["answer"],
                "C_answer": answers["C"]["answer"],
            }
        )
        print(f"{question['id']} A={answers['A']['correct']} C={answers['C']['correct']}")

    summary: dict[str, dict[str, float]] = {}
    for category in ("MathQ", "MCQ", "RQ"):
        subset = [row for row in rows if row["category"] == category]
        summary[category] = {
            "n": len(subset),
            "A": sum(row["A_correct"] for row in subset) / len(subset),
            "C": sum(row["C_correct"] for row in subset) / len(subset),
        }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "results" / "b1" / "pilot" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "config": config,
        "note": "Pilot on draft questions. Test split is not frozen. Not the ManuRAG 1515-pair set. Gemini judge unavailable (HTTP 402). RQ marks use lexical overlap, not RAGAS.",
        "summary": summary,
        "rows": rows,
    }
    (out_dir / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(out_dir / "results.json")


if __name__ == "__main__":
    main()
