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

    def test_index_search_and_provenance(self):
        built = self.run_cli("index", self.root, "--index", self.index)
        self.assertEqual(built.returncode, 0, built.stderr)
        result = self.run_cli("search", '"USB descriptor"', "--index", self.index, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["hit_count"], 2)
        for hit in payload["hits"]:
            self.assertEqual(len(hit["sha256"]), 64)
            self.assertGreater(hit["line"], 0)

    def test_boolean_query(self):
        self.assertEqual(self.run_cli("index", self.root, "--index", self.index).returncode, 0)
        result = self.run_cli("search", "USB AND descriptor NOT failed", "--index", self.index, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["hit_count"], 1)

    def test_verify_detects_changed_source(self):
        self.assertEqual(self.run_cli("index", self.root, "--index", self.index).returncode, 0)
        (self.root / "board.md").write_text("changed source\n", encoding="utf-8")
        result = self.run_cli("verify", "--index", self.index)
        self.assertEqual(result.returncode, 1)
        self.assertIn('"changed": 1', result.stdout)

    def test_original_sources_unchanged_by_indexing(self):
        before = hashlib.sha256((self.root / "board.md").read_bytes()).hexdigest()
        result = self.run_cli("index", self.root, "--index", self.index)
        self.assertEqual(result.returncode, 0, result.stderr)
        after = hashlib.sha256((self.root / "board.md").read_bytes()).hexdigest()
        self.assertEqual(before, after)

if __name__ == "__main__":
    unittest.main()
