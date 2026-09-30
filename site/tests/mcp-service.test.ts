import { describe, expect, it } from "vitest";
import { candidateRow } from "./candidate-fixtures";
import { emptyRequest, searchRows } from "../src/search";
import type { DetailRecord, FilterOptions, ProvisionalAdmission, SearchRow, SiteManifest } from "../src/types";
import type { PublicData } from "../mcp/public-data";
import { findAdmissionRows, getAdmission, getResearchRequirements, getSearchFacets, searchAdmissions, searchInputSchema, ServiceError } from "../mcp/service";

const flags = { returnee_flag: false, international_baccalaureate_flag: false,
  private_foreign_student_flag: false, adult_selection_flag: false };
const row = (update: Partial<SearchRow>): SearchRow => candidateRow({
  academic_field_groups: ["engineering"], prefecture_memberships: ["東京都"],
  gpa_parse_status: "not_numeric", grade_requirement_status: "unknown",
  overall_gpa_status: "no_safe_overall_floor", overall_gpa_min_tenths: null,
  overall_gpa_min_inclusive: null, additional_grade_conditions: null,
  special_flags: flags, ...update,
});
const rows: SearchRow[] = [
  row({ record_id: "A", university: "大学A", prefecture: "東京都", prefecture_memberships: ["東京都"],
    academic_field_groups: ["information"], selection_interview: "Yes", selection_oral_exam: "No",
    research_requirement_required: "Yes", exclusive_enrollment_status: "併願可", special_flags: flags,
    grade_requirement_status: "required", overall_gpa_status: "safe_simple_overall", overall_gpa_min_tenths: 35,
    overall_gpa_min_inclusive: true, additional_grade_conditions: false, application_end: "2026-10-10",
    search_text: "大学A JSEC 科学オリンピック" }),
  row({ record_id: "B", university: "大学B", prefecture: "神奈川県", prefecture_memberships: ["神奈川県"],
    academic_field_groups: ["information"], selection_interview: "Yes", selection_oral_exam: "Yes",
    research_requirement_required: "No", exclusive_enrollment_status: "専願", special_flags: flags,
    grade_requirement_status: "required", overall_gpa_status: "safe_simple_overall", overall_gpa_min_tenths: 38,
    overall_gpa_min_inclusive: true, additional_grade_conditions: false, application_end: "2026-10-01" }),
  row({ record_id: "C", university: "大学C", prefecture: "東京都", prefecture_memberships: ["東京都"],
    academic_field_groups: ["engineering"], selection_interview: "No", selection_oral_exam: "Unknown",
    research_requirement_required: "Unknown", special_flags: flags,
    grade_requirement_status: "required", overall_gpa_status: "safe_simple_overall", overall_gpa_min_tenths: 40,
    overall_gpa_min_inclusive: true, additional_grade_conditions: false, application_end: null }),
  row({ record_id: "D", university: "北海道教育大学", prefecture: "北海道", prefecture_memberships: ["北海道"], faculty_school: "教育学部",
    selection_name: "総合型選抜", special_flags: flags, grade_requirement_status: "unknown",
    research_requirement_required: "Unknown", application_end: null }),
];

const pending: ProvisionalAdmission = {
  provisional_id: "PA-1", university: "北海道教育大学", institution_type: "国立",
  faculty_school: "教育学部", selection_name: "学校推薦型選抜（一般・地域指定）",
  selection_family: "recommendation", special_filter_tag: "none", information_year: 2027,
  public_status: "details_pending", known_scope: "実施確認済み", known_detail: "詳細確認中",
  unknown_detail: "出願単位・評定・締切", official_source_url: "https://www.hokkyodai.ac.jp/exam/faculties/exam/download/",
  previous_year_source_url: null, previous_year_detail: null, release_expected_text: null,
  verified_on: "2026-09-29", related_update_queue_id: "UQ-1",
};

