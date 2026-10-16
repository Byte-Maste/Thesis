# PLAN.md

Single source of truth for what this project is, what we are trying to prove, what is realistically possible, and what to do next. Read this before touching code or the paper. If a decision changes, update this file in the same change.

Last updated: 2026-10-13

---

## 1. Project snapshot

| Item | Value |
|---|---|
| Working title | A Multimodal Knowledge Graph for Industrial Equipment Fault Diagnosis and Maintenance Documentation |
| Student | Krishna (M.Tech Integrated Programme, CSE, Sri Sairam Engineering College) |
| Guide | Ms. V Saranya |
| Course | 20CJPJ901 Project Phase 1 |
| Output | A research paper (IEEE format), a working demo, and a reproducible evaluation |
| Core idea | Extend a multi-modal RAG baseline (ManuRAG4-style) with a knowledge graph, hybrid retrieval routing, and a human-in-the-loop (HITL) correction layer |
| Priority order | Public MechQA benchmark first (see MECHQA.md). ManuRAG stays the method baseline, not the question file. Benchmark 2 (pump domain) remains later |

Existing artifacts (outside the repo, keep in sync):
- Research paper draft (.docx): intro, 22-reference literature survey, research gap, methodology, tech stack. Dataset/Algorithm sections still to be added.
- Thesis deck (.pptx) built on the Sairam template.
- KG insertion spec (where the graph attaches to the ManuRAG4 diagram).
- Eraser architecture diagram.

---

## 2. Problem and gap (short form)

Vector-only multi-modal RAG retrieves independent chunks by embedding similarity. That works for single-fact questions and degrades on questions that need facts chained across passages. In the base paper (ManuRAG), the best variant (ManuRAG4) reached 62.03% factual correctness on MathQ, 87.61% on MCQ and only 45.75% on RQ (review-style questions), its lowest of the three.

Prior work covers pieces of the answer but not the combination:
- ManuRAG: multi-modal RAG for manufacturing, no knowledge graph, no human correction.
- GraphRAG (Edge et al.): graph retrieval, general-domain, text-only.
- ChatP&ID: graph from P&IDs, but only structured DEXPI diagrams, no HITL.
- KG+LLM fault diagnosis (aviation, CNC): text-built graphs, no vision-parsed diagrams, no integrated HITL loop.

Claimed gap: no published system combines (a) multi-modal RAG, (b) a graph built from text and vision-parsed diagrams, (c) vector/graph routing per query, and (d) edge-level expert correction that is measured to improve correctness. Benchmark 1 tests (a)+(c) and part of the graph claim. Benchmark 2 is needed for (b) and (d).

---

## 3. Goals, hypotheses and decision rules

Hypotheses are written before running anything. We report results whatever they are.

| ID | Hypothesis | Benchmark | Evidence that supports it |
|---|---|---|---|
| H1 | Hybrid retrieval (C) improves factual correctness over the vector-only baseline (A) on RQ (review/multi-hop) questions | B1 | Paired bootstrap 95% CI for the difference excludes 0 |
| H2 | Hybrid does not hurt MCQ (no regression) | B1 | Difference CI includes 0 or is positive |
| H3 | Hybrid gives little or no gain on MathQ (calculation questions) | B1 | Report as measured, no claim of improvement |
| H4 | Gains are larger on multi-hop causal pump questions than on single-fact ones | B2 | Interaction visible across question categories |
| H5 | Parsing diagrams into the graph (D) beats text-only graph (C) on diagram-dependent questions | B2 | Paired CI excludes 0 |
| H6 | Correctness rises over successive HITL correction rounds (E) | B2 | Monotone or clearly positive trend across 3 rounds with CIs |

Proposed minimum effect of interest: +3 percentage points on factual correctness. Confirm with the guide before B1 results are seen.

Null results are acceptable outcomes. A paper that says "the graph helps on X, not on Y, because Z" is publishable. A paper that tuned on the test set is not.

---

## 4. What is possible and what is not

