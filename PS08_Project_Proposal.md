# Project Proposal

## Title

**GraphRAG-Verify: A Multimodal Knowledge-Graph-Augmented Retrieval System with Human-in-the-Loop Verification for Industrial Equipment Fault Diagnosis and Maintenance Documentation (Centrifugal Pump Domain)**

*(Working short title: GraphRAG-Verify for Industrial Maintenance QA)*

---

## 1. Domain of the Project

**Applied AI for Industrial Manufacturing / Intelligent Manufacturing Systems**, specifically at the intersection of:
- Multi-modal Information Retrieval and Retrieval-Augmented Generation (RAG)
- Knowledge Graph construction and graph-based reasoning
- Human-in-the-Loop (HITL) AI systems for high-stakes domains
- Computer vision for engineering diagram (P&ID) interpretation

Sub-domain: **Question Answering and Fault Diagnosis Support Systems for Centrifugal Pump Equipment**, using heterogeneous industrial documentation (manuals, maintenance logs, P&IDs, spec sheets) as the knowledge source.

---

## 2. Background and Problem Statement

### i) Main Topic and Exact Gap in Current Research

Industrial equipment documentation — manuals, maintenance logs, engineering schematics (P&IDs), spec tables — is heterogeneous, technical, and scattered across formats that require different processing pipelines to interpret correctly. Recent work has begun applying Retrieval-Augmented Generation (RAG) to this problem to let engineers query documentation in natural language instead of manually searching PDFs.

However, current state-of-the-art multi-modal RAG systems for this domain (notably **ManuRAG**, *Journal of Intelligent Manufacturing*, 2026) retrieve information as independent chunks ranked by embedding similarity. This works for single-fact lookup but breaks down on:

- **Multi-hop causal questions** (e.g., "why did pump-14 fail last Tuesday?") where the answer requires chaining facts across multiple documents — ManuRAG's own reported results show this weakness directly: factual correctness dropped to **45.75% on review/reasoning-type questions**, its lowest score across all evaluated categories, versus 87.6% on simpler multiple-choice questions.
- **Engineering diagrams and P&IDs specifically** — ManuRAG's future-work section explicitly limits itself to text, general figures, and tables, and does not address structured engineering schematics.
- **No verification or correction mechanism** — a wrong answer cannot be traced to a specific faulty fact or corrected in a way that improves future queries; the same error will recur indefinitely.

Complementary work (**ChatP&ID**, *AIChE Journal*, 2026) demonstrates that converting P&ID diagrams into a structured knowledge graph — rather than treating them as generic images — improves QA accuracy by 18% and cuts LLM token cost by 85% versus raw image ingestion. However, ChatP&ID operates only on standardized "smart" (DEXPI-format) P&IDs, not the scanned/legacy diagrams typical of real industrial maintenance archives, and includes no human verification loop.

**The exact gap**: no existing published system combines (a) multi-modal RAG over heterogeneous industrial documents, (b) a knowledge graph layer built from *both* text and vision-parsed engineering diagrams (including non-standardized, scanned P&IDs), and (c) an expert-in-the-loop verification and correction mechanism that measurably improves factual correctness over time.

### ii) Primary Goal / Main Research Question

**Primary goal**: Design and evaluate a knowledge-graph-augmented, multi-modal RAG system for centrifugal pump equipment documentation that improves factual correctness on multi-hop, causal, and relational maintenance queries beyond current text/vector-only baselines, while providing traceable, expert-correctable answers.

**Main research question**: *Does augmenting multi-modal RAG with a knowledge graph constructed from both textual documentation and vision-parsed engineering diagrams, combined with human-in-the-loop verification, significantly improve factual correctness on multi-hop industrial fault-diagnosis questions compared to vector-retrieval-only baselines?*

**Sub-questions**:
1. Does routing multi-hop/causal queries through graph traversal (vs. pure vector similarity) improve factual correctness and context recall, measured on a pump-domain QA benchmark?
2. Does incorporating vision-parsed P&ID structure into the graph (vs. text-only graph construction) improve answer accuracy for diagram-dependent questions?
3. Does HITL correction of graph edges measurably improve factual correctness on repeated/similar queries over successive correction cycles?

---

## 3. Limitations of Current Approaches, Motivation, and Societal Impact

### Why this needs solving

- **Safety-critical consequences of wrong answers**: unlike general-purpose QA, an incorrect diagnosis for equipment failure (e.g., misattributing a cavitation issue to the wrong cause) can lead to improper maintenance actions, extended downtime, or — in pressurized/rotating equipment like centrifugal pumps — safety incidents for maintenance personnel.
- **No traceability in current systems**: when a vector-RAG-based system gives a wrong answer, there's no structural way to identify *which* retrieved fact caused the error or to prevent it from recurring. This makes such systems unsuitable for high-stakes industrial deployment as-is, despite strong benchmark performance on simpler question types.
- **Tacit knowledge loss**: experienced technicians hold undocumented diagnostic knowledge that is never captured in formal manuals; current RAG systems only retrieve from what's already written down, missing this entirely.
- **Fragmented documentation formats**: real industrial sites hold decades of legacy documentation in inconsistent formats (scanned P&IDs, handwritten logs, mixed-language manuals), which current published systems (ManuRAG, ChatP&ID) do not fully address together.

