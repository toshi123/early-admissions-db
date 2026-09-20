"""Read-only, parameterized structured search over the published SQLite DB."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from .academic_field import (
    ACADEMIC_FIELD_MAPPING_CONTRACT_VERSION,
    ACADEMIC_FIELD_TAXONOMY_VERSION,
    GENERATED_MAPPING_STATUSES,
)
from .gpa_search import GPA_PARSER_CONTRACT_VERSION


SEARCH_CONTRACT_VERSION = "0.1"
GPA_MODES = frozenset({"safe", "review", "all"})

# SQL identifiers are fixed by this module. User values are always bound parameters.
MULTI_VALUE_FIELDS: tuple[str, ...] = (
    "university",
    "institution_type",
    "prefecture",
    "academic_field",
    "selection_category",
    "exclusive_enrollment_status",
    "school_recommendation_required",
    "academic_record_required",
    "common_test_required",
    "research_requirement_required",
    "research_activity_level_status",
    "selection_interview",
    "selection_oral_exam",
    "selection_presentation",
    "selection_essay",
    "selection_written_exam",
    "selection_common_test",
)

RESULT_COLUMNS: tuple[str, ...] = (
    "source_dataset",
    "source_version",
    "record_id",
    "institution_type",
    "university",
    "faculty_school",
    "department",
    "selection_category",
    "selection_name",
    "capacity",
    "prefecture",
    "academic_field",
    "academic_field_mapping_status",
    "academic_field_groups",
    "stem_flag",
    "exclusive_enrollment_status",
    "school_recommendation_required",
    "academic_record_required",
    "gpa_requirement",
    "gpa_derived_status",
    "gpa_parse_status",
    "gpa_search_disposition",
    "gpa_min_tenths",
    "common_test_required",
    "research_requirement_required",
    "research_activity_level_status",
    "selection_interview",
    "selection_oral_exam",
    "selection_presentation",
    "selection_essay",
    "selection_written_exam",
    "selection_common_test",
    "application_start",
    "application_end",
)

_SAFE_MATCH_SQL = """
(
    gs.admission_rowid IS NOT NULL
    AND (
        q.student_gpa_tenths > gs.gpa_min_tenths
        OR (
            q.student_gpa_tenths = gs.gpa_min_tenths
            AND gs.gpa_min_inclusive = 1
        )
    )
    AND (
        gs.gpa_max_tenths IS NULL
        OR q.student_gpa_tenths < gs.gpa_max_tenths
        OR (
            q.student_gpa_tenths = gs.gpa_max_tenths
            AND gs.gpa_max_inclusive = 1
        )
    )
)
""".strip()


class StructuredSearchError(RuntimeError):
    """Raised when search input or the read-only database is incompatible."""


@dataclass(frozen=True)
class SearchCriteria:
    university: tuple[str, ...] = ()
    institution_type: tuple[str, ...] = ()
    prefecture: tuple[str, ...] = ()
    academic_field: tuple[str, ...] = ()
    academic_field_group: tuple[str, ...] = ()
    academic_field_mapping_status: tuple[str, ...] = ()
    stem_flag: bool | None = None
    selection_category: tuple[str, ...] = ()
    exclusive_enrollment_status: tuple[str, ...] = ()
    school_recommendation_required: tuple[str, ...] = ()
    academic_record_required: tuple[str, ...] = ()
    common_test_required: tuple[str, ...] = ()
    research_requirement_required: tuple[str, ...] = ()
    research_activity_level_status: tuple[str, ...] = ()
    selection_interview: tuple[str, ...] = ()
    selection_oral_exam: tuple[str, ...] = ()
    selection_presentation: tuple[str, ...] = ()
    selection_essay: tuple[str, ...] = ()
    selection_written_exam: tuple[str, ...] = ()
    selection_common_test: tuple[str, ...] = ()
    gpa_tenths: int | None = None
    gpa_mode: str = "all"

    def validate(self) -> None:
        if self.gpa_mode not in GPA_MODES:
            raise StructuredSearchError(f"Unsupported GPA mode: {self.gpa_mode!r}")
        if self.gpa_tenths is None and self.gpa_mode != "all":
            raise StructuredSearchError("GPA mode safe/review requires a GPA value.")
        if self.gpa_tenths is not None and not 0 <= self.gpa_tenths <= 50:
            raise StructuredSearchError("GPA tenths must be between 0 and 50.")
        for field_name in MULTI_VALUE_FIELDS:
            values = getattr(self, field_name)
            if not isinstance(values, tuple):
                raise StructuredSearchError(
                    f"{field_name} values must be supplied as a tuple."
                )
            if any(not isinstance(value, str) or value == "" for value in values):
                raise StructuredSearchError(
                    f"{field_name} contains an empty or non-text value."
                )
        for field_name in (
            "academic_field_group",
            "academic_field_mapping_status",
        ):
            values = getattr(self, field_name)
            if not isinstance(values, tuple):
                raise StructuredSearchError(
                    f"{field_name} values must be supplied as a tuple."
                )
            if any(not isinstance(value, str) or value == "" for value in values):
                raise StructuredSearchError(
                    f"{field_name} contains an empty or non-text value."
                )
        invalid_statuses = set(self.academic_field_mapping_status).difference(
            GENERATED_MAPPING_STATUSES
        )
        if invalid_statuses:
            raise StructuredSearchError(
                "Unsupported academic-field mapping status: "
                + ", ".join(sorted(invalid_statuses))
            )


@dataclass(frozen=True)
class SearchSummary:
    total_matched_rows: int
    gpa_safe_match_rows: int | None
    gpa_safe_no_match_rows: int | None
    gpa_safe_numeric_rule_rows: int
    gpa_conditional_review_rows: int
    gpa_not_numerically_evaluable_rows: int
    rows_by_source_dataset: Mapping[str, int]
    university_count: int


@dataclass(frozen=True)
class SearchResult:
    criteria: SearchCriteria
    summary: SearchSummary
    rows: tuple[Mapping[str, Any], ...]
    offset: int
    limit: int | None
    result_meaning: str = (
        "safe match means overall GPA condition safely matched; "
        "it is not an application-eligibility determination"
    )


@dataclass(frozen=True)
class CompiledSearch:
    sql: str
    parameters: tuple[Any, ...]


@dataclass(frozen=True)
class _CompiledBase:
    from_sql: str
    where_sql: str
    parameters: tuple[Any, ...]
    gpa_supplied: bool


@contextmanager
def open_readonly_database(database_path: Path) -> Iterator[sqlite3.Connection]:
    """Open SQLite with both URI read-only mode and query_only protection."""

    path = database_path.resolve()
    if not path.is_file():
        raise StructuredSearchError(f"SQLite database does not exist: {path}")
    uri = path.as_uri() + "?mode=ro&immutable=1"
    try:
        connection = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as error:
        raise StructuredSearchError(
            f"Cannot open SQLite database read-only: {error}"
        ) from error
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        if connection.execute("PRAGMA query_only").fetchone()[0] != 1:
            raise StructuredSearchError("SQLite query_only mode could not be enabled.")
        _validate_database_contract(connection)
        yield connection
    except sqlite3.Error as error:
        raise StructuredSearchError(f"SQLite search failed: {error}") from error
    finally:
        connection.close()


def _validate_database_contract(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT database_schema_version, gpa_parser_contract_version,
               academic_field_mapping_contract_version,
               academic_field_taxonomy_version
        FROM build_metadata
        """
    ).fetchall()
    if len(rows) != 1:
        raise StructuredSearchError(
            "build_metadata must contain exactly one compatibility row."
        )
    if rows[0]["database_schema_version"] != "0.1":
        raise StructuredSearchError("SQLite database schema version is not 0.1.")
    if rows[0]["gpa_parser_contract_version"] != GPA_PARSER_CONTRACT_VERSION:
        raise StructuredSearchError("GPA parser contract version is incompatible.")
    if (
        rows[0]["academic_field_mapping_contract_version"]
        != ACADEMIC_FIELD_MAPPING_CONTRACT_VERSION
    ):
        raise StructuredSearchError(
            "Academic-field mapping contract version is incompatible."
        )
    if (
        rows[0]["academic_field_taxonomy_version"]
        != ACADEMIC_FIELD_TAXONOMY_VERSION
    ):
        raise StructuredSearchError(
            "Academic-field taxonomy version is incompatible."
        )


