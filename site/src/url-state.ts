import { emptyRequest, MULTI_FIELDS } from "./search";
import type { FilterOptions, MultiField, SearchRequest } from "./types";

const PARAMS = new Set<string>([
  ...MULTI_FIELDS,
  "stem",
  "gpa",
  "gpa_mode",
  "page",
  "university_query",
  "gpa_query",
]);

export interface SearchUrlState {
  request: SearchRequest;
  warnings: string[];
  universityQuery: string;
  gpaQuery: string;
}

function allowedValues(options: FilterOptions): Record<MultiField, Set<string>> {
  const values = (items: Array<{ value: string | null }>) => new Set(items.flatMap((item) => item.value === null ? [] : [item.value]));
  return {
    university: values(options.universities), institution_type: values(options.institution_types),
    prefecture: values(options.prefectures), academic_field: values(options.raw_academic_fields),
    academic_field_group: values(options.academic_field_groups),
    academic_field_mapping_status: values(options.academic_field_mapping_statuses),
    selection_category: values(options.selection_categories),
    exclusive_enrollment_status: values(options.exclusive_enrollment_statuses),
    school_recommendation_required: values(options.school_recommendation_required),
    academic_record_required: values(options.academic_record_required),
    common_test_required: values(options.common_test_required),
    research_requirement_required: values(options.research_requirement_required),
    research_activity_level_status: values(options.research_activity_level_status),
    selection_interview: values(options.selection_method_values.selection_interview),
    selection_oral_exam: values(options.selection_method_values.selection_oral_exam),
    selection_presentation: values(options.selection_method_values.selection_presentation),
    selection_essay: values(options.selection_method_values.selection_essay),
    selection_written_exam: values(options.selection_method_values.selection_written_exam),
    selection_common_test: values(options.selection_method_values.selection_common_test),
    english_requirement_status: values(options.english_requirement_statuses ?? []),
    prefecture_membership: values(options.prefecture_memberships ?? []),
  };
}

export function parseSearchParams(params: URLSearchParams, options: FilterOptions): SearchUrlState {
  const request = emptyRequest();
  const warnings: string[] = [];
  const allowed = allowedValues(options);
  for (const key of new Set(params.keys())) if (!PARAMS.has(key)) warnings.push(`未対応のパラメータ「${key}」を無視しました。`);
  for (const field of MULTI_FIELDS) {
    for (const value of params.getAll(field)) {
      if (allowed[field].has(value)) request[field].push(value);
      else warnings.push(`「${field}=${value}」は現在のデータにないため無視しました。`);
    }
  }
  const stem = params.get("stem");
  if (stem === "1") request.stem_flag = true;
  else if (stem === "0") request.stem_flag = false;
  else if (stem !== null) warnings.push("STEM指定を無視しました。");
  const gpa = params.get("gpa");
  if (gpa !== null) {
    if (/^(?:[0-4](?:\.\d)?|5(?:\.0)?)$/.test(gpa)) request.gpa_tenths = Math.round(Number(gpa) * 10);
    else warnings.push("GPAは0.0〜5.0、小数1桁で指定してください。");
  }
  const mode = params.get("gpa_mode");
  if (request.gpa_tenths !== null) {
    if (mode === null || mode === "safe") request.gpa_mode = "safe";
    else if (mode === "review" || mode === "all") request.gpa_mode = mode;
    else warnings.push("GPA modeをsafeとして扱いました。");
  } else if (mode !== null) warnings.push("GPA値がないためGPA modeを無視しました。");
  const page = params.get("page");
  if (page !== null && /^\d+$/.test(page) && Number(page) > 0) request.page = Number(page);
  else if (page !== null) warnings.push("ページ指定を無視しました。");
  const universityQuery = params.get("university_query") ?? request.university[0] ?? "";
  const gpaQuery = params.get("gpa_query") ?? (
    request.gpa_tenths === null ? "" : (request.gpa_tenths / 10).toFixed(1)
  );
  return { request, warnings, universityQuery, gpaQuery };
}

export function serializeRequest(request: SearchRequest): URLSearchParams {
  const params = new URLSearchParams();
  for (const field of MULTI_FIELDS) for (const value of request[field]) params.append(field, value);
  if (request.stem_flag !== null) params.set("stem", request.stem_flag ? "1" : "0");
  if (request.gpa_tenths !== null) {
    params.set("gpa", (request.gpa_tenths / 10).toFixed(1));
    params.set("gpa_mode", request.gpa_mode);
  }
  if (request.page > 1) params.set("page", String(request.page));
  return params;
}

export function serializeSearchFormState(
  request: SearchRequest,
  universityQuery: string,
  gpaQuery: string,
): URLSearchParams {
  const params = serializeRequest(request);
  if (universityQuery && request.university[0] !== universityQuery) {
    params.set("university_query", universityQuery);
  }
  const canonicalGpa = request.gpa_tenths === null
    ? ""
    : (request.gpa_tenths / 10).toFixed(1);
  if (gpaQuery && canonicalGpa !== gpaQuery) params.set("gpa_query", gpaQuery);
  return params;
}
