# ManuRAG: Multi-modal Retrieval Augmented Generation for Manufacturing Question Answering

**Authors:** Yunqing Li, Zihan Dong (co-first authors), Farhad Ameri, Jianbang Zhang
**Affiliations:** School of Manufacturing Systems and Networks, Arizona State University; Dept. of Mechanical and Aerospace Engineering, NC State University; AI Lab, Lenovo

**Source (open access, CC BY 4.0):** https://arxiv.org/abs/2601.15434
**Journal version (Springer, paywalled):** *Journal of Intelligent Manufacturing* (2026), https://doi.org/10.1007/s10845-026-02800-y — cite this DOI in your thesis; this document is the freely available early/preprint version of the same work, released under a CC BY 4.0 license.

---

## Abstract

The evolution of digital manufacturing necessitates intelligent Question Answering (QA) systems that can seamlessly integrate and analyze complex multi-modal data, such as text, images, formulas, and tables. Conventional Retrieval-Augmented Generation (RAG) methods often fall short in handling this complexity, resulting in subpar performance. We introduce ManuRAG, a novel multi-modal RAG framework designed for manufacturing question answering (MQA), incorporating specialized techniques to improve answer accuracy, reliability, and interpretability. To benchmark performance, we provide a dataset of 1,515 QA pairs spanning mathematical, multiple-choice, and review questions in manufacturing principles and practices. Experimental results demonstrate that ManuRAG4 significantly outperforms existing methods across all datasets. Furthermore, ManuRAG's adaptable design makes it applicable to other domains, including law, healthcare, and finance, establishing it as a versatile tool for domain-specific QA.

**Keywords:** Retrieval-Augmented Generation, Multi-modality, Manufacturing Question Answering, Information Extraction

---

## 1. Introduction

### 1.1 Background and Motivation

In the transition to Industry 5.0, QA systems play a crucial role in leveraging big data in manufacturing. A QA system is a type of information retrieval system designed to automatically answer questions posed by users in natural language, using a combination of NLP, machine learning, and knowledge bases. Potential users of MQA systems include mechanical design engineers calculating precise tolerances, production engineers optimizing assembly processes, machine operators implementing temperature adjustments, quality assurance teams verifying dimensional accuracy, and research teams exploring advanced materials and manufacturing techniques.

### 1.2 Challenges

Manufacturing documents span a wide array of data types — text, images, formulas, CAD models, tables, sensor data, and videos. Text may contain operational guidelines or maintenance logs requiring NLP; images (defect photos, assembly-line snapshots) demand computer vision; formulas embedded in documentation need precise recognition to enable troubleshooting.

The adoption of MQA systems in industry remains early-stage. GPT-powered chatbots represent the closest analogs but lack the robust multi-modal retrieval and domain-specific reasoning needed for real MQA.

Traditional retrieval methods are typically limited to either text-based or image-based data, failing to capture the full context of multi-modal information. Example: an engineer asking "Among the following models, which one has a five-link suspension?" may need to search across older models stored as text, a PDF with drawings and specs, and CAD models or annotated images — manually sifting through these formats is slow and error-prone.

Key limiting factors: manufacturing data is diverse and technical, requiring specialized processing per type; textual data uses domain-specific terminology while visual data (figures, tables, slides) demands advanced interpretation tools most systems lack; and transforming text and image data into a unified, low-loss format remains difficult.

### 1.3 Objectives

To overcome these limitations, the authors introduce a multi-modal RAG (MMRAG) system tailored for MQA that integrates images, formulas, tables, and text to deliver deeper, contextually accurate answers.

**Main contributions:**
1. A comprehensive multi-modal QA system tailored to manufacturing, designed to identify operational bottlenecks, improve product design, and support data-driven decisions.
2. Design and evaluation of multiple QA system variants (traditional RAG and MMRAG), with insights extending to law, healthcare, and finance domains.
3. A novel approach to multi-modal indexing and retrieval using links embedded in textual data and alignment of text with images either before or after embedding.

---

## 2. Related Work

### 2.1 Question Answering Systems
QA systems have evolved from domain-specific expert systems to LLMs (GPT, BERT) that use deep learning to interpret queries. Multi-modal models have advanced visual QA (VQA) and QA over tabular+textual data. However, none of these are suited to manufacturing's technical complexity — MQA requires precise extraction and robust integration of diverse multi-modal data, beyond existing QA models' capabilities.

