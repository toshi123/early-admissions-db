"""Deterministic 2026-09-22 English and academic-field crosswalk update.

Human-reviewed decision CSVs are the only authority for the new values.  This
module validates their one-to-one correspondence with the frozen review
packets, appends them to preserved historical crosswalks, and performs a
fail-closed focused audit against the 6,411-row candidate master dataset.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .academic_field import AcademicFieldCrosswalk, AcademicFieldTaxonomy
from .academic_field_v2 import AcademicFieldV2Contract
from .english_requirement import EnglishRequirementCrosswalk


UPDATE_ID = "update_20260922_v5_81_v1_08"
REPORT_DIR = Path("validation/reports") / UPDATE_ID
ENGLISH_PACKET = REPORT_DIR / "english_requirement_new_values.csv"
ACADEMIC_RAW_PACKET = REPORT_DIR / "academic_field_v0_2_new_raw_values.csv"
ACADEMIC_CONTEXT_PACKET = REPORT_DIR / "academic_field_v0_2_new_contexts.csv"
ENGLISH_DECISIONS = REPORT_DIR / "english_requirement_human_review_decisions_v0_2.csv"
ACADEMIC_RAW_DECISIONS = REPORT_DIR / "academic_field_raw_human_review_decisions_v0_3.csv"
ACADEMIC_CONTEXT_DECISIONS = REPORT_DIR / "academic_field_context_human_review_decisions_v0_3.csv"

ENGLISH_OLD = Path("schema/english_requirement/english_requirement_crosswalk_v0_1.csv")
ENGLISH_NEW = Path("schema/english_requirement/english_requirement_crosswalk_v0_2.csv")
ENGLISH_MANIFEST = Path("schema/english_requirement/english_requirement_crosswalk_manifest_v0_2.json")
ACADEMIC_V1_OLD = Path("schema/academic_field/academic_field_crosswalk_v0_1.csv")
ACADEMIC_V1_NEW = Path("schema/academic_field/academic_field_crosswalk_v0_2.csv")
ACADEMIC_V2_RAW_OLD = Path("schema/academic_field/v0_2/academic_field_raw_crosswalk_v0_2.csv")
ACADEMIC_V2_CONTEXT_OLD = Path("schema/academic_field/v0_2/academic_field_context_crosswalk_v0_2.csv")
ACADEMIC_V3_DIR = Path("schema/academic_field/v0_3")
ACADEMIC_V3_RAW = ACADEMIC_V3_DIR / "academic_field_raw_crosswalk_v0_3.csv"
ACADEMIC_V3_CONTEXT = ACADEMIC_V3_DIR / "academic_field_context_crosswalk_v0_3.csv"
ACADEMIC_V3_MANIFEST = ACADEMIC_V3_DIR / "academic_field_crosswalk_manifest_v0_3.json"
FOCUSED_JSON = REPORT_DIR / "english_academic_crosswalk_candidate_audit.json"
FOCUSED_MD = REPORT_DIR / "english_academic_crosswalk_candidate_audit.md"

CANDIDATE_MASTERS = (
    Path("sources/incoming/2026-09-22/kokkoritsu_v5_81/kokkoritsu_early_admissions_2027_master_v5_81.csv"),
    Path("sources/incoming/2026-09-22/shidai_v1_08/shidai_early_admissions_2027_master_v1_08.csv"),
)

RAW_HEADER = (
    "mapping_contract_version", "raw_value", "mapping_status",
    "broad_mapping_status", "subcategory_mapping_status", "group_code",
    "subcategory_code", "membership_order", "review_note",
)
CONTEXT_HEADER = (
    "mapping_contract_version", "source_dataset", "university", "faculty_school",
    "department", "academic_field", "mapping_status", "broad_mapping_status",
    "subcategory_mapping_status", "merge_mode", "group_code",
    "subcategory_code", "membership_order", "review_note",
)


class CrosswalkUpdateError(ValueError):
    """Raised when a reviewed decision or deterministic rebuild is invalid."""


def _read(path: Path) -> list[dict[str, str]]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise CrosswalkUpdateError(f"CSV must be UTF-8, LF, BOM-free: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, header: Sequence[str], rows: Iterable[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _metadata(path: Path, rows: int | None = None) -> dict[str, object]:
    display_path = path
    if path.is_absolute():
        try:
            display_path = path.relative_to(Path(__file__).resolve().parents[2])
        except ValueError:
            display_path = path
    value: dict[str, object] = {
        "path": display_path.as_posix(), "sha256": _sha256(path),
        "size_bytes": path.stat().st_size,
    }
    if rows is not None:
        value["rows"] = rows
    return value


def _validate_review_correspondence(
    packet: Sequence[dict[str, str]],
    decisions: Sequence[dict[str, str]],
    *,
    raw_column: str,
) -> None:
    if len(packet) != len(decisions):
        raise CrosswalkUpdateError("Review packet/decision row-count mismatch.")
    for order, (source, decision) in enumerate(zip(packet, decisions), 1):
        if decision["review_order"] != str(order):
            raise CrosswalkUpdateError(f"Non-contiguous review_order at {order}.")
        expected = source["raw_or_context"]
        actual = decision[raw_column]
        if expected != actual:
            raise CrosswalkUpdateError(f"Review correspondence mismatch at {order}.")
        for column in ("frequency", "representative_record_id"):
            if source[column] != decision[column]:
                raise CrosswalkUpdateError(
                    f"Review {column} mismatch at {order}: {source[column]!r} != {decision[column]!r}"
                )
        if (
            decision["reviewed_on"] != "2026-09-22"
            or decision["review_method"] != "human review"
            or decision["candidate_sources"] != "kokkoritsu 5.81 + shidai 1.08"
        ):
            raise CrosswalkUpdateError(f"Review metadata mismatch at {order}.")


def _validate_context_correspondence(
    packet: Sequence[dict[str, str]], decisions: Sequence[dict[str, str]]
) -> None:
    if len(packet) != len(decisions):
        raise CrosswalkUpdateError("Context packet/decision row-count mismatch.")
    for order, (source, decision) in enumerate(zip(packet, decisions), 1):
        if decision["review_order"] != str(order):
            raise CrosswalkUpdateError(f"Non-contiguous context review_order at {order}.")
        key = " | ".join(
            decision[column]
            for column in (
                "source_dataset", "university", "faculty_school", "department", "academic_field"
            )
        )
        if source["raw_or_context"] != key:
            raise CrosswalkUpdateError(f"Context correspondence mismatch at {order}.")
        for column in ("frequency", "representative_record_id"):
            if source[column] != decision[column]:
                raise CrosswalkUpdateError(f"Context {column} mismatch at {order}.")
        if decision["merge_mode"] != "authoritative":
            raise CrosswalkUpdateError("Reviewed context must be authoritative.")


def _candidate_rows(repo_root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path, dataset in zip(CANDIDATE_MASTERS, ("kokkoritsu", "shidai")):
        with (repo_root / path).open("r", encoding="utf-8-sig", newline="") as handle:
            rows.extend(dict(row, source_dataset=dataset) for row in csv.DictReader(handle))
    if len(rows) != 6411:
        raise CrosswalkUpdateError(f"Expected 6,411 candidate rows, found {len(rows)}.")
    return rows


def _validate_packet_frequencies(
    candidate_rows: Sequence[dict[str, str]],
    decisions: Sequence[dict[str, str]],
    field: str,
) -> None:
    counts = Counter(row[field] for row in candidate_rows if row[field])
    by_record = {row["record_id"]: row for row in candidate_rows}
    for decision in decisions:
        raw = decision["raw_value"]
        if counts[raw] != int(decision["frequency"]):
            raise CrosswalkUpdateError(f"Candidate frequency mismatch for {raw!r}.")
        representative = by_record.get(decision["representative_record_id"])
        if representative is None or representative[field] != raw:
            raise CrosswalkUpdateError(f"Candidate representative mismatch for {raw!r}.")


def _taxonomy_maps(repo_root: Path) -> tuple[dict[str, int], dict[str, tuple[str, int]]]:
    broad_rows = _read(
        repo_root / "schema/academic_field/v0_2/academic_field_broad_taxonomy_v0_2.csv"
    )
    sub_rows = _read(
        repo_root / "schema/academic_field/v0_2/academic_field_subcategory_taxonomy_v0_2.csv"
    )
    broad_order = {row["group_code"]: index for index, row in enumerate(broad_rows)}
    sub_info = {
        row["subcategory_code"]: (row["parent_group_code"], int(row["display_order"]))
        for row in sub_rows
    }
    return broad_order, sub_info


def _memberships(
    broad_text: str,
    sub_text: str,
    broad_order: Mapping[str, int],
    sub_info: Mapping[str, tuple[str, int]],
) -> list[tuple[str, str]]:
    groups = set(filter(None, broad_text.split("|")))
    subs = set(filter(None, sub_text.split("|")))
    if not groups:
        if subs:
            raise CrosswalkUpdateError("Subcategories cannot exist without a broad group.")
        return []
    if not groups.issubset(broad_order):
        raise CrosswalkUpdateError(f"Unknown broad group: {groups - set(broad_order)}")
    for sub in subs:
        if sub not in sub_info or sub_info[sub][0] not in groups:
            raise CrosswalkUpdateError(f"Invalid subcategory decision: {sub!r}")
    result: list[tuple[str, str]] = []
    for group in sorted(groups, key=broad_order.__getitem__):
        children = sorted(
            (sub for sub in subs if sub_info[sub][0] == group),
            key=lambda sub: sub_info[sub][1],
        )
        result.extend((group, sub) for sub in children)
        if not children:
            result.append((group, ""))
    return result


def _status(memberships: Sequence[tuple[str, str]]) -> tuple[str, str, str]:
    groups = {group for group, _ in memberships}
    subs = {sub for _, sub in memberships if sub}
    return (
        "single" if len(memberships) == 1 else "multi",
        "single" if len(groups) == 1 else "multi",
        "not_applicable" if not subs else ("single" if len(subs) == 1 else "multi"),
    )


def _build_english(repo_root: Path, decisions: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    old_rows = _read(repo_root / ENGLISH_OLD)
    old_values = {row["raw_value"] for row in old_rows}
    new_values = {row["raw_value"] for row in decisions}
    if old_values & new_values:
        raise CrosswalkUpdateError("English decision overlaps the previous crosswalk.")
    rows = [
        {**row, "contract_version": "0.2"}
        for row in old_rows
    ] + [
        {
            "contract_version": "0.2",
            "raw_value": row["raw_value"],
            "requirement_status": row["final_status"],
            "review_note": row["review_note"],
        }
        for row in decisions
    ]
    rows.sort(key=lambda row: row["raw_value"])
    _write_csv(
        repo_root / ENGLISH_NEW,
        ("contract_version", "raw_value", "requirement_status", "review_note"),
        rows,
    )
    return rows


def _reverse_compatibility(repo_root: Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for row in _read(
        repo_root / "schema/academic_field/v0_2/academic_field_v0_1_to_v0_2_crosswalk.csv"
    ):
        result.setdefault(row["to_group_code"], set()).add(row["from_group_code"])
    return result


def _build_academic_v1(
    repo_root: Path, decisions: Sequence[dict[str, str]]
) -> list[dict[str, str]]:
    old_rows = _read(repo_root / ACADEMIC_V1_OLD)
    old_values = {row["raw_value"] for row in old_rows}
    reverse = _reverse_compatibility(repo_root)
    additions: list[dict[str, str]] = []
    for decision in decisions:
        raw = decision["raw_value"]
        if raw in old_values:
            raise CrosswalkUpdateError(f"Academic v0.1 decision overlaps old raw: {raw!r}")
        mapped: set[str] = set()
        ambiguous = decision["raw_status"] == "review_required"
        for broad in filter(None, decision["broad_group_codes"].split("|")):
            candidates = reverse.get(broad, set())
            if len(candidates) != 1:
                ambiguous = True
            else:
                mapped.update(candidates)
        if ambiguous or not mapped:
            additions.append({
                "mapping_contract_version": "0.2", "raw_value": raw,
                "mapping_status": "review_required", "group_code": "",
                "group_order": "", "review_note": (
                    "Human-reviewed v0.2 membership has no unambiguous v0.1 compatibility projection; fail closed."
                ),
            })
            continue
        taxonomy = AcademicFieldTaxonomy.load(
            repo_root / "schema/academic_field/academic_field_taxonomy_v0_1.csv"
        )
        order = {item.group_code: item.display_order for item in taxonomy}
        groups = sorted(mapped, key=order.__getitem__)
        status = "single" if len(groups) == 1 else "multi"
        for index, group in enumerate(groups, 1):
            additions.append({
                "mapping_contract_version": "0.2", "raw_value": raw,
                "mapping_status": status, "group_code": group,
                "group_order": str(index),
                "review_note": "Conservative unique reverse projection from human-reviewed v0.2 broad membership.",
            })
    rows = [{**row, "mapping_contract_version": "0.2"} for row in old_rows] + additions
    rows.sort(key=lambda row: (row["raw_value"], int(row["group_order"] or 0)))
    _write_csv(repo_root / ACADEMIC_V1_NEW, tuple(rows[0]), rows)
    return rows


def _new_mapping_rows(
    decision: Mapping[str, str],
    *,
    broad_order: Mapping[str, int],
    sub_info: Mapping[str, tuple[str, int]],
    context: bool,
) -> list[dict[str, str]]:
    memberships = _memberships(
        decision["broad_group_codes"], decision["subcategory_codes"],
        broad_order, sub_info,
    )
    if not memberships:
        if context:
            raise CrosswalkUpdateError("Reviewed context cannot be unresolved.")
        status_values = ("review_required",) * 3
        memberships = [("", "")]
    else:
        status_values = _status(memberships)
    rows: list[dict[str, str]] = []
    for index, (group, sub) in enumerate(memberships, 1):
        row = {
            "mapping_contract_version": "0.3",
            "mapping_status": status_values[0],
            "broad_mapping_status": status_values[1],
            "subcategory_mapping_status": status_values[2],
            "group_code": group, "subcategory_code": sub,
            "membership_order": "" if not group else str(index),
            "review_note": decision["review_note"],
        }
        if context:
            row = {
                "mapping_contract_version": "0.3",
                **{
                    key: decision[key]
                    for key in (
                        "source_dataset", "university", "faculty_school",
                        "department", "academic_field",
                    )
                },
                "mapping_status": status_values[0],
                "broad_mapping_status": status_values[1],
                "subcategory_mapping_status": status_values[2],
                "merge_mode": decision["merge_mode"],
                "group_code": group, "subcategory_code": sub,
                "membership_order": str(index),
                "review_note": decision["review_note"],
            }
        else:
            row = {"mapping_contract_version": "0.3", "raw_value": decision["raw_value"], **row}
        rows.append(row)
    return rows


def _build_academic_v3(
    repo_root: Path,
    raw_decisions: Sequence[dict[str, str]],
    context_decisions: Sequence[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    broad_order, sub_info = _taxonomy_maps(repo_root)
    old_raw = _read(repo_root / ACADEMIC_V2_RAW_OLD)
    old_context = _read(repo_root / ACADEMIC_V2_CONTEXT_OLD)
    old_raw_values = {row["raw_value"] for row in old_raw}
    old_context_keys = {
        tuple(row[key] for key in CONTEXT_HEADER[1:6]) for row in old_context
    }
    new_raw_values = {row["raw_value"] for row in raw_decisions}
    if old_raw_values & new_raw_values:
        raise CrosswalkUpdateError("Academic raw decisions overlap v0.2 crosswalk.")
    new_context_keys = {
        tuple(row[key] for key in CONTEXT_HEADER[1:6]) for row in context_decisions
    }
    if old_context_keys & new_context_keys:
        raise CrosswalkUpdateError("Academic context decisions overlap v0.2 crosswalk.")
    if len(new_context_keys) != 71:
        raise CrosswalkUpdateError("Academic context decisions are not unique.")

    raw_rows = [{**row, "mapping_contract_version": "0.3"} for row in old_raw]
    for decision in raw_decisions:
        raw_rows.extend(_new_mapping_rows(
            decision, broad_order=broad_order, sub_info=sub_info, context=False
        ))
    raw_rows.sort(key=lambda row: (row["raw_value"], int(row["membership_order"] or 0)))

    context_rows = [{**row, "mapping_contract_version": "0.3"} for row in old_context]
    for decision in context_decisions:
        context_rows.extend(_new_mapping_rows(
            decision, broad_order=broad_order, sub_info=sub_info, context=True
        ))
    context_rows.sort(key=lambda row: (
        row["source_dataset"], row["university"], row["faculty_school"],
        row["department"], row["academic_field"], int(row["membership_order"] or 0),
    ))
    _write_csv(repo_root / ACADEMIC_V3_RAW, RAW_HEADER, raw_rows)
    _write_csv(repo_root / ACADEMIC_V3_CONTEXT, CONTEXT_HEADER, context_rows)
    return raw_rows, context_rows


def _classification_counts(values: Iterable[str]) -> dict[str, int]:
    counts = Counter(values)
    return dict(sorted(counts.items()))


def build_and_audit(repo_root: Path) -> dict[str, object]:
    english_packet = _read(repo_root / ENGLISH_PACKET)
    raw_packet = _read(repo_root / ACADEMIC_RAW_PACKET)
    context_packet = _read(repo_root / ACADEMIC_CONTEXT_PACKET)
    english_decisions = _read(repo_root / ENGLISH_DECISIONS)
    raw_decisions = _read(repo_root / ACADEMIC_RAW_DECISIONS)
    context_decisions = _read(repo_root / ACADEMIC_CONTEXT_DECISIONS)
    _validate_review_correspondence(
        english_packet, english_decisions, raw_column="raw_value"
    )
    _validate_review_correspondence(
        raw_packet, raw_decisions, raw_column="raw_value"
    )
    _validate_context_correspondence(context_packet, context_decisions)
    if _classification_counts(row["final_status"] for row in english_decisions) != {
        "not_required": 3, "required": 57, "review_required": 5, "unknown": 1
    }:
        raise CrosswalkUpdateError("English reviewed status totals differ from approval.")

    candidate_rows = _candidate_rows(repo_root)
    _validate_packet_frequencies(candidate_rows, english_decisions, "english_requirement")
    _validate_packet_frequencies(candidate_rows, raw_decisions, "academic_field")
    context_counts = Counter(
        (
            row["source_dataset"], row["university"], row["faculty_school"],
            row["department"], row["academic_field"],
        )
        for row in candidate_rows
    )
    by_record = {row["record_id"]: row for row in candidate_rows}
    for decision in context_decisions:
        key = tuple(decision[column] for column in CONTEXT_HEADER[1:6])
        if context_counts[key] != int(decision["frequency"]):
            raise CrosswalkUpdateError(f"Candidate context frequency mismatch: {key!r}")
        record = by_record.get(decision["representative_record_id"])
        if record is None or tuple(record[column] for column in CONTEXT_HEADER[1:6]) != key:
            raise CrosswalkUpdateError(f"Candidate context representative mismatch: {key!r}")

    english_rows = _build_english(repo_root, english_decisions)
    academic_v1_rows = _build_academic_v1(repo_root, raw_decisions)
    academic_raw_rows, academic_context_rows = _build_academic_v3(
        repo_root, raw_decisions, context_decisions
    )

    english_contract = EnglishRequirementCrosswalk.load(
        repo_root / ENGLISH_NEW, expected_version="0.2"
    )
    academic_taxonomy = AcademicFieldTaxonomy.load(
        repo_root / "schema/academic_field/academic_field_taxonomy_v0_1.csv"
    )
    academic_v1_contract = AcademicFieldCrosswalk.load(
        repo_root / ACADEMIC_V1_NEW, academic_taxonomy, expected_version="0.2"
    )
    academic_v2_contract = AcademicFieldV2Contract.load(repo_root)

    for decision in english_decisions:
        actual = english_contract.classify(decision["raw_value"])
        if actual.requirement_status != decision["final_status"]:
            raise CrosswalkUpdateError(
                f"English classification differs from review #{decision['review_order']}."
            )
    for decision in raw_decisions:
        actual = academic_v2_contract.classify(
            source_dataset="review_probe", university="review_probe",
            faculty_school="", department="", academic_field=decision["raw_value"],
        )
        expected_groups = set(filter(None, decision["broad_group_codes"].split("|")))
        expected_subs = set(filter(None, decision["subcategory_codes"].split("|")))
        actual_groups = {item[0] for item in actual.broad_memberships}
        actual_subs = {item[0] for item in actual.subcategory_memberships}
        if expected_groups != actual_groups or expected_subs != actual_subs:
            raise CrosswalkUpdateError(
                f"Academic raw membership differs from review #{decision['review_order']}."
            )
        if decision["raw_status"] == "review_required" and (
            actual.broad_mapping_status != "review_required"
            or actual.subcategory_mapping_status != "review_required"
        ):
            raise CrosswalkUpdateError(
                f"Academic raw review status differs at #{decision['review_order']}."
            )

    english_status = Counter()
    academic_v1_status = Counter()
    academic_v2_broad = Counter()
    academic_v2_sub = Counter()
    reviewed_context_hits = Counter()
    reviewed_context_keys = {
        tuple(row[column] for column in CONTEXT_HEADER[1:6]) for row in context_decisions
    }
    reviewed_context_by_key = {
        tuple(row[column] for column in CONTEXT_HEADER[1:6]): row
        for row in context_decisions
    }
    for row in candidate_rows:
        english_status[
            english_contract.classify(row["english_requirement"] or None).requirement_status
        ] += 1
        academic_v1_status[
            academic_v1_contract.lookup(row["academic_field"] or None).mapping_status
        ] += 1
        result = academic_v2_contract.classify(
            source_dataset=row["source_dataset"], university=row["university"],
            faculty_school=row["faculty_school"], department=row["department"],
            academic_field=row["academic_field"] or None,
        )
        academic_v2_broad[result.broad_mapping_status] += 1
        academic_v2_sub[result.subcategory_mapping_status] += 1
        key = (
            row["source_dataset"], row["university"], row["faculty_school"],
            row["department"], row["academic_field"],
        )
        if key in reviewed_context_keys:
            reviewed_context_hits[key] += 1
            if not result.context_mapping_consulted or result.context_mapping_effect != "authoritative":
                raise CrosswalkUpdateError(f"Reviewed context was not authoritative: {key!r}")
            decision = reviewed_context_by_key[key]
            expected_groups = set(
                filter(None, decision["broad_group_codes"].split("|"))
            )
            expected_subs = set(
                filter(None, decision["subcategory_codes"].split("|"))
            )
            if (
                {item[0] for item in result.broad_memberships} != expected_groups
                or {item[0] for item in result.subcategory_memberships}
                != expected_subs
            ):
                raise CrosswalkUpdateError(
                    f"Authoritative context leaked or lost membership: {key!r}"
                )

    if english_status["unmapped"] or academic_v1_status["unmapped"] or academic_v2_broad["unmapped"]:
        raise CrosswalkUpdateError("Focused candidate audit still contains prohibited unmapped rows.")
    if set(reviewed_context_hits) != reviewed_context_keys or sum(reviewed_context_hits.values()) != 88:
        raise CrosswalkUpdateError("Reviewed academic contexts were not all exercised exactly.")

    artifacts = {
        "english_crosswalk": _metadata(repo_root / ENGLISH_NEW, len(english_rows)),
        "academic_v0_1_compatibility_crosswalk": _metadata(
            repo_root / ACADEMIC_V1_NEW, len(academic_v1_rows)
        ),
        "academic_v0_2_raw_crosswalk": _metadata(
            repo_root / ACADEMIC_V3_RAW, len(academic_raw_rows)
        ),
        "academic_v0_2_context_crosswalk": _metadata(
            repo_root / ACADEMIC_V3_CONTEXT, len(academic_context_rows)
        ),
    }
    english_manifest = {
        "contract_version": "0.2", "previous_contract_version": "0.1",
        "reviewed_on": "2026-09-22", "review_method": "human review",
        "candidate_sources": {"kokkoritsu": "5.81", "shidai": "1.08"},
        "decision_count": 66,
        "decision_counts": _classification_counts(row["final_status"] for row in english_decisions),
        "semantic_policy": {
            "english_or_other_language_alternative": "required",
            "required_with_special_exemptions": "required",
            "merely_desirable": "not_required",
            "unpublished_external_requirement": "unknown",
        },
        "previous_artifact": _metadata(repo_root / ENGLISH_OLD, len(_read(repo_root / ENGLISH_OLD))),
        "artifact": artifacts["english_crosswalk"],
        "decision_artifact": _metadata(repo_root / ENGLISH_DECISIONS, 66),
    }
    _write_json(repo_root / ENGLISH_MANIFEST, english_manifest)
    academic_manifest = {
        "mapping_contract_version": "0.3",
        "previous_mapping_contract_version": "0.2",
        "taxonomy_version": "0.2",
        "reviewed_on": "2026-09-22", "review_method": "human review",
        "candidate_sources": {"kokkoritsu": "5.81", "shidai": "1.08"},
        "raw_decision_count": 39, "context_decision_count": 71,
        "context_merge_mode": "authoritative_exact_tuple_only",
        "preserved_taxonomy_artifacts": [
            _metadata(repo_root / "schema/academic_field/v0_2/academic_field_broad_taxonomy_v0_2.csv", 30),
            _metadata(repo_root / "schema/academic_field/v0_2/academic_field_subcategory_taxonomy_v0_2.csv", 89),
            _metadata(repo_root / "schema/academic_field/v0_2/academic_field_v0_1_to_v0_2_crosswalk.csv"),
        ],
        "previous_artifacts": [
            _metadata(repo_root / ACADEMIC_V2_RAW_OLD, len(_read(repo_root / ACADEMIC_V2_RAW_OLD))),
            _metadata(repo_root / ACADEMIC_V2_CONTEXT_OLD, len(_read(repo_root / ACADEMIC_V2_CONTEXT_OLD))),
        ],
        "artifacts": artifacts,
        "decision_artifacts": [
            _metadata(repo_root / ACADEMIC_RAW_DECISIONS, 39),
            _metadata(repo_root / ACADEMIC_CONTEXT_DECISIONS, 71),
        ],
    }
    _write_json(repo_root / ACADEMIC_V3_MANIFEST, academic_manifest)

    audit: dict[str, object] = {
        "status": "passed",
        "candidate_rows": len(candidate_rows),
        "correspondence": {"english": 66, "academic_raw": 39, "academic_context": 71},
        "reviewed_context_admission_rows": sum(reviewed_context_hits.values()),
        "english_classification_counts": dict(sorted(english_status.items())),
        "academic_v0_1_classification_counts": dict(sorted(academic_v1_status.items())),
        "academic_v0_2_broad_classification_counts": dict(sorted(academic_v2_broad.items())),
        "academic_v0_2_subcategory_classification_counts": dict(sorted(academic_v2_sub.items())),
        "prohibited_unmapped": {
            "english": english_status["unmapped"],
            "academic_v0_1": academic_v1_status["unmapped"],
            "academic_v0_2": academic_v2_broad["unmapped"],
        },
        "artifacts": artifacts,
    }
    _write_json(repo_root / FOCUSED_JSON, audit)
    (repo_root / FOCUSED_MD).write_text(
        "# English / Academic-field focused candidate audit\n\n"
        f"- Status: **PASS**\n- Candidate admissions: {len(candidate_rows):,}\n"
        "- Review correspondence: English 66 / Academic raw 39 / Academic context 71\n"
        f"- Reviewed context admission rows: {sum(reviewed_context_hits.values())}\n"
        f"- English counts: `{json.dumps(dict(sorted(english_status.items())), ensure_ascii=False)}`\n"
        f"- Academic v0.1 counts: `{json.dumps(dict(sorted(academic_v1_status.items())), ensure_ascii=False)}`\n"
        f"- Academic v0.2 broad counts: `{json.dumps(dict(sorted(academic_v2_broad.items())), ensure_ascii=False)}`\n"
        "- Prohibited unmapped rows: 0 / 0 / 0\n",
        encoding="utf-8", newline="\n",
    )
    return audit


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    result = build_and_audit(repo_root)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
