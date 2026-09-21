"""Generate the academic-field v0.2 SQLite QA receipt and branch key set."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from .academic_field_v0_2 import validate_and_summarize
from .academic_field_v2 import AcademicFieldV2Contract
from .sqlite_builder import DATABASE_FILENAME, DEFAULT_OUTPUT_DIR, canonical_json
from .structured_search import (
    AcademicFieldV2Branch,
    SearchCriteria,
    compile_result_query,
    open_readonly_database,
    search_database,
)


DEFAULT_REPORT = Path("validation/reports/academic_field_v0_2_sqlite_qa.md")
DEFAULT_BRANCH_KEYS = Path(
    "validation/reports/academic_field_v0_2_branch_logical_keys.tsv"
)

BROAD_EXAMPLES: tuple[tuple[str, int], ...] = (
    ("law_politics_policy", 81),
    ("economics", 150),
    ("business_commerce", 169),
    ("psychology", 25),
    ("languages", 128),
    ("natural_sciences", 702),
    ("engineering", 1642),
    ("information", 865),
)

SUBCATEGORY_EXAMPLES: tuple[tuple[str, str, int], ...] = (
    ("law_politics_policy", "law", 42),
    ("economics", "economics_general", 147),
    ("business_commerce", "management", 161),
    ("psychology", "psychology_general", 20),
    ("natural_sciences", "mathematics_statistics", 107),
    ("natural_sciences", "physics", 87),
    ("engineering", "mechanical", 332),
    ("nursing_health", "nursing", 279),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _query_count(database: Path, criteria: SearchCriteria) -> int:
    return search_database(database, criteria, limit=0).summary.total_matched_rows


def _plan(
    connection: sqlite3.Connection, criteria: SearchCriteria
) -> list[str]:
    compiled = compile_result_query(criteria, limit=1, offset=0)
    return [
        row[3]
        for row in connection.execute(
            "EXPLAIN QUERY PLAN " + compiled.sql, compiled.parameters
        )
    ]


def _membership_rows(
    connection: sqlite3.Connection, *, taxonomy_table: str, membership_table: str,
    code_column: str
) -> list[tuple[str, str, int]]:
    sql = f"""
        SELECT t.{code_column}, t.display_label_ja, COUNT(m.admission_rowid)
        FROM {taxonomy_table} AS t
        LEFT JOIN {membership_table} AS m USING ({code_column})
        GROUP BY t.{code_column}, t.rowid ORDER BY t.rowid
    """
    return [(row[0], row[1], row[2]) for row in connection.execute(sql)]


def _assert_equal(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise RuntimeError(f"{label}: expected={expected!r}, actual={actual!r}")


def generate_qa(
    repo_root: Path,
    *,
    database: Path,
    report_path: Path,
    branch_keys_path: Path,
) -> Mapping[str, Any]:
    manifest_path = database.parent / "build_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    layer = manifest["academic_field_v2"]
    contract = AcademicFieldV2Contract.load(repo_root)
    independent_freeze = validate_and_summarize(repo_root)

    broad_results: list[tuple[str, int, int]] = []
    for group_code, expected in BROAD_EXAMPLES:
        actual = _query_count(
            database,
            SearchCriteria(
                academic_field_v2_branches=(AcademicFieldV2Branch(group_code),)
            ),
        )
        _assert_equal(f"broad query {group_code}", actual, expected)
        broad_results.append((group_code, expected, actual))

    subcategory_results: list[tuple[str, str, int, int]] = []
    for group_code, subcategory_code, expected in SUBCATEGORY_EXAMPLES:
        actual = _query_count(
            database,
            SearchCriteria(
                academic_field_v2_branches=(
                    AcademicFieldV2Branch(group_code, (subcategory_code,)),
                )
            ),
        )
        _assert_equal(f"subcategory query {subcategory_code}", actual, expected)
        subcategory_results.append(
            (group_code, subcategory_code, expected, actual)
        )

    branch_criteria = SearchCriteria(
        academic_field_v2_branches=(
            AcademicFieldV2Branch(
                "natural_sciences", ("mathematics_statistics", "physics")
            ),
            AcademicFieldV2Branch("engineering"),
        )
    )
    branch_result = search_database(database, branch_criteria, limit=None)
    branch_keys = sorted(
        (
            str(row["source_dataset"]),
            str(row["source_version"]),
            str(row["record_id"]),
        )
        for row in branch_result.rows
    )
    branch_text = "source_dataset\tsource_version\trecord_id\n" + "".join(
        "\t".join(key) + "\n" for key in branch_keys
    )
    branch_keys_path.parent.mkdir(parents=True, exist_ok=True)
    branch_keys_path.write_text(branch_text, encoding="utf-8", newline="")
    branch_sha = _sha256(branch_keys_path)

    combined_specs = (
        (
            "東京都 AND 法学・政治・公共政策",
            SearchCriteria(
                prefecture=("東京都",),
                academic_field_v2_branches=(
                    AcademicFieldV2Branch("law_politics_policy"),
                ),
            ),
        ),
        (
            "東京都 AND 工学 AND 評定条件あり",
            SearchCriteria(
                prefecture=("東京都",),
                grade_requirement_status="required",
                academic_field_v2_branches=(
                    AcademicFieldV2Branch("engineering"),
                ),
            ),
        ),
        (
            "東京都/神奈川県 membership AND 情報 AND overall GPA 3.8",
            SearchCriteria(
                prefecture_membership=("東京都", "神奈川県"),
                grade_requirement_status="required",
                overall_gpa_tenths=38,
                academic_field_v2_branches=(
                    AcademicFieldV2Branch("information"),
                ),
            ),
        ),
    )
    combined_results = [
        (label, _query_count(database, criteria))
        for label, criteria in combined_specs
    ]

    ambiguous_specs = (
        ("人間科学", "kokkoritsu", "fixture大学", None, None),
        ("航空・パイロット", "shidai", "fixture大学", None, None),
        ("理学療法", "kokkoritsu", "fixture大学", None, None),
        ("言語聴覚", "kokkoritsu", "fixture大学", None, None),
        ("獣医学", "kokkoritsu", "fixture大学", None, None),
    )
    ambiguous_results = []
    for raw, dataset, university, faculty, department in ambiguous_specs:
        result = contract.classify(
            source_dataset=dataset,
            university=university,
            faculty_school=faculty,
            department=department,
            academic_field=raw,
        )
        ambiguous_results.append(
            (
                raw,
                result.broad_mapping_status,
                ",".join(value[0] for value in result.broad_memberships) or "none",
                ",".join(value[0] for value in result.subcategory_memberships)
                or "none",
            )
        )

    with open_readonly_database(database) as connection:
        broad_rows = _membership_rows(
            connection,
            taxonomy_table="academic_field_v2_broad_taxonomy",
            membership_table=(
                "admission_search_academic_field_broad_memberships_v2"
            ),
            code_column="group_code",
        )
        subcategory_rows = _membership_rows(
            connection,
            taxonomy_table="academic_field_v2_subcategory_taxonomy",
            membership_table=(
                "admission_search_academic_field_subcategory_memberships_v2"
            ),
            code_column="subcategory_code",
        )
        query_plans = {
            "broad": _plan(
                connection,
                SearchCriteria(
                    academic_field_v2_branches=(
                        AcademicFieldV2Branch("engineering"),
                    )
                ),
            ),
            "subcategory": _plan(
                connection,
                SearchCriteria(
                    academic_field_v2_branches=(
                        AcademicFieldV2Branch("engineering", ("mechanical",)),
                    )
                ),
            ),
            "multi_branch": _plan(connection, branch_criteria),
        }

    _assert_equal("broad taxonomy rows", len(broad_rows), 30)
    _assert_equal("subcategory taxonomy rows", len(subcategory_rows), 89)
    _assert_equal(
        "broad membership counts",
        {code: count for code, _, count in broad_rows},
        independent_freeze["broad_membership_counts"],
    )
    expected_subcategory_counts = {
        item.subcategory_code: independent_freeze[
            "subcategory_membership_counts"
        ].get(item.subcategory_code, 0)
        for item in contract.subcategories
    }
    _assert_equal(
        "subcategory membership counts",
        {code: count for code, _, count in subcategory_rows},
        expected_subcategory_counts,
    )
    _assert_equal(
        "manifest broad membership counts",
        layer["broad_membership_counts"],
        independent_freeze["broad_membership_counts"],
    )
    _assert_equal(
        "manifest subcategory membership counts",
        layer["subcategory_membership_counts"],
        expected_subcategory_counts,
    )
    _assert_equal("validation status", layer["validation_status"], "passed")

    v1 = manifest["academic_field_search"]
    v1_validation = manifest["validation"]["academic_field_search"]
    validation = manifest["validation"]["academic_field_v2"]
    lines = [
        "# Academic-field v0.2 SQLite QA",
        "",
        f"- Database: `{database.relative_to(repo_root)}`",
        f"- Database SHA-256: `{_sha256(database)}`",
        f"- Mapping/taxonomy version: `{layer['mapping_contract_version']}` / "
        f"`{layer['taxonomy_version']}`",
        f"- Validation: `{layer['validation_status']}`",
        "- Independent frozen-input membership reconciliation: `passed`",
        f"- Branch logical-key rows: {len(branch_keys)}",
        f"- Branch logical-key SHA-256: `{branch_sha}`",
        f"- Branch logical-key artifact: `{branch_keys_path.relative_to(repo_root)}`",
        "",
        "## Build counts",
        "",
        f"- Broad taxonomy: {layer['broad_taxonomy_rows']}",
        f"- Subcategory taxonomy: {layer['subcategory_taxonomy_rows']}",
        f"- Parent rows: {layer['parent_rows']}",
        f"- Broad membership rows: {layer['broad_membership_rows']}",
        f"- Subcategory membership rows: {layer['subcategory_membership_rows']}",
        f"- Raw crosswalk: {layer['raw_crosswalk_keys']} keys / "
        f"{layer['raw_crosswalk_rows']} rows",
        f"- Context crosswalk: {layer['context_crosswalk_tuples']} tuples / "
        f"{layer['context_crosswalk_rows']} rows",
        f"- Raw-only admissions: {layer['raw_only_mapping_admissions']}",
        f"- Context consulted: {layer['context_consulted_admissions']}",
        f"- Context effective: {layer['context_effect_admissions']}",
        f"- Raw mismatch: {layer['raw_mismatch_rows']}",
        "",
        "## Mapping status counts",
        "",
        f"- Broad: `{canonical_json(layer['broad_mapping_status_counts'])}`",
        "- Subcategory: "
        f"`{canonical_json(layer['subcategory_mapping_status_counts'])}`",
        f"- Context effects: `{canonical_json(layer['context_effect_counts'])}`",
        "",
        "## Broad membership counts",
        "",
        "| Code | Label | Admissions |",
        "|---|---|---:|",
        *(f"| `{code}` | {label} | {count} |" for code, label, count in broad_rows),
        "",
        "## Subcategory membership counts",
        "",
        "| Code | Label | Admissions |",
        "|---|---|---:|",
        *(
            f"| `{code}` | {label} | {count} |"
            for code, label, count in subcategory_rows
        ),
        "",
        "## Representative broad queries",
        "",
        "| Code | Expected | Actual |",
        "|---|---:|---:|",
        *(
            f"| `{code}` | {expected} | {actual} |"
            for code, expected, actual in broad_results
        ),
        "",
        "## Representative subcategory queries",
        "",
        "| Broad | Subcategory | Expected | Actual |",
        "|---|---|---:|---:|",
        *(
            f"| `{group}` | `{subcategory}` | {expected} | {actual} |"
            for group, subcategory, expected, actual in subcategory_results
        ),
        "",
        "## Branch semantics",
        "",
        "The executed predicate was `(natural_sciences AND "
        "(mathematics_statistics OR physics)) OR engineering`. It returned "
        f"{len(branch_keys)} logical keys. The complete sorted key set is saved "
        "in the companion TSV and its SHA-256 is recorded above.",
        "",
        "## Combined existing filters",
        "",
        "| Query | Rows |",
        "|---|---:|",
        *(f"| {label} | {count} |" for label, count in combined_results),
        "",
        "## Ambiguous and contained-token fixtures",
        "",
        "| Raw | Broad status | Broad membership | Subcategory membership |",
        "|---|---|---|---|",
        *(
            f"| {raw} | `{status}` | `{broad}` | `{subcategory}` |"
            for raw, status, broad, subcategory in ambiguous_results
        ),
        "",
        "Exact context fixtures for 地域デザイン and 国際, plus substring "
        "negative fixtures, are covered by automated tests. No runtime trim, "
        "substring, fuzzy, or inferred classification is used.",
        "",
        "## Query plans",
        "",
        *(
            f"- {name}: `{' / '.join(plan).replace('|', r'\|')}`"
            for name, plan in query_plans.items()
        ),
        "",
        "## v0.1 coexistence and validation",
        "",
        f"- v0.1 mapping counts: `{canonical_json(v1['classification_counts'])}`",
        f"- v0.1 group rows: {v1['group_rows']}",
        f"- v0.1 validation: `{v1_validation['status']}`",
        "- Supplying v0.1 and v0.2 filters together uses AND semantics.",
        f"- v0.2 foreign hierarchy failures: "
        f"{validation['missing_subcategory_parent_broad']}",
        f"- v0.2 order failures: {validation['taxonomy_order_mismatches']}",
        f"- PRAGMA foreign_key_check rows: "
        f"{manifest['validation']['pragmas']['foreign_key_check_rows']}",
        f"- PRAGMA quick_check: "
        f"`{manifest['validation']['pragmas']['quick_check']}`",
        "",
        "## Scope boundary",
        "",
        "Site-data and frontend were not changed. This receipt validates the "
        "SQLite derived layer and the structured-search oracle only.",
        "",
    ]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8", newline="")
    return {
        "status": "passed",
        "report": str(report_path),
        "branch_keys": str(branch_keys_path),
        "branch_key_rows": len(branch_keys),
        "branch_key_sha256": branch_sha,
        "combined_results": dict(combined_results),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate academic-field v0.2 SQLite QA receipts."
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--database", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--branch-keys", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    database = (
        args.database.resolve()
        if args.database
        else repo_root / DEFAULT_OUTPUT_DIR / DATABASE_FILENAME
    )
    report = args.report or repo_root / DEFAULT_REPORT
    branch_keys = args.branch_keys or repo_root / DEFAULT_BRANCH_KEYS
    result = generate_qa(
        repo_root,
        database=database,
        report_path=report,
        branch_keys_path=branch_keys,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