const options = {
  universities: ["大学A", "大学B", "大学C", "北海道教育大学"].map((value) => ({ value })),
  institution_types: [{ value: "国立" }],
  prefecture_memberships: ["東京都", "神奈川県", "北海道"].map((value) => ({ value })),
  academic_field_groups: ["information", "engineering"].map((value) => ({ value })),
  raw_academic_fields: [{ value: "工学" }],
  selection_categories: [{ value: "総合型選抜" }],
  exclusive_enrollment_statuses: ["専願", "併願可", "条件付き", "不明"].map((value) => ({ value })),
} as unknown as FilterOptions;

function fixture(overrides: Partial<PublicData> = {}): PublicData {
  return {
    manifest: { build_id: "fixture", counts: { universities: 4 } } as SiteManifest,
    options, rows, provisional: [pending],
    detail: async (recordId) => {
      const row = rows.find((item) => item.record_id === recordId);
      if (!row) return null;
      return { identity: { source_dataset: row.source_dataset, source_version: row.source_version, record_id: row.record_id },
        admission: { record_id: recordId, university: row.university, information_year: 2027, gpa_requirement: "Unknown",
          source_url: "https://example.edu/official", guideline_url: "https://example.edu/guideline",
          exclusive_enrollment_status: row.exclusive_enrollment_status },
        research_requirements: recordId === "A" ? [{ requirement_code: "JSEC", program_or_competition: "JSEC",
          requirement_detail: "応募可", alternative_allowed: "Unknown", source_url: "https://example.edu/research" }] : [],
      } as unknown as DetailRecord;
    },
    addSearchText: async () => undefined,
    ...overrides,
  };
}

const search = (input: Record<string, unknown>, data = fixture()) =>
  searchAdmissions(data, searchInputSchema.parse(input), "https://ea.ussapao.chatgpt.site");

