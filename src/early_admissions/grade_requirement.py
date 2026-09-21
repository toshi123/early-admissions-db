"""Exact-reviewed, fail-closed grade-requirement search mapping."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


GRADE_REQUIREMENT_MAPPING_CONTRACT_VERSION = "0.1"
GRADE_REQUIREMENT_SCHEMA_PATH = Path(
    "schema/sqlite/admission_search_grade_requirement_schema_v0_1.sql"
)
GRADE_REQUIREMENT_CROSSWALK_PATH = Path(
    "schema/grade_requirement/grade_requirement_crosswalk_v0_1.csv"
)
GRADE_REQUIREMENT_DESIGN_PATH = Path(
    "docs/grade_requirement_search_design_v0_1.md"
)

GRADE_REQUIREMENT_STATUSES = frozenset(
    {
        "required",
        "not_required",
        "review_required",
        "unknown",
        "not_applicable",
    }
)
OVERALL_GPA_STATUSES = frozenset(
    {
        "safe_simple_overall",
        "safe_overall_with_additional_conditions",
        "no_safe_overall_floor",
        "historical",
        "non_binding",
        "non_admission_numeric",
        "ambiguous",
        "unknown",
        "not_applicable",
    }
)


@dataclass(frozen=True)
class GradeRequirementResult:
    raw_value: str | None
    grade_requirement_status: str
    overall_gpa_min_tenths: int | None
    overall_gpa_min_inclusive: int | None
    overall_gpa_status: str
    additional_grade_conditions: int | None
    parse_status: str
    mapping_contract_version: str
    review_note: str | None

    def sqlite_values(self, admission_rowid: int) -> tuple[object, ...]:
        return (
            admission_rowid,
            self.raw_value,
            self.grade_requirement_status,
            self.overall_gpa_min_tenths,
            self.overall_gpa_min_inclusive,
            self.overall_gpa_status,
            self.additional_grade_conditions,
            self.parse_status,
            self.mapping_contract_version,
            self.review_note,
        )


class GradeRequirementCrosswalk:
    """A complete exact-value map for every reviewed non-NULL raw value."""

    _HEADER = [
        "contract_version",
        "raw_value",
        "grade_requirement_status",
        "overall_gpa_min_tenths",
        "overall_gpa_min_inclusive",
        "overall_gpa_status",
        "additional_grade_conditions",
        "review_note",
    ]

    def __init__(self, rows: dict[str, GradeRequirementResult]) -> None:
        self._rows = rows

    @classmethod
    def load(cls, path: Path) -> "GradeRequirementCrosswalk":
        rows: dict[str, GradeRequirementResult] = {}
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != cls._HEADER:
                raise ValueError("Grade-requirement crosswalk header mismatch.")
            for row in reader:
                if row["contract_version"] != GRADE_REQUIREMENT_MAPPING_CONTRACT_VERSION:
                    raise ValueError("Grade-requirement crosswalk version mismatch.")
                raw = row["raw_value"]
                status = row["grade_requirement_status"]
                overall_status = row["overall_gpa_status"]
                if (
                    not raw
                    or raw in rows
                    or status not in GRADE_REQUIREMENT_STATUSES
                    or overall_status not in OVERALL_GPA_STATUSES
                ):
                    raise ValueError(f"Invalid grade-requirement crosswalk row: {raw!r}")
                minimum = _optional_tenths(row["overall_gpa_min_tenths"])
                inclusive = _optional_bool(row["overall_gpa_min_inclusive"])
                additional = _optional_bool(row["additional_grade_conditions"])
                safe_status = overall_status in {
                    "safe_simple_overall",
                    "safe_overall_with_additional_conditions",
                }
                if safe_status != (minimum is not None):
                    raise ValueError(f"Unsafe overall GPA mapping for {raw!r}")
                if minimum is not None:
                    if inclusive != 1 or additional is None or status != "required":
                        raise ValueError(f"Incomplete overall GPA mapping for {raw!r}")
                    expected_status = (
                        "safe_overall_with_additional_conditions"
                        if additional
                        else "safe_simple_overall"
                    )
                    if overall_status != expected_status:
                        raise ValueError(f"Additional-condition mismatch for {raw!r}")
                elif inclusive is not None or additional is not None:
                    raise ValueError(f"Numeric flags without a safe floor for {raw!r}")
                rows[raw] = GradeRequirementResult(
                    raw_value=raw,
                    grade_requirement_status=status,
                    overall_gpa_min_tenths=minimum,
                    overall_gpa_min_inclusive=inclusive,
                    overall_gpa_status=overall_status,
                    additional_grade_conditions=additional,
                    parse_status="exact_crosswalk",
                    mapping_contract_version=GRADE_REQUIREMENT_MAPPING_CONTRACT_VERSION,
                    review_note=row["review_note"] or None,
                )
        return cls(rows)

    def __len__(self) -> int:
        return len(self._rows)

    def classify(self, raw_value: str | None) -> GradeRequirementResult:
        if raw_value is None:
            return GradeRequirementResult(
                raw_value=None,
                grade_requirement_status="unknown",
                overall_gpa_min_tenths=None,
                overall_gpa_min_inclusive=None,
                overall_gpa_status="unknown",
                additional_grade_conditions=None,
                parse_status="missing",
                mapping_contract_version=GRADE_REQUIREMENT_MAPPING_CONTRACT_VERSION,
                review_note="原値がSQL NULL",
            )
        matched = self._rows.get(raw_value)
        if matched is not None:
            return matched
        return GradeRequirementResult(
            raw_value=raw_value,
            grade_requirement_status="unmapped",
            overall_gpa_min_tenths=None,
            overall_gpa_min_inclusive=None,
            overall_gpa_status="unmapped",
            additional_grade_conditions=None,
            parse_status="unmapped",
            mapping_contract_version=GRADE_REQUIREMENT_MAPPING_CONTRACT_VERSION,
            review_note="監査済みcrosswalkにない新規原値",
        )


def _optional_tenths(raw: str) -> int | None:
    if raw == "":
        return None
    value = int(raw)
    if not 0 <= value <= 50:
        raise ValueError(f"Grade tenths outside 0..50: {value}")
    return value


def _optional_bool(raw: str) -> int | None:
    if raw == "":
        return None
    if raw not in {"0", "1"}:
        raise ValueError(f"Expected blank, 0, or 1; got {raw!r}")
    return int(raw)
