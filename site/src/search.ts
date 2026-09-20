import type { GpaDerivedStatus, MultiField, SearchRequest, SearchResult, SearchRow } from "./types";

export const MULTI_FIELDS: MultiField[] = [
  "university", "institution_type", "prefecture", "academic_field", "academic_field_group",
  "academic_field_mapping_status", "selection_category", "exclusive_enrollment_status",
  "school_recommendation_required", "academic_record_required", "common_test_required",
  "research_requirement_required", "research_activity_level_status", "selection_interview",
  "selection_oral_exam", "selection_presentation", "selection_essay", "selection_written_exam",
  "selection_common_test",
];

export function emptyRequest(): SearchRequest {
  return Object.assign(Object.fromEntries(MULTI_FIELDS.map((field) => [field, []])), {
    stem_flag: null, gpa_tenths: null, gpa_mode: "all", page: 1,
  }) as unknown as SearchRequest;
}

export function safeGpaMatch(row: SearchRow, value: number): boolean {
  if (row.gpa_parse_status !== "parsed_safe") return false;
  const lower = row.gpa_min_tenths === null || value > row.gpa_min_tenths ||
    (value === row.gpa_min_tenths && row.gpa_min_inclusive === true);
  const upper = row.gpa_max_tenths === null || value < row.gpa_max_tenths ||
    (value === row.gpa_max_tenths && row.gpa_max_inclusive === true);
  return lower && upper;
}

export function gpaStatus(row: SearchRow, value: number | null): GpaDerivedStatus {
  if (value === null) {
    if (row.gpa_parse_status === "parsed_safe") return "safe numeric rule (GPA not supplied)";
    if (row.gpa_parse_status === "conditional_review") return "conditional/review required";
    return "not numerically evaluable";
  }
  if (safeGpaMatch(row, value)) return "safe match";
  if (row.gpa_parse_status === "parsed_safe") return "safe no match";
  if (row.gpa_parse_status === "conditional_review") return "conditional/review required";
  return "not numerically evaluable";
}

function matches(row: SearchRow, request: SearchRequest): boolean {
  for (const field of MULTI_FIELDS) {
    const values = request[field];
    if (!values.length) continue;
    if (field === "academic_field_group") {
      if (!values.some((value) => row.academic_field_groups.includes(value))) return false;
    } else if (!values.includes(row[field as keyof SearchRow] as string)) return false;
  }
  if (request.stem_flag !== null && row.stem_flag !== request.stem_flag) return false;
  if (request.gpa_tenths !== null) {
    const safe = safeGpaMatch(row, request.gpa_tenths);
    if (request.gpa_mode === "safe" && !safe) return false;
    if (request.gpa_mode === "review" && !safe && row.gpa_parse_status !== "conditional_review") return false;
  }
  return true;
}

const sortFields: Array<keyof SearchRow> = [
  "prefecture", "university", "faculty_school", "department", "selection_category", "selection_name",
  "source_dataset", "source_version", "record_id",
];

export function searchRows(rows: SearchRow[], request: SearchRequest): SearchResult {
  if (request.gpa_tenths !== null && (request.gpa_tenths < 0 || request.gpa_tenths > 50)) throw new Error("GPA範囲が不正です");
  const matched = rows.filter((row) => matches(row, request)).slice().sort((a, b) => {
    for (const field of sortFields) {
      const compared = String(a[field] ?? "").localeCompare(String(b[field] ?? ""), "ja");
      if (compared) return compared;
    }
    return 0;
  }).map((row) => ({ ...row, gpa_derived_status: gpaStatus(row, request.gpa_tenths) }));
  const statuses = matched.map((row) => row.gpa_derived_status);
  const sources: Record<string, number> = {};
  for (const row of matched) sources[row.source_dataset] = (sources[row.source_dataset] ?? 0) + 1;
  return { rows: matched, summary: {
    total_matched_rows: matched.length,
    gpa_safe_match_rows: request.gpa_tenths === null ? null : statuses.filter((s) => s === "safe match").length,
    gpa_safe_no_match_rows: request.gpa_tenths === null ? null : statuses.filter((s) => s === "safe no match").length,
    gpa_safe_numeric_rule_rows: matched.filter((r) => r.gpa_parse_status === "parsed_safe").length,
    gpa_conditional_review_rows: matched.filter((r) => r.gpa_parse_status === "conditional_review").length,
    gpa_not_numerically_evaluable_rows: matched.filter((r) => !["parsed_safe", "conditional_review"].includes(r.gpa_parse_status)).length,
    rows_by_source_dataset: Object.fromEntries(Object.entries(sources).sort()),
    university_count: new Set(matched.map((row) => row.university)).size,
  }};
}

export function logicalKey(row: SearchRow): string {
  return `${row.source_dataset}\u001f${row.source_version}\u001f${row.record_id}`;
}
