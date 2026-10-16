# Pipeline

How a MechQA question is answered. The three retrieval flows are separate files. They share the setup below and differ only after the question is received.

Read `MECHQA.md` for the dataset decision. Do not start coding from this file until that plan still matches.

| Flow | Condition | File |
|---|---|---|
| Vector only | A | [flows/vector_only.md](flows/vector_only.md) |
| Graph only | B | [flows/graph_only.md](flows/graph_only.md) |
| Hybrid | C | [flows/hybrid.md](flows/hybrid.md) |

## Shared setup (run once)

```
MechQA validation split
        |
        v
dedupe paragraphs by context text
        |
        +--> chunk store (id, DOI, text)          used by vector only and hybrid
        |
        +--> triple store (Material, Property, Value, source chunk id)
             used by graph only and hybrid
```

Rules that apply to every flow:

- The gold `context` on a question row is not pasted into the prompt. Retrieval has to find it.
- Generator is Cohere, temperature 0, same prompt template, same top-k.
- The prompt slot is named `Context`. Each flow fills that slot with different text.
- The model must end with `Result: <span>`.
- Score is exact match against `answers.text`, reported by `qa_type`.
- Pilot size is 200 validation questions. The sample is chosen by hashing `id` before any run.

## Shared prompt

```
Answer the question using only the context below.
If the context is insufficient, say so.
End with the line: Result: <short answer>

Context:
{context}

Question: {question}
```

## What a run writes

Each condition writes `results/mechqa/<condition>/<timestamp>/results.json` with the question id, `qa_type`, retrieved chunk ids or triples, the model answer, and exact-match true or false. Run folders are not edited later.