### Societal / Industrial Impact

- **Reduced unplanned downtime**: faster, more accurate root-cause diagnosis directly reduces production loss in manufacturing plants relying on centrifugal pumps (chemical processing, water treatment, oil & gas, power generation).
- **Worker safety**: more reliable, traceable diagnostic support reduces risk of maintenance personnel acting on incorrect fault attribution in pressurized/rotating machinery contexts.
- **Knowledge retention**: capturing tacit expert knowledge into a structured, verifiable graph helps preserve institutional knowledge as experienced technicians retire — a recognized problem in manufacturing workforce transitions.
- **Broader applicability**: the same GraphRAG + HITL architecture generalizes to other safety-critical technical domains (aviation maintenance, medical device servicing, power grid infrastructure) beyond centrifugal pumps specifically.

---

## 4. Base Papers (Minimum 2, Reputed Journal/Conference)

| # | Title | Venue | Role in Your Work |
|---|---|---|---|
| 1 | **ManuRAG: Multi-modal Retrieval Augmented Generation for Manufacturing Question Answering** | *Journal of Intelligent Manufacturing* (Springer), 2026 — DOI: 10.1007/s10845-026-02800-y | **Core base paper.** Provides the multi-modal RAG backbone (text + image + table + formula retrieval, ManuRAG4 architecture) that you extend with a knowledge graph layer and HITL verification. |
| 2 | **GraphRAG for Engineering Diagrams: ChatP&ID Enables LLM Interaction with P&IDs** | *AIChE Journal* (Wiley), 2026 — DOI: 10.1002/aic.70540 | **Supporting base paper.** First published application of GraphRAG to P&IDs; provides the methodology and benchmark for graph-based reasoning over engineering diagrams, which you extend to unstructured/scanned P&IDs via vision-LLM parsing. |
| 3 *(optional third)* | **SOPRAG: Multi-view Graph Experts Retrieval for Industrial Standard Operating Procedures** | arXiv, 2026 (preprint; check for conference/journal placement before final submission) | Supporting reference for structure-aware graph retrieval over procedural industrial documents. |
| 4 *(optional third)* | **Knowledge graph validation by integrating LLMs and human-in-the-loop** | *Information Processing & Management* (Elsevier), 2025 | Supporting reference for the HITL correction/validation methodology and its measured effect on graph quality. |

*Recommendation: cite papers 1 and 2 as your two required base papers; use 3 and 4 as supporting related-work citations for the graph-construction and HITL-methodology sections respectively.*

---

## 5. Tools and Technology Identified

**Already in use (carried over from your PS-08 hackathon build):**
- **Backend**: FastAPI (Python)
- **LLM / Vision**: Cohere (text generation + embeddings), Gemini Vision (image/P&ID parsing)
- **Database**: PostgreSQL / Supabase with `pgvector` extension for vector storage
- **Frontend**: React + Vite
- **Object storage**: S3 (for raw extracted images/diagrams, referenced via UUID metadata)

**To be added for the knowledge graph + HITL extension:**
- **Graph storage**: Neo4j (dedicated graph DB, cleaner Cypher-based traversal) *or* adjacency tables within existing PostgreSQL/Supabase (lower infrastructure overhead — recommended given your existing stack)
- **Graph visualization**: React Flow (already used for your Knowledge Graph Explorer feature)
- **Orchestration**: LangChain / LangGraph for the retrieval-routing logic (query classification → vector vs. graph vs. hybrid retrieval)
- **Entity/relation extraction**: Gemini (schema-constrained extraction prompts for entity types: Equipment, Component, FailureMode, Cause, CorrectiveAction)
- **Evaluation**: RAGAS framework (factual correctness, context precision/recall — same metrics used in the ManuRAG base paper, for direct comparability)
- **HITL interface**: your existing HITL Verification Dashboard, extended to support graph-edge-level correction (not just document-level flags)

---

## Notes for refinement before submission

1. Confirm current publication status of SOPRAG (arXiv preprint as of this writing) before citing it as a "reputed" venue paper — check for conference/journal acceptance.
2. Your evaluation chapter should mirror the ManuRAG paper's benchmark structure (MathQ/MCQ/RQ-style categories, ~100-150 QA pairs is a defensible M.Tech-scale dataset) with an added multi-hop/causal category specific to your contribution.
3. Consider narrowing "societal impact" language to what you can actually demonstrate in your evaluation (e.g., downtime-reduction claims should be framed as *potential* impact unless you run a field/simulation study).
