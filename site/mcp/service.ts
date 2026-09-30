import { z } from "zod";
import { detailLink } from "../src/display";
import { discoverProvisional, hasUnverifiedFilters } from "../src/public-discovery";
import { emptyRequest, searchRows, validIsoDate } from "../src/search";
import type { DetailRecord, FilterOptions, SearchRequest, SearchRow } from "../src/types";
import type { PublicData } from "./public-data";

const yesNo = z.enum(["Yes", "No"]);
const shortString = z.string().min(1).max(120);
const stringList = z.array(shortString).max(30);

export const searchInputSchema = z.object({
  university: shortString.optional(),
  institution_types: stringList.optional(),
  prefectures: stringList.optional(),
  academic_groups: stringList.optional(),
  academic_fields: stringList.optional(),
  selection_categories: stringList.optional(),
  selection_families: z.array(z.enum(["recommendation", "comprehensive"])).max(2).optional(),
  special_filters: z.array(z.enum(["returnee_flag", "international_baccalaureate_flag", "private_foreign_student_flag", "adult_selection_flag"])).max(4).optional(),
  applicant_gpa: z.number().min(0).max(5).optional(),
  exclusive_enrollment_statuses: z.array(z.enum(["専願", "併願可", "条件付き", "不明"])).max(4).optional(),
  school_recommendation_required: yesNo.optional(),
  research_requirement_required: yesNo.optional(),
  selection_interview: yesNo.optional(),
  selection_oral_exam: yesNo.optional(),
  selection_presentation: yesNo.optional(),
  selection_essay: yesNo.optional(),
  selection_written_exam: yesNo.optional(),
  common_test_required: z.enum(["Yes", "No", "Conditional"]).optional(),
  application_end_from: z.string().optional(),
  free_text: z.string().trim().min(1).max(80).optional(),
  limit: z.number().int().min(1).max(100).optional(),
  offset: z.number().int().min(0).max(10000).optional(),
}).strict();

export type SearchInput = z.infer<typeof searchInputSchema>;
export class ServiceError extends Error {
  constructor(public code: "invalid_argument" | "record_not_found" | "database_unavailable" | "internal_error", message: string) { super(message); }
}

function allowed(values: string[] | undefined, options: Array<{ value: string | null }>, label: string): string[] {
  const allowedValues = new Set(options.map((item) => item.value));
  const requested = [...new Set(values ?? [])];
  const unknown = requested.find((value) => !allowedValues.has(value));
  if (unknown) throw new ServiceError("invalid_argument", `${label} に未登録の値があります: ${unknown}`);
  return requested;
}

function toRequest(input: SearchInput, options: FilterOptions): SearchRequest {
  const request = emptyRequest();
  request.university = allowed(input.university ? [input.university] : [], options.universities, "university");
  request.institution_type = allowed(input.institution_types, options.institution_types, "institution_types");
  request.prefecture_membership = allowed(input.prefectures, options.prefecture_memberships, "prefectures");
  request.academic_field_group = allowed(input.academic_groups, options.academic_field_groups, "academic_groups");
  request.academic_field = allowed(input.academic_fields, options.raw_academic_fields, "academic_fields");
  request.selection_category = allowed(input.selection_categories, options.selection_categories, "selection_categories");
  request.exclusive_enrollment_status = allowed(input.exclusive_enrollment_statuses, options.exclusive_enrollment_statuses, "exclusive_enrollment_statuses");
  if (input.selection_families) request.selection_families = [...new Set(input.selection_families)];
  if (input.special_filters) request.special_filters = [...new Set(input.special_filters)];
  for (const field of ["school_recommendation_required", "research_requirement_required", "selection_interview",
    "selection_oral_exam", "selection_presentation", "selection_essay", "selection_written_exam", "common_test_required"] as const) {
    if (input[field]) request[field] = [input[field]];
  }
  if (input.applicant_gpa !== undefined) {
    const tenths = Math.round(input.applicant_gpa * 10);
    if (Math.abs(input.applicant_gpa * 10 - tenths) > 1e-8) throw new ServiceError("invalid_argument", "applicant_gpa は小数第1位まで指定してください");
    request.applicant_gpa_tenths = tenths;
  }
  if (input.application_end_from) {
    if (!validIsoDate(input.application_end_from)) throw new ServiceError("invalid_argument", "application_end_from は有効なYYYY-MM-DDで指定してください");
    request.deadline_on_or_after = input.application_end_from;
  }
  request.free_text = input.free_text ?? null;
  return request;
}

function officialUrl(value: unknown): string | null {
  if (typeof value !== "string" || !value) return null;
  try { const url = new URL(value); return url.protocol === "https:" || url.protocol === "http:" ? url.href : null; }
  catch { return null; }
}

