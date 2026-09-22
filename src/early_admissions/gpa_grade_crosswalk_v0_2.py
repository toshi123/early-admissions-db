"""Build the human-reviewed GPA/Grade exact crosswalk freeze v0.2."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Mapping

from .english_requirement import (
    ENGLISH_REQUIREMENT_CROSSWALK_PATH,
    EnglishRequirementCrosswalk,
)
from .gpa_search import AUDIT_COLUMNS, GPACrosswalk, GPAParser
from .grade_requirement import (
    GradeRequirementCrosswalk,
)


CROSSWALK_VERSION = "0.2"
PREVIOUS_VERSION = "0.1"
REVIEWED_ON = "2026-09-22"
REVIEW_SOURCE = "human review"
CANDIDATE_SOURCES = {"kokkoritsu": "5.81", "shidai": "1.08"}

DECISION_PATH = Path(
    "validation/reports/update_20260922_v5_81_v1_08/"
    "gpa_grade_human_review_decisions_v0_2.csv"
)
GPA_PACKET_PATH = Path(
    "validation/reports/update_20260922_v5_81_v1_08/gpa_new_values.csv"
)
GRADE_PACKET_PATH = Path(
    "validation/reports/update_20260922_v5_81_v1_08/"
    "grade_requirement_new_values.csv"
)
PREVIOUS_GPA_CROSSWALK_PATH = Path(
    "validation/reports/gpa_requirement_raw_value_audit_v0_1.csv"
)
GPA_CROSSWALK_PATH = Path(
    "validation/reports/gpa_requirement_raw_value_audit_v0_2.csv"
)
PREVIOUS_GRADE_CROSSWALK_PATH = Path(
    "schema/grade_requirement/grade_requirement_crosswalk_v0_1.csv"
)
GRADE_CROSSWALK_PATH = Path(
    "schema/grade_requirement/grade_requirement_crosswalk_v0_2.csv"
)
MANIFEST_PATH = Path(
    "schema/grade_requirement/gpa_grade_crosswalk_manifest_v0_2.json"
)
CANDIDATE_AUDIT_JSON_PATH = Path(
    "validation/reports/update_20260922_v5_81_v1_08/"
    "gpa_grade_crosswalk_v0_2_candidate_audit.json"
)
CANDIDATE_AUDIT_MD_PATH = Path(
    "validation/reports/update_20260922_v5_81_v1_08/"
    "gpa_grade_crosswalk_v0_2_candidate_audit.md"
)
CANDIDATE_MASTER_PATHS = {
    "kokkoritsu": Path(
        "sources/incoming/2026-09-22/kokkoritsu_v5_81/"
        "kokkoritsu_early_admissions_2027_master_v5_81.csv"
    ),
    "shidai": Path(
        "sources/incoming/2026-09-22/shidai_v1_08/"
        "shidai_early_admissions_2027_master_v1_08.csv"
    ),
}

PACKET_IDENTITY_COLUMNS = (
    "raw_or_context",
    "frequency",
    "representative_university",
    "representative_faculty",
    "representative_department",
    "representative_record_id",
)
DECISION_COLUMNS = (
    "review_order",
    "raw_value",
    "frequency",
    "representative_university",
    "representative_faculty",
    "representative_department",
    "representative_record_id",
    "reviewed",
    "approved_grade_status",
    "approved_overall_floor",
    "approved_overall_floor_tenths",
    "approved_additional_conditions",
    "approved_numeric_status",
    "review_note",
    "reviewed_on",
    "review_source",
    "candidate_sources",
)
SAFE_NUMERIC_STATUSES = {
    "safe_simple_overall",
    "safe_overall_with_additional_conditions",
}
NUMERIC_STATUSES = SAFE_NUMERIC_STATUSES | {
    "no_safe_overall_floor",
    "non_binding",
    "non_admission_numeric",
    "historical",
    "ambiguous",
    "unknown",
}
GRADE_STATUSES = {"required", "not_required", "unknown", "review_required"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _csv_bytes(fieldnames: Iterable[str], rows: Iterable[Mapping[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=list(fieldnames),
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def load_decisions(root: Path) -> list[dict[str, str]]:
    path = root / DECISION_PATH
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != DECISION_COLUMNS:
            raise ValueError("Human-review decision header mismatch.")
        rows = list(reader)
    if len(rows) != 63:
        raise ValueError(f"Expected 63 human-review decisions, found {len(rows)}.")
    if [int(row["review_order"]) for row in rows] != list(range(1, 64)):
        raise ValueError("Human-review decision order must be exactly 1..63.")
    if len({row["raw_value"] for row in rows}) != 63:
        raise ValueError("Human-review decision raw values must be unique.")
    for row in rows:
        if (
            row["reviewed"] != "yes"
            or row["reviewed_on"] != REVIEWED_ON
            or row["review_source"] != REVIEW_SOURCE
            or row["candidate_sources"] != "kokkoritsu 5.81 + shidai 1.08"
            or row["approved_grade_status"] not in GRADE_STATUSES
            or row["approved_numeric_status"] not in NUMERIC_STATUSES
        ):
            raise ValueError(
                f"Invalid human-review decision metadata at #{row['review_order']}."
            )
        floor = row["approved_overall_floor_tenths"]
        display_floor = row["approved_overall_floor"]
        additional = row["approved_additional_conditions"]
        safe = row["approved_numeric_status"] in SAFE_NUMERIC_STATUSES
        if safe:
            if (
                row["approved_grade_status"] != "required"
                or not floor
                or not display_floor
                or additional not in {"true", "false"}
            ):
                raise ValueError(
                    f"Incomplete safe decision at #{row['review_order']}."
                )
            if int(floor) != int(Decimal(display_floor) * 10):
                raise ValueError(
                    f"Floor representation mismatch at #{row['review_order']}."
                )
            expected = (
                "safe_overall_with_additional_conditions"
                if additional == "true"
                else "safe_simple_overall"
            )
            if row["approved_numeric_status"] != expected:
                raise ValueError(
                    f"Safe/additional mismatch at #{row['review_order']}."
                )
        elif floor or display_floor:
            raise ValueError(
                f"Unsafe decision has a numeric floor at #{row['review_order']}."
            )
    return rows


def verify_packet_correspondence(
    root: Path, decisions: list[dict[str, str]]
) -> dict[str, Any]:
    gpa_rows = _read_csv(root / GPA_PACKET_PATH)
    grade_rows = _read_csv(root / GRADE_PACKET_PATH)
    if len(gpa_rows) != 63 or len(grade_rows) != 63:
        raise ValueError("Both review packets must contain exactly 63 rows.")
    mismatches: list[dict[str, Any]] = []
    for order, (gpa, grade, decision) in enumerate(
        zip(gpa_rows, grade_rows, decisions), start=1
    ):
        fields = [
            field
            for field in PACKET_IDENTITY_COLUMNS
            if gpa[field] != grade[field]
        ]
        if decision["raw_value"] != gpa["raw_or_context"]:
            fields.append("decision.raw_value")
        if decision["frequency"] != gpa["frequency"]:
            fields.append("decision.frequency")
        for field in PACKET_IDENTITY_COLUMNS[2:]:
            if decision[field] != gpa[field]:
                fields.append(f"decision.{field}")
        if fields:
            mismatches.append({"review_order": order, "fields": sorted(set(fields))})
    if mismatches:
        raise ValueError(f"Review packet correspondence mismatch: {mismatches[:5]}")
    return {"status": "passed", "rows": 63, "mismatches": 0}


def _candidate_occurrences(
    root: Path, decisions: list[dict[str, str]]
) -> dict[str, dict[str, Any]]:
    decision_raws = {row["raw_value"] for row in decisions}
    occurrences: dict[str, dict[str, Any]] = {
        raw: {
            "row_count": 0,
            "by_dataset": Counter(),
            "fallback_rows": 0,
            "record_ids": [],
        }
        for raw in decision_raws
    }
    for dataset, relative in CANDIDATE_MASTER_PATHS.items():
        for row in _read_csv(root / relative):
            raw = row["gpa_requirement"]
            if raw not in occurrences:
                continue
            item = occurrences[raw]
            item["row_count"] += 1
            item["by_dataset"][dataset] += 1
            item["fallback_rows"] += int(
                row["fallback_previous_year"].lower() == "true"
            )
            if len(item["record_ids"]) < 5:
                item["record_ids"].append(
                    f"{dataset}:{CANDIDATE_SOURCES[dataset]}:{row['record_id']}"
                )
    for decision in decisions:
        item = occurrences[decision["raw_value"]]
        if item["row_count"] != int(decision["frequency"]):
            raise ValueError(
                f"Candidate frequency mismatch at #{decision['review_order']}: "
                f"{item['row_count']} != {decision['frequency']}"
            )
        if not any(
            value.endswith(f":{decision['representative_record_id']}")
            for value in item["record_ids"]
        ):
            # The packet representative need not be among the first five, but it must
            # exist in the corresponding source rows.
            found = False
            for dataset, relative in CANDIDATE_MASTER_PATHS.items():
                for row in _read_csv(root / relative):
                    if (
                        row["record_id"] == decision["representative_record_id"]
                        and row["gpa_requirement"] == decision["raw_value"]
                    ):
                        found = True
                        break
                if found:
                    break
            if not found:
                raise ValueError(
                    f"Representative record mismatch at #{decision['review_order']}."
                )
    return occurrences


def _gpa_classification(
    decision: Mapping[str, str],
) -> tuple[str, str, str, str, str]:
    status = decision["approved_numeric_status"]
    floor = decision["approved_overall_floor"]
    if status == "safe_simple_overall":
        return (
            "safe_numeric",
            "simple_overall_minimum",
            "numeric",
            floor,
            floor,
        )
    if status in {
        "safe_overall_with_additional_conditions",
        "no_safe_overall_floor",
    }:
        return (
            "conditional_numeric",
            "other_complex_numeric",
            "numeric",
            floor,
            "",
        )
    if status == "non_binding":
        return (
            "do_not_numeric",
            "nonbinding_or_historical_numeric",
            "nonbinding",
            "",
            "",
        )
    if status == "non_admission_numeric":
        return (
            "do_not_numeric",
            "non_admission_or_inoperative_numeric",
            "numeric",
            "",
            "",
        )
    if status == "historical":
        return (
            "do_not_numeric",
            "nonbinding_or_historical_numeric",
            "historical",
            "",
            "",
        )
    if status == "ambiguous":
        return ("do_not_numeric", "unresolved", "unresolved", "", "")
    if status == "unknown":
        return ("do_not_numeric", "unknown", "unknown", "", "")
    raise ValueError(f"Unsupported numeric status: {status}")


def _build_gpa_rows(
    root: Path,
    decisions: list[dict[str, str]],
    occurrences: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    previous = _read_csv(root / PREVIOUS_GPA_CROSSWALK_PATH)
    previous_raw = {row["raw_value"] for row in previous}
    if previous_raw.intersection(row["raw_value"] for row in decisions):
        raise ValueError("A reviewed candidate raw already exists in GPA v0.1.")
    additions: list[dict[str, Any]] = []
    for decision in decisions:
        tier, primary, flags, numeric_tokens, safe_min = _gpa_classification(
            decision
        )
        occurrence = occurrences[decision["raw_value"]]
        additions.append(
            {
                "raw_value": decision["raw_value"],
                "row_count": occurrence["row_count"],
                "kokkoritsu_rows": occurrence["by_dataset"]["kokkoritsu"],
                "shidai_rows": occurrence["by_dataset"]["shidai"],
                "distinct_tier": tier,
                "primary_class": primary,
                "feature_flags": flags,
                "numeric_tokens": numeric_tokens,
                "safe_gpa_min": safe_min,
                "safe_gpa_max": "",
                "fallback_previous_year_rows": occurrence["fallback_rows"],
                "representative_record_ids": ";".join(occurrence["record_ids"]),
                "review_status": "reviewed",
            }
        )
    return previous + additions


def _build_grade_rows(
    root: Path, decisions: list[dict[str, str]]
) -> list[dict[str, Any]]:
    previous = _read_csv(root / PREVIOUS_GRADE_CROSSWALK_PATH)
    previous_raw = {row["raw_value"] for row in previous}
    if previous_raw.intersection(row["raw_value"] for row in decisions):
        raise ValueError("A reviewed candidate raw already exists in Grade v0.1.")
    rows = [{**row, "contract_version": CROSSWALK_VERSION} for row in previous]
    for decision in decisions:
        floor = decision["approved_overall_floor_tenths"]
        additional = (
            "1"
            if floor and decision["approved_additional_conditions"] == "true"
            else "0"
            if floor and decision["approved_additional_conditions"] == "false"
            else ""
        )
        note = (
            f"人手レビュー済み（{REVIEWED_ON}、decision "
            f"#{decision['review_order']}）。exact raw match。"
        )
        if (
            not floor
            and decision["approved_additional_conditions"] in {"true", "false"}
        ):
            note += (
                " human decisionのadditional判断はreview artifactに保持し、"
                "safe floorなしのためderived flagはNULL。"
            )
        rows.append(
            {
                "contract_version": CROSSWALK_VERSION,
                "raw_value": decision["raw_value"],
                "grade_requirement_status": decision["approved_grade_status"],
                "overall_gpa_min_tenths": floor,
                "overall_gpa_min_inclusive": "1" if floor else "",
                "overall_gpa_status": decision["approved_numeric_status"],
                "additional_grade_conditions": additional,
                "review_note": note,
            }
        )
    return rows


def build_artifact_bytes(root: Path) -> dict[Path, bytes]:
    root = root.resolve()
    decisions = load_decisions(root)
    correspondence = verify_packet_correspondence(root, decisions)
    occurrences = _candidate_occurrences(root, decisions)
    gpa_rows = _build_gpa_rows(root, decisions, occurrences)
    grade_rows = _build_grade_rows(root, decisions)
    gpa_bytes = _csv_bytes(AUDIT_COLUMNS, gpa_rows)
    grade_bytes = _csv_bytes(GradeRequirementCrosswalk._HEADER, grade_rows)

    grade_counts = Counter(row["approved_grade_status"] for row in decisions)
    numeric_counts = Counter(row["approved_numeric_status"] for row in decisions)
    floor_counts = Counter(
        row["approved_overall_floor"] or "NULL" for row in decisions
    )
    manifest = {
        "artifact": "gpa_grade_exact_crosswalk_freeze",
        "version": CROSSWALK_VERSION,
        "previous_version": PREVIOUS_VERSION,
        "reviewed_on": REVIEWED_ON,
        "review_source": REVIEW_SOURCE,
        "candidate_sources": CANDIDATE_SOURCES,
        "matching_policy": "raw exact match only",
        "packet_correspondence": correspondence,
        "operational_projection": {
            "additional_without_safe_floor": (
                "preserved in human decision artifact; projected as SQL NULL "
                "in the existing derived-layer contract"
            ),
            "strict_gpa_safe_subset": (
                "safe_simple_overall only; additional/no-floor rules remain "
                "non-definitive in the strict GPA layer"
            ),
        },
        "inputs": {
            "previous_gpa_crosswalk": {
                "path": PREVIOUS_GPA_CROSSWALK_PATH.as_posix(),
                "sha256": sha256_path(root / PREVIOUS_GPA_CROSSWALK_PATH),
            },
            "previous_grade_crosswalk": {
                "path": PREVIOUS_GRADE_CROSSWALK_PATH.as_posix(),
                "sha256": sha256_path(root / PREVIOUS_GRADE_CROSSWALK_PATH),
            },
            "gpa_review_packet": {
                "path": GPA_PACKET_PATH.as_posix(),
                "sha256": sha256_path(root / GPA_PACKET_PATH),
            },
            "grade_review_packet": {
                "path": GRADE_PACKET_PATH.as_posix(),
                "sha256": sha256_path(root / GRADE_PACKET_PATH),
            },
            "human_decisions": {
                "path": DECISION_PATH.as_posix(),
                "sha256": sha256_path(root / DECISION_PATH),
                "rows": len(decisions),
            },
            "candidate_masters": {
                dataset: {
                    "path": path.as_posix(),
                    "sha256": sha256_path(root / path),
                }
                for dataset, path in CANDIDATE_MASTER_PATHS.items()
            },
        },
        "outputs": {
            "gpa_crosswalk": {
                "path": GPA_CROSSWALK_PATH.as_posix(),
                "sha256": sha256_bytes(gpa_bytes),
                "rows": len(gpa_rows),
            },
            "grade_crosswalk": {
                "path": GRADE_CROSSWALK_PATH.as_posix(),
                "sha256": sha256_bytes(grade_bytes),
                "rows": len(grade_rows),
            },
        },
        "reviewed_decision_counts": {
            "grade_status": dict(sorted(grade_counts.items())),
            "numeric_status": dict(sorted(numeric_counts.items())),
            "overall_floor": dict(sorted(floor_counts.items())),
        },
    }
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return {
        GPA_CROSSWALK_PATH: gpa_bytes,
        GRADE_CROSSWALK_PATH: grade_bytes,
        MANIFEST_PATH: manifest_bytes,
    }


def write_artifacts(root: Path) -> dict[Path, str]:
    artifacts = build_artifact_bytes(root)
    receipts: dict[Path, str] = {}
    for relative, data in artifacts.items():
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        receipts[relative] = sha256_bytes(data)
    return receipts


def _optional_year(value: str) -> int | None:
    return int(value) if value else None


def _fallback_flag(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes"}


def _sorted_counter(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items()))


def candidate_audit_summary(root: Path) -> dict[str, Any]:
    """Re-evaluate only GPA/Grade over the accepted candidate source masters."""

    root = root.resolve()
    decisions = load_decisions(root)
    decision_by_raw = {row["raw_value"]: row for row in decisions}
    review_required_orders = [
        int(row["review_order"])
        for row in decisions
        if row["approved_grade_status"] == "review_required"
    ]
    expected_review_orders = [8, 10, 11, 12, 13, 14, 15, 45, 49, 52, 53, 54, 56]
    if review_required_orders != expected_review_orders:
        raise ValueError("review_required decision order changed.")

    previous_gpa_crosswalk = GPACrosswalk.load(root / PREVIOUS_GPA_CROSSWALK_PATH)
    current_gpa_crosswalk = GPACrosswalk.load(root / GPA_CROSSWALK_PATH)
    previous_gpa_parser = GPAParser(previous_gpa_crosswalk)
    current_gpa_parser = GPAParser(current_gpa_crosswalk)
    previous_grade_crosswalk = GradeRequirementCrosswalk.load(
        root / PREVIOUS_GRADE_CROSSWALK_PATH,
        expected_version=PREVIOUS_VERSION,
    )
    current_grade_crosswalk = GradeRequirementCrosswalk.load(
        root / GRADE_CROSSWALK_PATH,
        expected_version=CROSSWALK_VERSION,
    )
    english_crosswalk = EnglishRequirementCrosswalk.load(
        root / ENGLISH_REQUIREMENT_CROSSWALK_PATH
    )

    candidate_rows = 0
    affected_rows = 0
    affected_by_dataset: Counter[str] = Counter()
    grade_status_after: Counter[str] = Counter()
    numeric_status_after: Counter[str] = Counter()
    floor_after: Counter[str] = Counter()
    gpa_parser_before: Counter[str] = Counter()
    gpa_parser_after: Counter[str] = Counter()
    global_gpa_parser_before: Counter[str] = Counter()
    global_gpa_parser_after: Counter[str] = Counter()
    exact_counts: Counter[str] = Counter()
    global_counts: Counter[str] = Counter()
    rikkyo: dict[str, Any] | None = None

    for dataset, relative in CANDIDATE_MASTER_PATHS.items():
        for row in _read_csv(root / relative):
            candidate_rows += 1
            raw = row["gpa_requirement"] or None
            parse_kwargs = {
                "admission_year": _optional_year(row["admission_year"]),
                "information_year": _optional_year(row["information_year"]),
                "fallback_previous_year": _fallback_flag(
                    row["fallback_previous_year"]
                ),
            }
            gpa_before = previous_gpa_parser.parse(raw, **parse_kwargs)
            gpa_after = current_gpa_parser.parse(raw, **parse_kwargs)
            grade_before = previous_grade_crosswalk.classify(raw)
            grade_after = current_grade_crosswalk.classify(raw)
            global_gpa_parser_before[gpa_before.parse_status] += 1
            global_gpa_parser_after[gpa_after.parse_status] += 1
            global_counts["gpa_exact_unmapped_before"] += int(
                previous_gpa_crosswalk.get(raw) is None
            )
            global_counts["gpa_exact_unmapped_after"] += int(
                current_gpa_crosswalk.get(raw) is None
            )
            global_counts["grade_unmapped_before"] += int(
                grade_before.grade_requirement_status == "unmapped"
            )
            global_counts["grade_unmapped_after"] += int(
                grade_after.grade_requirement_status == "unmapped"
            )

            if raw in decision_by_raw:
                decision = decision_by_raw[raw]
                affected_rows += 1
                affected_by_dataset[dataset] += 1
                exact_counts["gpa_unmapped_before"] += int(
                    previous_gpa_crosswalk.get(raw) is None
                )
                exact_counts["gpa_unmapped_after"] += int(
                    current_gpa_crosswalk.get(raw) is None
                )
                exact_counts["grade_unmapped_before"] += int(
                    grade_before.grade_requirement_status == "unmapped"
                )
                exact_counts["grade_unmapped_after"] += int(
                    grade_after.grade_requirement_status == "unmapped"
                )
                gpa_parser_before[gpa_before.parse_status] += 1
                gpa_parser_after[gpa_after.parse_status] += 1
                grade_status_after[grade_after.grade_requirement_status] += 1
                numeric_status_after[grade_after.overall_gpa_status] += 1
                floor_after[
                    str(grade_after.overall_gpa_min_tenths)
                    if grade_after.overall_gpa_min_tenths is not None
                    else "NULL"
                ] += 1

                expected_floor = (
                    int(decision["approved_overall_floor_tenths"])
                    if decision["approved_overall_floor_tenths"]
                    else None
                )
                expected_additional = (
                    int(decision["approved_additional_conditions"] == "true")
                    if expected_floor is not None
                    else None
                )
                if (
                    grade_after.grade_requirement_status
                    != decision["approved_grade_status"]
                    or grade_after.overall_gpa_status
                    != decision["approved_numeric_status"]
                    or grade_after.overall_gpa_min_tenths != expected_floor
                    or grade_after.additional_grade_conditions
                    != expected_additional
                ):
                    raise ValueError(
                        "Candidate Grade result disagrees with decision "
                        f"#{decision['review_order']}."
                    )

            if row["record_id"] == "RIKKYO-2027-SCI-03":
                english = english_crosswalk.classify(row["english_requirement"] or None)
                rikkyo = {
                    "source_dataset": dataset,
                    "source_version": CANDIDATE_SOURCES[dataset],
                    "record_id": row["record_id"],
                    "review_order": int(decision_by_raw[row["gpa_requirement"]]["review_order"]),
                    "grade_requirement_status": grade_after.grade_requirement_status,
                    "overall_gpa_min_tenths": grade_after.overall_gpa_min_tenths,
                    "overall_gpa_status": grade_after.overall_gpa_status,
                    "additional_grade_conditions": grade_after.additional_grade_conditions,
                    "strict_gpa_parse_status": gpa_after.parse_status,
                    "strict_gpa_min_tenths": gpa_after.gpa_min_tenths,
                    "english_requirement_status": english.requirement_status,
                    "english_search_disposition": english.search_disposition,
                }

    if candidate_rows != 6411 or affected_rows != 596:
        raise ValueError(
            f"Candidate row regression: rows={candidate_rows}, affected={affected_rows}."
        )
    if any(
        exact_counts[key] != expected
        for key, expected in {
            "gpa_unmapped_before": 596,
            "gpa_unmapped_after": 0,
            "grade_unmapped_before": 596,
            "grade_unmapped_after": 0,
        }.items()
    ):
        raise ValueError(f"Candidate exact mapping regression: {dict(exact_counts)}")
    if rikkyo is None:
        raise ValueError("RIKKYO-2027-SCI-03 is absent from the candidate sources.")
    expected_rikkyo = {
        "review_order": 41,
        "grade_requirement_status": "required",
        "overall_gpa_min_tenths": 38,
        "overall_gpa_status": "safe_overall_with_additional_conditions",
        "additional_grade_conditions": 1,
        "strict_gpa_parse_status": "conditional_review",
        "strict_gpa_min_tenths": None,
        "english_requirement_status": "required",
        "english_search_disposition": "safe_exact",
    }
    if any(rikkyo[key] != value for key, value in expected_rikkyo.items()):
        raise ValueError(f"RIKKYO regression failed: {rikkyo}")

    decision_grade_counts = Counter(
        row["approved_grade_status"] for row in decisions
    )
    decision_numeric_counts = Counter(
        row["approved_numeric_status"] for row in decisions
    )
    decision_floor_counts = Counter(
        row["approved_overall_floor"] or "NULL" for row in decisions
    )
    return {
        "artifact": "gpa_grade_crosswalk_v0_2_candidate_audit",
        "profile": "candidate_audit_focused_gpa_grade",
        "scope": {
            "candidate_sources": CANDIDATE_SOURCES,
            "candidate_admissions": candidate_rows,
            "reviewed_distinct_raw_values": len(decisions),
            "affected_admissions": affected_rows,
            "affected_by_dataset": _sorted_counter(affected_by_dataset),
            "full_sqlite_or_site_rebuild_performed": False,
        },
        "packet_correspondence": verify_packet_correspondence(root, decisions),
        "decision_counts_distinct_raw": {
            "grade_status": _sorted_counter(decision_grade_counts),
            "numeric_status": _sorted_counter(decision_numeric_counts),
            "overall_floor": _sorted_counter(decision_floor_counts),
        },
        "candidate_affected_counts_after": {
            "grade_status": _sorted_counter(grade_status_after),
            "numeric_status": _sorted_counter(numeric_status_after),
            "overall_floor_tenths": _sorted_counter(floor_after),
        },
        "exact_crosswalk_unmapped": {
            "affected_admissions": dict(sorted(exact_counts.items())),
            "all_candidate_admissions": dict(sorted(global_counts.items())),
        },
        "parser_statuses": {
            "affected_before": _sorted_counter(gpa_parser_before),
            "affected_after": _sorted_counter(gpa_parser_after),
            "all_candidate_before": _sorted_counter(global_gpa_parser_before),
            "all_candidate_after": _sorted_counter(global_gpa_parser_after),
        },
        "review_required": {
            "distinct_raw_values": len(review_required_orders),
            "review_orders": review_required_orders,
            "affected_admissions": grade_status_after["review_required"],
            "raw_values": [
                {
                    "review_order": int(row["review_order"]),
                    "raw_value": row["raw_value"],
                    "candidate_admissions": int(row["frequency"]),
                }
                for row in decisions
                if row["approved_grade_status"] == "review_required"
            ],
        },
        "rikkyo_2027_sci_03": rikkyo,
        "crosswalks": {
            "previous_version": PREVIOUS_VERSION,
            "new_version": CROSSWALK_VERSION,
            "gpa_sha256": sha256_path(root / GPA_CROSSWALK_PATH),
            "grade_sha256": sha256_path(root / GRADE_CROSSWALK_PATH),
            "manifest_sha256": sha256_path(root / MANIFEST_PATH),
        },
        "status": "passed",
    }


def _candidate_audit_markdown(summary: Mapping[str, Any]) -> str:
    exact = summary["exact_crosswalk_unmapped"]["affected_admissions"]
    after = summary["candidate_affected_counts_after"]
    review = summary["review_required"]
    rikkyo = summary["rikkyo_2027_sci_03"]
    lines = [
        "# GPA / Grade crosswalk v0.2 candidate audit",
        "",
        f"Status: `{summary['status']}`",
        "",
        "This is a focused candidate-audit re-evaluation only. No full SQLite "
        "or Site-data rebuild was run.",
        "",
        "## Scope",
        "",
        f"- Candidate admissions: {summary['scope']['candidate_admissions']:,}",
        f"- Reviewed exact raw values: {summary['scope']['reviewed_distinct_raw_values']}",
        f"- Affected admissions: {summary['scope']['affected_admissions']}",
        "- Matching policy: raw exact match only",
        "",
        "## Before / after exact-crosswalk coverage",
        "",
        "| Layer | Before unmapped | After unmapped |",
        "|---|---:|---:|",
        f"| GPA | {exact['gpa_unmapped_before']} | {exact['gpa_unmapped_after']} |",
        f"| Grade | {exact['grade_unmapped_before']} | {exact['grade_unmapped_after']} |",
        "",
        "## Candidate admissions after review",
        "",
        "- Grade status: "
        f"`{json.dumps(after['grade_status'], ensure_ascii=False, sort_keys=True)}`",
        "- Numeric status: "
        f"`{json.dumps(after['numeric_status'], ensure_ascii=False, sort_keys=True)}`",
        "- Overall floor tenths: "
        f"`{json.dumps(after['overall_floor_tenths'], ensure_ascii=False, sort_keys=True)}`",
        "",
        "## Review-required decisions retained",
        "",
        f"Distinct raw values: {review['distinct_raw_values']}; affected admissions: "
        f"{review['affected_admissions']}",
        "",
        "| Order | Admissions | Exact raw value |",
        "|---:|---:|---|",
    ]
    lines.extend(
        f"| {item['review_order']} | {item['candidate_admissions']} | {item['raw_value']} |"
        for item in review["raw_values"]
    )
    lines.extend(
        [
            "",
            "## RIKKYO-2027-SCI-03",
            "",
            f"- Grade: `{rikkyo['grade_requirement_status']}`",
            f"- Overall floor: `{rikkyo['overall_gpa_min_tenths']}` tenths",
            f"- Overall status: `{rikkyo['overall_gpa_status']}`",
            f"- Strict GPA: `{rikkyo['strict_gpa_parse_status']}` with no numeric floor",
            f"- English: `{rikkyo['english_requirement_status']}` / "
            f"`{rikkyo['english_search_disposition']}` (English v0.2 review; GPA/Grade unchanged)",
            "",
        ]
    )
    return "\n".join(lines)


def write_candidate_audit_reports(root: Path) -> dict[Path, str]:
    summary = candidate_audit_summary(root)
    payloads = {
        CANDIDATE_AUDIT_JSON_PATH: (
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8"),
        CANDIDATE_AUDIT_MD_PATH: _candidate_audit_markdown(summary).encode("utf-8"),
    }
    receipts: dict[Path, str] = {}
    for relative, data in payloads.items():
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        receipts[relative] = sha256_bytes(data)
    return receipts


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    receipts = write_artifacts(root)
    receipts.update(write_candidate_audit_reports(root))
    for path, digest in receipts.items():
        print(f"{digest}  {path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
