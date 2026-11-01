# Search and indexing architecture

## Design goal

One search model should support multiple clients: command line, local research interface, automated reports, and future integrations. Do not create separate search semantics in each client.

## Search layers

1. **Original corpus:** user-authorized files and source documents, preserved in place or in an immutable evidence store.
2. **Extraction layer:** text, metadata, strings, symbols, tables, and structural representations extracted by versioned tools.
3. **Derived index:** rebuildable metadata and full-text indexes. The index is a navigation aid, never the evidence itself.
4. **Query engine:** consistent syntax and deterministic result ordering.
5. **Clients:** CLI first; UI and automation can follow without changing core semantics.

## Initial query capabilities

A future engine should support:

- Literal terms and quoted phrases.
- Boolean `AND`, `OR`, `NOT`, with parentheses.
- Field filters such as `path:`, `name:`, `ext:`, `kind:`, `date:`, `project:`, `author:`, and `device:`.
- Proximity queries such as `NEAR/5` where the indexed format supports positional text.
- Exact hash lookup.
- Part-number and manufacturer-marking lookup.
- Firmware strings, symbols, and address lookups.
- Protocol signature and command lookup.
- Cross-project component and subsystem correlation.

These are design requirements, not a claim that the engine already implements them.

## Engineering requirements

- Store source path/URI, project, evidence ID, source hash, extraction tool/version, extraction timestamp, and index version with each indexed record.
- Make indexing deterministic and incremental where feasible.
- Detect duplicate content by hash without discarding distinct source locations.
- Support explicit exclusions and report them.
- Make every result resolve to the original evidence and relevant locator (page, line, offset, address, packet, or measurement ID).
- Keep extraction errors visible.
- Do not infer equivalence from superficial string normalization. Any normalization must be documented and reversible or traceable to original text.
- Never treat a search hit as validation, authority, or proof.

## Provenance for a search run

Every saved search report should record:

- Exact query and query-language version.
- Repository/corpus scope and exclusions.
- Source revision or corpus manifest identifier.
- Search engine version and configuration.
- Date/time of execution.
- Result count and stable result identifiers.
- Any truncation or extraction limitations.

## Relationship to HsH Mersearch

EngiVerse may adapt general architectural lessons from HsH Mersearch: shared search semantics, multiple clients, provenance-bearing results, deterministic output, and rebuildable indexes. It should not blindly import SAT/HsH project data, private conversations, or theory-specific content. Any future code reuse requires source inspection, license review, pinned upstream commit, attribution, and tests on EngiVerse material.
