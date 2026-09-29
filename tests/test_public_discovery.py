from __future__ import annotations

import csv
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from early_admissions.public_discovery_builder import (
    INPUT_PATH, QUEUE_PATH, SCHEMA_PATH, build_public_discovery,
    validate_publication_registry,
)


ROOT = Path(__file__).resolve().parents[1]


class PublicDiscoveryTests(unittest.TestCase):
    def test_hokkaido_is_discoverable_without_a_canonical_guess(self) -> None:
        records = validate_publication_registry(ROOT)
        hokkaido = next(row for row in records if row["university"] == "北海道教育大学")
        self.assertEqual(hokkaido["public_status"], "details_pending")
        self.assertEqual(hokkaido["related_update_queue_id"], "UQ-2027-0046")
        self.assertIn("hokkyodai.ac.jp", str(hokkaido["official_source_url"]))
        self.assertIn("実出願単位", str(hokkaido["unknown_detail"]))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in (INPUT_PATH, QUEUE_PATH, SCHEMA_PATH):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / relative).read_bytes())
            database = root / "admissions.sqlite"
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("CREATE TABLE admissions (university TEXT, faculty_school TEXT, selection_name TEXT)")
                connection.commit()
            output = root / "site-data"
            manifest = build_public_discovery(root, database, output)
            self.assertEqual(manifest["published_rows"], len(records))
            payload = json.loads((output / "provisional_admissions.json").read_text(encoding="utf-8"))
            self.assertIn("PA-2027-0001", {row["provisional_id"] for row in payload["records"]})

            with closing(sqlite3.connect(database)) as connection:
                connection.execute("INSERT INTO admissions VALUES (?,?,?)", (
                    "北海道教育大学", "教育学部", "学校推薦型選抜（一般・地域指定）"))
                connection.commit()
            promoted = build_public_discovery(root, database, output)
            self.assertEqual(promoted["published_rows"], len(records) - 1)
            self.assertEqual(promoted["suppressed_confirmed_ids"], ["PA-2027-0001"])

    def test_official_source_and_previous_year_requirements_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in (INPUT_PATH, QUEUE_PATH, SCHEMA_PATH):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / relative).read_bytes())
            source = root / INPUT_PATH
            with source.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
                header = list(rows[0])
            rows[1]["previous_year_source_url"] = ""
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=header)
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, "previous_year_source_url"):
                validate_publication_registry(root)


if __name__ == "__main__":
    unittest.main()
