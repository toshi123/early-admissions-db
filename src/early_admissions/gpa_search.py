"""Fail-closed GPA derived-layer parser and read-only search helpers."""

from __future__ import annotations

import csv
import re
import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator, Mapping


GPA_PARSER_CONTRACT_VERSION = "0.1"
GPA_RESULT_MEANING = "overall GPA condition safely matched"
GPA_AUDIT_PATH = Path(
    "validation/reports/gpa_requirement_raw_value_audit_v0_1.csv"
)
GPA_SCHEMA_PATH = Path("schema/sqlite/admission_search_gpa_schema_v0_1.sql")
GPA_DESIGN_PATH = Path("docs/gpa_search_design_v0_1.md")

AUDIT_COLUMNS = (
    "raw_value",
    "row_count",
    "kokkoritsu_rows",
    "shidai_rows",
    "distinct_tier",
    "primary_class",
    "feature_flags",
    "numeric_tokens",
    "safe_gpa_min",
    "safe_gpa_max",
    "fallback_previous_year_rows",
    "representative_record_ids",
    "review_status",
)
NUMERIC_SAFETY_TIERS = {"safe_numeric", "conditional_numeric", "do_not_numeric"}
CONDITIONAL_TYPES = {
    "or_condition": "alternative_or",
    "overall_and_subject_compound": "compound_and",
    "and_condition": "compound_and",
    "subject_specific_condition": "subject_specific",
    "branch_condition": "branching",
    "range_or_upper_condition": "other",
    "other_complex_numeric": "other",
}
_GPA_INPUT = re.compile(r"(?:[0-4](?:\.[0-9])?|5(?:\.0)?)\Z")


class GPAContractError(ValueError):
    """Raised when the approved GPA crosswalk or a GPA query is invalid."""


@dataclass(frozen=True)
class GPARawRule:
    raw_value: str | None
    numeric_safety_tier: str
    primary_class: str
    feature_flags: frozenset[str]
    safe_gpa_min_tenths: int | None
    safe_gpa_max_tenths: int | None


@dataclass(frozen=True)
class GPAParseResult:
    raw_value: str | None
    numeric_safety_tier: str
    gpa_min_tenths: int | None
    gpa_min_inclusive: int | None
    gpa_max_tenths: int | None
    gpa_max_inclusive: int | None
    gpa_scale: str
    metric_scope: str
    gpa_condition_type: str
    parse_status: str
    search_disposition: str
    source_value_status: str
    has_subject_condition: int
    has_and_condition: int
    has_or_condition: int
    has_branch_condition: int
    parser_contract_version: str = GPA_PARSER_CONTRACT_VERSION

    def sqlite_values(self, admission_rowid: int) -> tuple[Any, ...]:
        """Return values in admission_search_gpa insertion order."""

        return (
            admission_rowid,
            self.raw_value,
            self.gpa_min_tenths,
            self.gpa_min_inclusive,
            self.gpa_max_tenths,
            self.gpa_max_inclusive,
            self.gpa_scale,
            self.metric_scope,
            self.gpa_condition_type,
            self.parse_status,
            self.search_disposition,
            self.source_value_status,
            self.has_subject_condition,
            self.has_and_condition,
            self.has_or_condition,
            self.has_branch_condition,
            self.parser_contract_version,
        )


@dataclass(frozen=True)
class GPASearchResult:
    student_gpa_tenths: int
    meaning: str
    total_matches: int
    rows: tuple[Mapping[str, Any], ...]


