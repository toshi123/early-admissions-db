"""CLI for read-only structured searches over early_admissions_2027.sqlite."""

from __future__ import annotations

import argparse
import csv
import sys
import unicodedata
from pathlib import Path
from typing import Any, Mapping, Sequence, TextIO

from .gpa_search import GPAContractError, parse_gpa_tenths
from .sqlite_builder import DATABASE_FILENAME, DEFAULT_OUTPUT_DIR
from .structured_search import (
    RESULT_COLUMNS,
    SearchCriteria,
    SearchResult,
    StructuredSearchError,
    search_database,
)


TABLE_GROUPS: tuple[tuple[str, tuple[tuple[str, int], ...]], ...] = (
    (
        "Identity and admission unit",
        (
            ("source_dataset", 12),
            ("source_version", 8),
            ("record_id", 24),
            ("university", 20),
            ("faculty_school", 18),
            ("department", 18),
            ("selection_category", 16),
            ("selection_name", 20),
            ("capacity", 12),
        ),
    ),
    (
        "Classification and location",
        (
            ("record_id", 24),
            ("institution_type", 10),
            ("prefecture", 10),
            ("academic_field", 18),
            ("academic_field_mapping_status", 18),
            ("academic_field_groups", 28),
            ("stem_flag", 9),
            ("exclusive_enrollment_status", 15),
            ("research_activity_level_status", 17),
        ),
    ),
    (
        "Requirements and GPA",
        (
            ("record_id", 24),
            ("gpa_requirement", 30),
            ("gpa_derived_status", 28),
            ("gpa_parse_status", 18),
            ("gpa_search_disposition", 18),
            ("gpa_min_tenths", 14),
            ("school_recommendation_required", 15),
            ("academic_record_required", 15),
            ("common_test_required", 15),
            ("research_requirement_required", 15),
        ),
    ),
    (
        "Selection methods and application period",
        (
            ("record_id", 24),
            ("selection_interview", 12),
            ("selection_oral_exam", 12),
            ("selection_presentation", 12),
            ("selection_essay", 12),
            ("selection_written_exam", 12),
            ("selection_common_test", 12),
            ("application_start", 18),
            ("application_end", 18),
        ),
    ),
)


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _add_multi_value_argument(
    parser: argparse.ArgumentParser,
    *flags: str,
    dest: str,
    help_text: str,
) -> None:
    parser.add_argument(
        *flags,
        dest=dest,
        action="extend",
        nargs="+",
        metavar="VALUE",
        help=help_text + " Multiple values within this field are ORed.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only structured search over early_admissions_2027.sqlite. "
            "Different fields are ANDed; values within one field are ORed."
        )
    )
    parser.add_argument(
        "--repo-root", type=Path, default=default_repo_root(), help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--database",
        type=Path,
        help="SQLite database path (default: published derived database).",
    )
    _add_multi_value_argument(
        parser, "--university", dest="university", help_text="Exact university name."
    )
    _add_multi_value_argument(
        parser,
        "--institution-type",
        dest="institution_type",
        help_text="Exact institution type, such as 国立, 公立, or 私立.",
    )
    _add_multi_value_argument(
        parser, "--prefecture", dest="prefecture", help_text="Exact prefecture."
    )
    _add_multi_value_argument(parser,"--prefecture-membership",dest="prefecture_membership",help_text="Derived exact-crosswalk prefecture membership.")
    _add_multi_value_argument(
        parser,
        "--academic-field",
        dest="academic_field",
        help_text="Exact raw academic-field value.",
    )
    _add_multi_value_argument(
        parser,
        "--academic-field-group",
        dest="academic_field_group",
        help_text="Frozen broad academic-field group code.",
    )
    _add_multi_value_argument(
        parser,
        "--academic-field-mapping-status",
        dest="academic_field_mapping_status",
        help_text=(
            "Academic-field mapping status: single, multi, review_required, "
            "unmapped, or not_applicable."
        ),
    )
    stem_group = parser.add_mutually_exclusive_group()
    stem_group.add_argument("--stem", action="store_true", help="Require stem_flag=1.")
    stem_group.add_argument(
        "--non-stem", action="store_true", help="Require stem_flag=0."
    )
    _add_multi_value_argument(
        parser,
        "--selection-category",
        dest="selection_category",
        help_text="Exact selection category.",
    )
    _add_multi_value_argument(
        parser,
        "--exclusive",
        "--exclusive-enrollment-status",
        dest="exclusive_enrollment_status",
        help_text="Exact exclusive-enrollment status.",
    )
    for flags, dest, label in (
        (("--school-recommendation-required",), "school_recommendation_required", "School recommendation requirement"),
        (("--academic-record-required",), "academic_record_required", "Academic record requirement"),
        (("--common-test-required",), "common_test_required", "Common Test requirement"),
        (("--research-requirement-required",), "research_requirement_required", "Research requirement"),
        (("--research-activity-level-status",), "research_activity_level_status", "Research-activity status"),
        (("--interview", "--selection-interview"), "selection_interview", "Interview flag"),
        (("--oral-exam", "--selection-oral-exam"), "selection_oral_exam", "Oral-exam flag"),
        (("--presentation", "--selection-presentation"), "selection_presentation", "Presentation flag"),
        (("--essay", "--selection-essay"), "selection_essay", "Essay flag"),
        (("--written-exam", "--selection-written-exam"), "selection_written_exam", "Written-exam flag"),
        (("--selection-common-test",), "selection_common_test", "Selection Common Test flag"),
    ):
        _add_multi_value_argument(
            parser, *flags, dest=dest, help_text=f"Exact {label} value."
        )
    parser.add_argument(
        "--gpa", help="Japanese five-point GPA from 0 to 5, at most one decimal."
    )
    parser.add_argument(
        "--gpa-mode",
        choices=("safe", "review", "all"),
        help=(
            "safe: strict safe matches only (default with --gpa); review: safe "
            "matches plus conditional/review rows; all: do not filter by GPA status."
        ),
    )
    parser.add_argument(
        "--format", choices=("table", "csv", "tsv"), default="table"
    )
    parser.add_argument(
        "--limit", type=int, default=20, help="Maximum displayed/exported rows."
    )
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument(
        "--all-results",
        action="store_true",
        help="Return all matching rows; overrides --limit.",
    )
    return parser


