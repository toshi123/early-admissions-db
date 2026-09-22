"""Frozen exact-value academic-field taxonomy and crosswalk contract v0.1."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


ACADEMIC_FIELD_MAPPING_CONTRACT_VERSION = "0.2"
ACADEMIC_FIELD_TAXONOMY_VERSION = "0.1"
ACADEMIC_FIELD_TAXONOMY_PATH = Path(
    "schema/academic_field/academic_field_taxonomy_v0_1.csv"
)
ACADEMIC_FIELD_CROSSWALK_PATH = Path(
    "schema/academic_field/academic_field_crosswalk_v0_2.csv"
)
ACADEMIC_FIELD_PREVIOUS_CROSSWALK_PATH = Path(
    "schema/academic_field/academic_field_crosswalk_v0_1.csv"
)
ACADEMIC_FIELD_SCHEMA_PATH = Path(
    "schema/sqlite/admission_search_academic_field_schema_v0_1.sql"
)
ACADEMIC_FIELD_DESIGN_PATH = Path("docs/academic_field_search_design_v0_1.md")
ACADEMIC_FIELD_FREEZE_PATH = Path("docs/academic_field_mapping_freeze_v0_1.md")
ACADEMIC_FIELD_TAXONOMY_SHA256 = (
    "f1f52d0282618eb5b22d3c420010718eb30f4ec14ad889dd574f218a5743a9f2"
)
ACADEMIC_FIELD_CROSSWALK_SHA256 = (
    "74162005e676a89c515a95d24bb78548df7ce6709fb04eb28c3ff14b57c99ab8"
)

FROZEN_MAPPING_STATUSES = frozenset({"single", "multi", "review_required"})
GENERATED_MAPPING_STATUSES = frozenset(
    {"single", "multi", "review_required", "unmapped", "not_applicable"}
)

TAXONOMY_HEADER = (
    "taxonomy_version",
    "group_code",
    "display_label",
    "description",
    "display_order",
)
CROSSWALK_HEADER = (
    "mapping_contract_version",
    "raw_value",
    "mapping_status",
    "group_code",
    "group_order",
    "review_note",
)


class AcademicFieldContractError(ValueError):
    """Raised when a taxonomy or exact-value crosswalk violates v0.1."""


@dataclass(frozen=True)
class AcademicFieldTaxonomyGroup:
    group_code: str
    display_label: str
    description: str
    display_order: int


@dataclass(frozen=True)
class AcademicFieldMapping:
    raw_value: str | None
    mapping_status: str
    group_codes: tuple[str, ...]
    review_note: str | None
    mapping_contract_version: str = ACADEMIC_FIELD_MAPPING_CONTRACT_VERSION


def _validated_csv_reader(path: Path, expected_header: tuple[str, ...]) -> csv.DictReader:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise AcademicFieldContractError(f"CSV contains a BOM: {path}")
    if b"\r" in raw:
        raise AcademicFieldContractError(f"CSV is not LF-only: {path}")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AcademicFieldContractError(f"CSV is not UTF-8: {path}") from error
    handle = path.open("r", encoding="utf-8", newline="")
    reader = csv.DictReader(handle)
    if tuple(reader.fieldnames or ()) != expected_header:
        handle.close()
        raise AcademicFieldContractError(
            f"CSV header mismatch for {path}: {reader.fieldnames!r}"
        )
    # Retain the file handle for DictReader iteration; the caller closes it by
    # exhausting the reader immediately inside the loader.
    reader._academic_field_handle = handle  # type: ignore[attr-defined]
    return reader


class AcademicFieldTaxonomy:
    def __init__(self, groups: tuple[AcademicFieldTaxonomyGroup, ...]) -> None:
        self.groups = groups
        self.by_code = {group.group_code: group for group in groups}

    @classmethod
    def load(cls, path: Path) -> "AcademicFieldTaxonomy":
        reader = _validated_csv_reader(path, TAXONOMY_HEADER)
        handle = reader._academic_field_handle  # type: ignore[attr-defined]
        try:
            rows = list(reader)
        finally:
            handle.close()
        groups: list[AcademicFieldTaxonomyGroup] = []
        seen: set[str] = set()
        for line_number, row in enumerate(rows, start=2):
            if row["taxonomy_version"] != ACADEMIC_FIELD_TAXONOMY_VERSION:
                raise AcademicFieldContractError(
                    f"Unexpected taxonomy version at {path}:{line_number}"
                )
            code = row["group_code"]
            if not code or code in seen:
                raise AcademicFieldContractError(
                    f"Empty or duplicate taxonomy code at {path}:{line_number}"
                )
            try:
                order = int(row["display_order"])
            except ValueError as error:
                raise AcademicFieldContractError(
                    f"Invalid taxonomy display_order at {path}:{line_number}"
                ) from error
            if not row["display_label"] or not row["description"]:
                raise AcademicFieldContractError(
                    f"Empty taxonomy label/description at {path}:{line_number}"
                )
            seen.add(code)
            groups.append(
                AcademicFieldTaxonomyGroup(
                    group_code=code,
                    display_label=row["display_label"],
                    description=row["description"],
                    display_order=order,
                )
            )
        if [group.display_order for group in groups] != list(
            range(1, len(groups) + 1)
        ):
            raise AcademicFieldContractError(
                "Taxonomy display_order must be contiguous and match file order."
            )
        if not groups:
            raise AcademicFieldContractError("Academic-field taxonomy is empty.")
        return cls(tuple(groups))

    def __len__(self) -> int:
        return len(self.groups)

    def __iter__(self) -> Iterator[AcademicFieldTaxonomyGroup]:
        return iter(self.groups)


class AcademicFieldCrosswalk:
    def __init__(
        self,
        mappings: tuple[AcademicFieldMapping, ...],
        taxonomy: AcademicFieldTaxonomy,
    ) -> None:
        self.mappings = mappings
        self.taxonomy = taxonomy
        self.by_raw_value = {
            mapping.raw_value: mapping
            for mapping in mappings
            if mapping.raw_value is not None
        }

    @classmethod
    def load(
        cls,
        path: Path,
        taxonomy: AcademicFieldTaxonomy,
        *,
        expected_version: str = ACADEMIC_FIELD_MAPPING_CONTRACT_VERSION,
    ) -> "AcademicFieldCrosswalk":
        reader = _validated_csv_reader(path, CROSSWALK_HEADER)
        handle = reader._academic_field_handle  # type: ignore[attr-defined]
        try:
            rows = list(reader)
        finally:
            handle.close()
        grouped: dict[str, list[tuple[int, dict[str, str]]]] = {}
        raw_order: list[str] = []
        for line_number, row in enumerate(rows, start=2):
            if row["mapping_contract_version"] != expected_version:
                raise AcademicFieldContractError(
                    f"Unexpected mapping contract version at {path}:{line_number}"
                )
            raw_value = row["raw_value"]
            if raw_value == "":
                raise AcademicFieldContractError(
                    f"Crosswalk raw_value is empty at {path}:{line_number}"
                )
            if raw_value not in grouped:
                grouped[raw_value] = []
                raw_order.append(raw_value)
            elif raw_order[-1] != raw_value:
                raise AcademicFieldContractError(
                    f"Crosswalk rows are not contiguous for {raw_value!r}"
                )
            grouped[raw_value].append((line_number, row))
        if raw_order != sorted(raw_order):
            raise AcademicFieldContractError(
                "Crosswalk raw values must be in deterministic sorted order."
            )

        mappings: list[AcademicFieldMapping] = []
        taxonomy_order = {
            group.group_code: group.display_order for group in taxonomy
        }
        for raw_value in raw_order:
            entries = grouped[raw_value]
            statuses = {row["mapping_status"] for _, row in entries}
            notes = {row["review_note"] for _, row in entries}
            if len(statuses) != 1 or not statuses.issubset(FROZEN_MAPPING_STATUSES):
                raise AcademicFieldContractError(
                    f"Invalid/inconsistent status for raw value {raw_value!r}"
                )
            if len(notes) != 1:
                raise AcademicFieldContractError(
                    f"Inconsistent review note for raw value {raw_value!r}"
                )
            status = next(iter(statuses))
            note = next(iter(notes)) or None
            group_codes: list[str] = []
            group_orders: list[int] = []
            for line_number, row in entries:
                code = row["group_code"]
                order_text = row["group_order"]
                if status == "review_required":
                    if code or order_text or not note:
                        raise AcademicFieldContractError(
                            f"review_required must have zero groups and a note at "
                            f"{path}:{line_number}"
                        )
                    continue
                if code not in taxonomy.by_code:
                    raise AcademicFieldContractError(
                        f"Unknown group code {code!r} at {path}:{line_number}"
                    )
                try:
                    order = int(order_text)
                except ValueError as error:
                    raise AcademicFieldContractError(
                        f"Invalid group_order at {path}:{line_number}"
                    ) from error
                if code in group_codes:
                    raise AcademicFieldContractError(
                        f"Duplicate group {code!r} for raw value {raw_value!r}"
                    )
                group_codes.append(code)
                group_orders.append(order)
            expected_count = 1 if status == "single" else 2
            if status == "single" and len(group_codes) != expected_count:
                raise AcademicFieldContractError(
                    f"single mapping must have one group for {raw_value!r}"
                )
            if status == "multi" and len(group_codes) < expected_count:
                raise AcademicFieldContractError(
                    f"multi mapping must have at least two groups for {raw_value!r}"
                )
            if status != "review_required":
                if group_orders != list(range(1, len(group_codes) + 1)):
                    raise AcademicFieldContractError(
                        f"Non-contiguous group_order for {raw_value!r}"
                    )
                display_orders = [taxonomy_order[code] for code in group_codes]
                if display_orders != sorted(display_orders):
                    raise AcademicFieldContractError(
                        f"Groups are not in taxonomy order for {raw_value!r}"
                    )
            mappings.append(
                AcademicFieldMapping(
                    raw_value=raw_value,
                    mapping_status=status,
                    group_codes=tuple(group_codes),
                    review_note=note,
                )
            )
        if not mappings:
            raise AcademicFieldContractError("Academic-field crosswalk is empty.")
        return cls(tuple(mappings), taxonomy)

    def lookup(self, raw_value: str | None) -> AcademicFieldMapping:
        """Return only an exact mapping; unknown text always fails closed."""

        if raw_value is None:
            return AcademicFieldMapping(
                raw_value=None,
                mapping_status="not_applicable",
                group_codes=(),
                review_note="academic_field is SQL NULL; no classification applied.",
            )
        mapping = self.by_raw_value.get(raw_value)
        if mapping is not None:
            return mapping
        return AcademicFieldMapping(
            raw_value=raw_value,
            mapping_status="unmapped",
            group_codes=(),
            review_note=(
                "Exact raw value is absent from the active frozen academic-field crosswalk."
            ),
        )

    def __len__(self) -> int:
        return len(self.mappings)

    def __iter__(self) -> Iterator[AcademicFieldMapping]:
        return iter(self.mappings)
