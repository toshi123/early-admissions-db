import { build } from "esbuild";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdir, readFile, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const frozen = JSON.parse(await readFile(path.join(site, "mcp/frozen-client-v0.1.json"), "utf8"));
const archive = path.join(site, "mcp", frozen.archive);
const hash = (bytes) => createHash("sha256").update(bytes).digest("hex");
if (hash(await readFile(archive)) !== frozen.sha256) throw new Error("Frozen MCP client archive hash mismatch");

const output = path.join(site, "dist-ea");
const client = path.join(output, "client");
await rm(output, { recursive: true, force: true });
await mkdir(client, { recursive: true });
execFileSync("tar", ["-xzf", archive, "-C", client], { stdio: "inherit" });

const data = path.join(client, "site-data");
const manifest = JSON.parse(await readFile(path.join(data, "build_manifest.json"), "utf8"));
if (manifest.artifact !== "early_admissions_site_data" || manifest.site_data_schema_version !== "0.3" ||
    manifest.build_id !== frozen.site_data_build_id || manifest.counts.search_rows !== frozen.confirmed_rows ||
    manifest.validation?.status !== "passed" || manifest.publication?.production_ready !== true) {
  throw new Error("Frozen MCP client has an unexpected or unvalidated Site-data manifest");
}

async function verifyReceipt(receipt) {
  if (!receipt || typeof receipt.path !== "string" || !/^[\w./-]+$/.test(receipt.path) ||
      receipt.path.startsWith("/") || receipt.path.split("/").includes("..")) {
    throw new Error("Invalid Site-data receipt path");
  }
  const bytes = await readFile(path.join(data, receipt.path));
  if (bytes.length !== receipt.size_bytes || hash(bytes) !== receipt.sha256) {
    throw new Error(`Site-data receipt mismatch: ${receipt.path}`);
  }
}

for (const receipt of manifest.outputs.artifacts) await verifyReceipt(receipt);
for (const [filename, artifact] of [
  ["public_discovery_manifest.json", "early_admissions_public_discovery_manifest"],
  ["special_selection_manifest.json", "early_admissions_special_selection_manifest"],
  ["mcp_text_index_manifest.json", "early_admissions_mcp_text_index_manifest"],
]) {
  const other = JSON.parse(await readFile(path.join(data, filename), "utf8"));
  if (other.artifact !== artifact || (filename === "mcp_text_index_manifest.json" && other.build_id !== manifest.build_id)) {
    throw new Error(`Unexpected ${filename}`);
  }
  await verifyReceipt(other.output);
}
const index = JSON.parse(await readFile(path.join(data, "mcp_text_index.json"), "utf8"));
if (index.build_id !== manifest.build_id || index.records.length !== frozen.confirmed_rows) {
  throw new Error("Frozen MCP text index count or build mismatch");
}

await build({
  entryPoints: [path.join(site, "mcp/worker.ts")],
  outfile: path.join(output, "index.js"),
  bundle: true, platform: "browser", format: "esm", target: "es2022", minify: true,
  legalComments: "none", logLevel: "warning",
});
console.log(JSON.stringify({ worker: "ea", build_id: manifest.build_id,
  confirmed_rows: frozen.confirmed_rows, receipts: manifest.outputs.artifacts.length }));
