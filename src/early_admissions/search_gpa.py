"""Read-only CLI for the fail-closed GPA safe subset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .gpa_search import GPAContractError, search_gpa
from .sqlite_builder import DATABASE_FILENAME, DEFAULT_OUTPUT_DIR


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only search for admissions whose overall GPA condition is "
            "safely matched by a Japanese five-point GPA."
        )
    )
    parser.add_argument("gpa", help="GPA from 0 to 5, with at most one decimal place")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=default_repo_root(),
        help="Repository root (default: inferred from installed module).",
    )
    parser.add_argument(
        "--database",
        type=Path,
        help="SQLite database path (default: the published derived database).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum records to display; the total count is always reported.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    database = args.database
    if database is None:
        database = args.repo_root / DEFAULT_OUTPUT_DIR / DATABASE_FILENAME
    try:
        result = search_gpa(database, args.gpa, limit=args.limit)
    except (OSError, GPAContractError) as error:
        print(f"GPA search failed: {error}", file=sys.stderr)
        return 1

    payload = {
        "query_gpa_tenths": result.student_gpa_tenths,
        "meaning": result.meaning,
        "total_matches": result.total_matches,
        "returned_rows": len(result.rows),
        "records": list(result.rows),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    print(f"Meaning: {result.meaning}")
    print(
        f"Query GPA: {result.student_gpa_tenths / 10:.1f}; "
        f"total matches: {result.total_matches}; displayed: {len(result.rows)}"
    )
    for row in result.rows:
        identifier = (
            f"{row['source_dataset']}:{row['source_version']}:{row['record_id']}"
        )
        display = " / ".join(
            value
            for value in (
                row["university"],
                row["faculty_school"],
                row["department"],
                row["selection_name"],
            )
            if value is not None
        )
        print(
            f"{identifier}\t{display}\tminimum={row['gpa_min']:.1f}\t"
            f"raw={row['raw_value']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
