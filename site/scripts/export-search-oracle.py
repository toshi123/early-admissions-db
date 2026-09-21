#!/usr/bin/env python3
"""Export the frozen 25-query Python oracle for frontend set-equality tests."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path


SITE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = SITE_ROOT.parent
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from early_admissions.search_qa import QA_SPECS  # noqa: E402
from early_admissions.site_search import (  # noqa: E402
    SearchRequest,
    load_search_rows,
    logical_key,
    search_rows,
)


def main() -> None:
    rows = load_search_rows(REPOSITORY_ROOT / "data" / "derived" / "site" / "v0_2")
    cases: list[dict[str, object]] = []
    for spec in QA_SPECS:
        criteria = asdict(spec.criteria)
        request = SearchRequest(**criteria)
        result = search_rows(rows, request, limit=None)
        cases.append(
            {
                "label": spec.label,
                "request": criteria,
                "logical_keys": [list(logical_key(row)) for row in result.rows],
                "summary": asdict(result.summary),
            }
        )
    output = SITE_ROOT / "tests" / "generated" / "search_oracle.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"cases": cases}, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Exported {len(cases)} frozen search-oracle cases")


if __name__ == "__main__":
    main()
