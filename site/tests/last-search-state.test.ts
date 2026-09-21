import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import {
  LAST_SEARCH_QUERY_KEY,
  canonicalSearchQuery,
  headerSearchHref,
  readLastSearchQuery,
  rememberLastSearch,
  type SearchStateStorage,
} from "../src/last-search-state";
import { parseSearchParams } from "../src/url-state";
import type { FilterOptions } from "../src/types";

const manifest = JSON.parse(readFileSync(join(process.cwd(), "public/site-data/build_manifest.json"), "utf8")) as {build_id:string};
const options = JSON.parse(readFileSync(join(process.cwd(), `public/site-data/assets/${manifest.build_id}/filter_options.json`), "utf8")) as FilterOptions;

class MemoryStorage implements SearchStateStorage {
  readonly values = new Map<string, string>();
  getItem(key: string): string | null { return this.values.get(key) ?? null; }
  setItem(key: string, value: string): void { this.values.set(key, value); }
}

describe("canonical last-search state", () => {
  it("uses the current recognized search query on /search", () => {
    const request = parseSearchParams(new URLSearchParams("institution_type=国立&prefecture_membership=東京都&page=4"), options).request;
    expect(headerSearchHref("/search", request, new MemoryStorage())).toBe(
      "/search?institution_type=%E5%9B%BD%E7%AB%8B&prefecture_membership=%E6%9D%B1%E4%BA%AC%E9%83%BD",
    );
  });

  it("uses the current recognized results query and omits pagination", () => {
    const request = parseSearchParams(new URLSearchParams("academic_field_group=engineering&gpa=3.8&grade_requirement=required&overall_gpa=3.8&page=3"), options).request;
    const href = headerSearchHref("/results", request, new MemoryStorage());
    expect(href).toContain("academic_field_group=engineering");
    expect(href).toContain("gpa=3.8");
    expect(href).toContain("grade_requirement=required");
    expect(href).toContain("overall_gpa=3.8");
    expect(href).not.toContain("page=");
  });

  it("restores a stored search from admission detail and about pages", () => {
    const storage = new MemoryStorage();
    const request = parseSearchParams(new URLSearchParams("university=東京大学&prefecture_membership=東京都&grade_requirement=required&overall_gpa=3.8"), options).request;
    rememberLastSearch(request, storage);
    const detailHref = headerSearchHref("/admissions/kokkoritsu/5.61/example", request, storage);
    expect(detailHref).toBe(headerSearchHref("/about/data", request, storage));
    const restored = parseSearchParams(new URL(detailHref, "https://example.test").searchParams, options);
    expect(restored.request.university).toEqual(["東京大学"]);
    expect(restored.request.prefecture_membership).toEqual(["東京都"]);
    expect(restored.request.grade_requirement_status).toBe("required");
    expect(restored.request.overall_gpa_tenths).toBe(38);
  });

  it("restores v0.2 Broad/Subcategory state through the header search link", () => {
    const storage = new MemoryStorage();
    const request = parseSearchParams(new URLSearchParams(
      "academic_field_v2=natural_sciences"
      + "&academic_subfield_v2=natural_sciences:mathematics_statistics"
      + "&academic_field_v2=engineering",
    ), options).request;
    rememberLastSearch(request, storage);
    const href = headerSearchHref(
      "/admissions/kokkoritsu/5.61/example",
      request,
      storage,
    );
    const restored = parseSearchParams(
      new URL(href, "https://example.test").searchParams,
      options,
    );
    expect(restored.request.academic_field_v2_branches).toEqual(request.academic_field_v2_branches);
  });

  it("falls back to /search when a new session has no remembered query", () => {
    const request = parseSearchParams(new URLSearchParams(), options).request;
    expect(headerSearchHref("/about/data", request, new MemoryStorage())).toBe("/search");
  });

  it("never persists unknown parameters or invalid recognized values", () => {
    const parsed = parseSearchParams(new URLSearchParams("prefecture_membership=不存在&unknown=1&institution_type=国立"), options);
    const storage = new MemoryStorage();
    const query = rememberLastSearch(parsed.request, storage);
    expect(query).toBe("institution_type=%E5%9B%BD%E7%AB%8B");
    expect(storage.values.get(LAST_SEARCH_QUERY_KEY)).toBe(query);
  });

  it("does not serialize invalid draft-only university or GPA text", () => {
    const parsed = parseSearchParams(new URLSearchParams("university_query=東京&gpa_query=3.&institution_type=私立"), options);
    expect(canonicalSearchQuery(parsed.request)).toBe("institution_type=%E7%A7%81%E7%AB%8B");
  });

  it("tolerates unavailable session storage", () => {
    const failing: SearchStateStorage = {
      getItem: () => { throw new Error("blocked"); },
      setItem: () => { throw new Error("blocked"); },
    };
    const request = parseSearchParams(new URLSearchParams("institution_type=公立"), options).request;
    expect(rememberLastSearch(request, failing)).toContain("institution_type=");
    expect(readLastSearchQuery(failing)).toBe("");
  });
});
