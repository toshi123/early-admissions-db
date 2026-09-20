"""Command-line entry point for read-only canonical validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .validator import ReadOnlyValidator, write_json_report, write_markdown_report


DEFAULT_JSON_REPORT = Path("validation/reports/unified_v0_1_validation_report.json")
DEFAULT_SUMMARY_REPORT = Path(
    "validation/reports/unified_v0_1_validation_summary.md"
)


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate canonical early-admissions source data against unified "
            "contract v0.1 without modifying source data."
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=default_repo_root(),
        help="Repository root (default: inferred from installed module).",
    )
    parser.add_argument(
        "--json-report",
        type=Path,
        default=DEFAULT_JSON_REPORT,
        help="Machine-readable JSON report path, relative to repo root by default.",
    )
    parser.add_argument(
        "--summary-report",
        type=Path,
        default=DEFAULT_SUMMARY_REPORT,
        help="Human-readable Markdown summary path, relative to repo root by default.",
    )
    parser.add_argument(
        "--representative-limit",
        type=int,
        default=5,
        help="Maximum representative record IDs shown per finding code.",
    )
    parser.add_argument(
        "--no-write-reports",
        action="store_true",
        help="Run validation and print the summary without writing report files.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the console summary.",
    )
    return parser


def resolve_output_path(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    if args.representative_limit < 1:
        raise SystemExit("--representative-limit must be at least 1")

    validator = ReadOnlyValidator(repo_root)
    result = validator.validate()

    if not args.no_write_reports:
        json_path = resolve_output_path(repo_root, args.json_report)
        summary_path = resolve_output_path(repo_root, args.summary_report)
        write_json_report(result, json_path, args.representative_limit)
        write_markdown_report(result, summary_path, args.representative_limit)
    else:
        json_path = None
        summary_path = None

    if not args.quiet:
        print(result.console_summary(args.representative_limit))
        if json_path is not None and summary_path is not None:
            print()
            print(f"JSON report: {json_path}")
            print(f"Summary report: {summary_path}")

    errors = result.summary(args.representative_limit)["by_severity"]["error"]
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