function detailUrl(row: SearchRow, baseUrl: string): string {
  return new URL(detailLink(row.source_dataset, row.source_version, row.record_id), baseUrl).href;
}

function resultRow(row: SearchRow, detail: DetailRecord, baseUrl: string) {
  const admission = detail.admission;
  return {
    record_id: row.record_id, university: row.university, institution_type: row.institution_type,
    prefecture: row.prefecture, faculty_school: row.faculty_school, department: row.department,
    selection_category: row.selection_category, selection_name: row.selection_name, slot_type: row.slot_type,
    academic_field: row.academic_field, academic_groups: row.academic_field_groups,
    gpa_requirement: row.gpa_requirement, applicant_grade_status: row.applicant_grade_status ?? null,
    exclusive_enrollment_status: row.exclusive_enrollment_status,
    research_requirement_required: row.research_requirement_required,
    selection_interview: row.selection_interview, selection_oral_exam: row.selection_oral_exam,
    selection_presentation: row.selection_presentation, selection_essay: row.selection_essay,
    selection_written_exam: row.selection_written_exam, common_test_required: row.common_test_required,
    application_start: row.application_start, application_end: row.application_end,
    deadline_filter_status: row.deadline_filter_status ?? null,
    information_year: row.information_year, publication_status: row.publication_status,
    fallback_previous_year: row.fallback_previous_year,
    detail_url: detailUrl(row, baseUrl), source_url: officialUrl(admission.source_url),
    guideline_url: officialUrl(admission.guideline_url), schedule_url: officialUrl(admission.schedule_url),
    previous_year_source_url: officialUrl(admission.previous_year_source_url),
    previous_year_source_reference: admission.previous_year_source_url && !officialUrl(admission.previous_year_source_url)
      ? admission.previous_year_source_url : null,
  };
}

export async function findAdmissionRows(data: PublicData, input: SearchInput) {
  const request = toRequest(input, data.options);
  if (request.free_text) await data.addSearchText();
  let matched: ReturnType<typeof searchRows>;
  try { matched = searchRows(data.rows, request); }
  catch (error) { throw new ServiceError("invalid_argument", error instanceof Error ? error.message : "検索条件が不正です"); }
  return { request, matched };
}

export async function searchAdmissions(data: PublicData, input: SearchInput, baseUrl: string) {
  const { request, matched } = await findAdmissionRows(data, input);
  const limit = input.limit ?? 20;
  const offset = input.offset ?? 0;
  const page = matched.rows.slice(offset, offset + limit);
  const results = await Promise.all(page.map(async (row) => {
    const detail = await data.detail(row.record_id);
    if (!detail) throw new ServiceError("database_unavailable", `公開詳細データが見つかりません: ${row.record_id}`);
    return resultRow(row, detail, baseUrl);
  }));
  const provisional = discoverProvisional(data.provisional, request, data.rows).map((record) => ({
    provisional_id: record.provisional_id, university: record.university,
    faculty_school: record.faculty_school, selection_name: record.selection_name,
    public_status: record.public_status, information_year: record.information_year,
    condition_match: hasUnverifiedFilters(request) || request.free_text ? "undetermined" : "identity_only",
    known_scope: record.known_scope, unknown_detail: record.unknown_detail,
    official_source_url: officialUrl(record.official_source_url),
    previous_year_source_url: officialUrl(record.previous_year_source_url),
    release_expected_text: record.release_expected_text,
  }));
  return {
    total: matched.rows.length, limit, offset, has_more: offset + results.length < matched.rows.length,
    results, provisional_count: provisional.length, provisional_admissions: provisional,
    note: "results はactual application unit確定済みのMaster行です。provisional_admissionsは募集単位・詳細未確定の存在確認情報であり、totalには含めません。UnknownはNoではありません。",
  };
}

const ADMISSION_FIELDS = {
  identity: ["record_id", "source_dataset", "source_version", "university", "institution_type", "prefecture", "faculty_school", "department", "selection_category", "selection_name", "slot_type", "capacity"],
  eligibility: ["eligibility_graduation", "gpa_requirement", "english_requirement", "subject_prerequisites", "school_recommendation_required", "school_nomination_limit", "school_nomination_limit_total", "school_nomination_limit_rule", "exclusive_enrollment_status", "exclusive_enrollment"],
  research: ["research_requirement_required", "research_activity_level_status", "research_activity_detail", "research_requirement_summary"],
  documents: ["academic_record_required", "academic_record_type", "academic_record_detail", "documents_summary"],
  selection: ["selection_process", "selection_interview", "selection_oral_exam", "selection_presentation", "selection_essay", "selection_written_exam", "selection_practical", "selection_group_discussion", "selection_aptitude_test", "selection_common_test", "selection_document_review", "common_test_required", "common_test_usage", "interview_detail", "oral_exam_subjects", "oral_exam_detail", "presentation_detail", "essay_detail", "written_exam_detail", "selection_method_detail"],
  schedule: ["application_start", "application_end", "web_registration_period", "first_stage_result_date", "second_stage_start", "second_stage_end", "final_result_date"],
  publication: ["information_year", "publication_status", "fallback_previous_year", "fallback_note", "current_year_release_expected", "source_status", "verification_grade", "verified_on"],
  special_selection_flags: ["international_baccalaureate_flag", "private_foreign_student_flag", "returnee_flag", "regional_quota_flag", "adult_selection_flag"],
} as const;

