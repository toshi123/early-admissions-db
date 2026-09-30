import { beforeAll, describe, expect, it } from "vitest";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { webcrypto } from "node:crypto";
import { emptyRequest, searchRows } from "../src/search";
import type { SearchRequest } from "../src/types";
import { loadPublicData, type PublicData } from "../mcp/public-data";
import { findAdmissionRows, searchInputSchema, type SearchInput } from "../mcp/service";

const origin = "https://ea.ussapao.chatgpt.site";
const root = path.resolve(import.meta.dirname, "../public");
const binding = {
  async fetch(request: Request): Promise<Response> {
    try { return new Response(new Uint8Array(await readFile(path.join(root, new URL(request.url).pathname))), { status: 200 }); }
    catch { return new Response("Not found", { status: 404 }); }
  },
};
let data: PublicData;

beforeAll(async () => {
  Object.defineProperty(globalThis, "crypto", { value: webcrypto, configurable: true });
  data = await loadPublicData(binding, origin);
});

function webRequest(set: (request: SearchRequest) => void): SearchRequest {
  const request = emptyRequest();
  set(request);
  return request;
}

const cases: Array<{ label: string; mcp: SearchInput; web: SearchRequest }> = [
  { label: "Tokyo", mcp: { prefectures: ["東京都"] }, web: webRequest((r) => { r.prefecture_membership = ["東京都"]; }) },
  { label: "Kanagawa", mcp: { prefectures: ["神奈川県"] }, web: webRequest((r) => { r.prefecture_membership = ["神奈川県"]; }) },
  { label: "information", mcp: { academic_groups: ["information"] }, web: webRequest((r) => { r.academic_field_group = ["information"]; }) },
  { label: "engineering", mcp: { academic_groups: ["engineering"] }, web: webRequest((r) => { r.academic_field_group = ["engineering"]; }) },
  { label: "applicant GPA 3.8", mcp: { applicant_gpa: 3.8 }, web: webRequest((r) => { r.applicant_gpa_tenths = 38; }) },
  { label: "interview Yes", mcp: { selection_interview: "Yes" }, web: webRequest((r) => { r.selection_interview = ["Yes"]; }) },
  { label: "oral Yes", mcp: { selection_oral_exam: "Yes" }, web: webRequest((r) => { r.selection_oral_exam = ["Yes"]; }) },
  { label: "research Yes", mcp: { research_requirement_required: "Yes" }, web: webRequest((r) => { r.research_requirement_required = ["Yes"]; }) },
  { label: "nonexclusive", mcp: { exclusive_enrollment_statuses: ["併願可"] }, web: webRequest((r) => { r.exclusive_enrollment_status = ["併願可"]; }) },
  { label: "common test No", mcp: { common_test_required: "No" }, web: webRequest((r) => { r.common_test_required = ["No"]; }) },
];

describe("real public Site-data Web/MCP record ID consistency", () => {
  for (const item of cases) it(item.label, async () => {
    const mcp = await findAdmissionRows(data, searchInputSchema.parse(item.mcp));
    const web = searchRows(data.rows, item.web);
    expect(mcp.matched.rows.map((row) => row.record_id)).toEqual(web.rows.map((row) => row.record_id));
  });
});
