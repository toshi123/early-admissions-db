import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { detailLink, displayValue, gpaLabel, stateClass, triStateLabel } from "../src/display";
import { parseSearchParams, serializeRequest, serializeSearchFormState } from "../src/url-state";
import type { FilterOptions } from "../src/types";

const dataRoot = process.env.SITE_DATA_DIR ?? join(process.cwd(), "public/site-data");
const manifest = JSON.parse(readFileSync(join(dataRoot, "build_manifest.json"), "utf8")) as {build_id:string};
const options = JSON.parse(readFileSync(join(dataRoot, `assets/${manifest.build_id}/filter_options.json`), "utf8")) as FilterOptions;

describe("URL state and explicit display semantics", () => {
  it("round-trips repeated OR parameters", () => {
    const parsed = parseSearchParams(new URLSearchParams("prefecture=東京都&prefecture=神奈川県&academic_field_group=engineering&gpa=3.8&gpa_mode=review&page=2"), options);
    expect(parsed.warnings).toEqual([]);
    expect(parseSearchParams(serializeRequest(parsed.request), options).request).toEqual(parsed.request);
  });

  it("ignores invalid values with visible-ready warnings", () => {
    const parsed = parseSearchParams(new URLSearchParams("prefecture=不存在&x=1&gpa=5.5"), options);
    expect(parsed.request.prefecture).toEqual([]);
    expect(parsed.warnings).toHaveLength(3);
  });

  it("does not collapse Unknown, No, and null", () => {
    expect(triStateLabel("Unknown", "あり", "なし")).toBe("不明");
    expect(triStateLabel("No", "あり", "なし")).toBe("なし");
    expect(triStateLabel(null, "あり", "なし")).toBe("—");
    expect(stateClass("Unknown")).not.toBe(stateClass("No"));
    expect(displayValue(null)).toBe("—");
  });

  it("keeps fallback and GPA language non-eligibility based", () => {
    expect(gpaLabel("safe match", false)).toContain("安全一致");
    expect(gpaLabel("safe match", true)).toContain("前年度参考値");
    expect(gpaLabel("safe match", false)).not.toContain("出願可能");
  });

  it("uses the logical key in detail routes", () => {
    expect(detailLink("kokkoritsu", "5.61", "A/B")).toBe("/admissions/kokkoritsu/5.61/A%2FB");
  });
  it("round-trips derived prefecture memberships independently of raw prefecture",()=>{
    const withPrefectures={...options,prefecture_memberships:[{value:"東京都",display_label:"東京都",region:"関東",display_order:13,unfiltered_count:1010},{value:"神奈川県",display_label:"神奈川県",region:"関東",display_order:14,unfiltered_count:684}]};
    const parsed=parseSearchParams(new URLSearchParams("prefecture_membership=東京都&prefecture_membership=神奈川県"),withPrefectures);
    expect(parsed.request.prefecture_membership).toEqual(["東京都","神奈川県"]);
    expect(parsed.request.prefecture).toEqual([]);
    expect(serializeRequest(parsed.request).getAll("prefecture_membership")).toEqual(["東京都","神奈川県"]);
  });

  it("round-trips unselected university and intermediate GPA form drafts", () => {
    const request = parseSearchParams(new URLSearchParams(), options).request;
    const params = serializeSearchFormState(request, "東京", "3.", "");
    const parsed = parseSearchParams(params, options);
    expect(parsed.universityQuery).toBe("東京");
    expect(parsed.gpaQuery).toBe("3.");
    expect(parsed.request.university).toEqual([]);
    expect(parsed.request.gpa_tenths).toBeNull();
  });

  it("round-trips the reviewed grade requirement and overall GPA independently", () => {
    const parsed = parseSearchParams(
      new URLSearchParams("grade_requirement=required&overall_gpa=3.8"),
      options,
    );
    expect(parsed.request.grade_requirement_status).toBe("required");
    expect(parsed.request.overall_gpa_tenths).toBe(38);
    expect(serializeRequest(parsed.request).toString()).toContain("overall_gpa=3.8");
    const old = parseSearchParams(new URLSearchParams("gpa=3.8&gpa_mode=safe"), options);
    expect(old.request.gpa_tenths).toBe(38);
    expect(old.request.grade_requirement_status).toBeNull();
  });

  it("round-trips public selection, applicant grade, and deadline without changing legacy GPA URLs", () => {
    const parsed = parseSearchParams(new URLSearchParams(
      "selection_family=recommendation&special_filter=returnee_flag&special_filter=international_baccalaureate_flag&applicant_gpa=3.8&deadline_on_or_after=2026-10-01",
    ), options);
    expect(parsed.warnings).toEqual([]);
    expect(parsed.request.selection_families).toEqual(["recommendation"]);
    expect(parsed.request.special_filters).toEqual(["returnee_flag", "international_baccalaureate_flag"]);
    expect(parsed.request.applicant_gpa_tenths).toBe(38);
    expect(parsed.request.deadline_on_or_after).toBe("2026-10-01");
    expect(parseSearchParams(serializeRequest(parsed.request), options).request).toEqual(parsed.request);
    expect(parseSearchParams(new URLSearchParams(), options).request.special_filters).toEqual([]);
    expect(parseSearchParams(new URLSearchParams(), options).request.selection_families).toEqual(["recommendation", "comprehensive"]);
  });

  it("fails closed for invalid or orphaned overall GPA URL state", () => {
    const orphaned = parseSearchParams(new URLSearchParams("overall_gpa=3.8"), options);
    expect(orphaned.request.overall_gpa_tenths).toBeNull();
    expect(orphaned.warnings).toContain("評定条件ありの指定がないため全体評定を無視しました。");
    const invalid = parseSearchParams(
      new URLSearchParams("grade_requirement=required&overall_gpa=3.75"),
      options,
    );
    expect(invalid.request.grade_requirement_status).toBe("required");
    expect(invalid.request.overall_gpa_tenths).toBeNull();
    expect(serializeRequest(invalid.request).toString()).toBe("grade_requirement=required");
  });

  it("canonicalizes v0.2 Broad and Subcategory parameters in taxonomy order", () => {
    const parsed = parseSearchParams(new URLSearchParams(
      "academic_field_v2=engineering&academic_field_v2=natural_sciences&academic_field_v2=engineering"
      + "&academic_subfield_v2=natural_sciences:physics"
      + "&academic_subfield_v2=natural_sciences:mathematics_statistics",
    ), options);
    expect(parsed.warnings).toEqual([]);
    expect(parsed.request.academic_field_v2_branches).toEqual([
      { group_code: "natural_sciences", subcategory_codes: ["mathematics_statistics", "physics"] },
      { group_code: "engineering", subcategory_codes: [] },
    ]);
    expect(serializeRequest(parsed.request).getAll("academic_field_v2")).toEqual([
      "natural_sciences", "engineering",
    ]);
    expect(serializeRequest(parsed.request).getAll("academic_subfield_v2")).toEqual([
      "natural_sciences:mathematics_statistics", "natural_sciences:physics",
    ]);
  });

  it("rejects orphaned or unknown v0.2 Subcategory parameters without adding a parent", () => {
    const parsed = parseSearchParams(new URLSearchParams(
      "academic_subfield_v2=natural_sciences:physics&academic_field_v2=unknown",
    ), options);
    expect(parsed.request.academic_field_v2_branches).toEqual([]);
    expect(parsed.warnings).toHaveLength(2);
    expect(serializeRequest(parsed.request).toString()).toBe("");
  });

  it("preserves legacy v0.1 and v0.2 filters as separate ANDed URL state", () => {
    const parsed = parseSearchParams(new URLSearchParams(
      "academic_field_group=engineering&academic_field_v2=natural_sciences",
    ), options);
    expect(parsed.request.academic_field_group).toEqual(["engineering"]);
    expect(parsed.request.academic_field_v2_branches).toEqual([
      { group_code: "natural_sciences", subcategory_codes: [] },
    ]);
    const serialized = serializeRequest(parsed.request);
    expect(serialized.get("academic_field_group")).toBe("engineering");
    expect(serialized.get("academic_field_v2")).toBe("natural_sciences");
  });
});