function pick(source: Record<string, unknown>, fields: readonly string[]): Record<string, unknown> {
  return Object.fromEntries(fields.map((field) => [field, source[field] ?? null]));
}

export async function getAdmission(data: PublicData, recordId: string, baseUrl: string) {
  const row = data.rows.find((item) => item.record_id === recordId);
  if (!row) throw new ServiceError("record_not_found", `record_id が見つかりません: ${recordId}`);
  const detail = await data.detail(recordId);
  if (!detail) throw new ServiceError("database_unavailable", `公開詳細データが見つかりません: ${recordId}`);
  const admission = detail.admission;
  return {
    ...Object.fromEntries(Object.entries(ADMISSION_FIELDS).map(([group, fields]) => [group, pick(admission, fields)])),
    evidence: pick(admission, ["exclusive_enrollment_evidence", "exclusive_enrollment_evidence_page"]),
    sources: {
      source_url: officialUrl(admission.source_url), guideline_url: officialUrl(admission.guideline_url),
      schedule_url: officialUrl(admission.schedule_url),
      exclusive_enrollment_evidence_url: officialUrl(admission.exclusive_enrollment_evidence_url),
      previous_year_source_url: officialUrl(admission.previous_year_source_url),
      previous_year_source_reference: admission.previous_year_source_url && !officialUrl(admission.previous_year_source_url)
        ? admission.previous_year_source_url : null,
    },
    detail_url: detailUrl(row, baseUrl),
  };
}

export async function getResearchRequirements(data: PublicData, recordId: string) {
  if (!data.rows.some((row) => row.record_id === recordId)) throw new ServiceError("record_not_found", `record_id が見つかりません: ${recordId}`);
  const detail = await data.detail(recordId);
  if (!detail) throw new ServiceError("database_unavailable", `公開詳細データが見つかりません: ${recordId}`);
  return {
    record_id: recordId,
    requirements: detail.research_requirements.map((row) => ({
      ...pick(row, ["requirement_code", "program_or_competition", "required_level", "requirement_detail", "alternative_allowed", "evidence_required", "verified_on"]),
      source_url: officialUrl(row.source_url),
    })),
  };
}

export function getSearchFacets(data: PublicData, universityQuery = "", academicFieldQuery = "") {
  const query = universityQuery.trim().toLocaleLowerCase("ja-JP");
  const fieldQuery = academicFieldQuery.trim().toLocaleLowerCase("ja-JP");
  if (query.length > 80 || fieldQuery.length > 80) throw new ServiceError("invalid_argument", "検索語は80文字以内にしてください");
  const values = data.options.universities.filter((item) => item.value?.toLocaleLowerCase("ja-JP").includes(query));
  const fields = data.options.raw_academic_fields.filter((item) => item.value?.toLocaleLowerCase("ja-JP").includes(fieldQuery));
  return {
    data_summary: { build_id: data.manifest.build_id, confirmed_rows: data.rows.length,
      provisional_rows: data.provisional.length, universities: data.manifest.counts.universities },
    institution_types: data.options.institution_types, prefectures: data.options.prefecture_memberships,
    academic_groups: data.options.academic_field_groups, selection_categories: data.options.selection_categories,
    academic_fields: fields.slice(0, 50), academic_fields_total: fields.length,
    exclusive_enrollment_statuses: data.options.exclusive_enrollment_statuses,
    selection_families: ["recommendation", "comprehensive"],
    special_filters: ["returnee_flag", "international_baccalaureate_flag", "private_foreign_student_flag", "adult_selection_flag"],
    available_flags: ["school_recommendation_required", "research_requirement_required", "selection_interview",
      "selection_oral_exam", "selection_presentation", "selection_essay", "selection_written_exam",
      "common_test_required"],
    universities: values.slice(0, 50), universities_total: values.length,
    note: "大学名と学問分野原文は完全一致で検索します。各候補は最大50件です。学問分野は既存taxonomyのacademic_groupsも利用できます。",
  };
}
