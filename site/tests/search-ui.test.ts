import { describe, expect, it, vi } from "vitest";
import { submitSearchNavigation } from "../src/navigation";
import { emptyRequest } from "../src/search";
import {
  applicationConditionLabels,
  compactResultCard,
  exclusiveEnrollmentLabel,
  evaluateSearchDraft,
  liveSearchResult,
  liveSummaryPresentation,
  selectionMethodLabels,
  universitySuggestions,
} from "../src/search-ui";
import type { FilterOptions, SearchRow } from "../src/types";

const options = {
  universities: [
    { value: "東京大学", display_label: "東京大学", unfiltered_count: 2 },
    { value: "東京都市大学", display_label: "東京都市大学", unfiltered_count: 1 },
    { value: "京都大学", display_label: "京都大学", unfiltered_count: 1 },
  ],
} as FilterOptions;

function row(update: Partial<SearchRow> = {}): SearchRow {
  return {
    source_dataset: "fixture", source_version: "1", record_id: "A", institution_type: "国立", university: "東京大学",
    prefecture: "東京都", prefecture_raw: "東京都", prefecture_mapping_status: "single", prefecture_memberships: ["東京都"],
    faculty_school: "工学部", department: "情報工学科", selection_category: "総合型選抜", selection_name: "特別選抜",
    slot_type: null, capacity: "2", academic_field: "工学", stem_flag: true, academic_field_mapping_status: "single",
    academic_field_groups: ["engineering"], exclusive_enrollment_status: "専願", school_recommendation_required: "No",
    academic_field_v2_broad_mapping_status: "single", academic_field_v2_subcategory_mapping_status: "single",
    academic_field_v2_broad_memberships: ["engineering"], academic_field_v2_subcategory_memberships: ["mechanical"],
    academic_field_v2_mapping_contract_version: "0.2", academic_field_v2_taxonomy_version: "0.2",
    academic_record_required: "Yes", common_test_required: "No", research_requirement_required: "No", research_activity_level_status: null,
    selection_interview: "Yes", selection_oral_exam: "Yes", selection_presentation: "Yes", selection_essay: "Yes",
    selection_written_exam: "Yes", selection_practical: "Yes", selection_group_discussion: "Yes", selection_aptitude_test: "Yes",
    selection_common_test: "Yes", gpa_requirement: "3.8以上", english_requirement: null,
    english_requirement_status: "not_applicable", english_requirement_parse_status: "missing", english_requirement_search_disposition: "not_searchable",
    gpa_parse_status: "parsed_safe", gpa_search_disposition: "safe_numeric", gpa_min_tenths: 38, gpa_min_inclusive: true,
    gpa_max_tenths: null, gpa_max_inclusive: null, gpa_source_value_status: "current", application_start: "9月1日", application_end: "9月5日",
    grade_requirement_status: "required", overall_gpa_min_tenths: 38,
    overall_gpa_min_inclusive: true, overall_gpa_status: "safe_simple_overall",
    additional_grade_conditions: false,
    fallback_previous_year: false, information_year: 2027, publication_status: null, detail_path: "details.json", ...update,
  };
}

describe("search form live behavior", () => {
  it("filters autocomplete suggestions by substring but applies only an exact university", () => {
    expect(universitySuggestions(options, "東京")).toEqual(["東京大学", "東京都市大学"]);
    const partial = evaluateSearchDraft(emptyRequest(), options, "東京", "");
    expect(partial.request.university).toEqual([]);
    expect(partial.errors).toEqual(["大学名は候補から1校選んでください。"]);
    const exact = evaluateSearchDraft(emptyRequest(), options, "東京大学", "");
    expect(exact.request.university).toEqual(["東京大学"]);
    expect(exact.errors).toEqual([]);
  });

  it("holds an invalid intermediate overall GPA without running a misleading count", () => {
    const request = emptyRequest(); request.grade_requirement_status = "required";
    const draft = evaluateSearchDraft(request, options, "", "3.");
    expect(draft.request.overall_gpa_tenths).toBeNull();
    expect(liveSearchResult([row()], draft)).toBeNull();
  });

  it("uses the same search result for live count and submitted results", () => {
    const rows = [row(), row({ record_id: "B", university: "京都大学" })];
    const request = emptyRequest(); request.grade_requirement_status = "required";
    const draft = evaluateSearchDraft(request, options, "東京大学", "3.8");
    const live = liveSearchResult(rows, draft)!;
    expect(live.summary.total_matched_rows).toBe(1);
    expect(live.rows.map((item) => item.record_id)).toEqual(["A"]);
    expect(liveSummaryPresentation(live)).toEqual({
      liveText: "該当 1件・1大学",
      floatingText: "1件・1大学",
      invalid: false,
    });
  });

  it("updates live counts for checkbox-only and reviewed numeric grade searches", () => {
    const rows = [
      row(),
      row({
        record_id: "SUBJECT", overall_gpa_min_tenths: null,
        overall_gpa_min_inclusive: null, overall_gpa_status: "no_safe_overall_floor",
        additional_grade_conditions: null,
      }),
      row({ record_id: "NONE", grade_requirement_status: "not_required" }),
    ];
    const request = emptyRequest(); request.grade_requirement_status = "required";
    const checkboxDraft = evaluateSearchDraft(request, options, "", "");
    expect(liveSearchResult(rows, checkboxDraft)?.summary.total_matched_rows).toBe(2);
    const numericDraft = evaluateSearchDraft(request, options, "", "3.8");
    expect(liveSearchResult(rows, numericDraft)?.summary.total_matched_rows).toBe(1);
  });

  it("does not expose a stale floating count for invalid drafts", () => {
    expect(liveSummaryPresentation(null)).toEqual({
      liveText: "入力を確認すると該当件数を表示します",
      floatingText: "条件を確認してください",
      invalid: true,
    });
  });
});

