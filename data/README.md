# Data

## Corpus (local only)

| Item | Value |
|---|---|
| Work | Mikell P. Groover, *Fundamentals of Modern Manufacturing: Materials, Processes, and Systems*, 4th edition, John Wiley & Sons, 2010 |
| Matches | ManuRAG reference for the retrieval corpus (arXiv 2601.15434, ref. [49]) |
| Pilot span | Chapter 10, Fundamentals of Metal Casting (PDF pages 219–233, body text only) |
| Licence | All rights reserved. The PDF stays in this folder or `data/raw/` and is gitignored. Do not commit it. |

## MechQA

| Item | Value |
|---|---|
| Source | https://huggingface.co/datasets/mz516/MechQA-dataset |
| Paper | Zhang and Cole, Journal of Chemical Information and Modeling, 2026 |
| Split used | validation (20,346 rows). The train split is not used |
| Pilot | 200 rows chosen in `src/mechqa_pilot.py` from `configs/mechqa_pilot.json` |
| Licence | Unverified. The Hugging Face card had no licence field on 2026-10-13. Raw rows stay in `data/processed/mechqa/` and are gitignored |
| Obtained | 2026-10-13, Krishna, via `datasets.load_dataset` |

## Questions

`benchmarks/b1/MathQ.jsonl`, `MCQ.jsonl`, and `RQ.jsonl` are original Chapter 10 questions for this project. They are not Groover's end-of-chapter quiz and not the ManuRAG 1,515-pair set. That set comes from the instructor solutions and was not found on arXiv, Springer, GitHub, Hugging Face, or Zenodo (checked 2026-10-11).

Topic for this chapter is `processes`. `split` is `dev` when `sha256(id) % 10 < 3`, otherwise `test`. Every row is `status: draft` until a second reviewer marks it `verified`. The test split is not frozen. Rebuild with `py -3 src/build_b1_ch10_questions.py`.