### 2.2 Information Extraction
Information extraction (IE) handles diverse formats (text, images, tables, multimedia). Layout detection models (R-CNN, LayoutLMv3) identify content regions; formula recognition relies on deep learning methods; OCR tools handle text across fonts/languages. In manufacturing, prior work has extracted knowledge from manufacturer websites (service discovery) and converted geometric CAD data into manufacturing insights — but no studies have focused on extracting information across the full range of multimedia sources in manufacturing documents, a research gap this paper addresses.

### 2.3 Prompt Engineering and RAG
LLMs perform well in general QA but struggle in manufacturing due to specialized terminology and hallucination risk. Prompt engineering techniques (Chain of Thought, Tree of Thought) improve multi-step reasoning. RAG grounds LLM outputs in external knowledge; tools like LlamaIndex and LangChain enable retrieval, while GraphRAG introduces graph-based retrieval for reasoning over interconnected data.

Multimodal RAG is an emerging extension integrating text, image, and other data types — it has shown applications in healthcare but **has not been tailored for the manufacturing domain** prior to this work. Multi-modal LLMs (Ovis, GPT-4o, Qwen) advance text+visual integration but are constrained by input token limits when processing large volumes of information — motivating the indexing/retrieval approach in MMRAG rather than raw ingestion.

---

## 3. Methodology

Traditional RAG systems are primarily designed for text, often overlooking real-world multi-modal information. ManuRAG extends RAG to incorporate multimodality for manufacturing documents. The underlying MLLM accepts both text and images, processing PDFs through a pipeline of object detection and text recognition models that categorizes documents into figures, images, formulas, and textual content.

**Four key stages:** multimodal data extraction → indexing → retrieval → answer generation.

### 3.1 Multi-modal Data Extraction

Directly using raw manufacturing PDFs in RAG is infeasible — their complex structure (images, tables, formulas, non-standard layouts) causes major information loss when naively converted to plain text. ManuRAG extracts and organizes multi-modal data using the **pdf-extract-kit** framework (built on MinerU, DocLayout-YOLO, UniMERNet, OpenDataLab).

- **3.1.1 Layout Detection** — Uses LayoutLMv3 to detect regions (images, tables, titles, text) and filter irrelevant components (page numbers, titles) that could hurt QA performance.
- **3.1.2 Formula Extraction** — Uses YOLOv8 to identify inline and block formulas with precise spatial locations (e.g., correctly isolating Young's modulus or Fick's first law equations from surrounding text).
- **3.1.3 Image and Table Extraction** — Tables are converted to LaTeX format using a converter model trained on the PubTabNet dataset for accurate, structured tabular extraction.
- **3.1.4 OCR** — Plain text extracted via Paddle-OCR (avoiding whole-page-as-single-input errors). Extracted content is stored with metadata: formulas in LaTeX, figures/tables as image files, text in markdown. Each visual element gets a UUID for consistent referencing.

### 3.2 Indexing

**3.2.1 Text Vector Database** — Text is chunked with overlap (chunk size *S*, overlap *O*): each chunk *Cᵢ* = (Tᵢ, αᵢ), where Tᵢ is textual content and αᵢ is the set of images referenced within it. Chunks are embedded via an LLM-based text embedding model: vCᵢ = Embed_Text(Cᵢ).

**3.2.2 Image Vector Database** — Visual data (figures, tables) is encoded into the *same* embedding space as text using a multi-modal embedding model (enabling cross-modal text-to-image / image-to-text retrieval): vIⱼ = Embed_MM(Iⱼ). Because multi-modal embedding models understand long/complex text less well than dedicated text embedders, some ManuRAG variants keep **separate** text and image vector databases to leverage the strengths of each.

### 3.3 Retrieval

Retrieval uses cosine similarity: Sim(q, v) = (q·v) / (‖q‖‖v‖)

- **3.3.1 Text retrieval** — Top-k text chunks retrieved by similarity to the query embedding in text space; the set of all images referenced within those chunks is also collected.
- **3.3.2 Image retrieval** — Query is separately encoded into the multi-modal embedding space; top-k images retrieved by similarity in that space.

### 3.4 Answer Generation

Two strategies:
- **3.4.1 Text-only** — LLM answers using only retrieved text chunks + prompt + question (no visual data). Efficient, but limited for multi-modal queries.
- **3.4.2 Multi-modal** — An MLLM answers using retrieved text chunks, retrieved images, images referenced within text, and the question together — incorporating visual context alongside text.

### 3.5 ManuRAG Variations

Four variants explore *when* text and image alignment happens (before embedding, in embedding space, or after embedding):