describe("compact result cards", () => {
  it("shows all positive selection-method labels and only the compact counseling fields", () => {
    expect(selectionMethodLabels(row())).toEqual([
      "面接", "口頭試問", "プレゼン", "小論文", "筆記", "実技", "グループ討論", "適性検査", "共通テスト",
    ]);
    const html = compactResultCard(row({ gpa_derived_status: "safe match", fallback_previous_year: true }), true);
    expect(html).toContain("評定：安全照合一致");
    expect(html).toContain("前年度情報");
    expect(html).not.toContain("募集人数");
    expect(html).not.toContain("評定条件（原文）");
    expect(html).not.toContain("出願期間");
    expect(html).toContain("専願");

    const groupedHtml = compactResultCard(row(), false, false);
    expect(groupedHtml).not.toContain("東京大学");
    expect(groupedHtml).toContain('class="admission-detail-link"');
    expect(groupedHtml).toContain("特別選抜");
  });

  it.each([
    ["required", true],
    ["not_required", false],
    ["review_required", false],
    ["unknown", false],
    ["unmapped", false],
    ["not_applicable", false],
  ] as const)("shows the English condition badge only for %s", (status, expected) => {
    const html = compactResultCard(row({ english_requirement_status: status }), false, false);
    expect(html.includes("条件：英語資格")).toBe(expected);
  });

  it.each([
    ["Yes", true],
    ["No", false],
    ["Unknown", false],
    [null, false],
  ] as const)("shows the research condition badge only for %s", (status, expected) => {
    const html = compactResultCard(row({ research_requirement_required: status }), false, false);
    expect(html.includes("条件：研究業績")).toBe(expected);
  });

  it("keeps methods, conditions, and exclusive status distinct within one chip row", () => {
    const fixture = row({ english_requirement_status: "required", research_requirement_required: "Yes" });
    expect(applicationConditionLabels(fixture)).toEqual(["評定", "英語資格", "研究業績"]);
    const html = compactResultCard(fixture, false, false);
    expect(html).toContain('class="result-chips" aria-label="選考方法・出願条件・専願併願"');
    expect(html).toContain('class="result-chip method-chip" aria-label="選考方法 面接"');
    expect(html).toContain('class="result-chip condition-chip" aria-label="出願条件 英語資格">条件：英語資格');
    expect(html).toContain('class="result-chip condition-chip" aria-label="出願条件 評定">評定');
    expect(html).toContain('class="result-chip condition-chip" aria-label="出願条件 研究業績">条件：研究業績');
    expect(html).toContain('class="result-chip exclusive-chip" aria-label="専願・併願 専願">専願');
    expect(html.indexOf("method-chip")).toBeLessThan(html.indexOf("condition-chip"));
    expect(html.indexOf("condition-chip")).toBeLessThan(html.indexOf("exclusive-chip"));
  });

  it("shows the grade chip only for reviewed required rows", () => {
    expect(compactResultCard(row(), false, false)).toContain('aria-label="出願条件 評定">評定');
    for (const status of ["not_required", "review_required", "unknown", "unmapped", "not_applicable"] as const) {
      expect(compactResultCard(row({ grade_requirement_status: status }), false, false)).not.toContain("出願条件 評定");
    }
  });

  it.each([
    ["専願", "専願"],
    ["併願可", "併願可"],
    ["条件付き", "条件付き"],
    ["不明", "不明"],
    [null, null],
    ["unexpected", null],
  ] as const)("maps exclusive enrollment status %s without strengthening its meaning", (value, expected) => {
    expect(exclusiveEnrollmentLabel(value)).toBe(expected);
    const html = compactResultCard(row({ exclusive_enrollment_status: value }), false, false);
    expect(html.includes('class="result-chip exclusive-chip"')).toBe(expected !== null);
  });

  it("keeps the candidate control beside the unified wrapping chip row", () => {
    document.body.innerHTML = compactResultCard(row(), false, false);
    const utility = document.querySelector(".result-card__utility")!;
    expect(utility.querySelector(".result-chips")).not.toBeNull();
    expect(utility.querySelector("button.candidate-toggle")).not.toBeNull();
  });
});

describe("search submission navigation", () => {
  it("renders the new results route and then scrolls to the top", async () => {
    const pushState = vi.fn();
    const render = vi.fn(async () => undefined);
    const scrollTo = vi.fn();
    const request = emptyRequest();
    request.prefecture_membership = ["東京都"];
    await submitSearchNavigation(request, { pushState, render, scrollTo });
    expect(pushState).toHaveBeenCalledWith(
      { transition: "search-submit" },
      "",
      "/results?prefecture_membership=%E6%9D%B1%E4%BA%AC%E9%83%BD",
    );
    expect(render).toHaveBeenCalledBefore(scrollTo);
    expect(scrollTo).toHaveBeenCalledWith({ top: 0, left: 0, behavior: "auto" });
  });
});
