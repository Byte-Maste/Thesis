# RAG vs Knowledge Graph — Teaching Storyboard
### (For GIF/animation conversion)

---

## Setup — show this as the opening frame, stays visible throughout

**Three source documents (small cards, all visible on screen):**

```
📄 Document A (Pump Manual v3, p.12)
"Impeller wear on the centrifugal pump leads to cavitation."

📄 Document B (Pump Manual v3, p.31)
"Cavitation is typically caused by insufficient suction pressure at the pump inlet."

📄 Document C (Maintenance Log #47)
"Insufficient suction pressure was traced to a blocked strainer during the March inspection."
```

**The Query (appears below the documents, highlighted box):**

> ❓ "Why did the pump fail due to a blocked strainer?"

---

## PART 1 — RAG (Vector Similarity Path)

**Frame 1.1 — Title card:** *"How RAG answers this"*

**Frame 1.2 — Embedding step**
- Show the query turning into a row of numbers/dots: `[0.21, -0.05, 0.88, ...]`
- Label: "Query converted into a vector (embedding)"

**Frame 1.3 — Similarity scoring**
- Show all 3 documents also as vectors/dots
- Draw a "closeness meter" or bar next to each document comparing to the query vector:
  - Document A: ▓▓░░░░░░░░ (low similarity — different words)
  - Document B: ▓▓▓░░░░░░░ (low-medium similarity)
  - Document C: ▓▓▓▓▓▓▓▓░░ (high similarity — shares "blocked strainer")
- Label: "RAG measures word/meaning closeness only — not connections between documents"

**Frame 1.4 — Retrieval**
- Document C lights up / gets pulled into a "Retrieved" box
- Documents A and B fade or stay greyed out (not retrieved — score too low)
- Label: "Only Document C is retrieved"

**Frame 1.5 — Answer generation**
- Document C flows into an "LLM" box (simple robot/brain icon)
- Output bubble: *"A blocked strainer causes low suction pressure."*
- Label in red/warning color: **"⚠ Incomplete — doesn't explain the pump failure itself"**

---

## PART 2 — Knowledge Graph Path

**Frame 2.1 — Title card:** *"How the Knowledge Graph answers this"*

**Frame 2.2 — Show the pre-built graph (this graph already exists, built ahead of time from all 3 documents)**
- Draw 4 connected nodes with labeled arrows between them:

```
[Blocked Strainer] --(traced_to)--> [Insufficient Suction Pressure]
                                            --(caused_by)--> [Cavitation]
                                                                  --(fails_via)--> [Impeller]
```

- Label: "Built once, ahead of time, from all 3 documents combined"

**Frame 2.3 — Entity extraction from the query**
- Query text appears again
- Highlight the phrase "blocked strainer" inside it
- Arrow pointing from that phrase to the matching node in the graph
- Label: "The system finds which graph node the query is talking about"

**Frame 2.4 — Graph traversal (the key visual moment)**
- Starting from the `Blocked Strainer` node, animate a highlight/glow traveling along each arrow, one hop at a time:
  - Blocked Strainer → Insufficient Suction Pressure (glow moves)
  - → Cavitation (glow moves)
  - → Impeller (glow moves)
- Label: "The system walks the connections — regardless of matching words"

**Frame 2.5 — Retrieval**
- All 4 connected nodes light up together in a "Retrieved" box (the full chain, not just one match)
- Label: "The entire connected chain is retrieved, even though the words don't match the query"

**Frame 2.6 — Answer generation**
- The full chain flows into the "LLM" box
- Output bubble: *"A blocked strainer reduces suction pressure, which causes cavitation, which wears down the impeller — leading to pump failure."*
- Label in green/success color: **"✓ Complete — traces the full cause-effect chain"**

---

## PART 3 — Side-by-side final comparison frame

Split screen, both final answers shown together:

| | RAG | Knowledge Graph |
|---|---|---|
| Retrieved | 1 document | 4 connected facts |
| Matched by | shared words | explicit relationships |
| Answer | "Blocked strainer → low pressure" | "Strainer → pressure → cavitation → impeller failure" |
| Missed | the rest of the causal chain | nothing — the graph already had it linked |

**Closing caption:**
> "RAG finds documents that *sound like* the question.
> A Knowledge Graph finds facts that are *actually connected* to it —
> even when the words are completely different."

---

## Notes for building the animation

- Keep the same 3 documents and same query visible/anchored throughout both parts so students can directly compare — don't let them scroll off screen.
- The single most important visual beat is **Frame 1.3 vs Frame 2.4**: one shows a *similarity bar chart* (RAG), the other shows a *glowing path traveling across connected nodes* (KG). That contrast is the whole lesson in one image if a student only remembers one frame.
- Color suggestion: use one consistent color (e.g., orange) for "RAG path" frames and a different one (e.g., blue) for "Knowledge Graph path" frames, so students visually associate color with mechanism throughout.
- If time/frame budget is limited, you can compress Frames 1.1-1.2 and 2.1-2.2 into single setup frames — the parts that must NOT be cut are 1.3, 1.4, 2.4, 2.5, and the final comparison table.
