import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "engiverse_search.py"

class EngiVerseSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "corpus"
        self.root.mkdir()
        (self.root / "board.md").write_text(
            "# Board notes\nUSB descriptor request failed\nController firmware revision A2\n",
            encoding="utf-8"
        )
        (self.root / "protocol.txt").write_text(
            "UART boot log\nI2C sensor address 0x48\nUSB descriptor returned\n",
            encoding="utf-8"
        )
        self.index = Path(self.temp.name) / "index.sqlite"

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            capture_output=True, text=True, check=False
        )

    def build(self):
        result = self.run_cli("index", self.root, "--index", self.index)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def search(self, query):
        result = self.run_cli("search", query, "--index", self.index, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_index_search_and_provenance(self):
        self.build()
        payload = self.search('"USB descriptor"')
        self.assertEqual(payload["hit_count"], 2)
        for hit in payload["hits"]:
            self.assertEqual(len(hit["sha256"]), 64)
            self.assertGreater(hit["line"], 0)

    def test_boolean_query(self):
        self.build()
        self.assertEqual(self.search("USB AND descriptor NOT failed")["hit_count"], 1)

    def test_verify_detects_changed_source(self):
        self.build()
        (self.root / "board.md").write_text("changed source\n", encoding="utf-8")
        result = self.run_cli("verify", "--index", self.index)
        self.assertEqual(result.returncode, 1)
        self.assertIn('"changed": 1', result.stdout)

    def test_original_sources_unchanged_by_indexing(self):
        before = hashlib.sha256((self.root / "board.md").read_bytes()).hexdigest()
        self.build()
        after = hashlib.sha256((self.root / "board.md").read_bytes()).hexdigest()
        self.assertEqual(before, after)

    def test_incremental_reuses_unchanged_and_adds_new(self):
        first = self.build()
        self.assertEqual(first["index_mode"], "full-rebuild")
        (self.root / "new.txt").write_text("new sensor controller\n", encoding="utf-8")
        second_result = self.run_cli("index", self.root, "--index", self.index)
        self.assertEqual(second_result.returncode, 0, second_result.stderr)
        second = json.loads(second_result.stdout)
        self.assertEqual(second["index_mode"], "incremental")
        self.assertEqual(second["incremental"]["reused_sources"], 2)
        self.assertEqual(second["incremental"]["added_sources"], 1)
        self.assertEqual(self.search("sensor")["hit_count"], 2)

    def test_incremental_reindexes_changed_and_removes_deleted(self):
        self.build()
        (self.root / "board.md").write_text("revised oscillator design\n", encoding="utf-8")
        (self.root / "protocol.txt").unlink()
        result = self.run_cli("index", self.root, "--index", self.index)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["incremental"]["changed_sources"], 1)
        self.assertEqual(report["incremental"]["removed_sources"], 1)
        self.assertEqual(report["files_indexed"], 1)
        self.assertEqual(self.search("oscillator")["hit_count"], 1)
        self.assertEqual(self.search("UART")["hit_count"], 0)

    def test_configuration_change_forces_full_rebuild(self):
        self.build()
        result = self.run_cli("index", self.root, "--index", self.index, "--max-bytes", "1000")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["index_mode"], "full-rebuild")

if __name__ == "__main__":
    unittest.main()
