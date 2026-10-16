# Vector only (condition A)

Retrieval is embedding similarity over MechQA paragraphs. No graph triples enter the prompt.

## Build

```
unique context paragraphs
        |
        v
Cohere embed (input_type = search_document)
        |
        v
vector index: chunk id, DOI, text, vector
```

Cache the vectors. Rebuild only when the paragraph set or the embedding model changes.

## Ask

```
question
   |
   v
Cohere embed (input_type = search_query)
   |
   v
cosine similarity against the vector index
   |
   v
Top@K paragraphs, highest score first
   |
   v
fill {context} with those paragraphs, each labeled with chunk id and DOI
   |
   v
shared prompt -> Cohere chat, temperature 0
   |
   v
read the Result line -> exact match vs answers.text
```

Top@K is the value in the experiment config. It is the same number used by graph only and hybrid.

## Provenance

The answer record stores the K chunk ids, their similarity scores, and the DOI of each paragraph. An answer with no chunk ids is a failed run, not a score.