def _values(namespace: argparse.Namespace, name: str) -> tuple[str, ...]:
    return tuple(getattr(namespace, name) or ())


def criteria_from_args(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> SearchCriteria:
    if args.gpa is None:
        if args.gpa_mode is not None:
            parser.error("--gpa-mode requires --gpa")
        gpa_tenths = None
        gpa_mode = "all"
    else:
        try:
            gpa_tenths = parse_gpa_tenths(args.gpa)
        except GPAContractError as error:
            parser.error(str(error))
        gpa_mode = args.gpa_mode or "safe"
    stem_flag = True if args.stem else False if args.non_stem else None
    return SearchCriteria(
        university=_values(args, "university"),
        institution_type=_values(args, "institution_type"),
        prefecture=_values(args, "prefecture"),
        prefecture_membership=_values(args, "prefecture_membership"),
        academic_field=_values(args, "academic_field"),
        academic_field_group=_values(args, "academic_field_group"),
        academic_field_mapping_status=_values(
            args, "academic_field_mapping_status"
        ),
        stem_flag=stem_flag,
        selection_category=_values(args, "selection_category"),
        exclusive_enrollment_status=_values(args, "exclusive_enrollment_status"),
        school_recommendation_required=_values(
            args, "school_recommendation_required"
        ),
        academic_record_required=_values(args, "academic_record_required"),
        common_test_required=_values(args, "common_test_required"),
        research_requirement_required=_values(
            args, "research_requirement_required"
        ),
        research_activity_level_status=_values(
            args, "research_activity_level_status"
        ),
        selection_interview=_values(args, "selection_interview"),
        selection_oral_exam=_values(args, "selection_oral_exam"),
        selection_presentation=_values(args, "selection_presentation"),
        selection_essay=_values(args, "selection_essay"),
        selection_written_exam=_values(args, "selection_written_exam"),
        selection_common_test=_values(args, "selection_common_test"),
        gpa_tenths=gpa_tenths,
        gpa_mode=gpa_mode,
    )


def _summary_lines(result: SearchResult) -> list[str]:
    summary = result.summary
    safe_matches = (
        "n/a (GPA not supplied)"
        if summary.gpa_safe_match_rows is None
        else str(summary.gpa_safe_match_rows)
    )
    safe_no_matches = (
        "n/a (GPA not supplied)"
        if summary.gpa_safe_no_match_rows is None
        else str(summary.gpa_safe_no_match_rows)
    )
    source_counts = ", ".join(
        f"{dataset}={count}"
        for dataset, count in summary.rows_by_source_dataset.items()
    ) or "none"
    shown_start = result.offset + 1 if result.rows else 0
    shown_end = result.offset + len(result.rows)
    return [
        "Search summary",
        f"  total matched rows: {summary.total_matched_rows}",
        f"  GPA safe match rows: {safe_matches}",
        f"  GPA safe no-match rows: {safe_no_matches}",
        f"  GPA safe numeric rule rows: {summary.gpa_safe_numeric_rule_rows}",
        "  GPA conditional/review rows: "
        f"{summary.gpa_conditional_review_rows}",
        "  GPA not numerically evaluable rows: "
        f"{summary.gpa_not_numerically_evaluable_rows}",
        f"  source datasets: {source_counts}",
        f"  universities: {summary.university_count}",
        f"  displayed rows: {shown_start}-{shown_end}",
        f"  meaning: {result.result_meaning}",
    ]


def render_summary(result: SearchResult, stream: TextIO) -> None:
    stream.write("\n".join(_summary_lines(result)) + "\n")


def _display_width(value: str) -> int:
    return sum(
        2 if unicodedata.east_asian_width(character) in {"W", "F"} else 1
        for character in value
    )


def _truncate(value: str, width: int) -> str:
    value = value.replace("\r", "↩").replace("\n", "↩")
    if _display_width(value) <= width:
        return value
    target = max(0, width - 1)
    result: list[str] = []
    used = 0
    for character in value:
        character_width = (
            2 if unicodedata.east_asian_width(character) in {"W", "F"} else 1
        )
        if used + character_width > target:
            break
        result.append(character)
        used += character_width
    return "".join(result) + "…"


def _cell(value: Any, width: int) -> str:
    text = "" if value is None else str(value)
    rendered = _truncate(text, width)
    return rendered + " " * (width - _display_width(rendered))


def _render_table_group(
    title: str,
    columns: tuple[tuple[str, int], ...],
    rows: Sequence[Mapping[str, Any]],
    stream: TextIO,
) -> None:
    widths = tuple(max(width, _display_width(name)) for name, width in columns)
    stream.write(f"\n{title}\n")
    separator = "+" + "+".join("-" * (width + 2) for width in widths) + "+\n"
    stream.write(separator)
    stream.write(
        "|"
        + "|".join(
            f" {_cell(name, width)} "
            for (name, _), width in zip(columns, widths)
        )
        + "|\n"
    )
    stream.write(separator)
    for row in rows:
        stream.write(
            "|"
            + "|".join(
                f" {_cell(row[name], width)} "
                for (name, _), width in zip(columns, widths)
            )
            + "|\n"
        )
    stream.write(separator)


def render_terminal_tables(result: SearchResult, stream: TextIO) -> None:
    for title, columns in TABLE_GROUPS:
        _render_table_group(title, columns, result.rows, stream)
    stream.write(
        "\nTerminal cells may be shortened for display; CSV/TSV exports contain "
        "complete stored values.\n"
    )


def render_delimited(result: SearchResult, stream: TextIO, *, delimiter: str) -> None:
    writer = csv.DictWriter(
        stream,
        fieldnames=RESULT_COLUMNS,
        delimiter=delimiter,
        lineterminator="\n",
        extrasaction="ignore",
    )
    writer.writeheader()
    for row in result.rows:
        writer.writerow({field: row[field] for field in RESULT_COLUMNS})


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.limit < 0:
        parser.error("--limit must be zero or greater")
    if args.offset < 0:
        parser.error("--offset must be zero or greater")
    criteria = criteria_from_args(args, parser)
    database = args.database
    if database is None:
        database = args.repo_root / DEFAULT_OUTPUT_DIR / DATABASE_FILENAME
    limit = None if args.all_results else args.limit
    try:
        result = search_database(
            database, criteria, limit=limit, offset=args.offset
        )
    except (OSError, StructuredSearchError) as error:
        print(f"Search failed: {error}", file=sys.stderr)
        return 1

    if args.format == "table":
        render_summary(result, sys.stdout)
        render_terminal_tables(result, sys.stdout)
    else:
        render_delimited(
            result,
            sys.stdout,
            delimiter="," if args.format == "csv" else "\t",
        )
        render_summary(result, sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