class GPACrosswalk:
    """Exact raw-value allowlist produced by the reviewed v0.1 audit."""

    def __init__(self, rules: Mapping[str | None, GPARawRule]) -> None:
        self._rules = dict(rules)

    @classmethod
    def load(cls, path: Path) -> "GPACrosswalk":
        rules: dict[str | None, GPARawRule] = {}
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != AUDIT_COLUMNS:
                raise GPAContractError(
                    f"GPA audit column mismatch: {tuple(reader.fieldnames or ())!r}"
                )
            for line_number, row in enumerate(reader, start=2):
                raw_value = row["raw_value"] or None
                if raw_value in rules:
                    raise GPAContractError(
                        f"Duplicate GPA audit raw value at line {line_number}: "
                        f"{raw_value!r}"
                    )
                tier = row["distinct_tier"]
                if tier not in NUMERIC_SAFETY_TIERS:
                    raise GPAContractError(
                        f"Invalid GPA audit tier at line {line_number}: {tier!r}"
                    )
                if row["review_status"] != "reviewed":
                    raise GPAContractError(
                        f"Unreviewed GPA audit rule at line {line_number}"
                    )
                flags = frozenset(filter(None, row["feature_flags"].split(";")))
                minimum = _optional_audited_tenths(row["safe_gpa_min"])
                maximum = _optional_audited_tenths(row["safe_gpa_max"])
                if tier == "safe_numeric":
                    if row["primary_class"] != "simple_overall_minimum":
                        raise GPAContractError(
                            f"Safe GPA rule is not a simple minimum at line {line_number}"
                        )
                    if minimum is None or maximum is not None:
                        raise GPAContractError(
                            f"Safe GPA bounds are invalid at line {line_number}"
                        )
                    if flags.intersection({"subject", "and", "or", "branch", "historical", "nonbinding"}):
                        raise GPAContractError(
                            f"Safe GPA rule has an unsafe flag at line {line_number}"
                        )
                elif minimum is not None or maximum is not None:
                    raise GPAContractError(
                        f"Non-safe GPA rule has approved bounds at line {line_number}"
                    )
                rules[raw_value] = GPARawRule(
                    raw_value=raw_value,
                    numeric_safety_tier=tier,
                    primary_class=row["primary_class"],
                    feature_flags=flags,
                    safe_gpa_min_tenths=minimum,
                    safe_gpa_max_tenths=maximum,
                )
        if None not in rules:
            raise GPAContractError("GPA audit must include the SQL NULL class.")
        return cls(rules)

    def get(self, raw_value: str | None) -> GPARawRule | None:
        return self._rules.get(raw_value)

    def __len__(self) -> int:
        return len(self._rules)