Realistic with the time and tools we have:
- Reimplementing a ManuRAG4-style baseline (structured extraction, figure/table descriptions, text embeddings, similarity retrieval) and comparing hybrid retrieval against it, same LLM and settings for every condition.
- Building a knowledge graph from one textbook using schema-constrained LLM extraction and entity resolution, and measuring whether graph retrieval changes answer correctness.
- A side-by-side demo (vector-only vs hybrid) with the graph path visualised.

Possible but uncertain (do not promise):
- A statistically clear gain on RQ. Textbook review questions are often answerable from one section, so the graph may add little. In the base paper, plain RAG (45.51) and ManuRAG4 (45.75) were nearly equal on RQ, which also suggests the metric or question type limits gains.
- Matching the base paper's absolute numbers. We use different models (Cohere/Gemini instead of GPT-4o/Ada v2/CLIP). Only the qualitative ordering of methods is comparable.
- Getting the base paper's exact QA set (see blockers).

Not possible with Benchmark 1 alone (needs Benchmark 2):
- Any claim about P&ID or scanned-diagram parsing.
- Any claim about pump fault diagnosis or maintenance.
- Any claim that HITL correction improves a pump-domain graph.

Not claimable at all without more work:
- Real-world downtime or safety impact. Frame it as potential impact only.

---

## 5. Architecture (target)

```
Documents -> Multi-modal extraction (layout, OCR, tables, formulas, figures)
   |-> Vector path:  text + figure/table descriptions -> embeddings -> pgvector (HNSW) -> Top@K text
   |-> Graph path:   schema-constrained entity/relation extraction (+ gleaning pass)
                     -> entity resolution -> graph store (nodes, edges, confidence, provenance)
                     -> HITL queue for low-confidence edges (Benchmark 2)

Query -> classifier (single-fact / conceptual / multi-hop)
   |-> vector search
   |-> entity extraction -> entity linking -> traversal (shortest path or N-hop) -> Top@K graph
Merge Top@K text + Top@K graph -> LLM (prompt P) -> answer with provenance
```

Stack (decided): FastAPI, Cohere (generation, embeddings), Gemini (vision/diagram parsing, extraction), PostgreSQL/Supabase + pgvector, React + Vite + React Flow, S3 for images, LangChain/LangGraph for routing, RAGAS for metrics.

Stack (undecided): graph store, Neo4j vs Postgres adjacency tables. Default to Postgres adjacency tables for B1 to avoid a new service; revisit if traversal queries get awkward.

---

## 6. Benchmarks

### Benchmark 1 (priority): manufacturing textbook QA, ManuRAG-style

- Source of the base paper's questions: a manufacturing textbook (Fundamentals of Modern Manufacturing). The paper describes its content as materials, processes, systems and electronics technologies. Map our topic list to the table of contents of the edition we actually have.
- Question sets in the base paper: MathQ 309, MCQ 471, RQ 735 (1,515 total), built from the textbook's official solutions.
- Metrics in the base paper (via RAGAS): factual correctness, semantic similarity, ROUGE (MCQ), context precision@K, context recall.
- Base paper settings for reference: chunk size 600, overlap 100, k=1, tuned on a 5% sample.
- Base paper reference numbers, for context only, not a target (factual correctness %):

| Method | MathQ | MCQ | RQ |
|---|---|---|---|
| RAG | 59.51 | 85.22 | 45.51 |
| RAGhq | 59.48 | 86.38 | 45.64 |
| ManuRAG4 | 62.03 | 87.61 | 45.75 |

Two possible routes, decided by blocker B-1 below:
- Route 1: the authors share their QA set. Use it as is, split dev/test, cite and credit.
- Route 2: not shared. Build our own textbook QA set from a textbook we legally own, writing the questions ourselves (not copying the solutions manual). This is a ManuRAG-style benchmark, not their benchmark. Say so plainly in the paper.

### Benchmark 2 (after B1): centrifugal pump domain

- Corpus: 8 to 15 documents we are allowed to use (open O&M manuals, a few P&IDs, spec sheets) plus maintenance logs we write and have a domain person check. Record every source and licence.
- Size: 60 to 80 questions.
- Categories: single-fact, relational, multi-hop causal, diagram-dependent.
- Used for H4, H5, H6.

