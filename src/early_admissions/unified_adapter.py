"""Loss-aware adapters from canonical sources to unified contract v0.1."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .validator import (
    BOOL_MAP,
    BOOLEAN_FIELDS,
    SOURCE_CONFIG,
    TABLE_CONFIG,
    TRISTATE_FIELDS,
    map_detail_completeness,
    map_research_activity_level,
    parse_int,
)


SOURCE_ORDER = ("kokkoritsu", "shidai")
TABLE_ORDER = ("master", "coverage", "research_requirements")


class AdapterError(RuntimeError):
    """Raised when validated source data cannot be adapted losslessly."""


@dataclass(frozen=True)
class CanonicalTable:
    dataset: str
    source_version: str
    name: str
    path: Path
    header: tuple[str, ...]
    rows: tuple[Mapping[str, str], ...]
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class CanonicalBundle:
    repo_root: Path
    source_versions: Mapping[str, str]
    source_schemas: Mapping[str, Mapping[str, Any]]
    source_schema_metadata: Mapping[str, Mapping[str, Any]]
    tables: Mapping[str, Mapping[str, CanonicalTable]]

    def table(self, dataset: str, table: str) -> CanonicalTable:
        return self.tables[dataset][table]


class CanonicalSourceLoader:
    """Read canonical CSV files without modifying them."""

    def __init__(self, repo_root: Path | str):
        self.repo_root = Path(repo_root).resolve()

    def load(self) -> CanonicalBundle:
        source_versions: dict[str, str] = {}
        source_schemas: dict[str, Mapping[str, Any]] = {}
        source_schema_metadata: dict[str, Mapping[str, Any]] = {}
        tables: dict[str, dict[str, CanonicalTable]] = {}

        for dataset in SOURCE_ORDER:
            config = SOURCE_CONFIG[dataset]
            schema_path = self.repo_root / config["schema"]
            schema_raw = schema_path.read_bytes()
            source_schema = json.loads(schema_raw.decode("utf-8"))
            source_version = str(source_schema["version"])
            source_versions[dataset] = source_version
            source_schemas[dataset] = source_schema
            source_schema_metadata[dataset] = {
                "path": str(schema_path.relative_to(self.repo_root)),
                "sha256": hashlib.sha256(schema_raw).hexdigest(),
                "size_bytes": len(schema_raw),
                "version": source_version,
            }

            canonical_dir = self.repo_root / config["canonical_dir"]
            tables[dataset] = {}
            for table_name in TABLE_ORDER:
                filename, schema_key = TABLE_CONFIG[table_name]
                expected_header = tuple(source_schema[schema_key])
                path = canonical_dir / filename
                tables[dataset][table_name] = self._read_table(
                    dataset=dataset,
                    source_version=source_version,
                    table_name=table_name,
                    path=path,
                    expected_header=expected_header,
                )

        return CanonicalBundle(
            repo_root=self.repo_root,
            source_versions=source_versions,
            source_schemas=source_schemas,
            source_schema_metadata=source_schema_metadata,
            tables=tables,
        )

    @staticmethod
    def _read_table(
        *,
        dataset: str,
        source_version: str,
        table_name: str,
        path: Path,
        expected_header: tuple[str, ...],
    ) -> CanonicalTable:
        raw = path.read_bytes()
        rows: list[Mapping[str, str]] = []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            header = tuple(reader.fieldnames or ())
            if header != expected_header:
                raise AdapterError(
                    f"Source header changed after validation: {dataset}/{table_name}"
                )
            for row_number, row in enumerate(reader, start=2):
                if None in row:
                    raise AdapterError(
                        f"Unexpected extra CSV cells at {path}:{row_number}"
                    )
                if any(value is None for value in row.values()):
                    raise AdapterError(
                        f"Missing CSV cells at {path}:{row_number}"
                    )
                rows.append(dict(row))

        return CanonicalTable(
            dataset=dataset,
            source_version=source_version,
            name=table_name,
            path=path,
            header=header,
            rows=tuple(rows),
            sha256=hashlib.sha256(raw).hexdigest(),
            size_bytes=len(raw),
        )


class UnifiedAdapter:
    """Apply only the normalization rules approved by unified contract v0.1."""

    def __init__(self, contract: Mapping[str, Any]):
        self.contract = contract
        table_contracts = contract["x-table-contracts"]
        self.columns: dict[str, tuple[str, ...]] = {
            table: tuple(table_contracts[table]["csv_columns"])
            for table in TABLE_ORDER
        }

    def iter_records(
        self, bundle: CanonicalBundle, table: str
    ) -> Iterable[dict[str, Any]]:
        if table not in TABLE_ORDER:
            raise AdapterError(f"Unknown table: {table}")
        for dataset in SOURCE_ORDER:
            source_table = bundle.table(dataset, table)
            for source_row in source_table.rows:
                if table == "master":
                    yield self.adapt_master(
                        source_row, dataset, source_table.source_version
                    )
                elif table == "coverage":
                    yield self.adapt_coverage(
                        source_row, dataset, source_table.source_version
                    )
                else:
                    yield self.adapt_research_requirement(
                        source_row, dataset, source_table.source_version
                    )

    def adapt_master(
        self, row: Mapping[str, str], dataset: str, source_version: str
    ) -> dict[str, Any]:
        output: dict[str, Any] = {
            "source_dataset": dataset,
            "source_version": source_version,
        }
        for source_field, raw in row.items():
            if source_field in {"research_activity_level", "detail_completeness"}:
                continue
            if source_field in {"admission_year", "information_year"}:
                output[source_field] = self._integer(raw, source_field)
            elif source_field in BOOLEAN_FIELDS:
                output[source_field] = self._boolean(raw, source_field)
            elif source_field in TRISTATE_FIELDS:
                output[source_field] = self._tri_state(raw, source_field)
            elif source_field == "common_test_required":
                output[source_field] = self._common_test_required(raw)
            else:
                output[source_field] = null_if_blank(raw)

        research_raw = row.get("research_activity_level", "")
        output["research_activity_level_status"] = map_research_activity_level(
            dataset, research_raw
        )
        output["research_activity_level_raw"] = null_if_blank(research_raw)

        detail_raw = row.get("detail_completeness", "")
        output["detail_completeness_status"] = map_detail_completeness(
            dataset, detail_raw
        )
        output["detail_completeness_raw"] = null_if_blank(detail_raw)
        return self._ordered("master", output)

    def adapt_coverage(
        self, row: Mapping[str, str], dataset: str, source_version: str
    ) -> dict[str, Any]:
        output: dict[str, Any] = {
            "source_dataset": dataset,
            "source_version": source_version,
        }
        for source_field, raw in row.items():
            if source_field == "master_rows":
                value = parse_int(raw)
                if value is None:
                    raise AdapterError(f"Invalid integer in Coverage.master_rows: {raw!r}")
                output[source_field] = value
            else:
                output[source_field] = null_if_blank(raw)
        return self._ordered("coverage", output)

    def adapt_research_requirement(
        self, row: Mapping[str, str], dataset: str, source_version: str
    ) -> dict[str, Any]:
        output: dict[str, Any] = {
            "source_dataset": dataset,
            "source_version": source_version,
        }
        output.update(
            {source_field: null_if_blank(raw) for source_field, raw in row.items()}
        )
        return self._ordered("research_requirements", output)

    def _ordered(self, table: str, values: Mapping[str, Any]) -> dict[str, Any]:
        columns = self.columns[table]
        missing = [column for column in columns if column not in values]
        extra = [column for column in values if column not in columns]
        if missing or extra:
            raise AdapterError(
                f"Adapter columns do not match {table}: missing={missing}, extra={extra}"
            )
        return {column: values[column] for column in columns}

    @staticmethod
    def _integer(raw: str, field_name: str) -> int | None:
        if raw == "":
            return None
        value = parse_int(raw)
        if value is None:
            raise AdapterError(f"Invalid integer in {field_name}: {raw!r}")
        return value

    @staticmethod
    def _boolean(raw: str, field_name: str) -> bool | None:
        if raw == "":
            return None
        if raw not in BOOL_MAP:
            raise AdapterError(f"Invalid boolean in {field_name}: {raw!r}")
        return BOOL_MAP[raw]

    @staticmethod
    def _tri_state(raw: str, field_name: str) -> str | None:
        if raw == "":
            return None
        if raw not in {"Yes", "No", "Unknown"}:
            raise AdapterError(f"Invalid tri-state in {field_name}: {raw!r}")
        return raw

    @staticmethod
    def _common_test_required(raw: str) -> str | None:
        if raw == "":
            return None
        if raw == "条件付き":
            return "Conditional"
        if raw not in {"Yes", "No", "Unknown"}:
            raise AdapterError(f"Invalid common_test_required value: {raw!r}")
        return raw


def null_if_blank(raw: str) -> str | None:
    """Convert only the empty source cell to logical null; never trim."""

    return None if raw == "" else raw


def serialize_value(value: Any) -> str:
    """Serialize one typed unified value to deterministic CSV text."""

    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return value
    raise AdapterError(f"Unsupported unified value type: {type(value).__name__}")


def write_unified_table(
    path: Path,
    columns: Sequence[str],
    records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Write deterministic UTF-8/LF/no-BOM CSV and return bounded metadata."""

    path.parent.mkdir(parents=True, exist_ok=True)
    row_count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(columns),
            lineterminator="\n",
            extrasaction="raise",
        )
        writer.writeheader()
        for record in records:
            writer.writerow(
                {column: serialize_value(record[column]) for column in columns}
            )
            row_count += 1

    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise AdapterError(f"Unexpected UTF-8 BOM in generated file: {path}")
    if b"\r" in raw:
        raise AdapterError(f"Unexpected CR line ending in generated file: {path}")
    return {
        "rows": row_count,
        "columns": len(columns),
        "size_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