| Variant | Description |
|---|---|
| **ManuRAG1** | Separate text and image vector databases; answer generation via MLLM. |
| **ManuRAG2** | Simplifies ManuRAG3 — text-only indexing/retrieval, answers generated via LLM (no image DB). |
| **ManuRAG3** | Extends ManuRAG1 by prioritizing retrieval of images *linked within* retrieved text chunks. |
| **ManuRAG4** | Converts visual content (figures/tables) referenced in text into **descriptive text** via an MLLM, then indexes that description in the text vector DB; answers generated via LLM (or optionally MLLM). Aligns modalities *before* embedding — best-performing variant, though some visual detail can be lost in the text conversion. |

---

## 4. Experiments

### 4.1 Settings

**Baselines:** GPT-4o (direct), GPT-4o with Chain-of-Thought, RAG (raw extracted text), RAGhq (high-quality structured text using the Section 3.1 pipeline), and ManuRAG1–4. All models use GPT-4o as the underlying MLLM; Ada v2 for text embedding; CLIP for image embedding (where used); built on LlamaIndex. Source documents: the textbook *Fundamentals of Modern Manufacturing* (materials, processes, systems, electronics technologies). All runs used k=1, chunk size S=600, overlap O=100 (values tuned on a 5% sample), in Google Colab.

**Evaluation datasets** — 1,515 QA pairs from the official textbook solutions (excluded from the RAG retrieval corpus itself):
- **MathQ** (309 pairs) — mathematical QA requiring factual accuracy, often multi-modal (formulas, tables, figures).
- **MCQ** (471 pairs) — multiple-choice, some requiring multi-modal analysis.
- **RQ** (735 pairs) — review/short-answer QA testing conceptual understanding.

### 4.2 Evaluation Metrics (via RAGAS + GPT-4)
- **Factual Correctness** — F1 over decomposed claims (precision/recall via natural language inference against reference).
- **Semantic Similarity** — cross-encoder similarity score (0–1) between generated and reference answers.
- **ROUGE** (n=1) — n-gram overlap F1, used for MCQ.
- **Context Precision@K** — relevance of retrieved chunks, weighted by rank.
- **Context Recall** — proportion of ground-truth claims attributable to retrieved context.

### 4.3 Overall Performance

**ManuRAG4 consistently performs best across all three datasets.**

| Category | Model | Factual Correctness (%) | Semantic Similarity (%) |
|---|---|---|---|
| MathQ | GPT-4o | 49.91 | 87.03 |
| MathQ | GPT-4o (CoT) | 56.22 | 86.85 |
| MathQ | RAG | 59.51 | 87.66 |
| MathQ | RAGhq | 59.48 | 87.90 |
| MathQ | ManuRAG1 | 19.14 | 77.03 |
| MathQ | ManuRAG2 | 56.69 | 87.32 |
| MathQ | ManuRAG3 | 55.31 | 87.32 |
| MathQ | **ManuRAG4** | **62.03** | 87.82 |
| MCQ | GPT-4o | 6.99 | 77.60 |
| MCQ | GPT-4o (CoT) | 78.58 | 94.79 |
| MCQ | RAG | 85.22 | 96.52 |
| MCQ | RAGhq | 86.38 | 96.62 |
| MCQ | ManuRAG1 | 86.82 | 95.27 |
| MCQ | ManuRAG2 | 60.54 | 91.20 |
| MCQ | ManuRAG3 | 61.62 | 90.15 |
| MCQ | **ManuRAG4** | **87.61** | 96.82 |
| RQ | GPT-4o | 38.01 | 89.93 |
| RQ | GPT-4o (CoT) | 40.47 | 89.92 |
| RQ | RAG | 45.51 | 91.08 |
| RQ | RAGhq | 45.64 | 91.12 |
| RQ | ManuRAG1 | 45.34 | 90.97 |
| RQ | ManuRAG2 | 40.53 | 91.15 |
| RQ | ManuRAG3 | 39.10 | 91.13 |
| RQ | **ManuRAG4** | **45.75** | 91.00 |

**ROUGE scores (MCQ):** GPT-4o 10.35% · GPT-4o(CoT) 77.61% · RAG 86.10% · RAGhq 86.71% · ManuRAG1 81.19% · ManuRAG2 63.13% · ManuRAG3 58.88% · **ManuRAG4 86.77%**

**Key findings:**
- ManuRAG1 performs well on MCQ/RQ (via image links in text) but very poorly on MathQ — separate-database retrieval struggles with math reasoning.
- ManuRAG3 (more images retrieved) does *not* lead to better answers — more retrieved images ≠ better MQA.
- Chain-of-Thought reliably improves GPT-4o baseline performance.
- RAGhq beats plain RAG, confirming the value of the structured multi-modal extraction pipeline (Section 3.1) over naive text dumping.
- Semantic similarity is uniformly high across models and is *not* a reliable proxy for factual correctness, especially on MathQ/MCQ — factual correctness is the more meaningful metric for MQA.

