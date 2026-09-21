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
from .academic_field_v0_2 import MAPPING_VERSION as ACADEMIC_FIELD_V2_MAPPING_VERSION
from .academic_field_v0_2 import TAXONOMY_VERSION as ACADEMIC_FIELD_V2_TAXONOMY_VERSION
from .gpa_search import GPA_PARSER_CONTRACT_VERSION
from .grade_requirement import (
    GRADE_REQUIREMENT_MAPPING_CONTRACT_VERSION,
    GRADE_REQUIREMENT_STATUSES,
)
from .english_requirement import ENGLISH_REQUIREMENT_CONTRACT_VERSION
from .prefecture_search import PREFECTURE_MAPPING_CONTRACT_VERSION, PREFECTURE_TAXONOMY_VERSION


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
    "grade_requirement_status",
    "overall_gpa_min_tenths",
    "overall_gpa_min_inclusive",
    "overall_gpa_status",
    "additional_grade_conditions",
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
class AcademicFieldV2Branch:
    """One broad branch with an optional OR-list of child subcategories."""

    group_code: str
    subcategory_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SearchCriteria:
    university: tuple[str, ...] = ()
    institution_type: tuple[str, ...] = ()
    prefecture: tuple[str, ...] = ()
    prefecture_membership: tuple[str, ...] = ()
    academic_field: tuple[str, ...] = ()
    academic_field_group: tuple[str, ...] = ()
    academic_field_mapping_status: tuple[str, ...] = ()
    academic_field_v2_branches: tuple[AcademicFieldV2Branch, ...] = ()
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
    english_requirement_status: tuple[str, ...] = ()
    gpa_tenths: int | None = None
    gpa_mode: str = "all"
    grade_requirement_status: str | None = None
    overall_gpa_tenths: int | None = None

    def validate(self) -> None:
        if self.gpa_mode not in GPA_MODES:
            raise StructuredSearchError(f"Unsupported GPA mode: {self.gpa_mode!r}")
        if self.gpa_tenths is None and self.gpa_mode != "all":
            raise StructuredSearchError("GPA mode safe/review requires a GPA value.")
        if self.gpa_tenths is not None and not 0 <= self.gpa_tenths <= 50:
            raise StructuredSearchError("GPA tenths must be between 0 and 50.")
        if (
            self.grade_requirement_status is not None
            and self.grade_requirement_status not in GRADE_REQUIREMENT_STATUSES
        ):
            raise StructuredSearchError("Unsupported grade requirement status.")
        if self.overall_gpa_tenths is not None:
            if not 0 <= self.overall_gpa_tenths <= 50:
                raise StructuredSearchError("Overall GPA tenths must be between 0 and 50.")
            if self.grade_requirement_status != "required":
                raise StructuredSearchError(
                    "Overall GPA search requires grade_requirement_status='required'."
                )
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
            "english_requirement_status",
            "prefecture_membership",
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
        if not isinstance(self.academic_field_v2_branches, tuple):
            raise StructuredSearchError(
                "academic_field_v2_branches must be supplied as a tuple."
            )
        group_codes: list[str] = []
        for branch in self.academic_field_v2_branches:
            if not isinstance(branch, AcademicFieldV2Branch):
                raise StructuredSearchError(
                    "Each academic-field v0.2 branch must use "
                    "AcademicFieldV2Branch."
                )
            if not branch.group_code:
                raise StructuredSearchError(
                    "Academic-field v0.2 branch has an empty broad code."
                )
            if not isinstance(branch.subcategory_codes, tuple) or any(
                not isinstance(value, str) or value == ""
                for value in branch.subcategory_codes
            ):
                raise StructuredSearchError(
                    "Academic-field v0.2 subcategory codes must be non-empty text."
                )
            group_codes.append(branch.group_code)
        if len(group_codes) != len(set(group_codes)):
            raise StructuredSearchError(
                "Academic-field v0.2 broad branches must be unique."
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
               grade_requirement_mapping_contract_version,
               academic_field_mapping_contract_version,
               academic_field_taxonomy_version,
               academic_field_v2_mapping_contract_version,
               academic_field_v2_taxonomy_version,
               english_requirement_parser_contract_version
               ,prefecture_mapping_contract_version, prefecture_taxonomy_version
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
        rows[0]["grade_requirement_mapping_contract_version"]
        != GRADE_REQUIREMENT_MAPPING_CONTRACT_VERSION
    ):
        raise StructuredSearchError("Grade-requirement contract version is incompatible.")
    if (
        rows[0]["academic_field_mapping_contract_version"]
        != ACADEMIC_FIELD_MAPPING_CONTRACT_VERSION
    ):
        raise StructuredSearchError(
            "Academic-field mapping contract version is incompatible."
        )
    if rows[0]["english_requirement_parser_contract_version"] != ENGLISH_REQUIREMENT_CONTRACT_VERSION:
        raise StructuredSearchError("English-requirement contract version is incompatible.")
    if rows[0]["prefecture_mapping_contract_version"] != PREFECTURE_MAPPING_CONTRACT_VERSION or rows[0]["prefecture_taxonomy_version"] != PREFECTURE_TAXONOMY_VERSION:
        raise StructuredSearchError("Prefecture membership contract is incompatible.")
    if (
        rows[0]["academic_field_taxonomy_version"]
        != ACADEMIC_FIELD_TAXONOMY_VERSION
    ):
        raise StructuredSearchError(
            "Academic-field taxonomy version is incompatible."
        )
    if (
        rows[0]["academic_field_v2_mapping_contract_version"]
        != ACADEMIC_FIELD_V2_MAPPING_VERSION
        or rows[0]["academic_field_v2_taxonomy_version"]
        != ACADEMIC_FIELD_V2_TAXONOMY_VERSION
    ):
        raise StructuredSearchError(
            "Academic-field v0.2 contract is incompatible."
        )


