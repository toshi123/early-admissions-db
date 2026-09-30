import { build } from "esbuild";
import { createHash } from "node:crypto";
import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const output = path.join(site, "dist-mcp");
const client = path.join(output, "client");
const data = path.join(client, "site-data");
const manifest = JSON.parse(await readFile(path.join(site, "dist/site-data/build_manifest.json"), "utf8"));
if (manifest.artifact !== "early_admissions_site_data" || manifest.site_data_schema_version !== "0.3" || manifest.validation?.status !== "passed") {
  throw new Error("Validated Site-data v0.3 is required before building MCP artifacts");
}

await rm(output, { recursive: true, force: true });
await mkdir(path.join(output, "server"), { recursive: true });
await cp(path.join(site, "dist"), client, { recursive: true });

const textFields = ["university", "faculty_school", "department", "selection_category", "selection_name",
  "academic_field", "gpa_requirement", "english_requirement", "research_activity_detail",
  "research_requirement_summary", "selection_method_detail", "documents_summary"];
const records = [];
for (const receipt of manifest.outputs.artifacts.filter((item) => item.kind === "detail_shard")) {
  const bytes = await readFile(path.join(data, receipt.path));
  const sha256 = createHash("sha256").update(bytes).digest("hex");
  if (bytes.byteLength !== receipt.size_bytes || sha256 !== receipt.sha256) throw new Error(`Detail shard integrity failed: ${receipt.path}`);
  const payload = JSON.parse(bytes.toString("utf8"));
  if (payload.build_id !== manifest.build_id) throw new Error(`Detail shard build mismatch: ${receipt.path}`);
  for (const detail of payload.details) {
    records.push({
      record_id: detail.identity.record_id,
      text: [
        ...textFields.map((field) => detail.admission[field]),
        ...detail.research_requirements.flatMap((row) => [row.program_or_competition, row.requirement_detail, row.required_level]),
      ].filter((value) => typeof value === "string" && value).join(" "),
    });
  }
}
records.sort((a, b) => a.record_id.localeCompare(b.record_id, "ja"));
if (records.length !== manifest.counts.search_rows || new Set(records.map((row) => row.record_id)).size !== records.length) {
  throw new Error("MCP text index count or record_id mismatch");
}
const indexBytes = Buffer.from(JSON.stringify({ build_id: manifest.build_id, records }));
await writeFile(path.join(data, "mcp_text_index.json"), indexBytes);
await writeFile(path.join(data, "mcp_text_index_manifest.json"), JSON.stringify({
  artifact: "early_admissions_mcp_text_index_manifest", build_id: manifest.build_id,
  output: { path: "mcp_text_index.json", size_bytes: indexBytes.length, sha256: createHash("sha256").update(indexBytes).digest("hex") },
}) + "\n");

await build({
  entryPoints: [path.join(site, "mcp/worker.ts")],
  outfile: path.join(output, "server/index.js"),
  bundle: true, platform: "browser", format: "esm", target: "es2022", minify: true,
  legalComments: "none", logLevel: "warning",
});
await writeFile(path.join(output, "server/wrangler.json"), JSON.stringify({
  name: "early-admissions-mcp", main: "index.js", compatibility_date: "2026-09-29",
  assets: { directory: "../client", binding: "ASSETS", run_worker_first: ["/mcp"],
    not_found_handling: "single-page-application" },
}, null, 2) + "\n");
await mkdir(path.join(output, ".openai"), { recursive: true });
await cp(path.join(site, "mcp/hosting.json"), path.join(output, ".openai/hosting.json"));
console.log(JSON.stringify({ build_id: manifest.build_id, confirmed_rows: records.length,
  text_index_bytes: indexBytes.length, output }));