### 4.4 Context-based Performance

| Category | Model | Context Precision MCQ (%) | Context Precision MathQ (%) | Context Precision RQ (%) | Context Recall MCQ (%) | Context Recall MathQ (%) | Context Recall RQ (%) |
|---|---|---|---|---|---|---|---|
| | RAG | 81.95 | 92.56 | 92.24 | 33.39 | 67.83 | 81.23 |
| | RAGhq | 85.35 | 93.20 | 93.74 | 34.61 | 57.00 | 81.27 |
| | ManuRAG1 | 79.41 | 33.66 | 92.79 | 33.36 | 30.95 | 81.47 |
| | ManuRAG2 | 80.89 | 33.33 | 92.52 | 32.01 | 22.98 | 80.63 |
| | ManuRAG3 | 79.41 | 33.33 | 92.65 | 33.44 | 20.47 | 80.86 |
| | **ManuRAG4** | **86.84** | **93.53** | 91.84 | **37.88** | 62.26 | **81.56** |

ManuRAG4 (aligning text and images *before* embedding, via MLLM-generated descriptive text) achieves the best context precision for MathQ and MCQ, and the strongest overall precision/recall balance. RAGhq wins on RQ context precision, showing the value of high-quality indexed text for review-style questions. Plain RAG achieves the highest MathQ recall, illustrating a precision/recall trade-off with shorter indexed text. ManuRAG1–3 (separate vector stores) show notably poor MathQ precision (~33%) — a key limitation of not aligning modalities before embedding.

---

## 5. Conclusion and Future Work

ManuRAG introduces a multi-modal RAG framework tailored for manufacturing QA. ManuRAG4 — which converts visual content to descriptive text before embedding — consistently outperforms text-only RAG and naive multi-modal variants. The framework's design is presented as adaptable to other domains (law, healthcare, finance).

**Stated limitations / future work (explicitly named by the authors — useful for positioning your thesis's novelty):**
1. A stronger multi-modal embedding model (e.g., Jina-CLIP) could improve text-image alignment in the embedding space.
2. Incorporating advanced retrieval designs from other RAG frameworks (the authors cite ontology-grounded RAG and graph-RAG-for-supplier-discovery work) may further boost performance — **the paper does not implement a knowledge graph layer itself.**
3. Future versions should support additional data types: CAD models, videos, and time-series sensor data — **the current system does not handle engineering diagrams/schematics (like P&IDs) or sensor/time-series data at all.**

---

## Appendix A: Prompt Design

**MathQ prompt:**
> As a manufacturing expert, solve the math question step by step using the provided context and your knowledge of manufacturing calculations. Make sure to clearly explain your reasoning: {context_str}
> Question: Query: {query_str}
> Answer:

**MCQ prompt:**
> As a manufacturing expert, answer the following multi-choice questions based on the provided context step by step. Select the correct letter choices only.
> Answer format: "Explanation": "Your explanation here.", "YourChoice": "Answer. (d), (e), and (g)."
> {context_str}
> Answer the following question: Query: {query_str}
> Answer:

**RQ prompt:**
> You are an expert in manufacturing major. You need to answer the following short response question based on the context and your knowledge of manufacturing processes and materials. Please provide a detailed explanation and justify your answer. Be concise, clear, and accurate.
> {context_str}
> Answer the following question: Query: {query_str}
> Answer:

---

## Appendix B: QA Examples
The paper includes worked comparisons (MathQ, MCQ, RQ) across GPT-4o (CoT), RAG, and the best ManuRAG variant, showing cases where ManuRAG4 correctly references tabular data (e.g., Table 4.1 in the source textbook) that GPT-4o (CoT) alone cannot access.

---

### Notes for Krishna's PS-08 thesis positioning

The authors themselves flag exactly the two gaps your PS-08 system already addresses:
1. **No knowledge graph layer** — ManuRAG is pure multi-modal RAG (vector retrieval), not graph-based. Your PS-08 GraphRAG + HITL Verification Dashboard is a structural extension, not a duplicate.
2. **No engineering-diagram / schematic handling** — the authors list CAD models and videos as future work, but P&IDs specifically aren't mentioned. Your Gemini Vision-based P&ID parsing for Centrifugal Pump equipment fills a gap the base paper's own "future work" section leaves open.

This gives you a clean, citable "gap statement": *ManuRAG establishes multi-modal RAG for manufacturing QA but does not incorporate structured knowledge graphs or engineering-diagram parsing — both of which this work addresses.*