def _validate_academic_filter_values(
    connection: sqlite3.Connection, criteria: SearchCriteria
) -> None:
    if criteria.academic_field_group:
        approved = {row[0] for row in connection.execute("SELECT group_code FROM academic_field_taxonomy")}
        invalid = set(criteria.academic_field_group).difference(approved)
        if invalid:
            raise StructuredSearchError("Unknown academic-field group: " + ", ".join(sorted(invalid)))
    if criteria.prefecture_membership:
        approved_prefectures={row[0] for row in connection.execute("SELECT prefecture_label FROM prefecture_taxonomy")}
        invalid_prefectures=set(criteria.prefecture_membership).difference(approved_prefectures)
        if invalid_prefectures:
            raise StructuredSearchError("Unknown prefecture membership: " + ", ".join(sorted(invalid_prefectures)))
    if criteria.academic_field_v2_branches:
        broad_codes = {
            row[0]
            for row in connection.execute(
                "SELECT group_code FROM academic_field_v2_broad_taxonomy"
            )
        }
        subcategory_parents = {
            row[0]: row[1]
            for row in connection.execute(
                """
                SELECT subcategory_code, parent_group_code
                FROM academic_field_v2_subcategory_taxonomy
                """
            )
        }
        for branch in criteria.academic_field_v2_branches:
            if branch.group_code not in broad_codes:
                raise StructuredSearchError(
                    "Unknown academic-field v0.2 broad group: "
                    + branch.group_code
                )
            for subcategory in branch.subcategory_codes:
                actual_parent = subcategory_parents.get(subcategory)
                if actual_parent is None:
                    raise StructuredSearchError(
                        "Unknown academic-field v0.2 subcategory: "
                        + subcategory
                    )
                if actual_parent != branch.group_code:
                    raise StructuredSearchError(
                        "Academic-field v0.2 subcategory parent mismatch: "
                        f"{subcategory} belongs to {actual_parent}, not "
                        f"{branch.group_code}."
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
            JOIN admission_search_english_requirement AS er USING (admission_rowid)
            JOIN admission_search_grade_requirements AS gr USING (admission_rowid)
            CROSS JOIN (SELECT ? AS student_gpa_tenths) AS q
        """
        parameters.append(criteria.gpa_tenths)
    else:
        from_sql = """
            FROM admissions AS a
            JOIN admission_search_gpa AS g USING (admission_rowid)
            LEFT JOIN admission_search_gpa_safe AS gs USING (admission_rowid)
            JOIN admission_search_academic_fields AS af USING (admission_rowid)
            JOIN admission_search_english_requirement AS er USING (admission_rowid)
            JOIN admission_search_grade_requirements AS gr USING (admission_rowid)
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
    if criteria.academic_field_v2_branches:
        branches: list[str] = []
        for branch in criteria.academic_field_v2_branches:
            branch_sql = (
                "EXISTS (SELECT 1 FROM "
                "admission_search_academic_field_broad_memberships_v2 AS b2 "
                "WHERE b2.admission_rowid = a.admission_rowid "
                "AND b2.group_code = ?)"
            )
            parameters.append(branch.group_code)
            subcategories = _deduplicate(branch.subcategory_codes)
            if subcategories:
                placeholders = ", ".join("?" for _ in subcategories)
                branch_sql += (
                    " AND EXISTS (SELECT 1 FROM "
                    "admission_search_academic_field_subcategory_memberships_v2 "
                    "AS s2 WHERE s2.admission_rowid = a.admission_rowid "
                    "AND s2.parent_group_code = ? "
                    f"AND s2.subcategory_code IN ({placeholders}))"
                )
                parameters.append(branch.group_code)
                parameters.extend(subcategories)
            branches.append(f"({branch_sql})")
        predicates.append("(" + " OR ".join(branches) + ")")
    if criteria.stem_flag is not None:
        predicates.append("a.stem_flag = ?")
        parameters.append(int(criteria.stem_flag))
    english_values = _deduplicate(criteria.english_requirement_status)
    if english_values:
        if set(english_values).difference({"required", "not_required"}):
            raise StructuredSearchError("English requirement filter accepts only safe exact statuses.")
        placeholders = ", ".join("?" for _ in english_values)
        predicates.append(f"er.requirement_status IN ({placeholders}) AND er.search_disposition = 'safe_exact'")
        parameters.extend(english_values)
    prefecture_values = _deduplicate(criteria.prefecture_membership)
    if prefecture_values:
        placeholders = ", ".join("?" for _ in prefecture_values)
        predicates.append("EXISTS (SELECT 1 FROM admission_search_prefecture_memberships pm WHERE pm.admission_rowid=a.admission_rowid AND pm.prefecture_label IN (" + placeholders + "))")
        parameters.extend(prefecture_values)

    if criteria.gpa_tenths is not None:
        if criteria.gpa_mode == "safe":
            predicates.append(_SAFE_MATCH_SQL)
        elif criteria.gpa_mode == "review":
            predicates.append(
                f"({_SAFE_MATCH_SQL} OR g.parse_status = 'conditional_review')"
            )
    if criteria.grade_requirement_status is not None:
        predicates.append("gr.grade_requirement_status = ?")
        parameters.append(criteria.grade_requirement_status)
    if criteria.overall_gpa_tenths is not None:
        predicates.append(
            "gr.parse_status = 'exact_crosswalk' "
            "AND gr.overall_gpa_min_tenths IS NOT NULL "
            "AND (? > gr.overall_gpa_min_tenths "
            "OR (? = gr.overall_gpa_min_tenths "
            "AND gr.overall_gpa_min_inclusive = 1))"
        )
        parameters.extend((criteria.overall_gpa_tenths, criteria.overall_gpa_tenths))
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
            gr.grade_requirement_status,
            gr.overall_gpa_min_tenths,
            gr.overall_gpa_min_inclusive,
            gr.overall_gpa_status,
            gr.additional_grade_conditions,
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
