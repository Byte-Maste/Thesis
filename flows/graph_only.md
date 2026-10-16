# Graph only (condition B)

Retrieval walks extracted triples. No paragraph text from vector search enters the prompt.

## Build

```
unique context paragraphs
        |
        v
schema-constrained extraction, one gleaning pass
        |
        v
triples: Material --has_property--> Property --has_value--> Value
         plus source chunk id and DOI
        |
        v
entity resolution: exact string match, then embedding similarity for aliases
        |
        v
JSON triple store for the pilot
```

Schema vocabulary is only `Material`, `Property`, and `Value`. A new relation name is a schema change and requires a rebuild.

## Ask

```
question
   |
   v
extract the material name and the property name mentioned in the question
   |
   v
link those strings to nodes (exact match, then embedding similarity)
   |
   +-- both linked --> triples that connect that material to that property
   |
   +-- one linked  --> triples one hop from that node
   |
   v
Top@K triples
   |
   v
fill {context} with serialized triples only
   |     Ti-6Al-4V --has_property--> yield strength --has_value--> 765 MPa (chunk c014)
   v
shared prompt -> Cohere chat, temperature 0
   |
   v
read the Result line -> exact match vs answers.text
```

If nothing links, `{context}` is the sentence `No graph facts matched.` The model still answers under the same prompt. That row counts as a retrieval miss.

## Provenance

The answer record stores the linked nodes, the triples, and the source chunk id on each triple. An answer with no attempted link is a failed run, not a score.
