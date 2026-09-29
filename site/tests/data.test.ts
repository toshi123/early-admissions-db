import { beforeEach, describe, expect, it, vi } from "vitest";
import { createHash } from "node:crypto";
import { loadDetail, loadManifest, loadSearchData, loadSpecialSelectionIndex, resetDataCacheForTests, SiteDataError } from "../src/data";
import type { SearchRow, SiteManifest } from "../src/types";
import type { DetailCache } from "../src/data";
import { candidateDetail, candidateRow } from "./candidate-fixtures";

beforeEach(() => { resetDataCacheForTests(); vi.restoreAllMocks(); });

describe("Site-data protections", () => {
  it("reuses verified detail shards during export while retaining exact identity checks", async () => {
    const row = candidateRow({ detail_path: "detail.json" });
    const bytes = new TextEncoder().encode(JSON.stringify({ build_id: "test", site_data_schema_version: "0.3", details: [candidateDetail(row)] }));
    const manifest = { build_id: "test", outputs: { artifacts: [{ kind: "detail_shard", path: "detail.json", size_bytes: bytes.byteLength, sha256: createHash("sha256").update(bytes).digest("hex") }] } } as SiteManifest;
    vi.stubGlobal("fetch", vi.fn(async () => new Response(bytes)));
    const cache: DetailCache = new Map();
    await loadDetail(manifest, row, cache); await loadDetail(manifest, row, cache);
    expect(fetch).toHaveBeenCalledTimes(1);
    await expect(loadDetail(manifest, { ...row, source_version: "other" }, cache)).rejects.toThrow("見つかりません");
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("never retains failed integrity checks in the export-scoped detail cache", async () => {
    const row = candidateRow({ detail_path: "detail.json" });
    const bytes = new TextEncoder().encode(JSON.stringify({ build_id: "test", site_data_schema_version: "0.3", details: [candidateDetail(row)] }));
    const manifest = { build_id: "test", outputs: { artifacts: [{ kind: "detail_shard", path: "detail.json", size_bytes: bytes.byteLength, sha256: createHash("sha256").update(bytes).digest("hex") }] } } as SiteManifest;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(new Response("corrupt")).mockResolvedValueOnce(new Response(bytes)));
    const cache: DetailCache = new Map();
    await expect(loadDetail(manifest, row, cache)).rejects.toThrow("整合性");
    expect(cache.size).toBe(0);
    expect((await loadDetail(manifest, row, cache)).detail.identity).toEqual(candidateDetail(row).identity);
  });

  it("rejects manifest build-ID mismatch or failed validation", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ artifact: "early_admissions_site_data", site_data_schema_version: "0.3", build_id: "bad", validation: { status: "failed" }, outputs: { artifacts: [] } }))));
    await expect(loadManifest()).rejects.toBeInstanceOf(SiteDataError);
  });

  it("treats a missing detail shard as data error, not zero results", async () => {
    const manifest = { outputs: { artifacts: [] } } as unknown as SiteManifest;
    await expect(loadDetail(manifest, { detail_path: "missing.json" } as SearchRow)).rejects.toThrow("目録にありません");
  });

  it("rejects an asset from another build ID", async () => {
    const bytes = new TextEncoder().encode(JSON.stringify({ site_data_schema_version: "0.3", build_id: "bbbbbbbbbbbbbbbbbbbb" }));
    const sha256 = createHash("sha256").update(bytes).digest("hex");
    const validManifest = {
      artifact: "early_admissions_site_data", site_data_schema_version: "0.3", build_id: "aaaaaaaaaaaaaaaaaaaa",
      validation: { status: "passed" }, counts: { search_rows: 0 },
      outputs: { artifacts: [{ kind: "filter_options", path: "filter.json", size_bytes: bytes.byteLength, sha256, record_count: 0 }] },
    };
    let call = 0;
    vi.stubGlobal("fetch", vi.fn(async () => call++ === 0 ? new Response(JSON.stringify(validManifest)) : new Response(bytes)));
    await expect(loadSearchData()).rejects.toThrow("build ID");
  });

  it("rejects a special-selection index from a different SQLite input", async () => {
    const site = { input: { sqlite_sha256: "a".repeat(64) }, counts: { search_rows: 1 } } as SiteManifest;
    const manifest = { artifact: "early_admissions_special_selection_manifest", schema_version: "0.1",
      sqlite_sha256: "b".repeat(64), rows: 1, output: { path: "special_selection_index.json" } };
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(manifest))));
    await expect(loadSpecialSelectionIndex(site)).rejects.toThrow("入力DB");
  });
});
