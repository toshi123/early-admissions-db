import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { WebStandardStreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js";
import { z } from "zod";
import { getAdmission, getResearchRequirements, getSearchFacets, searchAdmissions, searchInputSchema, ServiceError } from "./service";
import { loadPublicData, type PublicData } from "./public-data";

type Env = { ASSETS: { fetch(request: Request): Promise<Response> } };
let cached: Promise<PublicData> | null = null;

function data(env: Env, origin: string): Promise<PublicData> {
  if (!cached) cached = loadPublicData(env.ASSETS, origin).catch((error) => {
    cached = null;
    throw new ServiceError("database_unavailable", error instanceof Error ? error.message : "公開データの取得に失敗しました");
  });
  return cached;
}

function reply(value: Record<string, unknown>, message: string) {
  return { structuredContent: value, content: [{ type: "text" as const, text: message }] };
}

async function readOnly(fn: () => Promise<Record<string, unknown>> | Record<string, unknown>, summary: (value: Record<string, unknown>) => string) {
  try {
    const value = await fn();
    return reply(value, summary(value));
  } catch (error) {
    const code = error instanceof ServiceError ? error.code :
      error instanceof Error && /Public |index |build mismatch|integrity failure/.test(error.message) ? "database_unavailable" : "internal_error";
    const message = error instanceof ServiceError ? error.message :
      code === "database_unavailable" ? "公開データを取得できませんでした。" : "内部エラーが発生しました。";
    console.error("MCP read failure", code, error instanceof Error ? error.message : String(error));
    return { isError: true, structuredContent: { error: { code, message } },
      content: [{ type: "text" as const, text: `${code}: ${message}` }] };
  }
}

function makeServer(env: Env, origin: string): McpServer {
  const server = new McpServer({ name: "early-admissions-2027", version: "0.1.0" }, {
    instructions: "Read-only access to the public 2027 Japanese early university admissions database. Each confirmed record_id is one actual application unit. Use search_admissions, then get_admission and get_research_requirements for details. Provisional admissions have confirmed existence but uncertain application units and are returned separately. Unknown is not No. Previous-year reference is not confirmed 2027 detail. Use official source URLs before application decisions.",
  });
  const annotations = { readOnlyHint: true, destructiveHint: false, openWorldHint: false };
  server.registerTool("search_admissions", {
    title: "2027年度早期入試を検索",
    description: "Search confirmed 2027 Japanese early university admission application units using the same filtering logic as the public Web Site. Each result has a record_id, not one row per university. applicant_gpa is the student's grade average: 3.8 matches safe requirements of 3.8 or lower and no-grade requirements; uncertain numeric rules remain marked unknown. Multiple values within a field are OR, different fields are AND. Special selections are excluded unless special_filters are selected. Provisional existence notices are returned separately and are never counted as confirmed units. Unknown is not No; previous-year details are references only.",
    inputSchema: searchInputSchema,
    annotations,
  }, async (input) => readOnly(async () => {
    const result = await searchAdmissions(await data(env, origin), input, origin);
    return result;
  }, (value) => `${value.total} confirmed application units; ${value.provisional_count} provisional existence notices. Results are paginated.`));
  server.registerTool("get_admission", {
    title: "募集単位の詳細を取得",
    description: "Get the published detail for exactly one confirmed admission by record_id. Raw Unknown and null values remain distinct. Source links and previous-year status are included. Use after search_admissions; verify eligibility in official university material.",
    inputSchema: z.object({ record_id: z.string().min(1).max(160) }).strict(), annotations,
  }, async ({ record_id }) => readOnly(async () => getAdmission(await data(env, origin), record_id, origin),
    () => `Published admission detail for ${record_id}.`));
  server.registerTool("get_research_requirements", {
    title: "研究活動要件を取得",
    description: "Get every published ResearchRequirements child row for one confirmed admission record_id. An empty requirements array means no structured child row is published; it is not proof that research activity is unnecessary.",
    inputSchema: z.object({ record_id: z.string().min(1).max(160) }).strict(), annotations,
  }, async ({ record_id }) => readOnly(async () => getResearchRequirements(await data(env, origin), record_id),
    (value) => `${(value.requirements as unknown[]).length} structured research requirement rows for ${record_id}.`));
  server.registerTool("get_search_facets", {
    title: "検索可能な条件を取得",
    description: "Return the public Site's current filter option values, taxonomy groups, counts, available flags, and up to 50 university names or raw academic fields matching the optional queries. Use this to choose exact structured arguments for search_admissions.",
    inputSchema: z.object({ university_query: z.string().max(80).optional(), academic_field_query: z.string().max(80).optional() }).strict(), annotations,
  }, async ({ university_query, academic_field_query }) => readOnly(async () => getSearchFacets(await data(env, origin), university_query, academic_field_query),
    () => "Public search facets and data summary."));
  return server;
}

function cors(response: Response): Response {
  const headers = new Headers(response.headers);
  headers.set("Access-Control-Allow-Origin", "*");
  headers.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  headers.set("Access-Control-Allow-Headers", "Content-Type, MCP-Protocol-Version, MCP-Session-Id, Authorization");
  headers.set("Access-Control-Expose-Headers", "MCP-Session-Id, MCP-Protocol-Version");
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname !== "/mcp") return env.ASSETS.fetch(request);
    if (request.method === "OPTIONS") return cors(new Response(null, { status: 204 }));
    const server = makeServer(env, url.origin);
    const transport = new WebStandardStreamableHTTPServerTransport({ sessionIdGenerator: undefined, enableJsonResponse: true });
    await server.connect(transport);
    try { return cors(await transport.handleRequest(request)); }
    finally { await server.close(); }
  },
};
