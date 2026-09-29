import { describe, expect, it } from "vitest";
import { candidateRow } from "./candidate-fixtures";
import { discoverProvisional, provisionalCard } from "../src/public-discovery";
import { applicantGradeStatus, deadlineStatus, emptyRequest, searchRows } from "../src/search";
import { groupPublicAdmissionsByUniversity, publicUniversityGroupMarkup } from "../src/university-groups";
import type { ProvisionalAdmission, SearchRow, SpecialSelectionFlags } from "../src/types";

const noFlags: SpecialSelectionFlags = {
  returnee_flag: false, international_baccalaureate_flag: false,
  private_foreign_student_flag: false, adult_selection_flag: false,
};
const confirmed = (id: string, update: Partial<SearchRow> = {}): SearchRow => candidateRow({
  record_id: id, university: "北海道教育大学", faculty_school: "教育学部",
  selection_category: "総合型選抜", selection_name: `選抜${id}`,
  application_end: "2026-10-01", grade_requirement_status: "required",
  overall_gpa_status: "safe_simple_overall", overall_gpa_min_tenths: 35,
  overall_gpa_min_inclusive: true, additional_grade_conditions: false,
  special_flags: noFlags, ...update,
});
const pending: ProvisionalAdmission = {
  provisional_id: "PA-2027-0001", university: "北海道教育大学", institution_type: "国立",
  faculty_school: "教育学部", selection_name: "学校推薦型選抜（一般・地域指定）",
  selection_family: "recommendation", special_filter_tag: "none", information_year: 2027,
  public_status: "details_pending", known_scope: "2027年度実施確認済み", known_detail: "大学公式要項",
  unknown_detail: "actual application unit、評定、出願締切", official_source_url: "https://www.hokkyodai.ac.jp/exam/faculties/exam/download/",
  previous_year_source_url: "https://www.hokkyodai.ac.jp/exam/faculties/exam/download/kako.html",
  previous_year_detail: "2026年度の参考資料", release_expected_text: null,
  verified_on: "2026-09-28", related_update_queue_id: "UQ-2027-0046",
};

describe("public search policy", () => {
  it("shows Hokkaido's six confirmed units and one pending admission in one university list", () => {
    const request = emptyRequest(); request.university = ["北海道教育大学"];
    const rows = Array.from({ length: 6 }, (_, i) => confirmed(String(i)));
    const regular = searchRows(rows, request);
    const provisional = discoverProvisional([pending], request, rows);
    const groups = groupPublicAdmissionsByUniversity(regular.rows, provisional);
    expect(regular.summary.total_matched_rows).toBe(6);
    expect(provisional).toHaveLength(1);
    expect(groups).toHaveLength(1);
    expect(groups[0].admissions).toHaveLength(6);
    expect(groups[0].provisional).toHaveLength(1);
    const html = publicUniversityGroupMarkup(groups[0], 0, true, request);
    expect((html.match(/<article class="result-card/g) ?? []).length).toBe(7);
    expect(html).toContain("2027年度実施確認済み・詳細確認中");
    expect(html).toContain("2027年度大学公式情報");
    expect(html).toContain("前年実績（2026年度）");
  });

  it("suppresses a provisional record once the actual unit is confirmed", () => {
    const request = emptyRequest();
    const promoted = confirmed("PROMOTED", { selection_name: pending.selection_name,
      selection_category: "学校推薦型選抜" });
    expect(discoverProvisional([pending], request, [promoted])).toHaveLength(0);
  });

  it("defaults to recommendation and comprehensive while excluding the four flagged special types", () => {
    const request = emptyRequest();
    expect(request.selection_families).toEqual(["recommendation", "comprehensive"]);
    expect(request.special_filters).toEqual([]);
    const rows = [confirmed("R", { selection_category: "学校推薦型選抜" }), confirmed("C"),
      confirmed("IB", { special_flags: { ...noFlags, international_baccalaureate_flag: true } })];
    expect(searchRows(rows, request).rows.map((r) => r.record_id)).toEqual(["R", "C"]);
    request.selection_families = ["recommendation"];
    expect(searchRows(rows, request).rows.map((r) => r.record_id)).toEqual(["R"]);
    request.selection_families = [];
    expect(() => searchRows(rows, request)).toThrow("少なくとも1つ");
    request.special_filters = ["returnee_flag", "international_baccalaureate_flag"];
    expect(searchRows(rows, request).rows.map((r) => r.record_id)).toEqual(["IB"]);
  });

  it("keeps unknown deadline rows and pending admissions while excluding known earlier deadlines", () => {
    const request = emptyRequest(); request.deadline_on_or_after = "2026-10-01";
    const rows = [confirmed("BEFORE", { application_end: "2026-09-30" }),
      confirmed("SAME"), confirmed("AFTER", { application_end: "2026-10-02" }),
      confirmed("UNKNOWN", { application_end: null }),
      confirmed("TEXT", { application_end: "10月1日" })];
    const result = searchRows(rows, request);
    expect(result.rows.map((r) => r.record_id).sort()).toEqual(["AFTER", "SAME", "TEXT", "UNKNOWN"]);
    expect(result.rows.filter((r) => r.deadline_filter_status === "unknown")).toHaveLength(2);
    expect(discoverProvisional([pending], request, rows)).toHaveLength(1);
    expect(provisionalCard(pending, true, request)).toContain("出願締切を確認できていません");
    expect(deadlineStatus(rows[0], request.deadline_on_or_after)).toBe("exclude");
  });

  it("matches applicant grade 3.8 against 3.5 and 3.8, keeps no requirement and undecidable", () => {
    const request = emptyRequest(); request.applicant_gpa_tenths = 38;
    const rows = [confirmed("35"), confirmed("38", { overall_gpa_min_tenths: 38 }),
      confirmed("40", { overall_gpa_min_tenths: 40 }),
      confirmed("NONE", { grade_requirement_status: "not_required", overall_gpa_min_tenths: null }),
      confirmed("UNKNOWN", { grade_requirement_status: "unknown", overall_gpa_min_tenths: null }),
      confirmed("SUBJECT", { overall_gpa_status: "no_safe_overall_floor", overall_gpa_min_tenths: null }),
      confirmed("ADDITIONAL", { overall_gpa_status: "safe_overall_with_additional_conditions", additional_grade_conditions: true })];
    const result = searchRows(rows, request);
    expect(result.rows.map((r) => r.record_id).sort()).toEqual(["35", "38", "ADDITIONAL", "NONE", "SUBJECT", "UNKNOWN"].sort());
    expect(result.rows.filter((r) => r.applicant_grade_status === "unknown")).toHaveLength(3);
    expect(applicantGradeStatus(rows[2], 38)).toBe("exclude");
    expect(discoverProvisional([pending], request, rows)).toHaveLength(1);
    expect(provisionalCard(pending, true, request)).toContain("評定条件を数値だけで判定できません");
  });
});
