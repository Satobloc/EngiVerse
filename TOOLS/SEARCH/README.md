# EngiVerse Search

Version: 0.2.0  
Status: local prototype with incremental indexing

## Requirements

- Python 3.10 or newer
- SQLite built with FTS5 support
- No third-party Python packages

## Quick start

```bash
python tools/engiverse_search.py index PROJECTS HARDWARE FIRMWARE PROTOCOLS DOCUMENTATION
python tools/engiverse_search.py search '"USB descriptor"'
python tools/engiverse_search.py search 'controller AND firmware NOT obsolete'
python tools/engiverse_search.py verify
python -m unittest discover -s tests -v
```

The default index is `indexes/engiverse.sqlite`. It is a generated local artifact and is excluded from Git.

## Indexing behavior

The first run creates a full index. Later runs with the same roots, exclusions, extension set, and maximum file size use content hashes to detect changes:

- Unchanged source files are retained in the existing index.
- Added files are extracted and indexed.
- Changed files have their prior records removed and are re-indexed.
- Deleted or newly excluded files are removed from the index.
- A change in index configuration forces a clean rebuild.

The index is assembled in a temporary SQLite database and replaces the previous index only after the transaction completes. The source corpus is read-only. A full rebuild remains available by deleting the local index before running the command again.

**Important:** incremental indexing still reads and hashes every eligible file on each run. It avoids reparsing unchanged content and rebuilding its FTS records, but it does not yet avoid the I/O cost of hashing the corpus.

## Search

Search uses SQLite FTS5 syntax: terms, quoted phrases, `AND`, `OR`, `NOT`, parentheses, prefix terms, and `NEAR` expressions. This is not the full Mersearch query language. Field expressions such as `author:`, `date:`, `math:`, and `has:` are not implemented.

Each hit includes source root, relative path, line number, SHA-256 of the complete source file, and matching line text.

## Verify

`verify` compares current source hashes with the hashes recorded in the index. It reports changed and missing sources but does not modify the index.

## Supported input

The current extractor indexes non-empty lines from text/source formats listed in `tools/engiverse_search.py`. It does not yet extract text from PDFs, Office documents, images, firmware binaries, filesystems, or packet captures. The `.hex` extension is treated as text only; this does not decode Intel HEX semantics.

## Provenance and limitations

A hash identifies exact file bytes, not correctness, authorship, safety, or authority. Search hits are retrieval leads, not validation. Indexes contain extracted source text and should be protected according to the sensitivity of the corpus. Symlinks are skipped to avoid unintentionally indexing outside declared roots.

## Design lineage

The prototype takes general architectural lessons from pinned HsH Mersearch 1.0: read-only source handling, deterministic retrieval, locators, explicit corpus scope, and provenance-bearing results. It is an independent implementation, not a copied or validated port of Mersearch.
