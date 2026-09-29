import { emptyRequest, MULTI_FIELDS, validIsoDate } from "./search";
import type { FilterOptions, MultiField, SearchRequest } from "./types";

const PARAMS = new Set<string>([
  ...MULTI_FIELDS,
  "stem",
  "gpa",
  "gpa_mode",
  "page",
  "university_query",
  "gpa_query",
  "grade_requirement",
  "overall_gpa",
  "overall_gpa_query",
  "academic_field_v2",
  "academic_subfield_v2",
  "selection_family", "special_filter", "applicant_gpa", "deadline_on_or_after",
  "applicant_gpa_query", "deadline_query",
]);

export interface SearchUrlState {
  request: SearchRequest;
  warnings: string[];
  universityQuery: string;
  gpaQuery: string;
  overallGpaQuery: string;
  applicantGpaQuery: string;
  deadlineQuery: string;
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
  const families = params.getAll("selection_family");
  if (families.length) {
    request.selection_families = [...new Set(families.filter((value): value is "recommendation" | "comprehensive" => value === "recommendation" || value === "comprehensive"))];
    if (families.some((value) => value !== "recommendation" && value !== "comprehensive" && value !== "none")) warnings.push("未対応の選抜方式指定を無視しました。");
  }
  const special = params.getAll("special_filter");
  const validSpecial = ["returnee_flag", "international_baccalaureate_flag", "private_foreign_student_flag", "adult_selection_flag"] as const;
  request.special_filters = [...new Set(special.filter((value): value is typeof validSpecial[number] => validSpecial.includes(value as typeof validSpecial[number])))];
  if (special.some((value) => !validSpecial.includes(value as typeof validSpecial[number]))) warnings.push("未対応の特別選抜指定を無視しました。");
  for (const key of new Set(params.keys())) if (!PARAMS.has(key)) warnings.push(`未対応のパラメータ「${key}」を無視しました。`);
  for (const field of MULTI_FIELDS) {
    for (const value of params.getAll(field)) {
      if (allowed[field].has(value)) request[field].push(value);
      else warnings.push(`「${field}=${value}」は現在のデータにないため無視しました。`);
    }
  }
  const broadOptions = options.academic_field_v2_broad_groups;
  const broadByCode = new Map(
    broadOptions.map((item) => [item.group_code, item] as const),
  );
  const requestedBroad = new Set<string>();
  for (const code of params.getAll("academic_field_v2")) {
    if (broadByCode.has(code)) requestedBroad.add(code);
    else warnings.push(`「academic_field_v2=${code}」は現在の分類にないため無視しました。`);
  }
  const selectedSubcategories = new Map<string, Set<string>>();
  const subcategoryByCode = new Map(
    options.academic_field_v2_subcategories.map((item) => [item.subcategory_code, item] as const),
  );
  for (const value of params.getAll("academic_subfield_v2")) {
    const separator = value.indexOf(":");
    const parent = separator < 0 ? "" : value.slice(0, separator);
    const code = separator < 0 ? "" : value.slice(separator + 1);
    const option = subcategoryByCode.get(code);
    if (!option || option.parent_group_code !== parent) {
      warnings.push(`「academic_subfield_v2=${value}」は現在の分類にないため無視しました。`);
      continue;
    }
    if (!requestedBroad.has(parent)) {
      warnings.push(`「academic_subfield_v2=${value}」は親の学問分野がないため無視しました。`);
      continue;
    }
    const selected = selectedSubcategories.get(parent) ?? new Set<string>();
    selected.add(code);
    selectedSubcategories.set(parent, selected);
  }
  request.academic_field_v2_branches = broadOptions
    .filter((item) => requestedBroad.has(item.group_code))
    .map((item) => ({
      group_code: item.group_code,
      subcategory_codes: options.academic_field_v2_subcategories
        .filter((subcategory) =>
          subcategory.parent_group_code === item.group_code
          && selectedSubcategories.get(item.group_code)?.has(subcategory.subcategory_code))
        .map((subcategory) => subcategory.subcategory_code),
    }));
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
  const gradeRequirement = params.get("grade_requirement");
  if (gradeRequirement === "required") request.grade_requirement_status = "required";
  else if (gradeRequirement !== null) warnings.push("未対応の評定条件指定を無視しました。");
  const overallGpa = params.get("overall_gpa");
  if (overallGpa !== null) {
    if (request.grade_requirement_status !== "required") {
      warnings.push("評定条件ありの指定がないため全体評定を無視しました。");
    } else if (/^(?:[0-4](?:\.\d)?|5(?:\.0)?)$/.test(overallGpa)) {
      request.overall_gpa_tenths = Math.round(Number(overallGpa) * 10);
    } else warnings.push("全体評定は0.0〜5.0、小数1桁で指定してください。");
  }
  const applicantGpa = params.get("applicant_gpa");
  if (applicantGpa !== null) {
    if (/^(?:[0-4](?:\.\d)?|5(?:\.0)?)$/.test(applicantGpa)) request.applicant_gpa_tenths = Math.round(Number(applicantGpa) * 10);
    else warnings.push("あなたの評定平均は0.0〜5.0、小数1桁で指定してください。");
  }
  const deadline = params.get("deadline_on_or_after");
  if (deadline !== null) {
    if (validIsoDate(deadline)) request.deadline_on_or_after = deadline;
    else warnings.push("出願締切日は有効な日付で指定してください。");
  }
  const page = params.get("page");
  if (page !== null && /^\d+$/.test(page) && Number(page) > 0) request.page = Number(page);
  else if (page !== null) warnings.push("ページ指定を無視しました。");
  const universityQuery = params.get("university_query") ?? request.university[0] ?? "";
  const gpaQuery = params.get("gpa_query") ?? (
    request.gpa_tenths === null ? "" : (request.gpa_tenths / 10).toFixed(1)
  );
  const overallGpaQuery = params.get("overall_gpa_query") ?? (
    request.overall_gpa_tenths === null
      ? ""
      : (request.overall_gpa_tenths / 10).toFixed(1)
  );
  return { request, warnings, universityQuery, gpaQuery, overallGpaQuery,
    applicantGpaQuery: params.get("applicant_gpa_query") ?? (request.applicant_gpa_tenths === null ? "" : (request.applicant_gpa_tenths / 10).toFixed(1)),
    deadlineQuery: params.get("deadline_query") ?? request.deadline_on_or_after ?? "" };
}

