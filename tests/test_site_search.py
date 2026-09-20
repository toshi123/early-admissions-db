from __future__ import annotations

import unittest

from early_admissions.site_search import SearchRequest, SiteSearchError, search_rows


def row(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "source_dataset": "fixture",
        "source_version": "1",
        "record_id": "A",
        "university": "大学A",
        "institution_type": "国立",
        "prefecture": "東京都",
        "academic_field": "工学",
        "academic_field_groups": ["engineering"],
        "academic_field_mapping_status": "single",
        "stem_flag": True,
        "selection_category": "総合型選抜",
        "exclusive_enrollment_status": "専願",
        "school_recommendation_required": "No",
        "academic_record_required": "Yes",
        "common_test_required": "No",
        "research_requirement_required": "Unknown",
        "research_activity_level_status": None,
        "selection_interview": "Yes",
        "selection_oral_exam": "No",
        "selection_presentation": "Unknown",
        "selection_essay": None,
        "selection_written_exam": "No",
        "selection_common_test": "No",
        "faculty_school": "工学部",
        "department": None,
        "selection_name": "選抜A",
        "gpa_parse_status": "parsed_safe",
        "gpa_min_tenths": 38,
        "gpa_min_inclusive": True,
        "gpa_max_tenths": None,
        "gpa_max_inclusive": None,
    }
    value.update(updates)
    return value


class SiteSearchUnitTests(unittest.TestCase):
    def test_and_between_fields_or_within_field(self) -> None:
        rows = [
            row(),
            row(record_id="B", prefecture="神奈川県", university="大学B"),
            row(record_id="C", prefecture="大阪府", university="大学A"),
        ]
        result = search_rows(
            rows,
            SearchRequest(
                prefecture=("東京都", "神奈川県"), university=("大学A",)
            ),
            limit=None,
        )
        self.assertEqual([item["record_id"] for item in result.rows], ["A"])

    def test_gpa_modes_fail_closed(self) -> None:
        rows = [
            row(),
            row(record_id="B", gpa_parse_status="conditional_review", gpa_min_tenths=None, gpa_min_inclusive=None),
            row(record_id="C", gpa_parse_status="not_numeric", gpa_min_tenths=None, gpa_min_inclusive=None),
        ]
        safe = search_rows(rows, SearchRequest(gpa_tenths=38, gpa_mode="safe"), limit=None)
        review = search_rows(rows, SearchRequest(gpa_tenths=38, gpa_mode="review"), limit=None)
        all_rows = search_rows(rows, SearchRequest(gpa_tenths=38, gpa_mode="all"), limit=None)
        self.assertEqual(safe.summary.total_matched_rows, 1)
        self.assertEqual(review.summary.total_matched_rows, 2)
        self.assertEqual(all_rows.summary.total_matched_rows, 3)
        self.assertEqual(all_rows.summary.gpa_not_numerically_evaluable_rows, 1)

    def test_null_unknown_and_no_are_distinct(self) -> None:
        rows = [
            row(record_id="NULL", selection_essay=None),
            row(record_id="UNKNOWN", selection_essay="Unknown"),
            row(record_id="NO", selection_essay="No"),
        ]
        result = search_rows(
            rows, SearchRequest(selection_essay=("Unknown",)), limit=None
        )
        self.assertEqual([item["record_id"] for item in result.rows], ["UNKNOWN"])

    def test_invalid_gpa_mode_without_value_is_rejected(self) -> None:
        with self.assertRaisesRegex(SiteSearchError, "requires a GPA"):
            search_rows([], SearchRequest(gpa_mode="review"))


if __name__ == "__main__":
    unittest.main()
