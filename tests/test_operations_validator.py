from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from early_admissions.operations_validator import QUEUE_COLUMNS, REAUDIT_COLUMNS, validate_operations


class OperationsValidatorTest(unittest.TestCase):
    def _write_fixture(self, root: Path) -> None:
        op = root / "data" / "operations"
        op.mkdir(parents=True)
        with (op / "update_queue.csv").open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=QUEUE_COLUMNS)
            writer.writeheader()
            writer.writerow({
                "queue_id": "UQ-1", "institution_type": "国立", "university": "テスト大学",
                "selection_name": "推薦", "document_type": "募集要項",
                "publication_status": "公開予定", "release_expected_text": "10月上旬",
                "release_expected_from": "2026-10-01", "release_expected_to": "2026-10-10",
                "release_schedule_url": "https://example.edu", "last_checked_on": "2026-09-27",
                "next_check_on": "2026-10-01", "action_status": "待機",
            })
        with (op / "coverage_reaudit_2027.csv").open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=REAUDIT_COLUMNS)
            writer.writeheader()
            writer.writerow({
                "source_dataset": "kokkoritsu", "institution_type": "国立", "university": "テスト大学",
                "baseline_research_status": "x", "baseline_master_rows": "1",
                "reaudit_status": "要項公開待ち", "official_system_checked": "未実施",
                "capacity_table_checked": "未実施", "schedule_checked": "未実施",
                "guideline_index_checked": "未実施", "master_compared": "未実施",
                "kawai_crosscheck": "未実施", "update_queue_open_count": "1",
            })

    def test_valid_fixture_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_fixture(root)
            self.assertEqual([], validate_operations(root))

    def test_update_needed_requires_publication(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_fixture(root)
            qpath = root / "data" / "operations" / "update_queue.csv"
            rows = list(csv.DictReader(qpath.open(encoding="utf-8")))
            rows[0]["action_status"] = "更新必要"
            with qpath.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=QUEUE_COLUMNS)
                writer.writeheader()
                writer.writerows(rows)
            errors = validate_operations(root)
            self.assertTrue(any("更新必要 requires 公開済 or 一部公開" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