class GPAParser:
    """Apply only exact, reviewed rules; every unknown expression fails closed."""

    def __init__(self, crosswalk: GPACrosswalk) -> None:
        self.crosswalk = crosswalk

    def parse(
        self,
        raw_value: str | None,
        *,
        admission_year: int | None,
        information_year: int | None,
        fallback_previous_year: int | bool | None,
    ) -> GPAParseResult:
        rule = self.crosswalk.get(raw_value)
        fallback = fallback_previous_year in (1, True)
        explicitly_historical = bool(
            rule and "historical" in rule.feature_flags
        )
        year_mismatch = (
            admission_year is not None
            and information_year is not None
            and admission_year != information_year
        )
        historical = fallback or explicitly_historical or year_mismatch

        if raw_value is None:
            return self._result(
                raw_value=None,
                rule=rule,
                tier="do_not_numeric",
                gpa_condition_type="not_applicable",
                parse_status="not_applicable",
                search_disposition="not_searchable",
                gpa_scale="unknown",
                metric_scope="none",
                source_value_status=(
                    "previous_year_reference" if historical else "current"
                ),
            )
        if historical:
            return self._result(
                raw_value=raw_value,
                rule=rule,
                tier="do_not_numeric",
                gpa_condition_type="historical_reference",
                parse_status="historical_reference",
                search_disposition="not_searchable",
                gpa_scale="unknown",
                metric_scope=_metric_scope(rule),
                source_value_status="previous_year_reference",
            )
        if rule is None:
            return self._result(
                raw_value=raw_value,
                rule=None,
                tier="do_not_numeric",
                gpa_condition_type="other",
                parse_status="unparsed",
                search_disposition="review_required",
                gpa_scale="unknown",
                metric_scope="unknown",
                source_value_status="current",
            )
        if rule.numeric_safety_tier == "safe_numeric":
            if (
                admission_year is None
                or information_year is None
                or admission_year != information_year
            ):
                return self._result(
                    raw_value=raw_value,
                    rule=rule,
                    tier="do_not_numeric",
                    gpa_condition_type="other",
                    parse_status="unparsed",
                    search_disposition="review_required",
                    gpa_scale="unknown",
                    metric_scope="unknown",
                    source_value_status="current",
                )
            return self._result(
                raw_value=raw_value,
                rule=rule,
                tier="safe_numeric",
                gpa_condition_type="simple_overall_minimum",
                parse_status="parsed_safe",
                search_disposition="safe_numeric",
                gpa_scale="japanese_5_point",
                metric_scope="overall",
                source_value_status="current",
                gpa_min_tenths=rule.safe_gpa_min_tenths,
                gpa_min_inclusive=1,
            )
        if rule.numeric_safety_tier == "conditional_numeric":
            return self._result(
                raw_value=raw_value,
                rule=rule,
                tier="conditional_numeric",
                gpa_condition_type=CONDITIONAL_TYPES[rule.primary_class],
                parse_status="conditional_review",
                search_disposition="review_required",
                gpa_scale="japanese_5_point",
                metric_scope=_metric_scope(rule),
                source_value_status="current",
            )

        condition_type, parse_status, disposition = _do_not_numeric_status(rule)
        return self._result(
            raw_value=raw_value,
            rule=rule,
            tier="do_not_numeric",
            gpa_condition_type=condition_type,
            parse_status=parse_status,
            search_disposition=disposition,
            gpa_scale="unknown",
            metric_scope=_metric_scope(rule),
            source_value_status="current",
        )

    @staticmethod
    def _result(
        *,
        raw_value: str | None,
        rule: GPARawRule | None,
        tier: str,
        gpa_condition_type: str,
        parse_status: str,
        search_disposition: str,
        gpa_scale: str,
        metric_scope: str,
        source_value_status: str,
        gpa_min_tenths: int | None = None,
        gpa_min_inclusive: int | None = None,
    ) -> GPAParseResult:
        flags = rule.feature_flags if rule else frozenset()
        return GPAParseResult(
            raw_value=raw_value,
            numeric_safety_tier=tier,
            gpa_min_tenths=gpa_min_tenths,
            gpa_min_inclusive=gpa_min_inclusive,
            gpa_max_tenths=None,
            gpa_max_inclusive=None,
            gpa_scale=gpa_scale,
            metric_scope=metric_scope,
            gpa_condition_type=gpa_condition_type,
            parse_status=parse_status,
            search_disposition=search_disposition,
            source_value_status=source_value_status,
            has_subject_condition=int("subject" in flags),
            has_and_condition=int("and" in flags),
            has_or_condition=int("or" in flags),
            has_branch_condition=int("branch" in flags),
        )


def _optional_audited_tenths(value: str) -> int | None:
    if value == "":
        return None
    return _decimal_to_tenths(value, label="audited GPA")


def parse_gpa_tenths(value: str) -> int:
    """Parse a query GPA without using binary floating point."""

    if not _GPA_INPUT.fullmatch(value):
        raise GPAContractError(
            "GPA must be from 0 to 5 with at most one decimal place."
        )
    return _decimal_to_tenths(value, label="GPA")


def _decimal_to_tenths(value: str, *, label: str) -> int:
    decimal = Decimal(value)
    tenths = decimal * 10
    if tenths != tenths.to_integral_value() or not 0 <= tenths <= 50:
        raise GPAContractError(f"{label} is not an exact Japanese five-point tenth: {value!r}")
    return int(tenths)


def _metric_scope(rule: GPARawRule | None) -> str:
    if rule is None:
        return "unknown"
    has_subject = "subject" in rule.feature_flags
    if rule.primary_class == "subject_specific_condition":
        return "subject"
    if rule.primary_class == "overall_and_subject_compound" or has_subject:
        return "mixed"
    if rule.primary_class in {"null", "explicit_no_numeric_threshold", "non_numeric_condition"}:
        return "none"
    if rule.numeric_safety_tier == "conditional_numeric":
        return "overall"
    return "unknown"


