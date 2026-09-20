"""Run the frozen representative structured-search QA set and write a report."""

from __future__ import annotations

import argparse
import hashlib
import shlex
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .sqlite_builder import DATABASE_FILENAME, DEFAULT_OUTPUT_DIR
from .structured_search import SearchCriteria, StructuredSearchError, search_database


DEFAULT_REPORT = Path("validation/reports/search_cli_qa_v0_1.md")


@dataclass(frozen=True)
class QASpec:
    label: str
    arguments: tuple[str, ...]
    criteria: SearchCriteria


def _gpa(value: int, mode: str = "safe") -> dict[str, object]:
    return {"gpa_tenths": value, "gpa_mode": mode}


QA_SPECS: tuple[QASpec, ...] = (
    QASpec(
        "東京＋理系",
        ("--prefecture", "東京都", "--stem"),
        SearchCriteria(prefecture=("東京都",), stem_flag=True),
    ),
    QASpec(
        "東京＋理系＋評定3.8",
        ("--prefecture", "東京都", "--stem", "--gpa", "3.8"),
        SearchCriteria(prefecture=("東京都",), stem_flag=True, **_gpa(38)),
    ),
    QASpec(
        "東京＋理系＋評定3.8＋研究活動関連",
        (
            "--prefecture",
            "東京都",
            "--stem",
            "--gpa",
            "3.8",
            "--research-activity-level-status",
            "required",
            "relevant",
        ),
        SearchCriteria(
            prefecture=("東京都",),
            stem_flag=True,
            research_activity_level_status=("required", "relevant"),
            **_gpa(38),
        ),
    ),
    QASpec(
        "東京/神奈川＋併願可",
        ("--prefecture", "東京都", "神奈川県", "--exclusive", "併願可"),
        SearchCriteria(
            prefecture=("東京都", "神奈川県"),
            exclusive_enrollment_status=("併願可",),
        ),
    ),
    QASpec(
        "学校推薦型＋推薦必要",
        (
            "--selection-category",
            "学校推薦型選抜",
            "--school-recommendation-required",
            "Yes",
        ),
        SearchCriteria(
            selection_category=("学校推薦型選抜",),
            school_recommendation_required=("Yes",),
        ),
    ),
    QASpec(
        "共通テスト不要",
        ("--common-test-required", "No"),
        SearchCriteria(common_test_required=("No",)),
    ),
    QASpec(
        "口頭試問あり",
        ("--oral-exam", "Yes"),
        SearchCriteria(selection_oral_exam=("Yes",)),
    ),
    QASpec(
        "プレゼンあり",
        ("--presentation", "Yes"),
        SearchCriteria(selection_presentation=("Yes",)),
    ),
    QASpec(
        "面接＋小論文",
        ("--interview", "Yes", "--essay", "Yes"),
        SearchCriteria(selection_interview=("Yes",), selection_essay=("Yes",)),
    ),
    QASpec(
        "GPA 3.5 strict-safe",
        ("--gpa", "3.5"),
        SearchCriteria(**_gpa(35)),
    ),
    QASpec(
        "GPA 3.8 strict-safe",
        ("--gpa", "3.8"),
        SearchCriteria(**_gpa(38)),
    ),
    QASpec(
        "GPA 4.0 strict-safe",
        ("--gpa", "4.0"),
        SearchCriteria(**_gpa(40)),
    ),
    QASpec(
        "国公立＋研究実績要件あり",
        (
            "--institution-type",
            "国立",
            "公立",
            "--research-requirement-required",
            "Yes",
        ),
        SearchCriteria(
            institution_type=("国立", "公立"),
            research_requirement_required=("Yes",),
        ),
    ),
    QASpec(
        "私立＋共通テスト不要＋併願可",
        (
            "--institution-type",
            "私立",
            "--common-test-required",
            "No",
            "--exclusive",
            "併願可",
        ),
        SearchCriteria(
            institution_type=("私立",),
            common_test_required=("No",),
            exclusive_enrollment_status=("併願可",),
        ),
    ),
    QASpec(
        "東京/神奈川＋工学/情報＋GPA 4.0",
        (
            "--prefecture",
            "東京都",
            "神奈川県",
            "--academic-field",
            "工学",
            "情報",
            "--gpa",
            "4.0",
        ),
        SearchCriteria(
            prefecture=("東京都", "神奈川県"),
            academic_field=("工学", "情報"),
            **_gpa(40),
        ),
    ),
    QASpec(
        "GPA 3.8 review mode",
        ("--gpa", "3.8", "--gpa-mode", "review"),
        SearchCriteria(**_gpa(38, "review")),
    ),
    QASpec(
        "GPA 3.8 all mode",
        ("--gpa", "3.8", "--gpa-mode", "all"),
        SearchCriteria(**_gpa(38, "all")),
    ),
    QASpec(
        "面接＋筆記試験＋共通テスト不要",
        (
            "--interview",
            "Yes",
            "--written-exam",
            "Yes",
            "--common-test-required",
            "No",
        ),
        SearchCriteria(
            selection_interview=("Yes",),
            selection_written_exam=("Yes",),
            common_test_required=("No",),
        ),
    ),
    QASpec(
        "東京＋工学group",
        ("--prefecture", "東京都", "--academic-field-group", "engineering"),
        SearchCriteria(
            prefecture=("東京都",), academic_field_group=("engineering",)
        ),
    ),
    QASpec(
        "東京＋情報group",
        ("--prefecture", "東京都", "--academic-field-group", "information"),
        SearchCriteria(
            prefecture=("東京都",), academic_field_group=("information",)
        ),
    ),
    QASpec(
        "東京/神奈川＋工学OR情報group＋GPA 3.8",
        (
            "--prefecture",
            "東京都",
            "神奈川県",
            "--academic-field-group",
            "engineering",
            "information",
            "--gpa",
            "3.8",
        ),
        SearchCriteria(
            prefecture=("東京都", "神奈川県"),
            academic_field_group=("engineering", "information"),
            **_gpa(38),
        ),
    ),
    QASpec(
        "医学group",
        ("--academic-field-group", "medicine"),
        SearchCriteria(academic_field_group=("medicine",)),
    ),
    QASpec(
        "医歯薬group",
        (
            "--academic-field-group",
            "medicine",
            "dentistry",
            "pharmacy",
        ),
        SearchCriteria(
            academic_field_group=("medicine", "dentistry", "pharmacy")
        ),
    ),
    QASpec(
        "農学OR生命科学group",
        (
            "--academic-field-group",
            "agriculture_fisheries",
            "life_sciences",
        ),
        SearchCriteria(
            academic_field_group=("agriculture_fisheries", "life_sciences")
        ),
    ),
    QASpec(
        "要確認academic field",
        ("--academic-field-mapping-status", "review_required"),
        SearchCriteria(academic_field_mapping_status=("review_required",)),
    ),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _markdown(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _write_report(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text.replace("\r\n", "\n").replace("\r", "\n"))


def _portable_database_path(database_path: Path) -> str:
    resolved = database_path.resolve()
    try:
        return str(resolved.relative_to(default_repo_root().resolve()))
    except ValueError:
        return database_path.name


def run_qa(database_path: Path, report_path: Path) -> tuple[int, str]:
    before_hash = _sha256(database_path)
    rows: list[str] = []
    for index, spec in enumerate(QA_SPECS, start=1):
        result = search_database(database_path, spec.criteria, limit=3)
        summary = result.summary
        safe = (
            "—"
            if summary.gpa_safe_match_rows is None
            else str(summary.gpa_safe_match_rows)
        )
        sources = ", ".join(
            f"{dataset}={count}"
            for dataset, count in summary.rows_by_source_dataset.items()
        ) or "none"
        representatives = "; ".join(
            f"{row['record_id']} ({row['university']}, {row['gpa_derived_status']})"
            for row in result.rows
        ) or "none"
        command = shlex.join(("./scripts/search", *spec.arguments, "--limit", "3"))
        rows.append(
            "| "
            + " | ".join(
                (
                    str(index),
                    _markdown(spec.label) + f"<br><code>{_markdown(command)}</code>",
                    str(summary.total_matched_rows),
                    safe,
                    str(summary.gpa_conditional_review_rows),
                    str(summary.gpa_not_numerically_evaluable_rows),
                    _markdown(sources),
                    str(summary.university_count),
                    _markdown(representatives),
                )
            )
            + " |"
        )
    after_hash = _sha256(database_path)
    if after_hash != before_hash:
        raise StructuredSearchError("SQLite database changed during read-only QA.")
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
    report = "\n".join(
        (
            "# Structured search CLI v0.1 representative QA",
            "",
            f"- Generated: `{timestamp}`",
            f"- SQLite: `{_portable_database_path(database_path)}`",
            f"- SQLite SHA-256 before/after: `{before_hash}` / `{after_hash}`",
            f"- Queries: {len(QA_SPECS)}",
            "- Access: URI `mode=ro&immutable=1` plus `PRAGMA query_only=ON`",
            "- GPA meaning: `safe match` means `overall GPA condition safely matched`; it is not an application-eligibility determination.",
            "",
            "## Results",
            "",
            "| # | Query and command | Total | GPA safe match | Conditional/review | Not numerically evaluable | Sources | Universities | Representative results |",
            "|---:|---|---:|---:|---:|---:|---|---:|---|",
            *rows,
            "",
            "## Search friction observed",
            "",
            "- Broad academic-field group search is derived from the frozen exact-value crosswalk. Raw `academic_field` remains visible and separately searchable; review/unmapped rows require the mapping-status filter.",
            "- `application_start` and `application_end` remain lossless raw text; the intentionally empty normalized-date layer means chronological range filtering is not available in v0.1.",
            "- `capacity` is raw text rather than a normalized integer, so capacity range searches are not safe.",
            "- `research_activity_level_status` includes `required`, `relevant`, `none`, `unknown`, `unmapped`, and SQL NULL. A broad “research related” search must state explicitly whether it means `required`, `relevant`, or both.",
            "- `common_test_required` and `selection_common_test` are separate concepts and must remain separate filters; `common_test_required` also contains `Conditional` in the current snapshot.",
            "- GPA conditional rules remain review-only. The CLI can expose them with `--gpa-mode review` or `all`, but never evaluates them automatically.",
            "- v0.1 uses exact categorical matching and does not provide vocabulary discovery, partial university-name matching, or NULL-specific filter switches.",
            "",
            "## Scope boundary",
            "",
            "No SQLite, canonical, release, or unified input was modified. This QA did not create a Site, JSON search index, AI natural-language search, or conditional-GPA evaluator.",
            "",
        )
    )
    _write_report(report_path, report)
    return len(QA_SPECS), before_hash


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run structured-search QA v0.1.")
    parser.add_argument("--repo-root", type=Path, default=default_repo_root())
    parser.add_argument("--database", type=Path)
    parser.add_argument("--report", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    database = args.database or (
        args.repo_root / DEFAULT_OUTPUT_DIR / DATABASE_FILENAME
    )
    report = args.report or (args.repo_root / DEFAULT_REPORT)
    try:
        count, database_hash = run_qa(database, report)
    except (OSError, StructuredSearchError) as error:
        print(f"Search QA failed: {error}", file=sys.stderr)
        return 1
    print(f"Structured search QA: passed ({count} queries)")
    print(f"SQLite SHA-256 unchanged: {database_hash}")
    print(f"Report: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