---

## 7. Experimental conditions

Same LLM, temperature 0, same prompt template, same top-k for every condition. Only retrieval differs.

| Cond. | Description | Benchmark |
|---|---|---|
| F0 | Closed-book LLM with chain-of-thought (floor) | B1, B2 |
| F1 | Plain RAG over extracted text (floor, mirrors base paper RAG) | B1, B2 |
| A | ManuRAG4-style vector-only baseline (main baseline) | B1, B2 |
| B | Graph-only retrieval | B1, B2 |
| C | Hybrid with query routing | B1, B2 |
| D | C plus diagram content parsed into the graph | B2 |
| E | D plus HITL-corrected edges (3 rounds) | B2 |

Sanity check for the baseline: A should rank at or above F1 on at least MCQ and RQ, as in the base paper. If not, debug ingestion before building anything on top.

---

## 8. Measurement and statistics

- Factual correctness, semantic similarity, context precision/recall via RAGAS. ROUGE for MCQ as in the base paper.
- Graph path accuracy: did traversal reach the gold evidence chain (B2, and B1 where evidence is known).
- Triple quality: hand-label about 200 extracted triples, report precision and recall.
- Cost: tokens, latency, and LLM calls per query and per ingestion.
- Judge model must be a different family from the generator. Human-check 20 to 30% of judged items and report agreement.
- Each condition run 3 to 5 times. Report mean and std. Use paired bootstrap for differences. Report confidence intervals, not just p-values.
- Split: 30% dev, 70% test, assigned deterministically by hashing the question id. Tune only on dev. The test set is frozen once the first test run starts.

---

## 9. Benchmark 1 work breakdown (topics)

Each topic has a deliverable and an acceptance check. Do them roughly in this order.

| # | Topic | Deliverable | Done when |
|---|---|---|---|
| T1 | Data access and licensing | Written decision on Route 1 vs Route 2; textbook edition and access confirmed; source/licence table | Route chosen, nothing copyrighted is committed to the repo |
| T2 | Corpus ingestion | Pipeline from textbook PDF to text, tables (LaTeX), formulas, figures with UUIDs | One full chapter ingested and spot-checked; failure cases listed |
| T3 | Benchmark QA set | MathQ / MCQ / RQ files in the schema from CONTRIBUTING.md, with dev/test split | Counts per category and topic reported; test split frozen |
| T4 | Baseline reproduction (F0, F1, A) | Runnable baselines with a config file | Qualitative ordering matches the base paper, or the discrepancy is explained |
| T5 | KG schema for manufacturing | Entity and relation vocabulary (for example Process, Material, Parameter, Property, Equipment) | Schema reviewed on 20 sample chunks; no unmapped frequent concept |
| T6 | KG construction | Extraction with gleaning pass, entity resolution, graph store | Pilot on one chapter: extraction cost measured, triple precision/recall on a hand-labelled sample |
| T7 | Graph and hybrid retrieval (B, C) | Entity linking, traversal, query classifier, merge step | Retrieval returns provenance for each answer; router accuracy measured on dev |
| T8 | Evaluation harness | One command runs all conditions and writes a results table | Reproducible from config and seed; all LLM calls cached and logged |
| T9 | Ablations and analysis | Results by category and topic, error analysis, CIs | H1 to H3 answered with CIs; failure taxonomy written |
| T10 | Reporting | Results and discussion sections in the paper; figures | Draft reviewed by the guide |

Textbook subject areas to balance across in T3 and T9 (confirm chapter mapping from the actual table of contents): materials, processes, manufacturing systems, electronics technologies.

Go/no-go checkpoint after T9: if H1 shows no gain and the error analysis shows the graph is not the bottleneck, decide with the guide whether to refocus the paper on Benchmark 2 where the graph should matter more.

---

## 10. Timeline (relative weeks, adjust to the academic calendar)