def _do_not_numeric_status(rule: GPARawRule) -> tuple[str, str, str]:
    if rule.primary_class == "unknown":
        return "unknown", "unknown", "not_searchable"
    if rule.primary_class == "unresolved":
        return "other", "unparsed", "review_required"
    if rule.primary_class == "explicit_no_numeric_threshold":
        return "no_numeric_threshold", "not_numeric", "not_searchable"
    if rule.primary_class == "non_numeric_condition":
        return "qualitative", "not_numeric", "not_searchable"
    if rule.primary_class == "non_admission_or_inoperative_numeric":
        return "non_admission_numeric", "not_numeric", "not_searchable"
    if rule.primary_class == "nonbinding_or_historical_numeric":
        return "qualitative", "not_numeric", "not_searchable"
    return "other", "unparsed", "review_required"


def iter_safe_matches(
    connection: sqlite3.Connection, student_gpa_tenths: int, *, limit: int
) -> Iterator[sqlite3.Row]:
    sql = """
        SELECT a.source_dataset, a.source_version, a.record_id,
               a.university, a.faculty_school, a.department,
               a.selection_name, g.raw_value, g.gpa_min_tenths,
               g.gpa_min
        FROM admission_search_gpa_safe AS g
        JOIN admissions AS a USING (admission_rowid)
        WHERE (? > g.gpa_min_tenths
               OR (? = g.gpa_min_tenths AND g.gpa_min_inclusive = 1))
          AND (g.gpa_max_tenths IS NULL
               OR ? < g.gpa_max_tenths
               OR (? = g.gpa_max_tenths AND g.gpa_max_inclusive = 1))
        ORDER BY a.source_dataset, a.source_version, a.record_id
        LIMIT ?
    """
    yield from connection.execute(
        sql,
        (
            student_gpa_tenths,
            student_gpa_tenths,
            student_gpa_tenths,
            student_gpa_tenths,
            limit,
        ),
    )


def search_gpa(database_path: Path, value: str, *, limit: int = 20) -> GPASearchResult:
    """Search only the safe subset through an immutable, read-only connection."""

    if limit < 0:
        raise GPAContractError("limit must be zero or greater")
    student_gpa_tenths = parse_gpa_tenths(value)
    uri = database_path.resolve().as_uri() + "?mode=ro&immutable=1"
    try:
        connection = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as error:
        raise GPAContractError(f"Cannot open SQLite database read-only: {error}") from error
    connection.row_factory = sqlite3.Row
    try:
        contract = connection.execute(
            "SELECT DISTINCT parser_contract_version FROM admission_search_gpa"
        ).fetchall()
        if [row[0] for row in contract] not in (
            [],
            [GPA_PARSER_CONTRACT_VERSION],
        ):
            raise GPAContractError("SQLite GPA parser contract version is incompatible.")
        count = connection.execute(
            """
            SELECT COUNT(*) FROM admission_search_gpa_safe AS g
            WHERE (? > g.gpa_min_tenths
                   OR (? = g.gpa_min_tenths AND g.gpa_min_inclusive = 1))
              AND (g.gpa_max_tenths IS NULL
                   OR ? < g.gpa_max_tenths
                   OR (? = g.gpa_max_tenths AND g.gpa_max_inclusive = 1))
            """,
            (student_gpa_tenths,) * 4,
        ).fetchone()[0]
        rows = tuple(
            dict(row)
            for row in iter_safe_matches(
                connection, student_gpa_tenths, limit=limit
            )
        )
    except sqlite3.Error as error:
        raise GPAContractError(f"SQLite GPA layer is unavailable: {error}") from error
    finally:
        connection.close()
    return GPASearchResult(
        student_gpa_tenths=student_gpa_tenths,
        meaning=GPA_RESULT_MEANING,
        total_matches=count,
        rows=rows,
    )
