"""Command-line entry point for deterministic unified dataset generation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .unified_adapter import TABLE_ORDER
from .unified_builder import (
    DEFAULT_OUTPUT_DIR,
    UnifiedBuildError,
    UnifiedBuildPipeline,
)


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build and validate deterministic unified v0.1 CSV files from "
            "read-only canonical source data."
        )
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = UnifiedBuildPipeline(
            args.repo_root,
            output_dir=args.output_dir,
        ).build()
    except (OSError, KeyError, ValueError, UnifiedBuildError) as error:
        print(f"Unified build failed: {error}", file=sys.stderr)
        return 1

    if not args.quiet:
        severity = result.source_validation_summary["by_severity"]
        print("Unified build status: passed")
        print(
            "Source validation: "
            f"errors={severity['error']}, warnings={severity['warning']}, "
            f"informational={severity['informational']}"
        )
        print("Outputs:")
        for table in TABLE_ORDER:
            item = result.output_metadata[table]
            print(
                f"  {table}: rows={item['rows']}, sha256={item['sha256']}"
            )
        print("Determinism: 2 builds are byte-identical")
        print(f"Manifest: {result.manifest_path}")
        print(f"Summary: {result.summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
