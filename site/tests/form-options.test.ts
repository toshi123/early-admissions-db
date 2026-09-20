import { describe, expect, it } from "vitest";
import { inValueOrder } from "../src/form-options";

describe("search form option order", () => {
  it("shows institution types in the counseling order", () => {
    const items = ["公立", "国立", "私立"].map((value) => ({ value, display_label: value }));
    expect(inValueOrder(items, ["国立", "公立", "私立"]).map((item) => item.value)).toEqual(["国立", "公立", "私立"]);
  });

  it("shows exclusivity values in the requested order without changing the internal unknown value", () => {
    const items = ["併願可", "不明", "専願", "条件付き"].map((value) => ({ value, display_label: value }));
    expect(inValueOrder(items, ["専願", "併願可", "条件付き", "不明"]).map((item) => item.value)).toEqual(["専願", "併願可", "条件付き", "不明"]);
  });
});