export function serializeRequest(request: SearchRequest): URLSearchParams {
  const params = new URLSearchParams();
  if (request.selection_families.length !== 2) {
    for (const family of request.selection_families) params.append("selection_family", family);
    if (!request.selection_families.length) params.append("selection_family", "none");
  }
  for (const filter of request.special_filters) params.append("special_filter", filter);
  for (const field of MULTI_FIELDS) for (const value of request[field]) params.append(field, value);
  const seenBroad = new Set<string>();
  for (const branch of request.academic_field_v2_branches) {
    if (seenBroad.has(branch.group_code)) continue;
    seenBroad.add(branch.group_code);
    params.append("academic_field_v2", branch.group_code);
    const seenSubcategories = new Set<string>();
    for (const code of branch.subcategory_codes) {
      if (seenSubcategories.has(code)) continue;
      seenSubcategories.add(code);
      params.append(
        "academic_subfield_v2",
        `${branch.group_code}:${code}`,
      );
    }
  }
  if (request.stem_flag !== null) params.set("stem", request.stem_flag ? "1" : "0");
  if (request.gpa_tenths !== null) {
    params.set("gpa", (request.gpa_tenths / 10).toFixed(1));
    params.set("gpa_mode", request.gpa_mode);
  }
  if (request.grade_requirement_status === "required") {
    params.set("grade_requirement", "required");
    if (request.overall_gpa_tenths !== null) {
      params.set("overall_gpa", (request.overall_gpa_tenths / 10).toFixed(1));
    }
  }
  if (request.applicant_gpa_tenths !== null) params.set("applicant_gpa", (request.applicant_gpa_tenths / 10).toFixed(1));
  if (request.deadline_on_or_after !== null) params.set("deadline_on_or_after", request.deadline_on_or_after);
  if (request.page > 1) params.set("page", String(request.page));
  return params;
}

export function serializeSearchFormState(
  request: SearchRequest,
  universityQuery: string,
  gpaQuery: string,
  overallGpaQuery: string,
  applicantGpaQuery = "",
  deadlineQuery = "",
): URLSearchParams {
  const params = serializeRequest(request);
  if (universityQuery && request.university[0] !== universityQuery) {
    params.set("university_query", universityQuery);
  }
  const canonicalGpa = request.gpa_tenths === null
    ? ""
    : (request.gpa_tenths / 10).toFixed(1);
  if (gpaQuery && canonicalGpa !== gpaQuery) params.set("gpa_query", gpaQuery);
  const canonicalOverallGpa = request.overall_gpa_tenths === null
    ? ""
    : (request.overall_gpa_tenths / 10).toFixed(1);
  if (overallGpaQuery && canonicalOverallGpa !== overallGpaQuery) {
    params.set("overall_gpa_query", overallGpaQuery);
  }
  const canonicalApplicant = request.applicant_gpa_tenths === null ? "" : (request.applicant_gpa_tenths / 10).toFixed(1);
  if (applicantGpaQuery && canonicalApplicant !== applicantGpaQuery) params.set("applicant_gpa_query", applicantGpaQuery);
  if (deadlineQuery && deadlineQuery !== request.deadline_on_or_after) params.set("deadline_query", deadlineQuery);
  return params;
}
