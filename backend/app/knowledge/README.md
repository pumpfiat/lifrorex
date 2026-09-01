# Deterministic Knowledge Deduplication

Step 9G compares only `Knowledge.content`. It preserves the original stored text,
but normalizes Unicode, case, whitespace, and terminal sentence punctuation for
comparison before generating a SHA-256 fingerprint.

Two records are duplicates only when those normalized values are identical. This
does not attempt semantic equivalence, similarity, embeddings, or LLM-based
deduplication. `KnowledgeRepository.create_or_get` retains the first record as
canonical. Evidence remains separately associated with that canonical record
through `EvidenceRepository`, preserving its Document and Source provenance.