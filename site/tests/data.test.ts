import { beforeEach, describe, expect, it, vi } from "vitest";
import { createHash } from "node:crypto";
import { loadDetail, loadManifest, loadSearchData, resetDataCacheForTests, SiteDataError } from "../src/data";
import type { SearchRow, SiteManifest } from "../src/types";

beforeEach(() => { resetDataCacheForTests(); vi.restoreAllMocks(); });

describe("Site-data protections", () => {
  it("rejects manifest build-ID mismatch or failed validation", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ artifact: "early_admissions_site_data", site_data_schema_version: "0.1", build_id: "bad", validation: { status: "failed" }, outputs: { artifacts: [] } }))));
    await expect(loadManifest()).rejects.toBeInstanceOf(SiteDataError);
  });

  it("treats a missing detail shard as data error, not zero results", async () => {
    const manifest = { outputs: { artifacts: [] } } as unknown as SiteManifest;
    await expect(loadDetail(manifest, { detail_path: "missing.json" } as SearchRow)).rejects.toThrow("目録にありません");
  });

  it("rejects an asset from another build ID", async () => {
    const bytes = new TextEncoder().encode(JSON.stringify({ site_data_schema_version: "0.1", build_id: "bbbbbbbbbbbbbbbbbbbb" }));
    const sha256 = createHash("sha256").update(bytes).digest("hex");
    const validManifest = {
      artifact: "early_admissions_site_data", site_data_schema_version: "0.1", build_id: "aaaaaaaaaaaaaaaaaaaa",
      validation: { status: "passed" }, counts: { search_rows: 0 },
      outputs: { artifacts: [{ kind: "filter_options", path: "filter.json", size_bytes: bytes.byteLength, sha256, record_count: 0 }] },
    };
    let call = 0;
    vi.stubGlobal("fetch", vi.fn(async () => call++ === 0 ? new Response(JSON.stringify(validManifest)) : new Response(bytes)));
    await expect(loadSearchData()).rejects.toThrow("build ID");
  });
});
