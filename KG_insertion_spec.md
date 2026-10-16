# Where the Knowledge Graph Attaches to ManuRAG4 — Diagram Modification Spec

## Reference: the original ManuRAG4 diagram (base paper figure)

```
Manufacturing Documents → Multi-modal Data Extraction → [Formulas | Titles & Paragraphs | Figures | Tables]
    → Textual Data / Visual Data → transformed into Descriptions → Embedded
    → Text Vector Database → Calculating Sim(q,v) and Ranking (with Q)
    → Top@K Text → LLM (with P) → A_LLM
```

This is a **single-path pipeline**: everything gets embedded into one vector store, and retrieval is pure similarity ranking. Your contribution branches a second path off this pipeline and merges it back in before the LLM step.

---

## Exact insertion points (two new branches)

### Branch 1 — insert immediately after "Multi-modal Data Extraction"

Right where the original diagram splits into `Textual Data` / `Visual Data` boxes, add a **parallel** branch (draw it below or above the existing text/visual split, same vertical level, clearly forking from the same point):

```
Multi-modal Data Extraction
    ├──> [existing path] Textual Data / Visual Data → Descriptions → Embedded → Text Vector Database
    └──> [NEW path] Entity & Relation Extraction (LLM, schema-constrained)
              ↓
         Entity Resolution (dedupe/merge against existing nodes)
              ↓
         Knowledge Graph Store (nodes + edges + confidence weight)
              ↓
         HITL Verification Queue (low-confidence edges flagged for expert review)
```

**Label this new branch box clearly as "Knowledge Graph Construction"** — visually it should look like a sibling process to the existing "Embedded → Text Vector Database" path, not a sub-step of it. Both branches consume the same extracted content (Textual Data AND Visual Data/Figures — this is important, your graph branch pulls from *both*, including the P&ID/Figures box, which the original diagram's vector path also uses but your graph path uses more deliberately for structural relationships).

### Branch 2 — insert immediately after the "Q" (query) box, in parallel with "Calculating Sim(q,v) and Ranking"

The original diagram feeds `Q` only into the similarity/ranking oval. Add a second arrow from `Q` going down/below into a new parallel process:

```
Q (query)
    ├──> [existing] Calculating Sim(q,v) and Ranking → Top@K Text
    └──> [NEW] Query Entity Extraction → Entity Linking (match to graph nodes)
              ↓
         Graph Traversal (N-hop or shortest-path between linked entities)
              ↓
         Retrieved Subgraph (Top@K Graph)
```

### Merge point — before the LLM box

The original diagram feeds only `Top@K Text` into the `LLM` box (alongside `P`, the prompt). Change this to show **two inputs converging**:

```
Top@K Text ──┐
             ├──> LLM (with P) → A_LLM
Top@K Graph ─┘
```

Draw both arrows entering the LLM box from the left, same as the original single arrow — just show two labeled arrows merging instead of one.

---

## Summary of new boxes to add (for your slide legend / box list)

| New Box | Sits Between | Purpose |
|---|---|---|
| Entity & Relation Extraction | Multi-modal Data Extraction → KG store | LLM extracts (subject, relation, object) triples from text + figures |
| Entity Resolution | Extraction → KG store | Deduplicates/merges entities across documents (e.g., "impeller" mentioned in two manuals → one node) |
| Knowledge Graph Store | Resolution → HITL queue | Stores nodes, edges, and confidence weight/metadata |
| HITL Verification Queue | KG store → (feedback loop back into KG store) | Expert reviews/corrects low-confidence edges |
| Query Entity Extraction | Q → Entity Linking | Same extraction model applied to the incoming query |
| Entity Linking | Query extraction → Graph Traversal | Matches query entities to existing graph nodes |
| Graph Traversal | Entity Linking → Top@K Graph | Walks the graph (shortest-path or N-hop) to retrieve a connected subgraph |
| Top@K Graph | Traversal → LLM | Serialized subgraph triples, parallel to Top@K Text |

---

## What data trains/builds this (be precise: this is knowledge-base construction, not model fine-tuning)

Nothing in this pipeline involves training a neural network from scratch or fine-tuning an LLM — Gemini and Cohere are used as-is, off-the-shelf. What actually gets "built" from your data is the **knowledge graph itself** (the set of nodes and edges), plus your **evaluation benchmark**. Two separate things:

1. **Knowledge graph construction corpus** — the same heterogeneous documents already feeding your vector pipeline: centrifugal pump manuals, maintenance logs, spec sheets, and P&IDs (scanned/legacy, parsed via Gemini Vision). Every document that goes through "Multi-modal Data Extraction" also feeds the new Entity & Relation Extraction branch — same source documents, two parallel uses.
2. **Evaluation dataset** — a separate, smaller QA benchmark you construct yourself (~100-150 pairs, following the paper's MathQ/MCQ/RQ structure but adding a multi-hop/causal category), used only to measure factual correctness before/after adding the graph — not used to build the graph itself.

---

## Algorithms used (name these explicitly on your slide/thesis)

- **Entity/Relation Extraction**: LLM-based schema-constrained extraction (Gemini, structured JSON output mode) with a **gleaning pass** (a documented technique from Microsoft's GraphRAG methodology — a follow-up prompt asking the model to catch anything missed in the first pass), rather than classical BERT-based NER, since it needs no labeled training data and generalizes to pump-domain vocabulary directly.
- **Entity Resolution**: exact-match/alias-table lookup for equipment IDs and model numbers, falling back to **cosine similarity over entity embeddings** with a threshold for fuzzy name matches (e.g., "the impeller" vs. "Impeller Assembly #4").
- **Query Classification / Routing**: lightweight LLM few-shot classification (or keyword heuristics as a cheaper first pass) deciding vector-only vs. graph vs. hybrid retrieval per incoming query.
- **Entity Linking**: same extraction model applied to the query, matched against existing graph nodes (exact match first, embedding similarity fallback).
- **Graph Traversal**: **shortest-path search** when the query names two linked entities (e.g., "how are X and Y related"); **N-hop neighborhood traversal** when only one entity is named and the question is exploratory ("what could cause X").
- **Retrieval fusion**: results from both paths (Top@K Text + Top@K Graph) are simply concatenated into the LLM's context — no learned re-ranking model, keeping this a defensible, explainable design choice for an M.Tech-scale system rather than an added ML component you'd need to separately validate.
