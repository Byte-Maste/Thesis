# Project Proposal — Short Version

## Title
**A Multimodal Knowledge-Graph for Industrial Equipment Fault Diagnosis and Maintenance Documentation**

---

**1. Domain:** Applied AI for Industrial Manufacturing — multi-modal RAG, knowledge graphs, and human-in-the-loop verification applied to centrifugal pump maintenance documentation.

**2i. Gap in current research:** Existing multi-modal RAG systems (ManuRAG) retrieve independent text/image chunks by similarity and score only 45.75% factual correctness on multi-hop reasoning questions, since no published system combines a knowledge graph over both text *and* vision-parsed P&IDs with human correction.

**2ii. Research question:** Does adding a knowledge graph (built from text + parsed engineering diagrams) with human-in-the-loop verification improve factual correctness on multi-hop maintenance questions compared to vector-only RAG?

**3. Why solve it / impact:** Vector-only RAG gives untraceable answers with no way to correct recurring errors, which is risky for safety-critical equipment; solving this improves diagnostic reliability, reduces downtime, and helps capture tacit expert knowledge before it's lost.

**4. Base papers:**
- ManuRAG — *Journal of Intelligent Manufacturing* (Springer), 2026
- ChatP&ID — *AIChE Journal* (Wiley), 2026

**5. Tools:** FastAPI, Gemini Vision, Cohere, PostgreSQL/Supabase (pgvector), React + Vite, S3, LangChain/LangGraph, Neo4j or Postgres adjacency tables for the graph, React Flow, RAGAS for evaluation.