| Week | Focus |
|---|---|
| 1 | T1, T2 pilot, contact ManuRAG authors, decide route |
| 2 | T3, T4, T8 skeleton; baseline running on dev |
| 3 | T5, T6 on a pilot chapter; extrapolate full-extraction cost before running everything |
| 4 | T7, T9 on dev, then the single frozen test run; go/no-go |
| 5 to 6 | Benchmark 2: corpus, 60 to 80 questions, diagram parsing, HITL rounds |
| 7 | Paper: dataset, setup, results, discussion, limitations; fill missing reference authors |
| 8 | Buffer, demo polish, plagiarism check, guide sign-off, release |

---

## 11. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Authors do not share the QA set | Cannot reuse their benchmark | Route 2; state clearly it is ManuRAG-style |
| Textbook questions are single-section, so no gain from the graph | H1 fails on B1 | Report honestly; shift weight to B2; analyse which questions needed multiple passages |
| Extraction cost on a full textbook is high | Budget or time overrun | Pilot one chapter first; cache calls; extract once per schema version |
| Schema drift (relations named inconsistently) | Fragmented graph, weak traversal | Fixed vocabulary, canonicalisation step, resolution thresholds tuned on dev only |
| LLM judge bias or noise | Misleading metrics | Different-family judge, human spot-check, report agreement |
| Test-set leakage | Invalid claims | Hash split, freeze test, log every run, no prompt edits after first test run |
| Title and scope mismatch (pump fault diagnosis vs textbook benchmark) | Reviewer objection | Present B1 as general manufacturing QA and B2 as the domain study; decide title (see section 12) |
| Different models than the base paper | Numbers not comparable | Re-run the baseline ourselves; only claim relative gains |

---

## 12. Open decisions and blockers

| ID | Item | Owner | Status |
|---|---|---|---|
| B-1 | Is the ManuRAG QA set released? | Krishna | Closed for the next experiment. No public file. Coding target is MechQA (see MECHQA.md). |
| B-2 | Which textbook edition do we have access to, and can we use it legally? | Krishna | Open |
| D-1 | Keep causal QA in scope, or maintenance-only? Affects title and B2 question categories | Krishna + guide | Open |
| D-2 | Graph store: Neo4j or Postgres adjacency tables | Krishna | Default Postgres, revisit after T6 |
| D-3 | Judge model for RAGAS (must differ from generator) | Krishna | Open |
| D-4 | Minimum effect of interest (+3 pp proposed) | Guide | Open |
| P-1 | Seven references in the paper draft still show "Authors," placeholders (ChatP&ID, SOPRAG, KG validation with HITL, KG-driven aviation fault diagnosis, CNC fault diagnosis, fault diagnosis review, LLM-empowered KG construction survey). Fill from the publisher pages | Krishna | Open |
| P-2 | Paper draft needs Dataset and Algorithm sections | Krishna | Open |
| P-3 | Verify SOPRAG publication status before citing it as a reputed-venue paper | Krishna | Open |

---

## 13. Definition of done

Benchmark 1 is done when: baselines reproduce the base paper's qualitative ordering, A/B/C are evaluated on the frozen test split with CIs, H1 to H3 are answered, and the error analysis is written, all reproducible from a config and seed.

The project is done when: Benchmark 2 results (H4 to H6) are in, the paper has all sections and verified references, the side-by-side demo runs, the code and non-restricted data are released with licences respected, and the guide has signed off.

---

## 14. Key references

- ManuRAG (Li, Dong, Ameri, Zhang), Journal of Intelligent Manufacturing, 2026. Core base paper. Open preprint: arXiv 2601.15434 (CC BY 4.0).
- ChatP&ID, AIChE Journal, 2026. Supporting base paper (GraphRAG on P&IDs).
- GraphRAG (Edge et al., 2024), RAG (Lewis et al., 2020), ReAct (Yao et al., 2023), HNSW (Malkov and Yashunin, 2020), LayoutLMv3 (Huang et al., 2022).
- KG+LLM fault diagnosis: Liu, Qian, Zhao, Tao (IEEE TII, 2024) and related aviation/CNC work.
- Full list: see the paper draft's reference section.
