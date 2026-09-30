import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const url = new URL(process.env.MCP_URL ?? "http://127.0.0.1:8787/mcp");
const client = new Client({ name: "early-admissions-smoke", version: "0.1.0" });
await client.connect(new StreamableHTTPClientTransport(url));
try {
  const listed = await client.listTools();
  const names = listed.tools.map((tool) => tool.name).sort();
  const expected = ["get_admission", "get_research_requirements", "get_search_facets", "search_admissions"];
  if (JSON.stringify(names) !== JSON.stringify(expected)) throw new Error(`Unexpected tools: ${names.join(",")}`);
  if (listed.tools.some((tool) => tool.annotations?.readOnlyHint !== true || tool.annotations?.destructiveHint !== false)) {
    throw new Error("Read-only tool annotations missing");
  }
  const call = (name, args) => client.callTool({ name, arguments: args });
  const facets = await call("get_search_facets", { university_query: "北海道教育大学" });
  if (facets.isError || facets.structuredContent.universities_total !== 1) throw new Error("Facet lookup failed");
  const search = await call("search_admissions", { university: "北海道教育大学", limit: 20 });
  if (search.isError || search.structuredContent.total !== 6 || search.structuredContent.provisional_count !== 1) {
    throw new Error(`Hokkaido search mismatch: ${JSON.stringify({ total: search.structuredContent?.total, provisional: search.structuredContent?.provisional_count })}`);
  }
  const id = search.structuredContent.results[0].record_id;
  const detail = await call("get_admission", { record_id: id });
  const research = await call("get_research_requirements", { record_id: id });
  const missing = await call("get_admission", { record_id: "NO-SUCH-RECORD" });
  const zero = await call("search_admissions", { university: "北海道教育大学", selection_oral_exam: "No", research_requirement_required: "Yes" });
  const page = await call("search_admissions", { university: "北海道教育大学", limit: 1, offset: 1 });
  let invalidRejected = false;
  try {
    const invalid = await call("search_admissions", { selection_interview: "Maybe" });
    invalidRejected = Boolean(invalid.isError);
  } catch { invalidRejected = true; }
  if (detail.isError || research.isError || !missing.isError || missing.structuredContent?.error?.code !== "record_not_found" ||
      zero.isError || page.isError || page.structuredContent.results.length !== 1 || !invalidRejected) throw new Error("Tool call smoke failed");
  console.log(JSON.stringify({ initialize: "pass", tools: names, hokkaido_confirmed: search.structuredContent.total,
    hokkaido_provisional: search.structuredContent.provisional_count, detail: "pass", research: "pass",
    record_not_found: "pass", zero_results: zero.structuredContent.total, pagination: "pass", invalid_input: "pass" }));
} finally { await client.close(); }
