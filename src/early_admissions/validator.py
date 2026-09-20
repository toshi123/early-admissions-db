"""Read-only validation for canonical early-admissions source datasets.

The validator reports contract findings but never mutates source data. It uses
only the Python standard library so it can run in a clean checkout.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field as dataclass_field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SEVERITIES = ("error", "warning", "informational")

CODE_SEVERITY = {
    "CONTRACT_DOCUMENT_MISSING": "error",
    "SOURCE_DATASET_UNSUPPORTED": "error",
    "SOURCE_VERSION_MISMATCH": "error",
    "UNIFIED_SOURCE_SCHEMA_MAPPING_MISMATCH": "error",
    "SOURCE_COLUMN_COUNT_MISMATCH": "error",
    "SOURCE_COLUMN_ORDER_MISMATCH": "error",
    "SOURCE_ROW_WIDTH_MISMATCH": "error",
    "MASTER_PK_BLANK": "error",
    "MASTER_PK_DUPLICATE": "error",
    "COVERAGE_KEY_BLANK": "error",
    "COVERAGE_KEY_DUPLICATE": "error",
    "COVERAGE_MASTER_ROWS_MISMATCH": "error",
    "RESEARCH_ADMISSION_ID_BLANK": "error",
    "RESEARCH_ORPHAN_FK": "error",
    "REQUIRED_VALUE_MISSING": "error",
    "INVALID_INTEGER_VALUE": "error",
    "SOURCE_INSTITUTION_TYPE_MISMATCH": "error",
    "INVALID_BOOLEAN_VALUE": "error",
    "INVALID_TRISTATE_VALUE": "error",
    "INVALID_COMMON_TEST_REQUIRED": "error",
    "INVALID_ENUM_VALUE": "error",
    "RESEARCH_EXACT_DUPLICATE": "warning",
    "RESEARCH_REQUIRED_WITHOUT_CHILD": "warning",
    "RESEARCH_DENORMALIZED_FIELD_MISMATCH": "warning",
    "DETAIL_COMPLETENESS_UNMAPPED": "warning",
    "RESEARCH_ACTIVITY_LEVEL_UNMAPPED": "warning",
    "PROVENANCE_URL_MISSING": "warning",
    "WHITESPACE_PADDING": "warning",
    "RESEARCH_NOT_REQUIRED_WITH_CHILD": "informational",
    "COVERAGE_ZERO_MASTER_ROWS": "informational",
    "DATE_RAW_PARTIAL": "informational",
    "DATE_RAW_UNPARSED": "informational",
    "COMMON_TEST_FIELDS_DIFFER": "informational",
}

TABLE_CONFIG = {
    "master": ("master.csv", "master_columns"),
    "coverage": ("coverage.csv", "coverage_columns"),
    "research_requirements": (
        "research_requirements.csv",
        "research_requirements_columns",
    ),
}

SOURCE_CONFIG = {
    "kokkoritsu": {
        "canonical_dir": Path("data/canonical/kokkoritsu"),
        "schema": Path(
            "schema/kokkoritsu/kokkoritsu_early_admissions_schema_v5_61.json"
        ),
    },
    "shidai": {
        "canonical_dir": Path("data/canonical/shidai"),
        "schema": Path(
            "schema/shidai/shidai_early_admissions_schema_v0_97.json"
        ),
    },
}

CONTRACT_PATH = Path("schema/unified/early_admissions_unified_schema_v0_1.json")
CONTRACT_DOCUMENTS = (
    Path("docs/unified_data_contract.md"),
    Path("docs/unified_field_mapping_v0_1.md"),
)

TRISTATE_FIELDS = (
    "school_recommendation_required",
    "research_requirement_required",
    "academic_record_required",
    "selection_document_review",
    "selection_interview",
    "selection_oral_exam",
    "selection_presentation",
    "selection_essay",
    "selection_written_exam",
    "selection_practical",
    "selection_group_discussion",
    "selection_aptitude_test",
    "selection_common_test",
)

BOOLEAN_FIELDS = ("stem_flag", "fallback_previous_year")

MASTER_DATE_FIELDS = (
    "application_start",
    "application_end",
    "web_registration_period",
    "first_stage_result_date",
    "second_stage_start",
    "second_stage_end",
    "final_result_date",
    "verified_on",
)

DISPLAY_FIELDS = (
    "university",
    "faculty_school",
    "department",
    "selection_name",
)

BOOL_MAP = {
    "True": True,
    "Yes": True,
    "False": False,
    "No": False,
}

KOKKORITSU_RESEARCH_LEVEL_MAP = {
    "explicit_requirement": "required",
    "探究活動必須": "required",
    "必須（指定実績のいずれか）": "required",
    "関連する課外活動実績が出願要件": "required",
    "relevant": "relevant",
    "related": "relevant",
    "explicitly_evaluated": "relevant",
    "探究活動重視": "relevant",
    "研究活動重視": "relevant",
    "none": "none",
    "なし": "none",
    "not_specified": "unknown",
}

ISO_DATE_RE = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)")


@dataclass(frozen=True)
class SourceRow:
    """One source CSV row with stable logical row numbering."""

    row_number: int
    values: Mapping[str, str]


@dataclass
class TableData:
    """Parsed source table and bounded input metadata."""

    dataset: str
    name: str
    path: Path
    header: list[str]
    rows: list[SourceRow]
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class Issue:
    """One validation finding."""

    code: str
    severity: str
    dataset: str
    table: str
    message: str
    record_id: str | None = None
    field: str | None = None
    row_number: int | None = None
    details: Mapping[str, Any] = dataclass_field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "code": self.code,
            "severity": self.severity,
            "dataset": self.dataset,
            "table": self.table,
            "message": self.message,
        }
        if self.record_id is not None:
            data["record_id"] = self.record_id
        if self.field is not None:
            data["field"] = self.field
        if self.row_number is not None:
            data["row_number"] = self.row_number
        if self.details:
            data["details"] = dict(self.details)
        return data


@dataclass
class ValidationResult:
    """Complete validation outcome and report formatting helpers."""

    contract_version: str
    repo_root: Path
    generated_at: str = dataclass_field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    issues: list[Issue] = dataclass_field(default_factory=list)
    inputs: list[dict[str, Any]] = dataclass_field(default_factory=list)
    metrics: dict[str, Any] = dataclass_field(default_factory=dict)

    def add_issue(
        self,
        *,
        code: str,
        severity: str,
        dataset: str,
        table: str,
        message: str,
        record_id: str | None = None,
        field_name: str | None = None,
        row_number: int | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        if severity not in SEVERITIES:
            raise ValueError(f"Unsupported severity: {severity}")
        expected_severity = CODE_SEVERITY.get(code)
        if expected_severity is None:
            raise ValueError(f"Unregistered validation code: {code}")
        if severity != expected_severity:
            raise ValueError(
                f"Severity mismatch for {code}: expected {expected_severity}, got {severity}"
            )
        self.issues.append(
            Issue(
                code=code,
                severity=severity,
                dataset=dataset,
                table=table,
                message=message,
                record_id=record_id,
                field=field_name,
                row_number=row_number,
                details=details or {},
            )
        )

    def summary(self, representative_limit: int = 5) -> dict[str, Any]:
        by_severity = Counter(issue.severity for issue in self.issues)
        severity_counts = {severity: by_severity[severity] for severity in SEVERITIES}

        dataset_counts: dict[str, dict[str, Any]] = {}
        datasets = {item["dataset"] for item in self.inputs}
        datasets.update(issue.dataset for issue in self.issues)
        for dataset in sorted(datasets):
            subset = [issue for issue in self.issues if issue.dataset == dataset]
            severity = Counter(issue.severity for issue in subset)
            codes = Counter(issue.code for issue in subset)
            dataset_counts[dataset] = {
                "total": len(subset),
                "by_severity": {name: severity[name] for name in SEVERITIES},
                "by_code": dict(sorted(codes.items())),
            }

        code_counts: dict[str, dict[str, Any]] = {}
        for code in sorted({issue.code for issue in self.issues}):
            subset = [issue for issue in self.issues if issue.code == code]
            representatives: list[str] = []
            seen: set[str] = set()
            for issue in subset:
                if issue.record_id and issue.record_id not in seen:
                    representatives.append(issue.record_id)
                    seen.add(issue.record_id)
                    if len(representatives) >= representative_limit:
                        break
            code_counts[code] = {
                "severity": subset[0].severity,
                "count": len(subset),
                "by_dataset": dict(
                    sorted(Counter(issue.dataset for issue in subset).items())
                ),
                "representative_record_ids": representatives,
            }

        status = "failed" if severity_counts["error"] else "passed_with_findings"
        if not self.issues:
            status = "passed"

        return {
            "status": status,
            "total_issues": len(self.issues),
            "by_severity": severity_counts,
            "by_dataset": dataset_counts,
            "by_code": code_counts,
        }

    def to_dict(self, representative_limit: int = 5) -> dict[str, Any]:
        return {
            "report_version": "1",
            "contract_version": self.contract_version,
            "generated_at": self.generated_at,
            "repo_root": ".",
            "read_only": True,
            "summary": self.summary(representative_limit),
            "metrics": self.metrics,
            "inputs": self.inputs,
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def to_markdown(self, representative_limit: int = 5) -> str:
        summary = self.summary(representative_limit)
        lines = [
            "# Unified contract v0.1 validation summary",
            "",
            f"- Generated: `{self.generated_at}`",
            f"- Status: `{summary['status']}`",
            "- Mode: read-only; canonical and release data were not modified",
            f"- Contract version: `{self.contract_version}`",
            "",
            "## Severity totals",
            "",
            "| Severity | Count |",
            "|---|---:|",
        ]
        for severity in SEVERITIES:
            lines.append(f"| {severity} | {summary['by_severity'][severity]} |")

        lines.extend(
            [
                "",
                "## Dataset totals",
                "",
                "| Dataset | Errors | Warnings | Informational | Total |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for dataset, counts in summary["by_dataset"].items():
            severity = counts["by_severity"]
            lines.append(
                f"| {dataset} | {severity['error']} | {severity['warning']} | "
                f"{severity['informational']} | {counts['total']} |"
            )

        lines.extend(
            [
                "",
                "## Findings by code",
                "",
                "| Code | Severity | Count | Dataset counts | Representative record IDs |",
                "|---|---|---:|---|---|",
            ]
        )
        for code, counts in summary["by_code"].items():
            datasets = ", ".join(
                f"{name}={count}" for name, count in counts["by_dataset"].items()
            )
            representatives = ", ".join(counts["representative_record_ids"])
            lines.append(
                f"| `{code}` | {counts['severity']} | {counts['count']} | "
                f"{datasets} | {representatives} |"
            )

        lines.extend(
            [
                "",
                "## Inputs",
                "",
                "| Dataset | Table | Rows | Bytes | SHA-256 | Path |",
                "|---|---|---:|---:|---|---|",
            ]
        )
        for item in self.inputs:
            lines.append(
                f"| {item['dataset']} | {item['table']} | {item['rows']} | "
                f"{item['size_bytes']} | `{item['sha256']}` | `{item['path']}` |"
            )

        if self.metrics:
            lines.extend(
                [
                    "",
                    "## Crosswalk metrics",
                    "",
                    "```json",
                    json.dumps(self.metrics, ensure_ascii=False, indent=2, sort_keys=True),
                    "```",
                ]
            )

        lines.extend(
            [
                "",
                "## Boundary",
                "",
                "This run validated source canonical data only. It did not generate unified CSV, SQLite, JSON/search data, Excel, or site artifacts, and it did not modify canonical or release data.",
                "",
            ]
        )
        return "\n".join(lines)

    def console_summary(self, representative_limit: int = 5) -> str:
        summary = self.summary(representative_limit)
        severity = summary["by_severity"]
        lines = [
            f"Validation status: {summary['status']}",
            f"Errors: {severity['error']}",
            f"Warnings: {severity['warning']}",
            f"Informational: {severity['informational']}",
            "",
            "Findings by code:",
        ]
        for code, counts in summary["by_code"].items():
            datasets = ", ".join(
                f"{name}={count}" for name, count in counts["by_dataset"].items()
            )
            reps = ", ".join(counts["representative_record_ids"]) or "-"
            lines.append(
                f"  {code} [{counts['severity']}]: {counts['count']} "
                f"({datasets}); representatives: {reps}"
            )
        lines.extend(["", "Findings by dataset:"])
        for dataset, counts in summary["by_dataset"].items():
            by = counts["by_severity"]
            lines.append(
                f"  {dataset}: errors={by['error']}, warnings={by['warning']}, "
                f"informational={by['informational']}, total={counts['total']}"
            )
        return "\n".join(lines)


class ReadOnlyValidator:
    """Validate canonical sources against unified contract v0.1."""

    def __init__(self, repo_root: Path | str):
        self.repo_root = Path(repo_root).resolve()
        self.contract: dict[str, Any] = {}
        self.result: ValidationResult | None = None

    def validate(self) -> ValidationResult:
        self.contract = self._load_json(self.repo_root / CONTRACT_PATH)
        contract_version = str(
            self.contract.get("properties", {})
            .get("contract_version", {})
            .get("const", "unknown")
        )
        self.result = ValidationResult(
            contract_version=contract_version,
            repo_root=self.repo_root,
        )

        self._validate_contract_files()
        states: dict[str, dict[str, Any]] = {}
        for dataset, config in SOURCE_CONFIG.items():
            states[dataset] = self._validate_source(dataset, config)

        self._validate_cross_table_relationships(states)
        self.result.metrics = self._build_metrics(states)
        return self.result

    @property
    def _out(self) -> ValidationResult:
        if self.result is None:
            raise RuntimeError("Validation has not started")
        return self.result

    def _validate_contract_files(self) -> None:
        for rel_path in CONTRACT_DOCUMENTS:
            path = self.repo_root / rel_path
            if not path.is_file():
                self._out.add_issue(
                    code="CONTRACT_DOCUMENT_MISSING",
                    severity="error",
                    dataset="contract",
                    table="contract",
                    message=f"Required contract document is missing: {rel_path}",
                )

    def _validate_source(
        self, dataset: str, config: Mapping[str, Path]
    ) -> dict[str, Any]:
        schema_path = self.repo_root / config["schema"]
        source_schema = self._load_json(schema_path)
        source_version = str(source_schema.get("version", ""))
        version_matrix = self.contract.get("x-source-version-matrix", {})
        expected_version = version_matrix.get(dataset)

        if dataset not in version_matrix:
            self._out.add_issue(
                code="SOURCE_DATASET_UNSUPPORTED",
                severity="error",
                dataset=dataset,
                table="schema",
                message="Source dataset is not declared in the unified contract.",
            )
        elif source_version != expected_version:
            self._out.add_issue(
                code="SOURCE_VERSION_MISMATCH",
                severity="error",
                dataset=dataset,
                table="schema",
                message="Source schema version does not match the unified contract.",
                details={
                    "expected": expected_version,
                    "actual": source_version,
                },
            )

        tables: dict[str, TableData] = {}
        canonical_dir = self.repo_root / config["canonical_dir"]
        for table_name, (filename, schema_key) in TABLE_CONFIG.items():
            expected_header = list(source_schema.get(schema_key, []))
            self._validate_source_contract_alignment(
                dataset, table_name, expected_header
            )
            table = self._read_table(
                dataset=dataset,
                table_name=table_name,
                path=canonical_dir / filename,
                expected_header=expected_header,
            )
            tables[table_name] = table

        self._validate_master(dataset, source_version, tables["master"])
        self._validate_coverage(dataset, source_version, tables["coverage"])
        self._validate_research(
            dataset, source_version, tables["research_requirements"]
        )
        return {
            "dataset": dataset,
            "source_version": source_version,
            "source_schema": source_schema,
            "tables": tables,
        }

    def _validate_source_contract_alignment(
        self, dataset: str, table: str, source_columns: Sequence[str]
    ) -> None:
        contract_tables = self.contract.get("x-table-contracts", {})
        contract_columns = list(contract_tables.get(table, {}).get("csv_columns", []))
        if table == "master":
            projected: list[str] = []
            for column in contract_columns[2:]:
                if column == "research_activity_level_status":
                    projected.append("research_activity_level")
                elif column == "research_activity_level_raw":
                    continue
                elif column == "detail_completeness_status":
                    projected.append("detail_completeness")
                elif column == "detail_completeness_raw":
                    continue
                else:
                    projected.append(column)
        else:
            projected = contract_columns[2:]

        if projected != list(source_columns):
            self._out.add_issue(
                code="UNIFIED_SOURCE_SCHEMA_MAPPING_MISMATCH",
                severity="error",
                dataset=dataset,
                table=table,
                message="Unified contract projection does not match source schema columns.",
                details={
                    "source_columns": list(source_columns),
                    "projected_columns": projected,
                },
            )

    def _read_table(
        self,
        *,
        dataset: str,
        table_name: str,
        path: Path,
        expected_header: Sequence[str],
    ) -> TableData:
        raw = path.read_bytes()
        sha256 = hashlib.sha256(raw).hexdigest()
        rows: list[SourceRow] = []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader, [])
            if len(header) != len(expected_header):
                self._out.add_issue(
                    code="SOURCE_COLUMN_COUNT_MISMATCH",
                    severity="error",
                    dataset=dataset,
                    table=table_name,
                    message="CSV column count differs from the source schema.",
                    details={
                        "expected_count": len(expected_header),
                        "actual_count": len(header),
                    },
                )
            if header != list(expected_header):
                self._out.add_issue(
                    code="SOURCE_COLUMN_ORDER_MISMATCH",
                    severity="error",
                    dataset=dataset,
                    table=table_name,
                    message="CSV columns or column order differ from the source schema.",
                    details={
                        "expected": list(expected_header),
                        "actual": header,
                    },
                )

            for row_number, raw_row in enumerate(reader, start=2):
                if len(raw_row) != len(header):
                    self._out.add_issue(
                        code="SOURCE_ROW_WIDTH_MISMATCH",
                        severity="error",
                        dataset=dataset,
                        table=table_name,
                        message="CSV row width differs from its header.",
                        row_number=row_number,
                        details={
                            "expected_count": len(header),
                            "actual_count": len(raw_row),
                        },
                    )
                padded = raw_row[: len(header)] + [""] * max(
                    0, len(header) - len(raw_row)
                )
                rows.append(
                    SourceRow(
                        row_number=row_number,
                        values=dict(zip(header, padded)),
                    )
                )

        table = TableData(
            dataset=dataset,
            name=table_name,
            path=path,
            header=header,
            rows=rows,
            sha256=sha256,
            size_bytes=len(raw),
        )
        self._out.inputs.append(
            {
                "dataset": dataset,
                "table": table_name,
                "path": str(path.relative_to(self.repo_root)),
                "rows": len(rows),
                "columns": len(header),
                "size_bytes": len(raw),
                "sha256": sha256,
            }
        )
        return table

    def _validate_master(
        self, dataset: str, source_version: str, table: TableData
    ) -> None:
        del source_version  # validated once against the contract matrix
        seen_ids: dict[str, int] = {}
        for row in table.rows:
            values = row.values
            record_id = values.get("record_id", "")
            if not record_id:
                self._issue(
                    "MASTER_PK_BLANK",
                    "error",
                    dataset,
                    "master",
                    row,
                    "Master record_id is blank.",
                    field_name="record_id",
                )
            elif record_id in seen_ids:
                self._issue(
                    "MASTER_PK_DUPLICATE",
                    "error",
                    dataset,
                    "master",
                    row,
                    "Master record_id is duplicated within the source version.",
                    record_id=record_id,
                    field_name="record_id",
                    details={"first_row_number": seen_ids[record_id]},
                )
            else:
                seen_ids[record_id] = row.row_number

            self._validate_required_string(
                dataset, "master", row, record_id, "university"
            )
            self._validate_required_string(
                dataset, "master", row, record_id, "verified_on"
            )
            self._validate_integer(
                dataset,
                "master",
                row,
                record_id,
                "admission_year",
                required=True,
                expected=2027,
            )
            self._validate_integer(
                dataset,
                "master",
                row,
                record_id,
                "information_year",
                required=False,
            )
            self._validate_institution_type(dataset, "master", row, record_id)

            for field_name in BOOLEAN_FIELDS:
                value = values.get(field_name, "")
                if value and value not in BOOL_MAP:
                    self._issue(
                        "INVALID_BOOLEAN_VALUE",
                        "error",
                        dataset,
                        "master",
                        row,
                        f"Unsupported boolean source value in {field_name}.",
                        record_id=record_id,
                        field_name=field_name,
                        details={"value": value},
                    )

            for field_name in TRISTATE_FIELDS:
                value = values.get(field_name, "")
                if value not in {"", "Yes", "No", "Unknown"}:
                    self._issue(
                        "INVALID_TRISTATE_VALUE",
                        "error",
                        dataset,
                        "master",
                        row,
                        f"Unsupported tri-state value in {field_name}.",
                        record_id=record_id,
                        field_name=field_name,
                        details={"value": value},
                    )

            common_test = values.get("common_test_required", "")
            if common_test not in {"", "Yes", "No", "Unknown", "条件付き"}:
                self._issue(
                    "INVALID_COMMON_TEST_REQUIRED",
                    "error",
                    dataset,
                    "master",
                    row,
                    "Unsupported common_test_required value.",
                    record_id=record_id,
                    field_name="common_test_required",
                    details={"value": common_test},
                )

            exclusive = values.get("exclusive_enrollment_status", "")
            if exclusive not in {"専願", "併願可", "条件付き", "不明"}:
                self._issue(
                    "INVALID_ENUM_VALUE",
                    "error",
                    dataset,
                    "master",
                    row,
                    "exclusive_enrollment_status is outside the unified enum.",
                    record_id=record_id,
                    field_name="exclusive_enrollment_status",
                    details={"value": exclusive},
                )

            grade = values.get("verification_grade", "")
            if grade not in {"", "A", "B", "C"}:
                self._issue(
                    "INVALID_ENUM_VALUE",
                    "error",
                    dataset,
                    "master",
                    row,
                    "verification_grade is outside the unified enum.",
                    record_id=record_id,
                    field_name="verification_grade",
                    details={"value": grade},
                )

            detail_raw = values.get("detail_completeness", "")
            detail_status = map_detail_completeness(dataset, detail_raw)
            if detail_status == "unmapped":
                self._issue(
                    "DETAIL_COMPLETENESS_UNMAPPED",
                    "warning",
                    dataset,
                    "master",
                    row,
                    "detail_completeness has no approved v0.1 crosswalk.",
                    record_id=record_id,
                    field_name="detail_completeness",
                    details={"raw_value": detail_raw},
                )

            research_raw = values.get("research_activity_level", "")
            research_status = map_research_activity_level(dataset, research_raw)
            if research_status == "unmapped":
                self._issue(
                    "RESEARCH_ACTIVITY_LEVEL_UNMAPPED",
                    "warning",
                    dataset,
                    "master",
                    row,
                    "research_activity_level has no approved v0.1 crosswalk.",
                    record_id=record_id,
                    field_name="research_activity_level",
                    details={"raw_value": research_raw},
                )

            selection_common = values.get("selection_common_test", "")
            normalized_common = (
                "Conditional" if common_test == "条件付き" else common_test
            )
            if normalized_common and selection_common and normalized_common != selection_common:
                self._issue(
                    "COMMON_TEST_FIELDS_DIFFER",
                    "informational",
                    dataset,
                    "master",
                    row,
                    "common_test_required and selection_common_test differ; no equality constraint applies.",
                    record_id=record_id,
                    details={
                        "common_test_required": normalized_common,
                        "selection_common_test": selection_common,
                    },
                )

            self._validate_provenance_master(dataset, row, record_id)
            self._validate_whitespace(dataset, "master", row, record_id)
            self._validate_dates(
                dataset, "master", row, record_id, MASTER_DATE_FIELDS
            )

    def _validate_coverage(
        self, dataset: str, source_version: str, table: TableData
    ) -> None:
        del source_version
        seen: dict[tuple[str, str], int] = {}
        for row in table.rows:
            values = row.values
            university = values.get("university", "")
            institution_type = values.get("institution_type", "")
            record_id = coverage_record_id(institution_type, university)
            if not university or not institution_type:
                self._issue(
                    "COVERAGE_KEY_BLANK",
                    "error",
                    dataset,
                    "coverage",
                    row,
                    "Coverage key contains a blank value.",
                    record_id=record_id,
                )
            key = (institution_type, university)
            if key in seen:
                self._issue(
                    "COVERAGE_KEY_DUPLICATE",
                    "error",
                    dataset,
                    "coverage",
                    row,
                    "Coverage key is duplicated within the source version.",
                    record_id=record_id,
                    details={"first_row_number": seen[key]},
                )
            else:
                seen[key] = row.row_number

            self._validate_institution_type(dataset, "coverage", row, record_id)
            self._validate_integer(
                dataset,
                "coverage",
                row,
                record_id,
                "master_rows",
                required=True,
                minimum=0,
            )
            self._validate_required_string(
                dataset, "coverage", row, record_id, "checked_on"
            )

            master_rows = parse_int(values.get("master_rows", ""))
            if master_rows == 0 and any(
                values.get(field_name, "")
                for field_name in (
                    "undergraduate_scope",
                    "research_status",
                    "current_year_status",
                    "fallback_status",
                )
            ):
                self._issue(
                    "COVERAGE_ZERO_MASTER_ROWS",
                    "informational",
                    dataset,
                    "coverage",
                    row,
                    "Coverage explicitly records a zero-Master state.",
                    record_id=record_id,
                )

            official_url = values.get("official_source_url", "")
            out_of_scope = (
                values.get("undergraduate_scope", "").startswith("対象外")
                or values.get("research_status", "") == "対象外"
            )
            if not official_url and (master_rows or not out_of_scope):
                self._issue(
                    "PROVENANCE_URL_MISSING",
                    "warning",
                    dataset,
                    "coverage",
                    row,
                    "In-scope Coverage row has no official_source_url.",
                    record_id=record_id,
                    field_name="official_source_url",
                )

            self._validate_whitespace(dataset, "coverage", row, record_id)
            self._validate_dates(
                dataset, "coverage", row, record_id, ("checked_on",)
            )

    def _validate_research(
        self, dataset: str, source_version: str, table: TableData
    ) -> None:
        del source_version
        seen_rows: dict[tuple[str, ...], int] = {}
        source_columns = [column for column in table.header if column]
        for row in table.rows:
            values = row.values
            admission_id = values.get("admission_id", "")
            record_id = admission_id or f"row:{row.row_number}"
            if not admission_id:
                self._issue(
                    "RESEARCH_ADMISSION_ID_BLANK",
                    "error",
                    dataset,
                    "research_requirements",
                    row,
                    "ResearchRequirements admission_id is blank.",
                    record_id=record_id,
                    field_name="admission_id",
                )
            self._validate_required_string(
                dataset,
                "research_requirements",
                row,
                record_id,
                "university",
            )
            self._validate_required_string(
                dataset,
                "research_requirements",
                row,
                record_id,
                "verified_on",
            )

            signature = tuple(values.get(column, "") for column in source_columns)
            if signature in seen_rows:
                self._issue(
                    "RESEARCH_EXACT_DUPLICATE",
                    "warning",
                    dataset,
                    "research_requirements",
                    row,
                    "ResearchRequirements row is an exact duplicate; source multiplicity is preserved.",
                    record_id=record_id,
                    details={"first_row_number": seen_rows[signature]},
                )
            else:
                seen_rows[signature] = row.row_number

            if not values.get("source_url", ""):
                self._issue(
                    "PROVENANCE_URL_MISSING",
                    "warning",
                    dataset,
                    "research_requirements",
                    row,
                    "ResearchRequirements row has no source_url.",
                    record_id=record_id,
                    field_name="source_url",
                )
            self._validate_whitespace(
                dataset, "research_requirements", row, record_id
            )
            self._validate_dates(
                dataset,
                "research_requirements",
                row,
                record_id,
                ("verified_on",),
            )

    def _validate_cross_table_relationships(
        self, states: Mapping[str, Mapping[str, Any]]
    ) -> None:
        for dataset, state in states.items():
            tables: Mapping[str, TableData] = state["tables"]
            master_rows = tables["master"].rows
            coverage_rows = tables["coverage"].rows
            research_rows = tables["research_requirements"].rows

            parents: dict[str, SourceRow] = {}
            master_counts: Counter[tuple[str, str]] = Counter()
            for row in master_rows:
                record_id = row.values.get("record_id", "")
                if record_id and record_id not in parents:
                    parents[record_id] = row
                master_counts[
                    (
                        row.values.get("institution_type", ""),
                        row.values.get("university", ""),
                    )
                ] += 1

            for row in coverage_rows:
                values = row.values
                parsed_count = parse_int(values.get("master_rows", ""))
                if parsed_count is None:
                    continue
                key = (
                    values.get("institution_type", ""),
                    values.get("university", ""),
                )
                actual_count = master_counts[key]
                if parsed_count != actual_count:
                    self._issue(
                        "COVERAGE_MASTER_ROWS_MISMATCH",
                        "error",
                        dataset,
                        "coverage",
                        row,
                        "Coverage.master_rows differs from the matching Master count.",
                        record_id=coverage_record_id(*key),
                        field_name="master_rows",
                        details={
                            "declared": parsed_count,
                            "actual": actual_count,
                        },
                    )

            child_counts: Counter[str] = Counter()
            for row in research_rows:
                values = row.values
                admission_id = values.get("admission_id", "")
                if admission_id:
                    child_counts[admission_id] += 1
                parent = parents.get(admission_id)
                if admission_id and parent is None:
                    self._issue(
                        "RESEARCH_ORPHAN_FK",
                        "error",
                        dataset,
                        "research_requirements",
                        row,
                        "ResearchRequirements admission_id does not resolve to Master in the same source dataset/version.",
                        record_id=admission_id,
                        field_name="admission_id",
                    )
                    continue
                if parent is None:
                    continue
                for field_name in DISPLAY_FIELDS:
                    child_value = values.get(field_name, "")
                    parent_value = parent.values.get(field_name, "")
                    if child_value != parent_value:
                        self._issue(
                            "RESEARCH_DENORMALIZED_FIELD_MISMATCH",
                            "warning",
                            dataset,
                            "research_requirements",
                            row,
                            "ResearchRequirements display field differs from its Master parent.",
                            record_id=admission_id,
                            field_name=field_name,
                            details={
                                "parent_value": parent_value,
                                "child_value": child_value,
                            },
                        )

            for record_id, parent in parents.items():
                flag = parent.values.get("research_requirement_required", "")
                count = child_counts[record_id]
                if flag == "Yes" and count == 0:
                    self._issue(
                        "RESEARCH_REQUIRED_WITHOUT_CHILD",
                        "warning",
                        dataset,
                        "master",
                        parent,
                        "research_requirement_required is Yes but no child detail row exists.",
                        record_id=record_id,
                    )
                elif flag == "No" and count > 0:
                    self._issue(
                        "RESEARCH_NOT_REQUIRED_WITH_CHILD",
                        "informational",
                        dataset,
                        "master",
                        parent,
                        "research_requirement_required is No and child detail rows exist; no contradiction is inferred.",
                        record_id=record_id,
                        details={"child_rows": count},
                    )

    def _validate_provenance_master(
        self, dataset: str, row: SourceRow, record_id: str
    ) -> None:
        values = row.values
        if not values.get("source_url", ""):
            self._issue(
                "PROVENANCE_URL_MISSING",
                "warning",
                dataset,
                "master",
                row,
                "Master row has no source_url.",
                record_id=record_id,
                field_name="source_url",
            )
        if (
            values.get("exclusive_enrollment_status", "") != "不明"
            and not values.get("exclusive_enrollment_evidence_url", "")
        ):
            self._issue(
                "PROVENANCE_URL_MISSING",
                "warning",
                dataset,
                "master",
                row,
                "Known exclusive-enrollment status has no evidence URL.",
                record_id=record_id,
                field_name="exclusive_enrollment_evidence_url",
            )
        fallback = BOOL_MAP.get(values.get("fallback_previous_year", ""))
        if fallback is True and not values.get("previous_year_source_url", ""):
            self._issue(
                "PROVENANCE_URL_MISSING",
                "warning",
                dataset,
                "master",
                row,
                "Fallback row has no previous_year_source_url.",
                record_id=record_id,
                field_name="previous_year_source_url",
            )

    def _validate_whitespace(
        self, dataset: str, table: str, row: SourceRow, record_id: str
    ) -> None:
        for field_name, value in row.values.items():
            if value and value != value.strip():
                self._issue(
                    "WHITESPACE_PADDING",
                    "warning",
                    dataset,
                    table,
                    row,
                    "Source value has leading or trailing whitespace; value is not modified.",
                    record_id=record_id,
                    field_name=field_name,
                    details={"leading": value[:1].isspace(), "trailing": value[-1:].isspace()},
                )

    def _validate_dates(
        self,
        dataset: str,
        table: str,
        row: SourceRow,
        record_id: str,
        fields: Iterable[str],
    ) -> None:
        for field_name in fields:
            raw = row.values.get(field_name, "")
            status = classify_raw_date(raw)
            if status == "partial":
                self._issue(
                    "DATE_RAW_PARTIAL",
                    "informational",
                    dataset,
                    table,
                    row,
                    "Raw date/period contains an ISO date plus additional text or range structure.",
                    record_id=record_id,
                    field_name=field_name,
                    details={"raw_value": raw, "parse_status": status},
                )
            elif status == "unparsed":
                self._issue(
                    "DATE_RAW_UNPARSED",
                    "informational",
                    dataset,
                    table,
                    row,
                    "Raw date/period is nonblank but has no unambiguous ISO date token.",
                    record_id=record_id,
                    field_name=field_name,
                    details={"raw_value": raw, "parse_status": status},
                )

    def _validate_required_string(
        self,
        dataset: str,
        table: str,
        row: SourceRow,
        record_id: str,
        field_name: str,
    ) -> None:
        if not row.values.get(field_name, ""):
            self._issue(
                "REQUIRED_VALUE_MISSING",
                "error",
                dataset,
                table,
                row,
                f"Required value is blank: {field_name}.",
                record_id=record_id,
                field_name=field_name,
            )

    def _validate_integer(
        self,
        dataset: str,
        table: str,
        row: SourceRow,
        record_id: str,
        field_name: str,
        *,
        required: bool,
        expected: int | None = None,
        minimum: int | None = None,
    ) -> None:
        raw = row.values.get(field_name, "")
        if not raw and not required:
            return
        parsed = parse_int(raw)
        if parsed is None:
            self._issue(
                "INVALID_INTEGER_VALUE",
                "error",
                dataset,
                table,
                row,
                f"Field cannot be parsed as an integer: {field_name}.",
                record_id=record_id,
                field_name=field_name,
                details={"value": raw},
            )
            return
        if expected is not None and parsed != expected:
            self._issue(
                "INVALID_INTEGER_VALUE",
                "error",
                dataset,
                table,
                row,
                f"Field does not equal the contract value: {field_name}.",
                record_id=record_id,
                field_name=field_name,
                details={"value": parsed, "expected": expected},
            )
        if minimum is not None and parsed < minimum:
            self._issue(
                "INVALID_INTEGER_VALUE",
                "error",
                dataset,
                table,
                row,
                f"Field is below the contract minimum: {field_name}.",
                record_id=record_id,
                field_name=field_name,
                details={"value": parsed, "minimum": minimum},
            )

    def _validate_institution_type(
        self, dataset: str, table: str, row: SourceRow, record_id: str
    ) -> None:
        value = row.values.get("institution_type", "")
        allowed = {"国立", "公立"} if dataset == "kokkoritsu" else {"私立"}
        if value not in allowed:
            self._issue(
                "SOURCE_INSTITUTION_TYPE_MISMATCH",
                "error",
                dataset,
                table,
                row,
                "institution_type is inconsistent with source_dataset.",
                record_id=record_id,
                field_name="institution_type",
                details={"value": value, "allowed": sorted(allowed)},
            )

    def _build_metrics(
        self, states: Mapping[str, Mapping[str, Any]]
    ) -> dict[str, Any]:
        crosswalks: dict[str, Any] = {}
        row_counts: dict[str, Any] = {}
        for dataset, state in states.items():
            tables: Mapping[str, TableData] = state["tables"]
            detail_counts: Counter[str] = Counter()
            research_counts: Counter[str] = Counter()
            for row in tables["master"].rows:
                detail_status = map_detail_completeness(
                    dataset, row.values.get("detail_completeness", "")
                )
                research_status = map_research_activity_level(
                    dataset, row.values.get("research_activity_level", "")
                )
                detail_counts[metric_status(detail_status)] += 1
                research_counts[metric_status(research_status)] += 1
            crosswalks[dataset] = {
                "detail_completeness_status": dict(sorted(detail_counts.items())),
                "research_activity_level_status": dict(
                    sorted(research_counts.items())
                ),
            }
            row_counts[dataset] = {
                name: len(table.rows) for name, table in tables.items()
            }
        return {"row_counts": row_counts, "crosswalks": crosswalks}

    def _issue(
        self,
        code: str,
        severity: str,
        dataset: str,
        table: str,
        row: SourceRow,
        message: str,
        *,
        record_id: str | None = None,
        field_name: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self._out.add_issue(
            code=code,
            severity=severity,
            dataset=dataset,
            table=table,
            message=message,
            record_id=record_id,
            field_name=field_name,
            row_number=row.row_number,
            details=details,
        )

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)


def parse_int(raw: str) -> int | None:
    """Parse a strict base-10 integer without trimming source data."""

    if not raw or not re.fullmatch(r"-?\d+", raw):
        return None
    try:
        return int(raw, 10)
    except ValueError:
        return None


def metric_status(value: str | None) -> str:
    """Return a stable JSON object key for a nullable mapped status."""

    return value if value is not None else "null"


def map_detail_completeness(dataset: str, raw: str) -> str | None:
    """Return the approved v0.1 common detail-completeness status."""

    if not raw:
        return None
    if dataset == "shidai" and raw in {"complete", "partial", "pending", "unknown"}:
        return raw
    if dataset == "kokkoritsu" and raw.startswith("detailed"):
        return "complete"
    if dataset == "kokkoritsu" and raw.startswith("partial"):
        return "partial"
    return "unmapped"


def map_research_activity_level(dataset: str, raw: str) -> str | None:
    """Return the approved v0.1 common research-activity status."""

    if not raw:
        return None
    if dataset == "shidai" and raw in {"required", "relevant", "none", "unknown"}:
        return raw
    if dataset == "kokkoritsu":
        return KOKKORITSU_RESEARCH_LEVEL_MAP.get(raw, "unmapped")
    return "unmapped"


def classify_raw_date(raw: str) -> str:
    """Classify date/period parseability without changing the raw value."""

    if not raw:
        return "not_applicable"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        try:
            date.fromisoformat(raw)
        except ValueError:
            return "unparsed"
        return "parsed"

    valid_tokens = []
    for match in ISO_DATE_RE.finditer(raw):
        token = match.group(1)
        try:
            date.fromisoformat(token)
        except ValueError:
            continue
        valid_tokens.append(token)
    return "partial" if valid_tokens else "unparsed"


def coverage_record_id(institution_type: str, university: str) -> str:
    return f"{institution_type}:{university}"


def write_json_report(
    result: ValidationResult, path: Path, representative_limit: int = 5
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            result.to_dict(representative_limit),
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
        )
        + "\n",
        encoding="utf-8",
    )


def write_markdown_report(
    result: ValidationResult, path: Path, representative_limit: int = 5
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        result.to_markdown(representative_limit),
        encoding="utf-8",
    )
