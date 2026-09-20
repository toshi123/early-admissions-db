import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { detailLink, displayValue, gpaLabel, stateClass, triStateLabel } from "../src/display";
import { parseSearchParams, serializeRequest } from "../src/url-state";
import type { FilterOptions } from "../src/types";

const options = JSON.parse(readFileSync(join(process.cwd(), "public/site-data/assets/bbffbaee7aadbdb0ae43/filter_options.json"), "utf8")) as FilterOptions;

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
});
