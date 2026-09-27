from __future__ import annotations

import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from early_admissions.validator import (
    CODE_SEVERITY,
    Issue,
    ReadOnlyValidator,
    ValidationResult,
    classify_raw_date,
    map_detail_completeness,
    map_research_activity_level,
    metric_status,
    parse_int,
    write_json_report,
    write_markdown_report,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def write_csv(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_synthetic_repo(root: Path) -> dict[str, dict[str, object]]:
    contract_paths = [
        Path("docs/unified_data_contract.md"),
        Path("docs/unified_field_mapping_v0_1.md"),
        Path("schema/unified/early_admissions_unified_schema_v0_2.json"),
        Path("schema/kokkoritsu/kokkoritsu_early_admissions_schema_v5_82.json"),
        Path("schema/shidai/shidai_early_admissions_schema_v1_09.json"),
    ]
    for rel_path in contract_paths:
        destination = root / rel_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / rel_path, destination)

    states: dict[str, dict[str, object]] = {}
    for dataset, institution_type in (
        ("kokkoritsu", "国立"),
        ("shidai", "私立"),
    ):
        schema_path = next((root / "schema" / dataset).glob("*.json"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        master_header = schema["master_columns"]
        coverage_header = schema["coverage_columns"]
        research_header = schema["research_requirements_columns"]

        master = {field: "" for field in master_header}
        master.update(
            {
                "record_id": f"{dataset.upper()}-1",
                "admission_year": "2027",
                "institution_type": institution_type,
                "university": f"{dataset}大学",
                "stem_flag": "True",
                "school_recommendation_required": "No",
                "exclusive_enrollment_status": "不明",
                "common_test_required": "No",
                "research_activity_level": (
                    "none" if dataset == "shidai" else "なし"
                ),
                "research_requirement_required": "No",
                "academic_record_required": "Unknown",
                "detail_completeness": (
                    "complete" if dataset == "shidai" else "detailed（fixture）"
                ),
                "verification_grade": "A",
                "verified_on": "2026-09-20",
                "source_url": "https://example.test/source",
                "information_year": "2027",
                "fallback_previous_year": "False",
                "international_baccalaureate_flag": "No",
                "private_foreign_student_flag": "No",
                "returnee_flag": "No",
                "regional_quota_flag": "No",
            }
        )
        for field in (
            "selection_document_review",
            "selection_interview",
            "selection_oral_exam",
            "selection_presentation",
            "selection_essay",
            "selection_written_exam",
            "selection_practical",
            "selection_group_discussion",
            "selection_aptitude_test",
            "selection_common_test",
        ):
            master[field] = "No"

        coverage = {field: "" for field in coverage_header}
        coverage.update(
            {
                "institution_type": institution_type,
                "university": master["university"],
                "undergraduate_scope": "対象",
                "research_status": "fixture",
                "master_rows": "1",
                "checked_on": "2026-09-20",
                "official_source_url": "https://example.test/coverage",
            }
        )

        canonical = root / "data" / "canonical" / dataset
        write_csv(canonical / "master.csv", master_header, [master])
        write_csv(canonical / "coverage.csv", coverage_header, [coverage])
        write_csv(canonical / "research_requirements.csv", research_header, [])
        states[dataset] = {
            "master_header": master_header,
            "coverage_header": coverage_header,
            "research_header": research_header,
            "master": master,
            "coverage": coverage,
            "canonical": canonical,
        }
    return states


class MappingTests(unittest.TestCase):
    def test_detail_completeness_crosswalk(self) -> None:
        self.assertEqual(
            map_detail_completeness("kokkoritsu", "detailed（再監査済）"),
            "complete",
        )
        self.assertEqual(
            map_detail_completeness("kokkoritsu", "partial（確認待ち）"),
            "partial",
        )
        self.assertEqual(
            map_detail_completeness("kokkoritsu", "説明文"), "unmapped"
        )
        self.assertEqual(
            map_detail_completeness("shidai", "complete"), "complete"
        )
        self.assertEqual(
            map_detail_completeness("shidai", "partial"), "partial"
        )
        self.assertIsNone(map_detail_completeness("shidai", ""))

    def test_research_activity_crosswalk(self) -> None:
        self.assertEqual(
            map_research_activity_level("kokkoritsu", "explicit_requirement"),
            "required",
        )
        self.assertEqual(
            map_research_activity_level("kokkoritsu", "探究活動重視"),
            "relevant",
        )
        self.assertEqual(
            map_research_activity_level("kokkoritsu", "なし"), "none"
        )
        self.assertEqual(
            map_research_activity_level("kokkoritsu", "not_specified"),
            "unknown",
        )
        self.assertEqual(
            map_research_activity_level("kokkoritsu", "activity_based"),
            "unmapped",
        )
        self.assertEqual(
            map_research_activity_level("shidai", "required"), "required"
        )
        self.assertIsNone(map_research_activity_level("kokkoritsu", ""))

    def test_null_crosswalk_status_is_reported_as_null_metric(self) -> None:
        self.assertEqual(metric_status(None), "null")
        self.assertEqual(metric_status("complete"), "complete")

    def test_strict_integer_parser(self) -> None:
        self.assertEqual(parse_int("2027"), 2027)
        self.assertEqual(parse_int("0"), 0)
        self.assertIsNone(parse_int(""))
        self.assertIsNone(parse_int(" 1"))
        self.assertIsNone(parse_int("1.0"))


class DateClassificationTests(unittest.TestCase):
    def test_date_parseability_without_rewriting(self) -> None:
        self.assertEqual(classify_raw_date(""), "not_applicable")
        self.assertEqual(classify_raw_date("2026-11-10"), "parsed")
        self.assertEqual(
            classify_raw_date("2026-11-10（第一次選考実施時）"), "partial"
        )
        self.assertEqual(classify_raw_date("2027-02-10 17:00"), "partial")
        self.assertEqual(classify_raw_date("Unknown"), "unparsed")
        self.assertEqual(classify_raw_date("2027-02-30"), "unparsed")


class ResultFormattingTests(unittest.TestCase):
    def test_summary_counts_and_representatives(self) -> None:
        result = ValidationResult(contract_version="0.1", repo_root=REPO_ROOT)
        result.issues.extend(
            [
                Issue(
                    code="E",
                    severity="error",
                    dataset="kokkoritsu",
                    table="master",
                    message="error",
                    record_id="K-1",
                ),
                Issue(
                    code="W",
                    severity="warning",
                    dataset="shidai",
                    table="master",
                    message="warning",
                    record_id="S-1",
                ),
                Issue(
                    code="W",
                    severity="warning",
                    dataset="shidai",
                    table="master",
                    message="warning",
                    record_id="S-1",
                ),
                Issue(
                    code="I",
                    severity="informational",
                    dataset="shidai",
                    table="coverage",
                    message="info",
                    record_id="S-2",
                ),
            ]
        )
        summary = result.summary(representative_limit=2)
        self.assertEqual(summary["status"], "failed")
        self.assertEqual(summary["by_severity"]["error"], 1)
        self.assertEqual(summary["by_severity"]["warning"], 2)
        self.assertEqual(summary["by_severity"]["informational"], 1)
        self.assertEqual(summary["by_code"]["W"]["count"], 2)
        self.assertEqual(
            summary["by_code"]["W"]["representative_record_ids"], ["S-1"]
        )

    def test_report_writers(self) -> None:
        result = ValidationResult(contract_version="0.1", repo_root=REPO_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            json_path = root / "report.json"
            markdown_path = root / "summary.md"
            write_json_report(result, json_path)
            write_markdown_report(result, markdown_path)
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["read_only"])
            self.assertEqual(payload["summary"]["status"], "passed")
            self.assertIn("read-only", markdown_path.read_text(encoding="utf-8"))


class SyntheticContractTests(unittest.TestCase):
    def test_minimal_valid_fixture_has_no_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build_synthetic_repo(root)
            result = ReadOnlyValidator(root).validate()
            self.assertEqual(result.summary()["by_severity"]["error"], 0)

    def test_error_paths_and_severity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            states = build_synthetic_repo(root)
            state = states["kokkoritsu"]
            canonical = state["canonical"]
            master = dict(state["master"])
            invalid_master = dict(master)
            invalid_master["stem_flag"] = "Maybe"
            write_csv(
                canonical / "master.csv",
                state["master_header"],
                [invalid_master, master],
            )

            coverage = dict(state["coverage"])
            coverage["master_rows"] = "0"
            write_csv(
                canonical / "coverage.csv",
                state["coverage_header"],
                [coverage],
            )

            research = {field: "" for field in state["research_header"]}
            research.update(
                {
                    "admission_id": "MISSING",
                    "university": "missing大学",
                    "source_url": "https://example.test/research",
                    "verified_on": "2026-09-20",
                }
            )
            write_csv(
                canonical / "research_requirements.csv",
                state["research_header"],
                [research, research],
            )

            result = ReadOnlyValidator(root).validate()
            summary = result.summary()
            self.assertGreater(summary["by_severity"]["error"], 0)
            self.assertEqual(summary["by_code"]["MASTER_PK_DUPLICATE"]["count"], 1)
            self.assertEqual(summary["by_code"]["INVALID_BOOLEAN_VALUE"]["count"], 1)
            self.assertEqual(
                summary["by_code"]["COVERAGE_MASTER_ROWS_MISMATCH"]["count"],
                1,
            )
            self.assertEqual(summary["by_code"]["RESEARCH_ORPHAN_FK"]["count"], 2)
            duplicate = summary["by_code"]["RESEARCH_EXACT_DUPLICATE"]
            self.assertEqual(duplicate["severity"], "warning")
            self.assertEqual(duplicate["count"], 1)

    def test_column_order_violation_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            states = build_synthetic_repo(root)
            state = states["shidai"]
            header = list(state["coverage_header"])
            header[0], header[1] = header[1], header[0]
            write_csv(
                state["canonical"] / "coverage.csv",
                header,
                [state["coverage"]],
            )
            result = ReadOnlyValidator(root).validate()
            finding = result.summary()["by_code"]["SOURCE_COLUMN_ORDER_MISMATCH"]
            self.assertEqual(finding["severity"], "error")
            self.assertEqual(finding["count"], 1)


class CanonicalIntegrationTests(unittest.TestCase):
    def test_current_canonical_snapshot(self) -> None:
        result = ReadOnlyValidator(REPO_ROOT).validate()
        summary = result.summary()
        self.assertEqual(summary["by_severity"]["error"], 0)
        self.assertEqual(len(result.inputs), 6)
        for issue in result.issues:
            self.assertEqual(issue.severity, CODE_SEVERITY[issue.code])

        expected_code_counts = {
            "RESEARCH_EXACT_DUPLICATE": 4,
            "RESEARCH_REQUIRED_WITHOUT_CHILD": 45,
            "RESEARCH_NOT_REQUIRED_WITH_CHILD": 55,
            "RESEARCH_DENORMALIZED_FIELD_MISMATCH": 10,
            "DETAIL_COMPLETENESS_UNMAPPED": 767,
            "RESEARCH_ACTIVITY_LEVEL_UNMAPPED": 281,
            "PROVENANCE_URL_MISSING": 55,
            "WHITESPACE_PADDING": 5,
            "COMMON_TEST_FIELDS_DIFFER": 109,
            "COVERAGE_ZERO_MASTER_ROWS": 10,
        }
        for code, expected in expected_code_counts.items():
            self.assertEqual(
                summary["by_code"][code]["count"],
                expected,
                msg=code,
            )

        self.assertGreater(summary["by_code"]["DATE_RAW_PARTIAL"]["count"], 0)
        self.assertGreater(summary["by_code"]["DATE_RAW_UNPARSED"]["count"], 0)
        self.assertEqual(
            result.metrics["crosswalks"]["kokkoritsu"]
            ["detail_completeness_status"]["unmapped"],
            767,
        )
        self.assertEqual(
            result.metrics["crosswalks"]["kokkoritsu"]
            ["research_activity_level_status"]["unmapped"],
            281,
        )


if __name__ == "__main__":
    unittest.main()
