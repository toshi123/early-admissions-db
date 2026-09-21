import { describe, expect, it } from "vitest";
import { emptyRequest, gpaStatus, searchRows } from "../src/search";
import type { SearchRow } from "../src/types";

function row(update: Partial<SearchRow> = {}): SearchRow {
  return {
    source_dataset: "fixture", source_version: "1", record_id: "A", institution_type: "国立", university: "大学A",
    prefecture: "東京都", prefecture_raw:"東京都", prefecture_mapping_status:"single", prefecture_memberships:["東京都"], faculty_school: "工学部", department: null, selection_category: "総合型選抜", selection_name: "選抜A",
    slot_type: null, capacity: "2", academic_field: "工学", stem_flag: true, academic_field_mapping_status: "single",
    academic_field_groups: ["engineering"], exclusive_enrollment_status: "専願", school_recommendation_required: "No",
    academic_field_v2_broad_mapping_status: "single", academic_field_v2_subcategory_mapping_status: "single",
    academic_field_v2_broad_memberships: ["engineering"], academic_field_v2_subcategory_memberships: ["mechanical"],
    academic_field_v2_mapping_contract_version: "0.2", academic_field_v2_taxonomy_version: "0.2",
    academic_record_required: "Yes", common_test_required: "No", research_requirement_required: "Unknown",
    research_activity_level_status: null, selection_interview: "Yes", selection_oral_exam: "No", selection_presentation: "Unknown",
    selection_essay: null, selection_written_exam: "No", selection_practical: "No", selection_group_discussion: "No",
    selection_aptitude_test: "No", selection_common_test: "No", gpa_requirement: "3.8以上",
    gpa_parse_status: "parsed_safe", gpa_search_disposition: "safe_numeric", gpa_min_tenths: 38, gpa_min_inclusive: true,
    gpa_max_tenths: null, gpa_max_inclusive: null, gpa_source_value_status: "current", application_start: null, application_end: null,
    grade_requirement_status: "required", overall_gpa_min_tenths: 38,
    overall_gpa_min_inclusive: true, overall_gpa_status: "safe_simple_overall",
    additional_grade_conditions: false,
    english_requirement: "英検準1級以上", english_requirement_status: "required", english_requirement_parse_status: "exact_crosswalk", english_requirement_search_disposition: "safe_exact",
    fallback_previous_year: false, information_year: 2027, publication_status: null, detail_path: "details.json", ...update,
  };
}

describe("frozen frontend search semantics", () => {
  it("uses OR within one field and AND between fields", () => {
    const request = emptyRequest(); request.prefecture = ["東京都", "神奈川県"]; request.university = ["大学A"];
    const result = searchRows([row(), row({ record_id: "B", prefecture: "神奈川県", university: "大学B" }), row({ record_id: "C", prefecture: "大阪府" })], request);
    expect(result.rows.map((item) => item.record_id)).toEqual(["A"]);
  });

  it("keeps academic broad-group membership as OR", () => {
    const request = emptyRequest(); request.academic_field_group = ["information", "medicine"];
    const result = searchRows([row({ academic_field_groups: ["engineering", "information"] }), row({ record_id: "B", academic_field_groups: ["humanities"] })], request);
    expect(result.rows.map((item) => item.record_id)).toEqual(["A"]);
  });

  it("keeps v0.2 subcategories OR within a Broad branch and Broad branches OR", () => {
    const rows = [
      row(),
      row({ record_id: "P", academic_field_v2_broad_memberships: ["natural_sciences"], academic_field_v2_subcategory_memberships: ["physics"] }),
      row({ record_id: "C", academic_field_v2_broad_memberships: ["natural_sciences"], academic_field_v2_subcategory_memberships: ["chemistry"] }),
    ];
    const request = emptyRequest();
    request.academic_field_v2_branches = [
      { group_code: "natural_sciences", subcategory_codes: ["mathematics_statistics", "physics"] },
      { group_code: "engineering", subcategory_codes: [] },
    ];
    expect(searchRows(rows, request).rows.map((item) => item.record_id)).toEqual(["A", "P"]);
  });

  it("ANDs legacy v0.1 and v0.2 academic-field filters", () => {
    const request = emptyRequest();
    request.academic_field_group = ["engineering"];
    request.academic_field_v2_branches = [{ group_code: "engineering", subcategory_codes: [] }];
    const legacyOnly = row({ record_id: "B", academic_field_v2_broad_memberships: ["natural_sciences"] });
    expect(searchRows([row(), legacyOnly], request).rows.map((item) => item.record_id)).toEqual(["A"]);
  });

  it("fails closed for GPA safe, review, and all", () => {
    const rows = [row(), row({ record_id: "B", gpa_parse_status: "conditional_review", gpa_min_tenths: null, gpa_min_inclusive: null }), row({ record_id: "C", gpa_parse_status: "not_numeric", gpa_min_tenths: null, gpa_min_inclusive: null })];
    const request = emptyRequest(); request.gpa_tenths = 38;
    request.gpa_mode = "safe"; expect(searchRows(rows, request).rows.map((item) => item.record_id)).toEqual(["A"]);
    request.gpa_mode = "review"; expect(searchRows(rows, request).rows.map((item) => item.record_id).sort()).toEqual(["A", "B"]);
    request.gpa_mode = "all"; expect(searchRows(rows, request).summary.gpa_not_numerically_evaluable_rows).toBe(1);
  });

  it("distinguishes safe threshold boundaries", () => {
    expect(gpaStatus(row(), 37)).toBe("safe no match");
    expect(gpaStatus(row(), 38)).toBe("safe match");
  });

  it("separates grade requirement membership from reviewed overall GPA filtering", () => {
    const subjectOnly = row({
      record_id: "SUBJECT", overall_gpa_min_tenths: null,
      overall_gpa_min_inclusive: null, overall_gpa_status: "no_safe_overall_floor",
      additional_grade_conditions: null,
    });
    const noRequirement = row({ record_id: "NONE", grade_requirement_status: "not_required" });
    const checkbox = emptyRequest(); checkbox.grade_requirement_status = "required";
    expect(searchRows([row(), subjectOnly, noRequirement], checkbox).rows.map((item) => item.record_id)).toEqual(["A", "SUBJECT"]);
    checkbox.overall_gpa_tenths = 38;
    expect(searchRows([row(), subjectOnly, noRequirement], checkbox).rows.map((item) => item.record_id)).toEqual(["A"]);
  });

  it("filters English requirements only by safe derived status", () => {
    const request = emptyRequest(); request.english_requirement_status = ["required"];
    const unsafe = row({record_id:"B", english_requirement_status:"review_required", english_requirement_search_disposition:"review_required"});
    expect(searchRows([row(), unsafe], request).rows.map(item=>item.record_id)).toEqual(["A"]);
  });
  it("uses derived prefecture membership without changing raw exact semantics",()=>{
    const composite=row({record_id:"B",prefecture:"東京都・埼玉県",prefecture_raw:"東京都・埼玉県",prefecture_mapping_status:"multi",prefecture_memberships:["東京都","埼玉県"]});
    const derived=emptyRequest();derived.prefecture_membership=["東京都"];
    expect(searchRows([row(),composite],derived).rows.map(x=>x.record_id)).toEqual(["A","B"]);
    const raw=emptyRequest();raw.prefecture=["東京都"];
    expect(searchRows([row(),composite],raw).rows.map(x=>x.record_id)).toEqual(["A"]);
  });
});
