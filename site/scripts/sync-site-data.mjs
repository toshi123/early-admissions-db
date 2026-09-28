import { cp, mkdir, readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(siteRoot, "..");
const source = resolve(repoRoot, "data/derived/site/v0_3");
const destination = resolve(siteRoot, "public/site-data");

const manifest = JSON.parse(await readFile(resolve(source, "build_manifest.json"), "utf8"));
if (manifest.site_data_schema_version !== "0.3" || manifest.validation?.status !== "passed" ||
    manifest.publication?.production_ready !== true) {
  throw new Error("Site-data manifest is not a production-ready v0.3 projection.");
}

const publicDiscovery = JSON.parse(await readFile(resolve(source, "public_discovery_manifest.json"), "utf8"));
if (publicDiscovery.artifact !== "early_admissions_public_discovery_manifest" ||
    publicDiscovery.schema_version !== "0.1" ||
    publicDiscovery.sqlite_sha256 !== manifest.input.sqlite_sha256) {
  throw new Error("Public discovery layer is not aligned with the production SQLite input.");
}

await mkdir(destination, { recursive: true });
await cp(resolve(source, "build_manifest.json"), resolve(destination, "build_manifest.json"));
await cp(resolve(source, "assets"), resolve(destination, "assets"), { recursive: true });
await cp(resolve(source, "public_discovery_manifest.json"), resolve(destination, "public_discovery_manifest.json"));
await cp(resolve(source, "provisional_admissions.json"), resolve(destination, "provisional_admissions.json"));
await cp(resolve(repoRoot, "docs/third_party_notices.md"), resolve(siteRoot, "public/third-party-notices.txt"));
console.log(`Synced Site-data build ${manifest.build_id}`);
