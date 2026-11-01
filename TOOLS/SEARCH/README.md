# EngiVerse Search

Version: 0.1.0  
Status: initial local prototype

## Requirements

- Python 3.10 or newer
- SQLite built with FTS5 support (commonly included with standard Python distributions)

No third-party Python packages are required.

## Quick start

From the repository root:

```bash
python tools/engiverse_search.py index PROJECTS HARDWARE FIRMWARE PROTOCOLS DOCUMENTATION
python tools/engiverse_search.py search '"USB descriptor"'
python tools/engiverse_search.py search 'controller AND firmware NOT obsolete'
python tools/engiverse_search.py verify
```

The default index is `indexes/engiverse.sqlite`. The `indexes/` directory is excluded from source scanning and should remain a generated local artifact, not committed evidence.

## Commands

### Build the index

```bash
python tools/engiverse_search.py index <root> [<root> ...] [--index PATH] [--exclude NAME] [--max-bytes N]
```

This first release performs a deterministic full rebuild into a temporary SQLite database, then atomically replaces the previous index. It does not modify source files. Supported formats are source/text formats listed in the script; binary firmware, PDF extraction, image OCR, and schematic parsing are not yet implemented.

### Search

```bash
python tools/engiverse_search.py search 'FTS5 QUERY' [--path GLOB] [--limit N] [--json]
```

Search uses SQLite FTS5 syntax: terms, quoted phrases, `AND`, `OR`, `NOT`, parentheses, prefix terms, and `NEAR` expressions. This is not yet the full Mersearch query language. In particular, field expressions such as `author:`, `date:`, `math:`, and `has:` are not implemented.

Each hit reports source root, relative path, line number, SHA-256 of the complete source file, and matching line excerpt. A hash identifies the indexed bytes; it does not establish correctness, origin, safety, or authority.

### Verify source integrity

```bash
python tools/engiverse_search.py verify [--index PATH]
```

Compares current source hashes with those recorded at index time. A changed or missing source is reported and causes exit status 1. Verification does not update the index.

## Current limitations

- Line-oriented extraction only. Structured JSON is indexed as source lines, not semantic fields.
- PDF, Office documents, images, firmware binaries, filesystems, and packet captures require dedicated extractors.
- Full rebuild only; incremental content-hash indexing is a later step.
- FTS5 syntax is the query language for this prototype.
- The index stores extracted line text and provenance metadata. Protect the local index according to the sensitivity of its source corpus.
- Symlinks are skipped to avoid unintentionally indexing content outside declared roots.

## Design lineage

The architecture takes general lessons from the pinned HsH Mersearch 1.0 design: read-only source handling, deterministic retrieval, source locators, explicit corpus scope, and provenance-bearing results. This implementation is independent prototype code, not a copied or validated port of Mersearch. Any future code reuse must be reviewed against the upstream license and pinned source revision.
