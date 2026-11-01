#!/usr/bin/env python3
"""EngiVerse Search 0.2.0: incremental, provenance-aware local text indexing.

The SQLite index is derived and rebuildable. Source files are never modified.
Requires Python 3.10+ and SQLite compiled with FTS5 support.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

TOOL_NAME = "EngiVerse Search"
TOOL_VERSION = "0.2.0"
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
      CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
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
        body, content='records', content_rowid='record_id', tokenize='unicode61'
      );
      CREATE INDEX idx_sources_hash ON sources(sha256);
      CREATE INDEX idx_records_source_line ON records(source_id, line_number);
    """)

def get_metadata(con: sqlite3.Connection) -> dict:
    return {row["key"]: json.loads(row["value"])
            for row in con.execute("SELECT key,value FROM metadata")}

def write_metadata(con: sqlite3.Connection, metadata: dict):
    con.execute("DELETE FROM metadata")
    con.executemany(
        "INSERT INTO metadata(key,value) VALUES(?,?)",
        [(key, json.dumps(value, ensure_ascii=False)) for key, value in metadata.items()]
    )

def add_source(con, root: Path, path: Path, digest: str):
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
        con.execute("INSERT INTO records_fts(rowid,body) VALUES(?,?)", (row.lastrowid, body))
        lines += 1
    con.execute("UPDATE sources SET line_count=? WHERE source_id=?", (lines, source_id))
    return lines

def remove_source(con: sqlite3.Connection, source_id: int):
    ids = [row[0] for row in con.execute(
        "SELECT record_id FROM records WHERE source_id=?", (source_id,)
    )]
    con.executemany("DELETE FROM records_fts WHERE rowid=?", ((rid,) for rid in ids))
    con.execute("DELETE FROM records WHERE source_id=?", (source_id,))
    con.execute("DELETE FROM sources WHERE source_id=?", (source_id,))

def index_command(args) -> int:
    roots = [p.resolve() for p in args.roots]
    excludes = DEFAULT_EXCLUDES | set(args.exclude)
    target = args.index.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    os.close(fd)
    temp = Path(temp_name)
    con = None
    try:
        prior_meta = {}
        compatible = False
        if target.is_file():
            try:
                with connect(target) as old_con:
                    prior_meta = get_metadata(old_con)
                    compatible = (
                        prior_meta.get("schema_version") == SCHEMA_VERSION
                        and prior_meta.get("roots") == [str(p) for p in roots]
                        and prior_meta.get("excluded_directory_names") == sorted(excludes)
                        and prior_meta.get("extensions") == sorted(TEXT_EXTENSIONS)
                        and prior_meta.get("max_bytes_per_file") == args.max_bytes
                    )
                if compatible:
                    shutil.copy2(target, temp)
            except (sqlite3.Error, OSError, ValueError, TypeError):
                compatible = False
        if not compatible:
            temp.unlink(missing_ok=True)
            con = connect(temp)
            create_schema(con)
            mode = "full-rebuild"
            previous = {}
        else:
            con = connect(temp)
            mode = "incremental"
            previous = {
                (row["root"], row["path"]): (row["source_id"], row["sha256"])
                for row in con.execute("SELECT source_id,root,path,sha256 FROM sources")
            }

        scanned = {}
        bytes_hashed = 0
        for root, path in discover_files(roots, excludes, args.max_bytes):
            relative = path.relative_to(root).as_posix() if root.is_dir() else path.name
            digest = sha256_file(path)
            stat = path.stat()
            key = (str(root), relative)
            scanned[key] = (root, path, digest, stat)
            bytes_hashed += stat.st_size

        removed = changed = added = reused = records_added = 0
        for key, (source_id, old_hash) in previous.items():
            current = scanned.get(key)
            if current is None:
                remove_source(con, source_id)
                removed += 1
            elif current[2] != old_hash:
                remove_source(con, source_id)
                changed += 1
        for key, (root, path, digest, stat) in scanned.items():
            old = previous.get(key)
            if old and old[1] == digest:
                con.execute(
                    "UPDATE sources SET size_bytes=?,mtime_ns=? WHERE source_id=?",
                    (stat.st_size, stat.st_mtime_ns, old[0])
                )
                reused += 1
            else:
                records_added += add_source(con, root, path, digest)
                if old is None:
                    added += 1

        files_indexed = con.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        records_indexed = con.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        metadata = {
            "schema_version": SCHEMA_VERSION,
            "tool_name": TOOL_NAME,
            "tool_version": TOOL_VERSION,
            "built_at_utc": utc_now(),
            "roots": [str(p) for p in roots],
            "excluded_directory_names": sorted(excludes),
            "extensions": sorted(TEXT_EXTENSIONS),
            "max_bytes_per_file": args.max_bytes,
            "files_indexed": files_indexed,
            "records_indexed": records_indexed,
            "bytes_hashed_this_run": bytes_hashed,
            "index_mode": mode,
            "incremental": {
                "reused_sources": reused,
                "added_sources": added,
                "changed_sources": changed,
                "removed_sources": removed,
                "records_added": records_added
            },
            "epistemic_note": "Search results are retrieval leads, not validation or authority."
        }
        write_metadata(con, metadata)
        con.commit()
        con.execute("PRAGMA optimize")
        con.close()
        con = None
        os.replace(temp, target)
        print(json.dumps(metadata, indent=2, ensure_ascii=False))
        return 0
    except Exception:
        if con is not None:
            con.close()
        temp.unlink(missing_ok=True)
        raise

