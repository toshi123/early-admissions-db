"""Command-line entry point for the SQLite v0.2 derived build."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .sqlite_builder import (
    DEFAULT_OUTPUT_DIR,
    SQLiteBuildError,
    SQLiteBuildPipeline,
)
from .validation_profile import PRODUCTION_PROFILE


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and validate the SQLite v0.3 artifact from unified CSVs."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=default_repo_root(),
        help="Repository root (default: inferred from installed module).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory, relative to repo root by default.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the successful build summary.",
    )
    parser.add_argument(
        "--validation-profile",
        choices=("production", "candidate-audit"),
        default=PRODUCTION_PROFILE,
        help=(
            "Validation policy (default: production). candidate-audit is an "
            "explicit inspection-only mode and never marks output production-ready."
        ),
    )
    parser.add_argument(
        "--build-timestamp-utc",
        help=(
            "Optional deterministic UTC timestamp recorded in the artifact "
            "(for example 2026-09-22T11:38:21Z)."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = SQLiteBuildPipeline(
            args.repo_root,
            output_dir=args.output_dir,
            validation_profile=args.validation_profile,
            build_timestamp_utc=args.build_timestamp_utc,
        ).build()
    except (OSError, KeyError, TypeError, ValueError, SQLiteBuildError) as error:
        print(f"SQLite build failed: {error}", file=sys.stderr)
        return 1

    if not args.quiet:
        print("SQLite build status: passed")
        print(f"Validation profile: {args.validation_profile}")
        print(
            f"Profile: {result.capabilities.profile}; "
            f"SQLite {result.capabilities.sqlite_version}; "
            f"FTS5={result.capabilities.fts5}; "
            f"trigram={result.capabilities.trigram}"
        )
        print(
            "Rows: "
            + ", ".join(
                f"{table}={count}" for table, count in result.row_counts.items()
            )
        )
        gpa = result.validation["gpa_search"]
        print(
            "GPA classifications: "
            + ", ".join(
                f"{tier}={count}"
                for tier, count in gpa["classification_counts"].items()
            )
        )
        print(
            "GPA 3.8 strict-safe matches: "
            f"{gpa['safe_match_counts']['3.8']} "
            f"({gpa['result_meaning']})"
        )
        print(
            f"Database: {result.database_path} "
            f"({result.database_size_bytes} bytes, sha256={result.database_sha256})"
        )
        print(f"Manifest: {result.manifest_path}")
        print(f"Summary: {result.summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
