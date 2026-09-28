import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { logicalKey, searchRows } from "../src/search";
import type { SearchRequest, SearchRow } from "../src/types";

const dataRoot = process.env.SITE_DATA_DIR ?? join(process.cwd(), "public/site-data");
const manifest = JSON.parse(readFileSync(join(dataRoot, "build_manifest.json"), "utf8"));
const rows = manifest.outputs.artifacts.filter((item: { kind: string }) => item.kind === "search_shard").flatMap((item: { path: string }) => {
  const payload = JSON.parse(readFileSync(join(dataRoot, item.path), "utf8"));
  expect(payload.build_id).toBe(manifest.build_id);
  return payload.rows as SearchRow[];
});
const oracle = JSON.parse(readFileSync(join(process.cwd(), "tests/generated/search_oracle.json"), "utf8")) as { cases: Array<{ label: string; request: SearchRequest; logical_keys: string[][]; summary: Record<string, unknown> }> };

describe("25-query Python oracle equivalence", () => {
  it("has the frozen 25 cases", () => expect(oracle.cases).toHaveLength(25));
  for (const example of oracle.cases) {
    it(example.label, () => {
      const result = searchRows(rows, { ...example.request, page: 1 });
      expect(new Set(result.rows.map(logicalKey))).toEqual(new Set(example.logical_keys.map((key) => key.join("\u001f"))));
      expect(result.summary.total_matched_rows).toBe(example.summary.total_matched_rows);
      expect(result.summary.rows_by_source_dataset).toEqual(example.summary.rows_by_source_dataset);
      expect(result.summary.university_count).toBe(example.summary.university_count);
      expect(result.summary.gpa_safe_match_rows).toBe(example.summary.gpa_safe_match_rows);
      expect(result.summary.gpa_conditional_review_rows).toBe(example.summary.gpa_conditional_review_rows);
      expect(result.summary.gpa_not_numerically_evaluable_rows).toBe(example.summary.gpa_not_numerically_evaluable_rows);
    });
  }
});