def search_command(args) -> int:
    if not args.index.is_file():
        raise FileNotFoundError(f"Index not found: {args.index}. Run 'index' first.")
    con = connect(args.index)
    query = args.query.strip()
    if not query:
        raise ValueError("Query must not be empty.")
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
        con.close()
        raise ValueError(f"Invalid or unsupported FTS5 query: {exc}") from exc
    hits = [{
        "root": row["root"], "path": row["path"], "line": row["line_number"],
        "sha256": row["sha256"], "excerpt": row["body"]
    } for row in rows]
    output = {
        "schema_version": 1, "tool": TOOL_NAME, "tool_version": TOOL_VERSION,
        "queried_at_utc": utc_now(), "query": query, "index": str(args.index.resolve()),
        "hit_count": len(hits), "hits": hits
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
    if not args.index.is_file():
        raise FileNotFoundError(f"Index not found: {args.index}")
    con = connect(args.index)
    rows = con.execute("SELECT root,path,sha256 FROM sources ORDER BY root,path").fetchall()
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
            details.append({
                "path": str(path), "status": "hash-mismatch",
                "indexed_sha256": row["sha256"], "current_sha256": actual
            })
    meta = get_metadata(con)
    con.close()
    report = {
        "tool": TOOL_NAME, "tool_version": TOOL_VERSION,
        "verified_at_utc": utc_now(), "index_built_at_utc": meta.get("built_at_utc"),
        "sources_checked": checked, "changed": changed, "missing": missing,
        "unchanged": checked - changed - missing, "details": details
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if changed or missing else 0

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    indexer = sub.add_parser("index", help="Build or incrementally update the derived full-text index.")
    indexer.add_argument("roots", nargs="+", type=Path)
    indexer.add_argument("--index", type=Path, default=Path("indexes/engiverse.sqlite"))
    indexer.add_argument("--exclude", action="append", default=[])
    indexer.add_argument("--max-bytes", type=int, default=10_000_000)
    indexer.set_defaults(func=index_command)
    searcher = sub.add_parser("search", help="Search an existing FTS5 index.")
    searcher.add_argument("query", help="FTS5 query: terms, phrases, AND, OR, NOT, NEAR.")
    searcher.add_argument("--index", type=Path, default=Path("indexes/engiverse.sqlite"))
    searcher.add_argument("--path", help="Restrict to a source path substring; * and ? wildcards supported.")
    searcher.add_argument("--limit", type=int, default=50)
    searcher.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    searcher.set_defaults(func=search_command)
    verifier = sub.add_parser("verify", help="Compare current source hashes with indexed hashes.")
    verifier.add_argument("--index", type=Path, default=Path("indexes/engiverse.sqlite"))
    verifier.set_defaults(func=verify_command)
    args = parser.parse_args()
    if getattr(args, "limit", 1) < 1 or getattr(args, "max_bytes", 1) < 1:
        parser.error("--limit and --max-bytes must be at least 1")
    return args.func(args)

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
