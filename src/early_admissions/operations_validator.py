from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Iterable

QUEUE_COLUMNS = [
    "queue_id", "institution_type", "university", "faculty_school", "selection_name",
    "document_type", "publication_status", "release_expected_text",
    "release_expected_from", "release_expected_to", "release_schedule_url",
    "last_checked_on", "next_check_on", "actual_release_on", "action_status",
    "related_record_id", "notes",
]
REAUDIT_COLUMNS = [
    "source_dataset", "institution_type", "university", "baseline_research_status",
    "baseline_master_rows", "reaudit_status", "official_system_checked",
    "capacity_table_checked", "schedule_checked", "guideline_index_checked",
    "master_compared", "kawai_crosscheck", "missing_candidate_count",
    "ambiguous_candidate_count", "obsolete_candidate_count",
    "update_queue_open_count", "last_audited_on", "notes",
]
PUBLICATION_STATUSES = {"公開済", "一部公開", "未公開", "公開予定", "不明"}
ACTION_STATUSES = {"待機", "確認時期到来", "更新必要", "更新中", "完了"}
REAUDIT_STATUSES = {"未再監査", "再監査中", "追加確認待ち", "要項公開待ち", "再監査済"}
CHECK_STATUSES = {"未実施", "一部実施", "実施済", "実施不能"}
DATE_FIELDS_QUEUE = ["release_expected_from", "release_expected_to", "last_checked_on", "next_check_on", "actual_release_on"]
DATE_FIELDS_REAUDIT = ["last_audited_on"]
COUNT_FIELDS = ["missing_candidate_count", "ambiguous_candidate_count", "obsolete_candidate_count", "update_queue_open_count"]


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def _is_date(value: str) -> bool:
    if not value:
        return True
    try:
        date.fromisoformat(value)
        return len(value) == 10
    except ValueError:
        return False


def _nonnegative_int_or_blank(value: str) -> bool:
    return value == "" or value.isdigit()


def validate_operations(root: Path) -> list[str]:
    errors: list[str] = []
    qpath = root / "data/operations/update_queue.csv"
    cpath = root / "data/operations/coverage_reaudit_2027.csv"
    if not qpath.exists():
        errors.append(f"missing file: {qpath.relative_to(root)}")
        return errors
    if not cpath.exists():
        errors.append(f"missing file: {cpath.relative_to(root)}")
        return errors

    qheader, qrows = _read_csv(qpath)
    cheader, crows = _read_csv(cpath)
    if qheader != QUEUE_COLUMNS:
        errors.append("update_queue.csv header does not match v0.1 contract")
    if cheader != REAUDIT_COLUMNS:
        errors.append("coverage_reaudit_2027.csv header does not match v0.1 contract")

    ids = [r.get("queue_id", "") for r in qrows]
    for qid, n in Counter(ids).items():
        if not qid:
            errors.append("update_queue.csv contains blank queue_id")
        elif n > 1:
            errors.append(f"duplicate queue_id: {qid}")

    open_counts: Counter[tuple[str, str]] = Counter()
    for lineno, r in enumerate(qrows, start=2):
        prefix = f"update_queue.csv:{lineno}"
        if not r.get("university"):
            errors.append(f"{prefix}: university is required")
        if r.get("publication_status") not in PUBLICATION_STATUSES:
            errors.append(f"{prefix}: invalid publication_status={r.get('publication_status')!r}")
        if r.get("action_status") not in ACTION_STATUSES:
            errors.append(f"{prefix}: invalid action_status={r.get('action_status')!r}")
        for field in DATE_FIELDS_QUEUE:
            if not _is_date(r.get(field, "")):
                errors.append(f"{prefix}: invalid ISO date in {field}: {r.get(field)!r}")
        start, end = r.get("release_expected_from", ""), r.get("release_expected_to", "")
        if start and end and date.fromisoformat(start) > date.fromisoformat(end):
            errors.append(f"{prefix}: release_expected_from is after release_expected_to")
        if r.get("publication_status") == "公開予定" and not r.get("release_expected_text"):
            errors.append(f"{prefix}: 公開予定 requires release_expected_text")
        if r.get("action_status") == "更新必要" and r.get("publication_status") not in {"公開済", "一部公開"}:
            errors.append(f"{prefix}: 更新必要 requires 公開済 or 一部公開")
        if r.get("action_status") in {"待機", "確認時期到来"} and not r.get("next_check_on"):
            errors.append(f"{prefix}: {r.get('action_status')} requires next_check_on")
        if r.get("action_status") != "完了":
            open_counts[(r.get("institution_type", ""), r.get("university", ""))] += 1

    seen_cov: set[tuple[str, str]] = set()
    ledger_counts: dict[tuple[str, str], int] = {}
    for lineno, r in enumerate(crows, start=2):
        prefix = f"coverage_reaudit_2027.csv:{lineno}"
        key = (r.get("institution_type", ""), r.get("university", ""))
        if key in seen_cov:
            errors.append(f"{prefix}: duplicate institution_type/university: {key}")
        seen_cov.add(key)
        if r.get("reaudit_status") not in REAUDIT_STATUSES:
            errors.append(f"{prefix}: invalid reaudit_status={r.get('reaudit_status')!r}")
        for field in ["official_system_checked", "capacity_table_checked", "schedule_checked", "guideline_index_checked", "master_compared", "kawai_crosscheck"]:
            if r.get(field) not in CHECK_STATUSES:
                errors.append(f"{prefix}: invalid {field}={r.get(field)!r}")
        for field in DATE_FIELDS_REAUDIT:
            if not _is_date(r.get(field, "")):
                errors.append(f"{prefix}: invalid ISO date in {field}: {r.get(field)!r}")
        for field in COUNT_FIELDS:
            if not _nonnegative_int_or_blank(r.get(field, "")):
                errors.append(f"{prefix}: {field} must be a non-negative integer or blank")
        ledger_counts[key] = int(r.get("update_queue_open_count") or 0)

    for key, n in open_counts.items():
        if key not in seen_cov:
            errors.append(f"UpdateQueue university missing from coverage re-audit ledger: {key}")
        elif ledger_counts.get(key, 0) != n:
            errors.append(f"open queue count mismatch for {key}: ledger={ledger_counts.get(key, 0)} actual={n}")
    for key, n in ledger_counts.items():
        if n and open_counts.get(key, 0) != n:
            errors.append(f"open queue count mismatch for {key}: ledger={n} actual={open_counts.get(key, 0)}")

    return errors


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate 2027 operational re-audit files")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(list(argv) if argv is not None else None)
    errors = validate_operations(args.root.resolve())
    if errors:
        print(f"operations validation: FAIL ({len(errors)} errors)")
        for err in errors:
            print(f"- {err}")
        return 1
    print("operations validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
