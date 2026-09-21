"""Pure structured search over the read-only static Site-data projection."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SITE_DATA_SCHEMA_VERSION = "0.2"
GPA_MODES = frozenset({"safe", "review", "all"})
LOGICAL_KEY_FIELDS = ("source_dataset", "source_version", "record_id")
MULTI_VALUE_FIELDS = (
    "university",
    "institution_type",
    "prefecture",
    "academic_field",
    "selection_category",
    "exclusive_enrollment_status",
    "school_recommendation_required",
    "academic_record_required",
    "common_test_required",
    "research_requirement_required",
    "research_activity_level_status",
    "selection_interview",
    "selection_oral_exam",
    "selection_presentation",
    "selection_essay",
    "selection_written_exam",
    "selection_common_test",
)


class SiteSearchError(RuntimeError):
    """Raised when a static projection or search request violates v0.2."""


@dataclass(frozen=True)
class AcademicFieldV2Branch:
    """One v0.2 broad branch with an optional OR-list of subcategories."""

    group_code: str
    subcategory_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SearchRequest:
    university: tuple[str, ...] = ()
    institution_type: tuple[str, ...] = ()
    prefecture: tuple[str, ...] = ()
    prefecture_membership: tuple[str, ...] = ()
    academic_field: tuple[str, ...] = ()
    academic_field_group: tuple[str, ...] = ()
    academic_field_mapping_status: tuple[str, ...] = ()
    academic_field_v2_branches: tuple[AcademicFieldV2Branch, ...] = ()
    stem_flag: bool | None = None
    selection_category: tuple[str, ...] = ()
    exclusive_enrollment_status: tuple[str, ...] = ()
    school_recommendation_required: tuple[str, ...] = ()
    academic_record_required: tuple[str, ...] = ()
    common_test_required: tuple[str, ...] = ()
    research_requirement_required: tuple[str, ...] = ()
    research_activity_level_status: tuple[str, ...] = ()
    selection_interview: tuple[str, ...] = ()
    selection_oral_exam: tuple[str, ...] = ()
    selection_presentation: tuple[str, ...] = ()
    selection_essay: tuple[str, ...] = ()
    selection_written_exam: tuple[str, ...] = ()
    selection_common_test: tuple[str, ...] = ()
    english_requirement_status: tuple[str, ...] = ()
    gpa_tenths: int | None = None
    gpa_mode: str = "all"
    grade_requirement_status: str | None = None
    overall_gpa_tenths: int | None = None

    def validate(self) -> None:
        if self.gpa_mode not in GPA_MODES:
            raise SiteSearchError(f"Unsupported GPA mode: {self.gpa_mode!r}")
        if self.gpa_tenths is None and self.gpa_mode != "all":
            raise SiteSearchError("GPA mode safe/review requires a GPA value.")
        if self.gpa_tenths is not None and not 0 <= self.gpa_tenths <= 50:
            raise SiteSearchError("GPA tenths must be between 0 and 50.")
        if self.grade_requirement_status not in {None, "required"}:
            raise SiteSearchError("Site grade requirement filter only accepts required.")
        if self.overall_gpa_tenths is not None:
            if not 0 <= self.overall_gpa_tenths <= 50:
                raise SiteSearchError("Overall GPA tenths must be between 0 and 50.")
            if self.grade_requirement_status != "required":
                raise SiteSearchError("Overall GPA search requires grade requirement.")
        for name in (*MULTI_VALUE_FIELDS, "academic_field_group", "academic_field_mapping_status", "english_requirement_status", "prefecture_membership"):
            values = getattr(self, name)
            if not isinstance(values, tuple) or any(
                not isinstance(value, str) or value == "" for value in values
            ):
                raise SiteSearchError(f"{name} must be a tuple of non-empty strings.")
        if not isinstance(self.academic_field_v2_branches, tuple):
            raise SiteSearchError("academic_field_v2_branches must be a tuple.")
        broad_codes: list[str] = []
        for branch in self.academic_field_v2_branches:
            if not isinstance(branch, AcademicFieldV2Branch) or not branch.group_code:
                raise SiteSearchError("Invalid academic-field v0.2 branch.")
            if not isinstance(branch.subcategory_codes, tuple) or any(
                not isinstance(code, str) or not code
                for code in branch.subcategory_codes
            ):
                raise SiteSearchError(
                    "Academic-field v0.2 subcategory codes must be non-empty text."
                )
            if len(branch.subcategory_codes) != len(set(branch.subcategory_codes)):
                raise SiteSearchError(
                    "Academic-field v0.2 subcategory codes must be unique per branch."
                )
            broad_codes.append(branch.group_code)
        if len(broad_codes) != len(set(broad_codes)):
            raise SiteSearchError(
                "Academic-field v0.2 broad branches must be unique."
            )


@dataclass(frozen=True)
class SearchSummary:
    total_matched_rows: int
    gpa_safe_match_rows: int | None
    gpa_safe_no_match_rows: int | None
    gpa_safe_numeric_rule_rows: int
    gpa_conditional_review_rows: int
    gpa_not_numerically_evaluable_rows: int
    rows_by_source_dataset: Mapping[str, int]
    university_count: int


@dataclass(frozen=True)
class SearchResultPage:
    request: SearchRequest
    summary: SearchSummary
    rows: tuple[Mapping[str, Any], ...]
    offset: int
    limit: int | None
    result_meaning: str = (
        "safe match means overall GPA condition safely matched; "
        "it is not an application-eligibility determination"
    )


def logical_key(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return tuple(str(row[field]) for field in LOGICAL_KEY_FIELDS)  # type: ignore[return-value]


def _safe_match(row: Mapping[str, Any], value: int) -> bool:
    if row["gpa_parse_status"] != "parsed_safe":
        return False
    minimum = row["gpa_min_tenths"]
    maximum = row["gpa_max_tenths"]
    lower = minimum is None or value > minimum or (
        value == minimum and row["gpa_min_inclusive"] is True
    )
    upper = maximum is None or value < maximum or (
        value == maximum and row["gpa_max_inclusive"] is True
    )
    return lower and upper


def gpa_status(row: Mapping[str, Any], value: int | None) -> str:
    if value is None:
        if row["gpa_parse_status"] == "parsed_safe":
            return "safe numeric rule (GPA not supplied)"
        if row["gpa_parse_status"] == "conditional_review":
            return "conditional/review required"
        return "not numerically evaluable"
    if _safe_match(row, value):
        return "safe match"
    if row["gpa_parse_status"] == "parsed_safe":
        return "safe no match"
    if row["gpa_parse_status"] == "conditional_review":
        return "conditional/review required"
    return "not numerically evaluable"


def _matches(row: Mapping[str, Any], request: SearchRequest) -> bool:
    for name in MULTI_VALUE_FIELDS:
        values = getattr(request, name)
        if values and row[name] not in values:
            return False
    if request.academic_field_group and not set(request.academic_field_group).intersection(
        row["academic_field_groups"]
    ):
        return False
    if request.academic_field_v2_branches:
        broad_memberships = set(row["academic_field_v2_broad_memberships"])
        subcategory_memberships = set(
            row["academic_field_v2_subcategory_memberships"]
        )
        if not any(
            branch.group_code in broad_memberships
            and (
                not branch.subcategory_codes
                or bool(
                    set(branch.subcategory_codes).intersection(
                        subcategory_memberships
                    )
                )
            )
            for branch in request.academic_field_v2_branches
        ):
            return False
    if request.prefecture_membership and not set(request.prefecture_membership).intersection(row["prefecture_memberships"]):
        return False
    if (
        request.academic_field_mapping_status
        and row["academic_field_mapping_status"]
        not in request.academic_field_mapping_status
    ):
        return False
    if request.stem_flag is not None and row["stem_flag"] is not request.stem_flag:
        return False
    if request.english_requirement_status:
        if set(request.english_requirement_status).difference({"required", "not_required"}):
            return False
        if row["english_requirement_status"] not in request.english_requirement_status or row["english_requirement_search_disposition"] != "safe_exact":
            return False
    if request.gpa_tenths is not None:
        safe = _safe_match(row, request.gpa_tenths)
        if request.gpa_mode == "safe" and not safe:
            return False
        if request.gpa_mode == "review" and not (
            safe or row["gpa_parse_status"] == "conditional_review"
        ):
            return False
    if (
        request.grade_requirement_status is not None
        and row["grade_requirement_status"] != request.grade_requirement_status
    ):
        return False
    if request.overall_gpa_tenths is not None:
        minimum = row["overall_gpa_min_tenths"]
        if minimum is None:
            return False
        if request.overall_gpa_tenths < minimum:
            return False
        if (
            request.overall_gpa_tenths == minimum
            and row["overall_gpa_min_inclusive"] is not True
        ):
            return False
    return True


def search_rows(
    rows: Iterable[Mapping[str, Any]],
    request: SearchRequest,
    *,
    limit: int | None = 20,
    offset: int = 0,
) -> SearchResultPage:
    """Apply the frozen CLI semantics without SQL or raw-value interpretation."""

    request.validate()
    if limit is not None and limit < 0:
        raise SiteSearchError("limit must be zero or greater")
    if offset < 0:
        raise SiteSearchError("offset must be zero or greater")
    matched = [dict(row) for row in rows if _matches(row, request)]
    matched.sort(
        key=lambda row: tuple(
            "" if row[field] is None else str(row[field])
            for field in (
                "prefecture",
                "university",
                "faculty_school",
                "department",
                "selection_category",
                "selection_name",
                *LOGICAL_KEY_FIELDS,
            )
        )
    )
    for row in matched:
        row["gpa_derived_status"] = gpa_status(row, request.gpa_tenths)
    statuses = [row["gpa_derived_status"] for row in matched]
    source_counts: dict[str, int] = {}
    for row in matched:
        source = row["source_dataset"]
        source_counts[source] = source_counts.get(source, 0) + 1
    summary = SearchSummary(
        total_matched_rows=len(matched),
        gpa_safe_match_rows=(
            statuses.count("safe match") if request.gpa_tenths is not None else None
        ),
        gpa_safe_no_match_rows=(
            statuses.count("safe no match") if request.gpa_tenths is not None else None
        ),
        gpa_safe_numeric_rule_rows=sum(
            row["gpa_parse_status"] == "parsed_safe" for row in matched
        ),
        gpa_conditional_review_rows=sum(
            row["gpa_parse_status"] == "conditional_review" for row in matched
        ),
        gpa_not_numerically_evaluable_rows=sum(
            row["gpa_parse_status"] not in {"parsed_safe", "conditional_review"}
            for row in matched
        ),
        rows_by_source_dataset=dict(sorted(source_counts.items())),
        university_count=len({row["university"] for row in matched}),
    )
    page = matched[offset:] if limit is None else matched[offset : offset + limit]
    return SearchResultPage(request, summary, tuple(page), offset, limit)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_search_rows(output_dir: Path) -> tuple[Mapping[str, Any], ...]:
    """Load and integrity-check all search shards named by the manifest."""

    manifest_path = output_dir / "build_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SiteSearchError(f"Cannot read Site-data manifest: {error}") from error
    if manifest.get("site_data_schema_version") != SITE_DATA_SCHEMA_VERSION:
        raise SiteSearchError("Site-data schema version mismatch.")
    build_id = manifest.get("build_id")
    artifacts = manifest.get("outputs", {}).get("artifacts", [])
    for item in artifacts:
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise SiteSearchError(f"Unsafe Site-data artifact path: {item['path']}")
        path = output_dir / relative
        if (
            not path.is_file()
            or path.stat().st_size != item["size_bytes"]
            or _sha256(path) != item["sha256"]
        ):
            raise SiteSearchError(
                f"Site-data artifact is missing or corrupt: {item['path']}"
            )
    search_artifacts = [item for item in artifacts if item.get("kind") == "search_shard"]
    if not search_artifacts:
        raise SiteSearchError("Manifest contains no search shards.")
    rows: list[Mapping[str, Any]] = []
    for item in sorted(search_artifacts, key=lambda value: value["path"]):
        path = output_dir / item["path"]
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise SiteSearchError(f"Invalid search shard JSON: {item['path']}") from error
        if payload.get("build_id") != build_id:
            raise SiteSearchError(f"Search shard build ID mismatch: {item['path']}")
        rows.extend(payload.get("rows", []))
    expected = manifest["counts"]["search_rows"]
    keys = [logical_key(row) for row in rows]
    if len(rows) != expected or len(keys) != len(set(keys)):
        raise SiteSearchError("Search shard completeness/uniqueness check failed.")
    return tuple(rows)