def _validate_academic_filter_values(
    connection: sqlite3.Connection, criteria: SearchCriteria
) -> None:
    if not criteria.academic_field_group:
        return
    approved = {
        row[0]
        for row in connection.execute(
            "SELECT group_code FROM academic_field_taxonomy"
        )
    }
    invalid = set(criteria.academic_field_group).difference(approved)
    if invalid:
        raise StructuredSearchError(
            "Unknown academic-field group: " + ", ".join(sorted(invalid))
        )


def _compile_base(criteria: SearchCriteria) -> _CompiledBase:
    criteria.validate()
    parameters: list[Any] = []
    predicates: list[str] = []
    if criteria.gpa_tenths is not None:
        from_sql = """
            FROM admissions AS a
            JOIN admission_search_gpa AS g USING (admission_rowid)
            LEFT JOIN admission_search_gpa_safe AS gs USING (admission_rowid)
            JOIN admission_search_academic_fields AS af USING (admission_rowid)
            CROSS JOIN (SELECT ? AS student_gpa_tenths) AS q
        """
        parameters.append(criteria.gpa_tenths)
    else:
        from_sql = """
            FROM admissions AS a
            JOIN admission_search_gpa AS g USING (admission_rowid)
            LEFT JOIN admission_search_gpa_safe AS gs USING (admission_rowid)
            JOIN admission_search_academic_fields AS af USING (admission_rowid)
        """

    for field_name in MULTI_VALUE_FIELDS:
        values = _deduplicate(getattr(criteria, field_name))
        if not values:
            continue
        placeholders = ", ".join("?" for _ in values)
        predicates.append(f"a.{field_name} IN ({placeholders})")
        parameters.extend(values)
    group_values = _deduplicate(criteria.academic_field_group)
    if group_values:
        placeholders = ", ".join("?" for _ in group_values)
        predicates.append(
            "EXISTS ("
            "SELECT 1 FROM admission_search_academic_field_groups AS afg "
            "WHERE afg.admission_rowid = a.admission_rowid "
            f"AND afg.group_code IN ({placeholders})"
            ")"
        )
        parameters.extend(group_values)
    status_values = _deduplicate(criteria.academic_field_mapping_status)
    if status_values:
        placeholders = ", ".join("?" for _ in status_values)
        predicates.append(f"af.mapping_status IN ({placeholders})")
        parameters.extend(status_values)
    if criteria.stem_flag is not None:
        predicates.append("a.stem_flag = ?")
        parameters.append(int(criteria.stem_flag))

    if criteria.gpa_tenths is not None:
        if criteria.gpa_mode == "safe":
            predicates.append(_SAFE_MATCH_SQL)
        elif criteria.gpa_mode == "review":
            predicates.append(
                f"({_SAFE_MATCH_SQL} OR g.parse_status = 'conditional_review')"
            )
    where_sql = "WHERE " + " AND ".join(predicates) if predicates else ""
    return _CompiledBase(
        from_sql=from_sql,
        where_sql=where_sql,
        parameters=tuple(parameters),
        gpa_supplied=criteria.gpa_tenths is not None,
    )


