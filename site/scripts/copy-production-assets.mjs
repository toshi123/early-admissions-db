import { execFileSync } from "node:child_process";
import { mkdir, readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(siteRoot, "..");
const derived = resolve(repoRoot, "data/derived/site/v0_3");
const output = resolve(siteRoot, "dist");
const manifest = JSON.parse(await readFile(resolve(derived, "build_manifest.json"), "utf8"));
const publicDiscovery = JSON.parse(await readFile(resolve(derived, "public_discovery_manifest.json"), "utf8"));
if (manifest.site_data_schema_version !== "0.3" || manifest.validation?.status !== "passed" ||
    manifest.publication?.production_ready !== true ||
    publicDiscovery.artifact !== "early_admissions_public_discovery_manifest" ||
    publicDiscovery.schema_version !== "0.1" ||
    publicDiscovery.sqlite_sha256 !== manifest.input.sqlite_sha256) {
  throw new Error("Production assets are not validated or do not share a SQLite input.");
}

await mkdir(resolve(output, "site-data"), { recursive: true });
// Vite's recursive publicDir copy stalls on old generated shards in Dropbox.
// Copy static files and the current generated projection as separate sources.
execFileSync("rsync", ["-a", "--exclude=site-data/", `${resolve(siteRoot, "public")}/`, `${output}/`], { stdio: "inherit" });
execFileSync("rsync", ["-a", "--delete", `${derived}/`, `${resolve(output, "site-data")}/`], { stdio: "inherit" });
console.log(`Copied production assets for Site-data build ${manifest.build_id}`);
