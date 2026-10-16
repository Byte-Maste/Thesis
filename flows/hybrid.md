# Hybrid (condition C)

Retrieval is the vector path and the graph path together. Neither path is dropped. There is no learned reranker.

## Build

Use the stores already built for the other two flows:

- vector index from [vector_only.md](vector_only.md)
- triple store from [graph_only.md](graph_only.md)

Do not embed or extract a second time for this condition.

## Ask

```
question
   |
   +--> vector only steps --> Top@K paragraphs
   |
   +--> graph only steps  --> Top@K triples
   |
   v
concatenate, paragraphs first, then a "Graph facts:" block
   |
   v
fill {context} with that merged text
   |
   v
shared prompt -> Cohere chat, temperature 0
   |
   v
read the Result line -> exact match vs answers.text
```

The merged context looks like this:

```
[c014 DOI:10.1038/...] The results of the room temperature tensile testing ...
[c022 DOI:10.1038/...] ...

Graph facts:
- Ti-6Al-4V --has_property--> yield strength --has_value--> 765 MPa (chunk c014)
```

Top@K on each side equals the top-k used in vector only and in graph only. Hybrid is not allowed a larger k.

## Provenance

The answer record stores both lists: the paragraph ids with scores, and the triples with source chunk ids. Missing either list means that side did not run, and the row is not scored as hybrid.
