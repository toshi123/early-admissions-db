import type { GpaDerivedStatus, MultiField, SearchRequest, SearchResult, SearchRow, SpecialFilter } from "./types";

export const MULTI_FIELDS: MultiField[] = [
  "university", "institution_type", "prefecture", "academic_field", "academic_field_group",
  "academic_field_mapping_status", "selection_category", "exclusive_enrollment_status",
  "school_recommendation_required", "academic_record_required", "common_test_required",
  "research_requirement_required", "research_activity_level_status", "selection_interview",
  "selection_oral_exam", "selection_presentation", "selection_essay", "selection_written_exam",
  "selection_common_test",
  "english_requirement_status",
  "prefecture_membership",
];

export function emptyRequest(): SearchRequest {
  return Object.assign(Object.fromEntries(MULTI_FIELDS.map((field) => [field, []])), {
    academic_field_v2_branches: [],
    stem_flag: null, gpa_tenths: null, gpa_mode: "all",
    grade_requirement_status: null, overall_gpa_tenths: null,
    applicant_gpa_tenths: null, deadline_on_or_after: null,
    selection_families: ["recommendation", "comprehensive"], special_filters: [], page: 1,
  }) as unknown as SearchRequest;
}

export function selectionFamily(category: string | null): "recommendation" | "comprehensive" | "other" {
  if (category?.startsWith("学校推薦型")) return "recommendation";
  if (category?.startsWith("総合型")) return "comprehensive";
  return "other";
}

export function specialSelectionMatch(row: SearchRow, selected: SpecialFilter[]): boolean {
  const flags = row.special_flags;
  if (selected.length) return selected.some((name) => flags?.[name] === true);
  return !flags || !Object.values(flags).some(Boolean);
}

export function deadlineStatus(row: SearchRow, date: string | null): "match" | "unknown" | "exclude" {
  if (!date) return "match";
  if (row.fallback_previous_year || !row.application_end || !/^\d{4}-\d{2}-\d{2}$/.test(row.application_end)) return "unknown";
  return row.application_end >= date ? "match" : "exclude";
}

export function validIsoDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

export function applicantGradeStatus(row: SearchRow, value: number | null): "match" | "unknown" | "exclude" {
  if (value === null) return "match";
  if (row.fallback_previous_year) return "unknown";
  if (row.grade_requirement_status === "not_required" || row.grade_requirement_status === "not_applicable") return "match";
  if (row.grade_requirement_status !== "required" || row.overall_gpa_status !== "safe_simple_overall" ||
      row.additional_grade_conditions !== false || row.overall_gpa_min_tenths === null) return "unknown";
  return value > row.overall_gpa_min_tenths ||
    (value === row.overall_gpa_min_tenths && row.overall_gpa_min_inclusive === true) ? "match" : "exclude";
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
  // Frozen v0.3 oracle requests predate the public UI selection controls.
  if (request.special_filters && !specialSelectionMatch(row, request.special_filters)) return false;
  if (request.selection_families && request.special_filters && !request.special_filters.length &&
      !request.selection_families.includes(selectionFamily(row.selection_category) as "recommendation" | "comprehensive")) return false;
  for (const field of MULTI_FIELDS) {
    const values = request[field];
    if (!values.length) continue;
    if (field === "academic_field_group") {
      if (!values.some((value) => row.academic_field_groups.includes(value))) return false;
    } else if (field === "prefecture_membership") {
      if (!values.some((value) => row.prefecture_memberships.includes(value))) return false;
    } else if (!values.includes(row[field as keyof SearchRow] as string)) return false;
  }
  if (request.academic_field_v2_branches.length) {
    const broad = new Set(row.academic_field_v2_broad_memberships);
    const subcategories = new Set(row.academic_field_v2_subcategory_memberships);
    const branchMatch = request.academic_field_v2_branches.some((branch) =>
      broad.has(branch.group_code)
      && (
        branch.subcategory_codes.length === 0
        || branch.subcategory_codes.some((code) => subcategories.has(code))
      ));
    if (!branchMatch) return false;
  }
  if (request.stem_flag !== null && row.stem_flag !== request.stem_flag) return false;
  if (request.gpa_tenths !== null) {
    const safe = safeGpaMatch(row, request.gpa_tenths);
    if (request.gpa_mode === "safe" && !safe) return false;
    if (request.gpa_mode === "review" && !safe && row.gpa_parse_status !== "conditional_review") return false;
  }
  if (
    request.grade_requirement_status !== null
    && row.grade_requirement_status !== request.grade_requirement_status
  ) return false;
  if (request.overall_gpa_tenths !== null) {
    if (row.overall_gpa_min_tenths === null) return false;
    if (request.overall_gpa_tenths < row.overall_gpa_min_tenths) return false;
    if (
      request.overall_gpa_tenths === row.overall_gpa_min_tenths
      && row.overall_gpa_min_inclusive !== true
    ) return false;
  }
  if (deadlineStatus(row, request.deadline_on_or_after ?? null) === "exclude") return false;
  if (applicantGradeStatus(row, request.applicant_gpa_tenths ?? null) === "exclude") return false;
  return true;
}

const sortFields: Array<keyof SearchRow> = [
  "prefecture", "university", "faculty_school", "department", "selection_category", "selection_name",
  "source_dataset", "source_version", "record_id",
];

export function searchRows(rows: SearchRow[], request: SearchRequest): SearchResult {
  if (request.selection_families && request.special_filters && !request.selection_families.length && !request.special_filters.length) throw new Error("少なくとも1つ選抜方式を選択してください");
  if (request.deadline_on_or_after != null && !validIsoDate(request.deadline_on_or_after)) throw new Error("出願締切日の指定が不正です");
  if (request.applicant_gpa_tenths != null && (request.applicant_gpa_tenths < 0 || request.applicant_gpa_tenths > 50)) throw new Error("あなたの評定平均が範囲外です");
  if (request.gpa_tenths !== null && (request.gpa_tenths < 0 || request.gpa_tenths > 50)) throw new Error("GPA範囲が不正です");
  if (request.grade_requirement_status !== null && request.grade_requirement_status !== "required") throw new Error("評定条件指定が不正です");
  if (request.overall_gpa_tenths !== null && (request.grade_requirement_status !== "required" || request.overall_gpa_tenths < 0 || request.overall_gpa_tenths > 50)) throw new Error("全体評定指定が不正です");
  const matched = rows.filter((row) => matches(row, request)).slice().sort((a, b) => {
    for (const field of sortFields) {
      const compared = String(a[field] ?? "").localeCompare(String(b[field] ?? ""), "ja");
      if (compared) return compared;
    }
    return 0;
  }).map((row) => ({ ...row, gpa_derived_status: gpaStatus(row, request.gpa_tenths),
    deadline_filter_status: request.deadline_on_or_after ? deadlineStatus(row, request.deadline_on_or_after) as "match" | "unknown" : undefined,
    applicant_grade_status: request.applicant_gpa_tenths != null ? applicantGradeStatus(row, request.applicant_gpa_tenths) as "match" | "unknown" : undefined }));
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