def _deduplicate(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _gpa_status_sql(gpa_supplied: bool) -> str:
    if gpa_supplied:
        return f"""
            CASE
                WHEN {_SAFE_MATCH_SQL} THEN 'safe match'
                WHEN g.parse_status = 'parsed_safe' THEN 'safe no match'
                WHEN g.parse_status = 'conditional_review'
                    THEN 'conditional/review required'
                ELSE 'not numerically evaluable'
            END
        """
    return """
        CASE
            WHEN g.parse_status = 'parsed_safe'
                THEN 'safe numeric rule (GPA not supplied)'
            WHEN g.parse_status = 'conditional_review'
                THEN 'conditional/review required'
            ELSE 'not numerically evaluable'
        END
    """


def compile_result_query(
    criteria: SearchCriteria, *, limit: int | None, offset: int
) -> CompiledSearch:
    """Compile the result query; returned SQL never contains user values."""

    if limit is not None and limit < 0:
        raise StructuredSearchError("limit must be zero or greater")
    if offset < 0:
        raise StructuredSearchError("offset must be zero or greater")
    base = _compile_base(criteria)
    status_sql = _gpa_status_sql(base.gpa_supplied)
    select_sql = f"""
        SELECT
            a.source_dataset,
            a.source_version,
            a.record_id,
            a.institution_type,
            a.university,
            a.faculty_school,
            a.department,
            a.selection_category,
            a.selection_name,
            a.capacity,
            a.prefecture,
            a.academic_field,
            af.mapping_status AS academic_field_mapping_status,
            (
                SELECT group_concat(ordered.group_code, ',')
                FROM (
                    SELECT afg.group_code
                    FROM admission_search_academic_field_groups AS afg
                    WHERE afg.admission_rowid = a.admission_rowid
                    ORDER BY afg.group_order
                ) AS ordered
            ) AS academic_field_groups,
            a.stem_flag,
            a.exclusive_enrollment_status,
            a.school_recommendation_required,
            a.academic_record_required,
            a.gpa_requirement,
            {status_sql} AS gpa_derived_status,
            g.parse_status AS gpa_parse_status,
            g.search_disposition AS gpa_search_disposition,
            g.gpa_min_tenths,
            a.common_test_required,
            a.research_requirement_required,
            a.research_activity_level_status,
            a.selection_interview,
            a.selection_oral_exam,
            a.selection_presentation,
            a.selection_essay,
            a.selection_written_exam,
            a.selection_common_test,
            a.application_start,
            a.application_end
        {base.from_sql}
        {base.where_sql}
        ORDER BY a.university, a.faculty_school, a.department,
                 a.selection_category, a.selection_name,
                 a.source_dataset, a.source_version, a.record_id
    """
    parameters = list(base.parameters)
    if limit is not None:
        select_sql += " LIMIT ? OFFSET ?"
        parameters.extend((limit, offset))
    elif offset:
        select_sql += " LIMIT -1 OFFSET ?"
        parameters.append(offset)
    return CompiledSearch(sql=select_sql, parameters=tuple(parameters))


def _summary(
    connection: sqlite3.Connection, criteria: SearchCriteria
) -> SearchSummary:
    base = _compile_base(criteria)
    if base.gpa_supplied:
        gpa_select = f"""
            COALESCE(SUM(CASE WHEN {_SAFE_MATCH_SQL} THEN 1 ELSE 0 END), 0)
                AS gpa_safe_match_rows,
            COALESCE(SUM(CASE
                WHEN g.parse_status = 'parsed_safe' AND NOT {_SAFE_MATCH_SQL}
                THEN 1 ELSE 0 END), 0) AS gpa_safe_no_match_rows
        """
    else:
        gpa_select = """
            NULL AS gpa_safe_match_rows,
            NULL AS gpa_safe_no_match_rows
        """
    summary_row = connection.execute(
        f"""
        SELECT
            COUNT(*) AS total_matched_rows,
            {gpa_select},
            COALESCE(SUM(CASE WHEN g.parse_status = 'parsed_safe'
                THEN 1 ELSE 0 END), 0) AS gpa_safe_numeric_rule_rows,
            COALESCE(SUM(CASE WHEN g.parse_status = 'conditional_review'
                THEN 1 ELSE 0 END), 0) AS gpa_conditional_review_rows,
            COALESCE(SUM(CASE WHEN g.parse_status NOT IN (
                'parsed_safe', 'conditional_review'
            ) THEN 1 ELSE 0 END), 0) AS gpa_not_numerically_evaluable_rows,
            COUNT(DISTINCT a.university) AS university_count
        {base.from_sql}
        {base.where_sql}
        """,
        base.parameters,
    ).fetchone()
    source_rows = connection.execute(
        f"""
        SELECT a.source_dataset, COUNT(*) AS rows
        {base.from_sql}
        {base.where_sql}
        GROUP BY a.source_dataset
        ORDER BY a.source_dataset
        """,
        base.parameters,
    ).fetchall()
    return SearchSummary(
        total_matched_rows=summary_row["total_matched_rows"],
        gpa_safe_match_rows=summary_row["gpa_safe_match_rows"],
        gpa_safe_no_match_rows=summary_row["gpa_safe_no_match_rows"],
        gpa_safe_numeric_rule_rows=summary_row["gpa_safe_numeric_rule_rows"],
        gpa_conditional_review_rows=summary_row["gpa_conditional_review_rows"],
        gpa_not_numerically_evaluable_rows=summary_row[
            "gpa_not_numerically_evaluable_rows"
        ],
        rows_by_source_dataset={row[0]: row[1] for row in source_rows},
        university_count=summary_row["university_count"],
    )


def search_database(
    database_path: Path,
    criteria: SearchCriteria,
    *,
    limit: int | None = 20,
    offset: int = 0,
) -> SearchResult:
    """Execute one structured search against an immutable read-only database."""

    compiled = compile_result_query(criteria, limit=limit, offset=offset)
    with open_readonly_database(database_path) as connection:
        _validate_academic_filter_values(connection, criteria)
        summary = _summary(connection, criteria)
        rows = tuple(
            dict(row)
            for row in connection.execute(compiled.sql, compiled.parameters)
        )
    return SearchResult(
        criteria=criteria,
        summary=summary,
        rows=rows,
        offset=offset,
        limit=limit,
    )
