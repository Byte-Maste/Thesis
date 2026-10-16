# MechQA plan

Working note for the next coding step. Read `PLAN.md` first. This file records the dataset we will actually run. It does not replace the ManuRAG method comparison.

Last updated: 2026-10-13

## Decision

The ManuRAG 1,515-pair file is not public. Groover’s solutions manual cannot be copied into this repo. The public set we will code against is **MechQA**.

MechQA is not ManuRAG. Scores on MechQA are not comparable to ManuRAG4’s 62.03 / 87.61 / 45.75. The paper must say that. What we compare is our own conditions on the same MechQA slice: vector-only against hybrid.

## What MechQA is

| Item | Value |
|---|---|
| Name | MechQA |
| Paper | Zhang and Cole, “Automatic Generation of a Mechanical Properties Question-Answering Dataset…”, Journal of Chemical Information and Modeling, 2026 |
| Download | https://huggingface.co/datasets/mz516/MechQA-dataset |
| Code | https://github.com/mz-516/MechQA |
| Rows | 202,068 SQuAD-style pairs |
| Authors’ split | 181,722 train, 20,346 validation |
| File size | about 38 MB |
| Source | Mechanical-property records distilled from the literature, then turned into questions. Five properties: ultimate tensile strength, yield strength, fracture strength, Young’s modulus, ductility |
| Licence | Not stated on the dataset card we checked. Record it in `data/README.md` before any file is committed. If the licence forbids redistribution, commit the download script only |

Each row has:

| Field | Role |
|---|---|
| `id` | Row id inside MechQA |
| `DOI` | Source paper |
| `question` | The question |
| `context` | The paragraph that contains the answer |
| `answers.text` | Gold answer span |
| `answers.answer_start` | Character offset of that span in `context` |
| `qa_type` | `Numeric Lookup`, `Entity Lookup`, or `Property Identification` |
| `Record Type` | Which property the row is about |

`qa_type` is the category we report, in place of MathQ / MCQ / RQ.

The gold `context` is the answer passage. A run that hands that paragraph to the model is not retrieval. The corpus is the set of **unique contexts**. Retrieval has to find the right one.

Spot-checks of the public preview show noisy pairs (the asked property and the span do not always match). We report that as dataset noise. We do not delete rows after seeing test scores.

## What we test

Same generator, temperature 0, same prompt, same top-k. Only retrieval changes.

| Condition | Retrieval |
|---|---|
| F0 | No context. Closed-book floor |
| A | Vector search over unique context chunks |
| B | Graph only: material, property, value |
| C | A and B merged into one prompt |

Hypothesis for this dataset: C should help Entity Lookup and Property Identification more than Numeric Lookup, because one paragraph often names several materials and several numbers. Numeric Lookup can already be answered from one retrieved sentence. State the result either way.

Exact match on the gold span is the primary score, because the answers are short (`765 MPa`, `Ti-6Al-4V`). A separate-family judge is not required for exact match. RAGAS stays optional and still needs a judge model different from the generator.

## Scale for the first code

Do not embed or extract all 202,068 rows on the trial Cohere key.

1. Download the validation split only.
2. Deduplicate contexts.
3. Pilot on **200 questions**, stratified across the three `qa_type` values, hashed from `id` so the sample can be repeated.
4. Keep that 200 frozen as the pilot. Do not grow it until A runs and the cost of one pass is known.
5. The authors’ train split is not used for prompt tuning.

Graph triples for the pilot are taken from those unique contexts, not from the whole corpus. Schema: `Material`, `Property`, `Value`, with relations `has_property` and `has_value`. One gleaning pass. Store them in a local JSON file first. Postgres comes after the pilot if the file is awkward.

## Coding order (not started)

| Step | Output |
|---|---|
| 1 | `data/README.md` entry: source, licence, date, who downloaded it. Raw file gitignored |
| 2 | Loader: validation rows to our JSONL, with `qa_type` kept |
| 3 | Unique-context index and Cohere embeddings, cached |
| 4 | Condition A on the 200-question pilot |
| 5 | Triple extraction and conditions B and C on the same 200 |
| 6 | One results table: exact match by `qa_type` for A, B, and C |

Chapter 10 questions under `data/benchmarks/b1/` stay as a draft demo. They are not this benchmark.

## What this does not claim

- We did not reproduce ManuRAG4.
- We did not use Groover’s solutions.
- Diagram parsing and human correction stay on Benchmark 2.
