import { describe, expect, it } from "vitest";
import {
  syncBroadSubcategoryVisibility,
  visibleSubcategories,
} from "../src/academic-field-v2-ui";
import type { AcademicFieldV2SubcategoryOption } from "../src/types";

const subcategories: AcademicFieldV2SubcategoryOption[] = [
  { subcategory_code: "physics", display_label_ja: "物理", parent_group_code: "natural_sciences", display_order: 2, ui_status: "primary", unfiltered_count: 87 },
  { subcategory_code: "mathematics_statistics", display_label_ja: "数学・数理・統計", parent_group_code: "natural_sciences", display_order: 1, ui_status: "primary", unfiltered_count: 107 },
  { subcategory_code: "hidden_nonzero", display_label_ja: "非表示", parent_group_code: "natural_sciences", display_order: 3, ui_status: "hidden", unfiltered_count: 1 },
  { subcategory_code: "zero", display_label_ja: "ゼロ", parent_group_code: "natural_sciences", display_order: 4, ui_status: "primary", unfiltered_count: 0 },
];

describe("academic-field v0.2 dynamic controls", () => {
  it("keeps taxonomy data while showing only current nonzero UI-visible children", () => {
    expect(subcategories).toHaveLength(4);
    expect(visibleSubcategories(subcategories, "natural_sciences").map((item) => item.subcategory_code)).toEqual([
      "mathematics_statistics", "physics",
    ]);
  });

  it("shows children for a checked Broad and clears them when Broad is unchecked", () => {
    document.body.innerHTML = `<form><input id="broad" value="natural_sciences" checked><div data-subcategories-for="natural_sciences" hidden><input id="math" type="checkbox" checked></div></form>`;
    const form = document.querySelector("form")!;
    const broad = document.querySelector<HTMLInputElement>("#broad")!;
    const nested = document.querySelector<HTMLElement>("[data-subcategories-for]")!;
    syncBroadSubcategoryVisibility(form, broad);
    expect(nested.hidden).toBe(false);
    broad.checked = false;
    syncBroadSubcategoryVisibility(form, broad);
    expect(nested.hidden).toBe(true);
    expect(document.querySelector<HTMLInputElement>("#math")!.checked).toBe(false);
  });
});
