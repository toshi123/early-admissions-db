"""CLI entry point for the Site-data projection v0.2 build."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .site_data_builder import (
    DEFAULT_DATABASE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_QA_REPORT,
    DEFAULT_SQLITE_MANIFEST,
    SiteDataBuildError,
    SiteDataBuildPipeline,
)


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build validated static Site-data v0.2 from SQLite."
    )
    parser.add_argument("--repo-root", type=Path, default=default_repo_root())
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--sqlite-manifest", type=Path, default=DEFAULT_SQLITE_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--qa-report", type=Path, default=DEFAULT_QA_REPORT)
    parser.add_argument("--quiet", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = SiteDataBuildPipeline(
            args.repo_root,
            database_path=args.database,
            sqlite_manifest_path=args.sqlite_manifest,
            output_dir=args.output_dir,
            qa_report_path=args.qa_report,
        ).build()
    except (OSError, KeyError, TypeError, ValueError, SiteDataBuildError) as error:
        print(f"Site-data build failed: {error}", file=sys.stderr)
        return 1
    if not args.quiet:
        print("Site-data build status: passed")
        print(f"Build ID: {result.build_id}")
        print(
            "Rows: "
            f"search={result.counts['search_rows']}, "
            f"details={result.counts['detail_records']}, "
            f"research={result.counts['research_requirement_rows']}"
        )
        print(
            "Shards: "
            f"search={result.size_report['search_shards']}, "
            f"details={result.size_report['detail_shards']}"
        )
        print(f"Manifest: {result.manifest_path} (sha256={result.manifest_sha256})")
        print(f"QA report: {result.qa_report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
