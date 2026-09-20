"""Fail-closed exact crosswalk for the English-qualification search layer."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


ENGLISH_REQUIREMENT_CONTRACT_VERSION = "0.1"
ENGLISH_REQUIREMENT_SCHEMA_PATH = Path(
    "schema/sqlite/admission_search_english_requirement_schema_v0_1.sql"
)
ENGLISH_REQUIREMENT_CROSSWALK_PATH = Path(
    "schema/english_requirement/english_requirement_crosswalk_v0_1.csv"
)
ENGLISH_REQUIREMENT_DESIGN_PATH = Path(
    "docs/english_requirement_search_design_v0_1.md"
)
ENGLISH_REQUIREMENT_STATUSES = frozenset(
    {"required", "not_required", "review_required", "unknown", "not_applicable"}
)


@dataclass(frozen=True)
class EnglishRequirementResult:
    raw_value: str | None
    requirement_status: str
    parse_status: str
    search_disposition: str
    review_note: str | None

    def sqlite_values(self, admission_rowid: int) -> tuple[object, ...]:
        return (
            admission_rowid,
            self.raw_value,
            self.requirement_status,
            self.parse_status,
            self.search_disposition,
            ENGLISH_REQUIREMENT_CONTRACT_VERSION,
            self.review_note,
        )


class EnglishRequirementCrosswalk:
    def __init__(self, rows: dict[str, tuple[str, str]]) -> None:
        self._rows = rows

    @classmethod
    def load(cls, path: Path) -> "EnglishRequirementCrosswalk":
        rows: dict[str, tuple[str, str]] = {}
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            expected = ["contract_version", "raw_value", "requirement_status", "review_note"]
            if reader.fieldnames != expected:
                raise ValueError("English requirement crosswalk header mismatch.")
            for row in reader:
                if row["contract_version"] != ENGLISH_REQUIREMENT_CONTRACT_VERSION:
                    raise ValueError("English requirement crosswalk version mismatch.")
                raw = row["raw_value"]
                status = row["requirement_status"]
                if not raw or raw in rows or status not in ENGLISH_REQUIREMENT_STATUSES:
                    raise ValueError(f"Invalid English requirement crosswalk row: {raw!r}")
                rows[raw] = (status, row["review_note"])
        return cls(rows)

    def __len__(self) -> int:
        return len(self._rows)

    def classify(self, raw_value: str | None) -> EnglishRequirementResult:
        if raw_value is None:
            return EnglishRequirementResult(
                None, "unknown", "missing", "not_searchable", "原値がSQL NULL"
            )
        matched = self._rows.get(raw_value)
        if matched is None:
            return EnglishRequirementResult(
                raw_value,
                "unmapped",
                "unmapped",
                "review_required",
                "監査済みcrosswalkにない新規原値",
            )
        status, note = matched
        disposition = (
            "safe_exact"
            if status in {"required", "not_required"}
            else "review_required"
            if status == "review_required"
            else "not_searchable"
        )
        return EnglishRequirementResult(
            raw_value, status, "exact_crosswalk", disposition, note or None
        )
