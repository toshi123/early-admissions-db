"""Exact-only runtime contract for academic-field taxonomy v0.2.

The frozen CSV artifacts are the sole classification authority.  This module
does not trim, normalize, tokenize, or infer from faculty/department text.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Mapping

from .academic_field_v0_2 import (
    BROAD_HEADER,
    COMPAT_HEADER,
    CONTEXT_HEADER,
    RAW_HEADER,
    SUBCATEGORY_HEADER,
    _group_contiguous,
    _read_frozen_csv,
    _validate_mapping_block,
)


MAPPING_VERSION = "0.4"
TAXONOMY_VERSION = "0.2"


ACADEMIC_FIELD_V2_SCHEMA_PATH = Path(
    "schema/sqlite/admission_search_academic_field_v0_3_schema.sql"
)
ACADEMIC_FIELD_V2_DESIGN_PATH = Path(
    "docs/academic_field_crosswalk_v0_3.md"
)
ACADEMIC_FIELD_V2_FREEZE_PATH = Path(
    "docs/academic_field_taxonomy_v0_2_freeze.md"
)
ACADEMIC_FIELD_V2_AUDIT_PATH = Path(
    "validation/reports/academic_field_taxonomy_v0_2_audit.md"
)
ACADEMIC_FIELD_V2_BROAD_PATH = Path(
    "schema/academic_field/v0_2/academic_field_broad_taxonomy_v0_2.csv"
)
ACADEMIC_FIELD_V2_SUBCATEGORY_PATH = Path(
    "schema/academic_field/v0_2/academic_field_subcategory_taxonomy_v0_2.csv"
)
ACADEMIC_FIELD_V2_RAW_PATH = Path(
    "schema/academic_field/v0_4/academic_field_raw_crosswalk_v0_4.csv"
)
ACADEMIC_FIELD_V2_CONTEXT_PATH = Path(
    "schema/academic_field/v0_4/academic_field_context_crosswalk_v0_4.csv"
)
ACADEMIC_FIELD_V2_COMPATIBILITY_PATH = Path(
    "schema/academic_field/v0_2/academic_field_v0_1_to_v0_2_crosswalk.csv"
)

ACADEMIC_FIELD_V2_FROZEN_SHA256: Mapping[Path, str] = {
    ACADEMIC_FIELD_V2_BROAD_PATH: (
        "ba33e98fa58196a3b530b26ce47d036073bdbf929a6fd16636e2ff58afe72ebd"
    ),
    ACADEMIC_FIELD_V2_SUBCATEGORY_PATH: (
        "9813972ec7698cd923fbbfb9bbee16bff7af12b371f23f5e733f6d391b92576e"
    ),
    ACADEMIC_FIELD_V2_RAW_PATH: (
        "f79e8a4b14cff99eb92a06f47f27aa4d06e4bbe51960fbb73a17225cf550d68c"
    ),
    ACADEMIC_FIELD_V2_CONTEXT_PATH: (
        "764673a1cc3aff882879bd74a87cfe550115065bffb41627412abc93b9178c05"
    ),
    ACADEMIC_FIELD_V2_COMPATIBILITY_PATH: (
        "55d3cbeebb0af7d6bcab6bb5b975616413ff8f5591cf3cab03089559913f92d7"
    ),
}

BROAD_RUNTIME_STATUSES = frozenset(
    {"single", "multi", "review_required", "unmapped", "not_applicable"}
)
SUBCATEGORY_RUNTIME_STATUSES = frozenset(
    {
        "single",
        "multi",
        "none",
        "review_required",
        "unmapped",
        "not_applicable",
    }
)
MAPPING_BASES = frozenset({"raw_exact", "context_exact", "raw_and_context"})
CONTEXT_EFFECTS = frozenset({"none", "additive", "authoritative"})


class AcademicFieldV2ContractError(ValueError):
    """Raised when frozen v0.2 artifacts or an exact lookup are invalid."""


@dataclass(frozen=True)
class BroadGroupV2:
    group_code: str
    display_label_ja: str
    ui_section: str
    display_order: int
    description: str
    status: str


@dataclass(frozen=True)
class SubcategoryV2:
    subcategory_code: str
    display_label_ja: str
    parent_group_code: str
    display_order: int
    description: str
    ui_status: str


@dataclass(frozen=True)
class ExactMappingV2:
    mapping_status: str
    broad_mapping_status: str
    subcategory_mapping_status: str
    memberships: tuple[tuple[str, str | None], ...]
    review_note: str
    merge_mode: str | None = None


@dataclass(frozen=True)
class AcademicFieldV2Classification:
    raw_value: str | None
    broad_mapping_status: str
    subcategory_mapping_status: str
    context_mapping_consulted: int
    context_mapping_effect: str
    review_note: str | None
    broad_memberships: tuple[tuple[str, str], ...]
    subcategory_memberships: tuple[tuple[str, str, str], ...]
    mapping_contract_version: str = MAPPING_VERSION
    taxonomy_version: str = TAXONOMY_VERSION


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class AcademicFieldV2Contract:
    """Loaded frozen taxonomy and exact raw/context mappings."""

    def __init__(
        self,
        *,
        broad_groups: tuple[BroadGroupV2, ...],
        subcategories: tuple[SubcategoryV2, ...],
        raw_mappings: Mapping[str, ExactMappingV2],
        context_mappings: Mapping[tuple[str, str, str, str, str], ExactMappingV2],
        raw_crosswalk_rows: int,
        context_crosswalk_rows: int,
        compatibility_crosswalk_rows: int,
    ) -> None:
        self.broad_groups = broad_groups
        self.subcategories = subcategories
        self.raw_mappings = dict(raw_mappings)
        self.context_mappings = dict(context_mappings)
        self.raw_crosswalk_rows = raw_crosswalk_rows
        self.context_crosswalk_rows = context_crosswalk_rows
        self.compatibility_crosswalk_rows = compatibility_crosswalk_rows
        self.broad_by_code = {item.group_code: item for item in broad_groups}
        self.subcategory_by_code = {
            item.subcategory_code: item for item in subcategories
        }
        self._broad_rank = {
            item.group_code: index for index, item in enumerate(broad_groups)
        }
        self._subcategory_rank = {
            item.subcategory_code: index
            for index, item in enumerate(subcategories)
        }

    @classmethod
    def load(cls, repo_root: Path) -> "AcademicFieldV2Contract":
        for relative, expected in ACADEMIC_FIELD_V2_FROZEN_SHA256.items():
            actual = _sha256(repo_root / relative)
            if actual != expected:
                raise AcademicFieldV2ContractError(
                    f"Frozen academic-field v0.2 SHA-256 mismatch for {relative}: "
                    f"expected={expected}, actual={actual}"
                )

        broad_rows = _read_frozen_csv(
            repo_root / ACADEMIC_FIELD_V2_BROAD_PATH, BROAD_HEADER
        )
        subcategory_rows = _read_frozen_csv(
            repo_root / ACADEMIC_FIELD_V2_SUBCATEGORY_PATH, SUBCATEGORY_HEADER
        )
        raw_rows = _read_frozen_csv(
            repo_root / ACADEMIC_FIELD_V2_RAW_PATH, RAW_HEADER
        )
        context_rows = _read_frozen_csv(
            repo_root / ACADEMIC_FIELD_V2_CONTEXT_PATH, CONTEXT_HEADER
        )
        compatibility_rows = _read_frozen_csv(
            repo_root / ACADEMIC_FIELD_V2_COMPATIBILITY_PATH, COMPAT_HEADER
        )

        broad_groups: list[BroadGroupV2] = []
        broad_codes: set[str] = set()
        section_orders: dict[str, list[int]] = {}
        for row in broad_rows:
            code = row["group_code"]
            if row["taxonomy_version"] != TAXONOMY_VERSION:
                raise AcademicFieldV2ContractError("Unexpected broad taxonomy version.")
            if not code or code in broad_codes or row["status"] != "active":
                raise AcademicFieldV2ContractError(
                    f"Invalid broad taxonomy row for {code!r}."
                )
            order = int(row["display_order"])
            section_orders.setdefault(row["ui_section"], []).append(order)
            broad_codes.add(code)
            broad_groups.append(
                BroadGroupV2(
                    group_code=code,
                    display_label_ja=row["display_label_ja"],
                    ui_section=row["ui_section"],
                    display_order=order,
                    description=row["description"],
                    status=row["status"],
                )
            )
        if len(broad_groups) != 30:
            raise AcademicFieldV2ContractError("Broad taxonomy must contain 30 rows.")
        if any(orders != list(range(1, len(orders) + 1)) for orders in section_orders.values()):
            raise AcademicFieldV2ContractError("Broad display order is not contiguous.")

        subcategories: list[SubcategoryV2] = []
        subcategory_parents: dict[str, str] = {}
        parent_orders: dict[str, list[int]] = {}
        for row in subcategory_rows:
            code = row["subcategory_code"]
            parent = row["parent_group_code"]
            if row["taxonomy_version"] != TAXONOMY_VERSION:
                raise AcademicFieldV2ContractError(
                    "Unexpected subcategory taxonomy version."
                )
            if not code or code in subcategory_parents or parent not in broad_codes:
                raise AcademicFieldV2ContractError(
                    f"Invalid subcategory taxonomy row for {code!r}."
                )
            if row["ui_status"] not in {"primary", "secondary", "hidden"}:
                raise AcademicFieldV2ContractError(
                    f"Invalid subcategory UI status for {code!r}."
                )
            order = int(row["display_order"])
            parent_orders.setdefault(parent, []).append(order)
            subcategory_parents[code] = parent
            subcategories.append(
                SubcategoryV2(
                    subcategory_code=code,
                    display_label_ja=row["display_label_ja"],
                    parent_group_code=parent,
                    display_order=order,
                    description=row["description"],
                    ui_status=row["ui_status"],
                )
            )
        if len(subcategories) != 89:
            raise AcademicFieldV2ContractError(
                "Subcategory taxonomy must contain 89 rows."
            )
        if any(orders != list(range(1, len(orders) + 1)) for orders in parent_orders.values()):
            raise AcademicFieldV2ContractError(
                "Subcategory display order is not contiguous."
            )

        raw_mappings: dict[str, ExactMappingV2] = {}
        raw_blocks = _group_contiguous(raw_rows, ("raw_value",), "raw crosswalk")
        raw_keys = [key[0] for key, _ in raw_blocks]
        if raw_keys != sorted(raw_keys):
            raise AcademicFieldV2ContractError("Raw crosswalk keys are not sorted.")
        for (raw_value,), block in raw_blocks:
            memberships = _validate_mapping_block(
                block, f"raw {raw_value!r}", broad_codes, subcategory_parents
            )
            raw_mappings[raw_value] = ExactMappingV2(
                mapping_status=block[0]["mapping_status"],
                broad_mapping_status=block[0]["broad_mapping_status"],
                subcategory_mapping_status=block[0]["subcategory_mapping_status"],
                memberships=memberships,
                review_note=block[0]["review_note"],
            )

        context_mappings: dict[
            tuple[str, str, str, str, str], ExactMappingV2
        ] = {}
        context_blocks = _group_contiguous(
            context_rows,
            (
                "source_dataset",
                "university",
                "faculty_school",
                "department",
                "academic_field",
            ),
            "context crosswalk",
        )
        context_keys = [key for key, _ in context_blocks]
        if context_keys != sorted(context_keys):
            raise AcademicFieldV2ContractError(
                "Context crosswalk keys are not sorted."
            )
        for key, block in context_blocks:
            modes = {row["merge_mode"] for row in block}
            if len(modes) != 1 or not modes.issubset(
                {"additive", "authoritative"}
            ):
                raise AcademicFieldV2ContractError(
                    f"Invalid context merge mode for {key!r}."
                )
            memberships = _validate_mapping_block(
                block, f"context {key!r}", broad_codes, subcategory_parents
            )
            mode = next(iter(modes))
            raw_mapping = raw_mappings.get(key[-1])
            if raw_mapping is None:
                raise AcademicFieldV2ContractError(
                    f"Context references unknown raw value: {key!r}."
                )
            if mode == "additive" and set(memberships) & set(
                raw_mapping.memberships
            ):
                raise AcademicFieldV2ContractError(
                    f"Additive context repeats a raw membership: {key!r}."
                )
            # v0.3 allows explicitly human-reviewed authoritative contexts to
            # replace either ambiguous or otherwise mapped raw memberships.
            # This applies only to exact tuples present in the frozen context
            # crosswalk; no rule is generalized to unreviewed contexts.
            context_mappings[key] = ExactMappingV2(
                mapping_status=block[0]["mapping_status"],
                broad_mapping_status=block[0]["broad_mapping_status"],
                subcategory_mapping_status=block[0]["subcategory_mapping_status"],
                memberships=memberships,
                review_note=block[0]["review_note"],
                merge_mode=mode,
            )

        old_taxonomy_path = (
            repo_root / "schema/academic_field/academic_field_taxonomy_v0_1.csv"
        )
        with old_taxonomy_path.open("r", encoding="utf-8", newline="") as handle:
            old_codes = {row["group_code"] for row in csv.DictReader(handle)}
        compatible_old_codes: set[str] = set()
        for row in compatibility_rows:
            if (
                row["from_taxonomy_version"] != "0.1"
                or row["to_taxonomy_version"] != TAXONOMY_VERSION
                or row["to_group_code"] not in broad_codes
            ):
                raise AcademicFieldV2ContractError(
                    f"Invalid compatibility row: {row!r}."
                )
            compatible_old_codes.add(row["from_group_code"])
        if compatible_old_codes != old_codes:
            raise AcademicFieldV2ContractError(
                "Compatibility crosswalk does not cover every v0.1 group."
            )

        return cls(
            broad_groups=tuple(broad_groups),
            subcategories=tuple(subcategories),
            raw_mappings=raw_mappings,
            context_mappings=context_mappings,
            raw_crosswalk_rows=len(raw_rows),
            context_crosswalk_rows=len(context_rows),
            compatibility_crosswalk_rows=len(compatibility_rows),
        )

    def classify(
        self,
        *,
        source_dataset: str,
        university: str,
        faculty_school: str | None,
        department: str | None,
        academic_field: str | None,
    ) -> AcademicFieldV2Classification:
        if academic_field is None:
            return AcademicFieldV2Classification(
                raw_value=None,
                broad_mapping_status="not_applicable",
                subcategory_mapping_status="not_applicable",
                context_mapping_consulted=0,
                context_mapping_effect="none",
                review_note=None,
                broad_memberships=(),
                subcategory_memberships=(),
            )

        raw_mapping = self.raw_mappings.get(academic_field)
        if raw_mapping is None:
            return AcademicFieldV2Classification(
                raw_value=academic_field,
                broad_mapping_status="unmapped",
                subcategory_mapping_status="unmapped",
                context_mapping_consulted=0,
                context_mapping_effect="none",
                review_note="No frozen exact raw-value mapping.",
                broad_memberships=(),
                subcategory_memberships=(),
            )

        context_key = (
            source_dataset,
            university,
            "" if faculty_school is None else faculty_school,
            "" if department is None else department,
            academic_field,
        )
        context_mapping = self.context_mappings.get(context_key)
        consulted = int(context_mapping is not None)
        effect = "none"
        raw_memberships = set(raw_mapping.memberships)
        context_memberships: set[tuple[str, str | None]] = set()
        if context_mapping is None:
            memberships = raw_memberships
            review_note = raw_mapping.review_note
        else:
            context_memberships = set(context_mapping.memberships)
            if context_memberships:
                effect = context_mapping.merge_mode or "none"
            if context_mapping.merge_mode == "authoritative":
                memberships = context_memberships
            else:
                memberships = raw_memberships | context_memberships
            review_note = context_mapping.review_note

        groups = {group for group, _ in memberships}
        subcategories = {
            subcategory
            for _, subcategory in memberships
            if subcategory is not None
        }
        if not groups:
            review_required = (
                raw_mapping.mapping_status == "review_required"
                or (
                    context_mapping is not None
                    and context_mapping.mapping_status == "review_required"
                )
            )
            status = "review_required" if review_required else "unmapped"
            return AcademicFieldV2Classification(
                raw_value=academic_field,
                broad_mapping_status=status,
                subcategory_mapping_status=status,
                context_mapping_consulted=consulted,
                context_mapping_effect="none",
                review_note=review_note,
                broad_memberships=(),
                subcategory_memberships=(),
            )

        def basis(raw_present: bool, context_present: bool) -> str:
            if raw_present and context_present:
                return "raw_and_context"
            return "raw_exact" if raw_present else "context_exact"

        raw_groups = {group for group, _ in raw_memberships}
        context_groups = {group for group, _ in context_memberships}
        broad_memberships = tuple(
            (
                group,
                basis(group in raw_groups, group in context_groups),
            )
            for group in sorted(groups, key=self._broad_rank.__getitem__)
        )
        raw_subcategories = {
            subcategory
            for _, subcategory in raw_memberships
            if subcategory is not None
        }
        context_subcategories = {
            subcategory
            for _, subcategory in context_memberships
            if subcategory is not None
        }
        subcategory_memberships = tuple(
            (
                subcategory,
                self.subcategory_by_code[subcategory].parent_group_code,
                basis(
                    subcategory in raw_subcategories,
                    subcategory in context_subcategories,
                ),
            )
            for subcategory in sorted(
                subcategories, key=self._subcategory_rank.__getitem__
            )
        )
        return AcademicFieldV2Classification(
            raw_value=academic_field,
            broad_mapping_status="single" if len(groups) == 1 else "multi",
            subcategory_mapping_status=(
                "none"
                if not subcategories
                else ("single" if len(subcategories) == 1 else "multi")
            ),
            context_mapping_consulted=consulted,
            context_mapping_effect=effect,
            review_note=review_note,
            broad_memberships=broad_memberships,
            subcategory_memberships=subcategory_memberships,
        )

    def __iter__(self) -> Iterator[BroadGroupV2]:
        return iter(self.broad_groups)