describe("MCP read-only service", () => {
  it("supports Tokyo, Tokyo-or-Kanagawa, information, and AND combinations", async () => {
    expect((await search({ prefectures: ["東京都"] })).results.map((r) => r.record_id)).toEqual(["A", "C"]);
    expect((await search({ prefectures: ["東京都", "神奈川県"] })).total).toBe(3);
    expect((await search({ academic_groups: ["information"] })).results.map((r) => r.record_id).sort()).toEqual(["A", "B"]);
    expect((await search({ prefectures: ["東京都", "神奈川県"], academic_groups: ["information"], applicant_gpa: 3.8, selection_interview: "Yes" })).results.map((r) => r.record_id).sort()).toEqual(["A", "B"]);
  });

  it("reuses applicant GPA, selection flags, research and exclusivity semantics", async () => {
    expect((await search({ applicant_gpa: 3.8 })).results.map((r) => r.record_id).sort()).toEqual(["A", "B", "D"]);
    expect((await search({ selection_interview: "Yes" })).results.map((r) => r.record_id).sort()).toEqual(["A", "B", "D"]);
    expect((await search({ selection_oral_exam: "Yes" })).results.map((r) => r.record_id)).toEqual(["B"]);
    expect((await search({ research_requirement_required: "Yes" })).results.map((r) => r.record_id)).toEqual(["A"]);
    expect((await search({ exclusive_enrollment_statuses: ["併願可"] })).results.map((r) => r.record_id)).toEqual(["A"]);
    expect((await search({ free_text: "JSEC" })).results.map((r) => r.record_id)).toEqual(["A"]);
  });

  it("keeps 0 results normal, paginates, and rejects invalid inputs", async () => {
    expect((await search({ university: "大学A", selection_oral_exam: "Yes" })).total).toBe(0);
    const page = await search({ limit: 1, offset: 1 });
    expect(page.total).toBe(4);
    expect(page.results).toHaveLength(1);
    expect(page.has_more).toBe(true);
    expect(() => searchInputSchema.parse({ selection_interview: "Maybe" })).toThrow();
    expect(() => searchInputSchema.parse({ arbitrary_sql: "SELECT * FROM admissions" })).toThrow();
    await expect(search({ prefectures: ["架空県"] })).rejects.toMatchObject({ code: "invalid_argument" });
    await expect(search({ applicant_gpa: 3.85 })).rejects.toMatchObject({ code: "invalid_argument" });
  });

  it("returns confirmed records and provisional existence separately without treating unknown as No", async () => {
    const result = await search({ university: "北海道教育大学", applicant_gpa: 3.8, application_end_from: "2026-10-01" });
    expect(result.total).toBe(1);
    expect(result.results[0]).toMatchObject({ record_id: "D", applicant_grade_status: "unknown", deadline_filter_status: "unknown" });
    expect(result.provisional_count).toBe(1);
    expect(result.provisional_admissions[0]).toMatchObject({ public_status: "details_pending", condition_match: "undetermined" });
    const duplicate = fixture({ provisional: [{ ...pending, selection_name: "総合型選抜" }] });
    expect((await search({ university: "北海道教育大学" }, duplicate)).provisional_count).toBe(0);
  });

  it("returns published detail, research child rows, facets and official URLs", async () => {
    const data = fixture();
    const admission = await getAdmission(data, "A", "https://ea.ussapao.chatgpt.site");
    expect(admission.sources.source_url).toBe("https://example.edu/official");
    expect(admission.detail_url).toContain("/admissions/");
    expect(admission).toMatchObject({ eligibility: {
      gpa_requirement: "Unknown", school_recommendation_required: null,
    } });
    const research = await getResearchRequirements(data, "A");
    expect(research.requirements).toHaveLength(1);
    expect(research.requirements[0]).toMatchObject({ requirement_code: "JSEC" });
    expect(getSearchFacets(data, "大学A").universities_total).toBe(1);
    expect(getSearchFacets(data, "", "工学").academic_fields.map((item) => item.value)).toEqual(["工学"]);
    expect(getSearchFacets(data).special_filters).toContain("returnee_flag");
    await expect(getAdmission(data, "missing", "https://ea.ussapao.chatgpt.site")).rejects.toBeInstanceOf(ServiceError);
  });

  it("keeps special selections OFF by default and ORs explicitly selected flags", async () => {
    const specialRows = [
      row({ record_id: "N", special_flags: flags }),
      row({ record_id: "R", special_flags: { ...flags, returnee_flag: true } }),
      row({ record_id: "I", special_flags: { ...flags, international_baccalaureate_flag: true } }),
    ];
    const data = fixture({ rows: specialRows, provisional: [] });
    expect((await findAdmissionRows(data, searchInputSchema.parse({}))).matched.rows.map((r) => r.record_id)).toEqual(["N"]);
    expect((await findAdmissionRows(data, searchInputSchema.parse({ special_filters: ["returnee_flag", "international_baccalaureate_flag"] }))).matched.rows.map((r) => r.record_id).sort()).toEqual(["I", "R"]);
  });

  it("returns the same confirmed IDs as the Web search engine for shared conditions", async () => {
    for (const input of [
      { prefectures: ["東京都"] }, { prefectures: ["神奈川県"] }, { academic_groups: ["information"] },
      { academic_groups: ["engineering"] }, { selection_interview: "Yes" as const },
      { selection_oral_exam: "Yes" as const }, { research_requirement_required: "Yes" as const },
      { exclusive_enrollment_statuses: ["専願" as const] }, { applicant_gpa: 3.8 },
      { common_test_required: "No" as const },
    ]) {
      const mcp = await search(input);
      const web = emptyRequest();
      if ("prefectures" in input) web.prefecture_membership = [...input.prefectures!];
      if ("academic_groups" in input) web.academic_field_group = [...input.academic_groups!];
      if ("selection_interview" in input) web.selection_interview = [input.selection_interview!];
      if ("selection_oral_exam" in input) web.selection_oral_exam = [input.selection_oral_exam!];
      if ("research_requirement_required" in input) web.research_requirement_required = [input.research_requirement_required!];
      if ("exclusive_enrollment_statuses" in input) web.exclusive_enrollment_status = [...input.exclusive_enrollment_statuses!];
      if ("applicant_gpa" in input) web.applicant_gpa_tenths = Math.round(input.applicant_gpa! * 10);
      if ("common_test_required" in input) web.common_test_required = [input.common_test_required!];
      expect(mcp.results.map((item) => item.record_id)).toEqual(searchRows(rows, web).rows.map((item) => item.record_id));
    }
  });
});
