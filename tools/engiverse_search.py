#!/usr/bin/env python3
"""EngiVerse Search 0.1.0: read-only, provenance-aware local text indexing.

The index is derived and rebuildable. Source files are never modified.
Requires Python 3.10+ and SQLite compiled with FTS5 support.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

TOOL_NAME = "EngiVerse Search"
TOOL_VERSION = "0.1.0"
SCHEMA_VERSION = 1
TEXT_EXTENSIONS = {
    ".txt", ".md", ".rst", ".csv", ".tsv", ".json", ".jsonl",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".xml",
    ".html", ".htm", ".py", ".js", ".ts", ".tsx", ".jsx", ".c",
    ".h", ".cpp", ".hpp", ".rs", ".go", ".java", ".cs", ".sh",
    ".ps1", ".bat", ".sql", ".tex", ".log", ".map", ".ld", ".s",
    ".asm", ".hex", ".sv", ".v", ".ino"
}
DEFAULT_EXCLUDES = {
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    ".idea", ".vscode", "indexes", "build", "dist"
}

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def discover_files(roots: list[Path], excludes: set[str], max_bytes: int):
    seen: set[Path] = set()
    for root in roots:
        root = root.resolve()
        if not root.exists():
            raise FileNotFoundError(f"Search root does not exist: {root}")
        candidates = [root] if root.is_file() else root.rglob("*")
        for path in candidates:
            if not path.is_file() or path.is_symlink():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                rel_parts = path.relative_to(root).parts if root.is_dir() else (path.name,)
                if any(part in excludes for part in rel_parts):
                    continue
                if path.suffix.lower() not in TEXT_EXTENSIONS:
                    continue
                if path.stat().st_size > max_bytes:
                    continue
            except (OSError, ValueError):
                continue
            yield root, path

def read_lines(path: Path):
    # Replacement decoding keeps a damaged byte sequence visible as U+FFFD
    # rather than silently dropping the rest of the source.
    with path.open("r", encoding="utf-8-sig", errors="replace", newline=None) as stream:
        for number, line in enumerate(stream, 1):
            text = line.rstrip("\r\n")
            if text.strip():
                yield number, text

def connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con

def check_fts(con: sqlite3.Connection):
    try:
        con.execute("CREATE VIRTUAL TABLE temp.__fts_probe USING fts5(value)")
        con.execute("DROP TABLE temp.__fts_probe")
    except sqlite3.OperationalError as exc:
        raise RuntimeError("This Python/SQLite build lacks FTS5 support") from exc

def create_schema(con: sqlite3.Connection):
    check_fts(con)
    con.executescript("""
      PRAGMA journal_mode=DELETE;
      PRAGMA synchronous=FULL;
      CREATE TABLE metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
      );
      CREATE TABLE sources (
        source_id INTEGER PRIMARY KEY,
        root TEXT NOT NULL,
        path TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        mtime_ns INTEGER NOT NULL,
        sha256 TEXT NOT NULL,
        line_count INTEGER NOT NULL,
        UNIQUE(root, path)
      );
      CREATE TABLE records (
        record_id INTEGER PRIMARY KEY,
        source_id INTEGER NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
        line_number INTEGER NOT NULL,
        body TEXT NOT NULL
      );
      CREATE VIRTUAL TABLE records_fts USING fts5(
        body,
        content='records',
        content_rowid='record_id',
        tokenize='unicode61'
      );
      CREATE INDEX idx_sources_hash ON sources(sha256);
      CREATE INDEX idx_records_source_line ON records(source_id, line_number);
    """)

def index_command(args) -> int:
    roots = [p.resolve() for p in args.roots]
    excludes = DEFAULT_EXCLUDES | set(args.exclude)
    target = args.index.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    os.close(fd)
    temp = Path(temp_name)
    file_count = record_count = byte_count = 0
    try:
        con = connect(temp)
        create_schema(con)
        con.execute("BEGIN")
        for root, path in discover_files(roots, excludes, args.max_bytes):
            try:
                digest = sha256_file(path)
                stat = path.stat()
                relative = path.relative_to(root).as_posix() if root.is_dir() else path.name
                cursor = con.execute(
                    "INSERT INTO sources(root,path,size_bytes,mtime_ns,sha256,line_count) VALUES(?,?,?,?,?,0)",
                    (str(root), relative, stat.st_size, stat.st_mtime_ns, digest)
                )
                source_id = cursor.lastrowid
                lines = 0
                for line_number, body in read_lines(path):
                    row = con.execute(
                        "INSERT INTO records(source_id,line_number,body) VALUES(?,?,?)",
                        (source_id, line_number, body)
                    )
                    con.execute(
                        "INSERT INTO records_fts(rowid,body) VALUES(?,?)",
                        (row.lastrowid, body)
                    )
                    lines += 1
                con.execute("UPDATE sources SET line_count=? WHERE source_id=?", (lines, source_id))
                file_count += 1
                record_count += lines
                byte_count += stat.st_size
            except (OSError, UnicodeError) as exc:
                print(f"WARNING: skipped {path}: {exc}", file=sys.stderr)
        metadata = {
            "schema_version": SCHEMA_VERSION,
            "tool_name": TOOL_NAME,
            "tool_version": TOOL_VERSION,
            "built_at_utc": utc_now(),
            "roots": [str(p) for p in roots],
            "excluded_directory_names": sorted(excludes),
            "extensions": sorted(TEXT_EXTENSIONS),
            "max_bytes_per_file": args.max_bytes,
            "files_indexed": file_count,
            "records_indexed": record_count,
            "source_bytes": byte_count,
            "index_mode": "full-rebuild",
            "epistemic_note": "Search results are retrieval leads, not validation or authority."
        }
        con.executemany(
            "INSERT INTO metadata(key,value) VALUES(?,?)",
            [(key, json.dumps(value, ensure_ascii=False)) for key, value in metadata.items()]
        )
        con.commit()
        con.execute("PRAGMA optimize")
        con.close()
        os.replace(temp, target)
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
        return 0
    except Exception:
        try:
            con.close()
        except Exception:
            pass
        temp.unlink(missing_ok=True)
        raise

def search_command(args) -> int:
    if not args.index.is_file():
        raise FileNotFoundError(f"Index not found: {args.index}. Run 'index' first.")
    con = connect(args.index)
    query = args.query.strip()
    if not query:
        raise ValueError("Query must not be empty.")
    # FTS5 provides phrase, AND, OR, NOT, prefix and NEAR syntax.
    sql = """
      SELECT r.line_number, r.body, s.root, s.path, s.sha256, s.size_bytes
      FROM records_fts f
      JOIN records r ON r.record_id=f.rowid
      JOIN sources s ON s.source_id=r.source_id
      WHERE records_fts MATCH ?
    """
    params: list[object] = [query]
    if args.path:
        sql += " AND s.path LIKE ? ESCAPE '\\'"
        pattern = args.path.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        params.append(pattern.replace("*", "%").replace("?", "_"))
    sql += " ORDER BY s.path COLLATE NOCASE, r.line_number LIMIT ?"
    params.append(args.limit)
    try:
        rows = con.execute(sql, params).fetchall()
    except sqlite3.OperationalError as exc:
        raise ValueError(f"Invalid or unsupported FTS5 query: {exc}") from exc
    hits = []
    for row in rows:
        hits.append({
            "root": row["root"],
            "path": row["path"],
            "line": row["line_number"],
            "sha256": row["sha256"],
            "excerpt": row["body"]
        })
    output = {
        "schema_version": 1,
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
        "queried_at_utc": utc_now(),
        "query": query,
        "index": str(args.index.resolve()),
        "hit_count": len(hits),
        "hits": hits
    }
    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f'{len(hits)} hit(s) for: {query}')
        for hit in hits:
            print(f'[{hit["sha256"][:12]}] {hit["path"]}:{hit["line"]}: {hit["excerpt"]}')
    con.close()
    return 0

def verify_command(args) -> int:
    con = connect(args.index)
    rows = con.execute("SELECT root,path,sha256,size_bytes FROM sources ORDER BY root,path").fetchall()
    checked = changed = missing = 0
    details = []
    for row in rows:
        path = Path(row["root"]) / row["path"]
        checked += 1
        if not path.is_file():
            missing += 1
            details.append({"path": str(path), "status": "missing"})
            continue
        actual = sha256_file(path)
        if actual != row["sha256"]:
            changed += 1
            details.append({"path": str(path), "status": "hash-mismatch", "indexed_sha256": row["sha256"], "current_sha256": actual})
    meta = {r["key"]: json.loads(r["value"]) for r in con.execute("SELECT key,value FROM metadata")}
    con.close()
    report = {
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
        "verified_at_utc": utc_now(),
        "index_built_at_utc": meta.get("built_at_utc"),
        "sources_checked": checked,
        "changed": changed,
        "missing": missing,
        "unchanged": checked - changed - missing,
        "details": details
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if changed or missing else 0

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    indexer = sub.add_parser("index", help="Build or replace a derived full-text index.")
    indexer.add_argument("roots", nargs="+", type=Path)
    indexer.add_argument("--index", type=Path, default=Path("indexes/engiverse.sqlite"))
    indexer.add_argument("--exclude", action="append", default=[])
    indexer.add_argument("--max-bytes", type=int, default=10_000_000)
    indexer.set_defaults(func=index_command)
    searcher = sub.add_parser("search", help="Search an existing FTS5 index.")
    searcher.add_argument("query", help='FTS5 query, e.g. "USB descriptor" or "controller AND firmware".')
    searcher.add_argument("--index", type=Path, default=Path("indexes/engiverse.sqlite"))
    searcher.add_argument("--path", help="Restrict to a source path substring; * and ? wildcards supported.")
    searcher.add_argument("--limit", type=int, default=50)
    searcher.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    searcher.set_defaults(func=search_command)
    verifier = sub.add_parser("verify", help="Compare current source hashes with indexed hashes.")
    verifier.add_argument("--index", type=Path, default=Path("indexes/engiverse.sqlite"))
    verifier.set_defaults(func=verify_command)
    args = parser.parse_args()
    if getattr(args, "limit", 1) < 1:
        parser.error("--limit must be at least 1")
    if getattr(args, "max_bytes", 1) < 1:
        parser.error("--max-bytes must be at least 1")
    return args.func(args)

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
