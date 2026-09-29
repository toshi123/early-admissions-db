from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from early_admissions.site_special_index import build_special_index


ROOT = Path(__file__).resolve().parents[1]


class SiteSpecialIndexTests(unittest.TestCase):
    def test_projects_all_four_flags_with_complete_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            db = base / "input.sqlite"
            with sqlite3.connect(db) as connection:
                connection.execute("CREATE TABLE admissions (source_dataset TEXT, source_version TEXT, record_id TEXT, "
                                   "returnee_flag INTEGER, international_baccalaureate_flag INTEGER, "
                                   "private_foreign_student_flag INTEGER, adult_selection_flag INTEGER)")
                connection.execute("INSERT INTO admissions VALUES ('kokkoritsu','5.83','R',1,0,0,0)")
                connection.execute("INSERT INTO admissions VALUES ('shidai','1.10','IB',0,1,0,0)")
            manifest = build_special_index(db, base / "out")
            payload = json.loads((base / "out/special_selection_index.json").read_text())
            schema = json.loads((ROOT / "schema/site/special_selection_index_schema_v0_1.json").read_text())
            Draft202012Validator(schema).validate(payload)
            self.assertEqual(manifest["rows"], 2)
            self.assertTrue(payload["records"][0]["flags"]["returnee_flag"])
            self.assertTrue(payload["records"][1]["flags"]["international_baccalaureate_flag"])
            self.assertFalse(payload["records"][1]["flags"]["private_foreign_student_flag"])

    def test_rejects_bad_flag_instead_of_treating_it_as_no(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            db = base / "input.sqlite"
            with sqlite3.connect(db) as connection:
                connection.execute("CREATE TABLE admissions (source_dataset TEXT, source_version TEXT, record_id TEXT, "
                                   "returnee_flag INTEGER, international_baccalaureate_flag INTEGER, "
                                   "private_foreign_student_flag INTEGER, adult_selection_flag INTEGER)")
                connection.execute("INSERT INTO admissions VALUES ('kokkoritsu','5.83','R',NULL,0,0,0)")
            with self.assertRaisesRegex(ValueError, "invalid special"):
                build_special_index(db, base / "out")


if __name__ == "__main__":
    unittest.main()
