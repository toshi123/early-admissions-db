import { cp, mkdir, readFile, rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const siteRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(siteRoot, "..");
const source = resolve(repoRoot, "data/derived/site/v0_2");
const destination = resolve(siteRoot, "public/site-data");

const manifest = JSON.parse(await readFile(resolve(source, "build_manifest.json"), "utf8"));
if (manifest.site_data_schema_version !== "0.2" || manifest.validation?.status !== "passed") {
  throw new Error("Site-data manifest is not a validated v0.2 projection.");
}

await rm(destination, { recursive: true, force: true });
await mkdir(destination, { recursive: true });
await cp(resolve(source, "build_manifest.json"), resolve(destination, "build_manifest.json"));
await cp(resolve(source, "assets"), resolve(destination, "assets"), { recursive: true });
await cp(resolve(repoRoot, "docs/third_party_notices.md"), resolve(siteRoot, "public/third-party-notices.txt"));
console.log(`Synced Site-data build ${manifest.build_id}`);
