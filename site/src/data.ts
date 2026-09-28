import type { ArtifactReceipt, DetailRecord, FilterOptions, ProvisionalAdmission, SearchRow, SiteManifest } from "./types";

const DATA_ROOT = "/site-data";
export class SiteDataError extends Error {}

export interface LoadMetrics {
  manifestFetchMs: number;
  filterFetchMs: number;
  filterHashVerifyMs: number;
  filterJsonParseMs: number;
  searchFetchMs: number;
  searchHashVerifyMs: number;
  searchJsonParseMs: number;
  clientPreparationMs: number;
  totalPreparationMs: number;
}

async function sha256Hex(bytes: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, "0")).join("");
}

async function fetchVerifiedJson<T>(receipt: ArtifactReceipt): Promise<{ value: T; fetchMs: number; hashVerifyMs: number; jsonParseMs: number }> {
  const started = performance.now();
  const response = await fetch(`${DATA_ROOT}/${receipt.path}`);
  if (!response.ok) throw new SiteDataError(`データファイルを取得できませんでした（${response.status}: ${receipt.path}）`);
  const bytes = await response.arrayBuffer();
  const fetched = performance.now();
  const digest = await sha256Hex(bytes);
  const verified = performance.now();
  if (bytes.byteLength !== receipt.size_bytes || digest !== receipt.sha256) {
    throw new SiteDataError(`データファイルの整合性を確認できませんでした（${receipt.path}）。`);
  }
  let value: T;
  try { value = JSON.parse(new TextDecoder().decode(bytes)) as T; }
  catch { throw new SiteDataError(`データファイルをJSONとして読めませんでした（${receipt.path}）。`); }
  return { value, fetchMs: fetched - started, hashVerifyMs: verified - fetched, jsonParseMs: performance.now() - verified };
}

function assertManifest(value: unknown): asserts value is SiteManifest {
  const manifest = value as Partial<SiteManifest>;
  if (manifest.artifact !== "early_admissions_site_data" || manifest.site_data_schema_version !== "0.3" ||
    manifest.validation?.status !== "passed" || !/^[0-9a-f]{20}$/.test(manifest.build_id ?? "") ||
    !Array.isArray(manifest.outputs?.artifacts)) {
    throw new SiteDataError("対応していない、または未検証のSite-data manifestです。");
  }
}

let manifestCache: Promise<{ manifest: SiteManifest; fetchMs: number }> | null = null;
export function loadManifest(): Promise<{ manifest: SiteManifest; fetchMs: number }> {
  if (!manifestCache) manifestCache = (async () => {
    const started = performance.now();
    const response = await fetch(`${DATA_ROOT}/build_manifest.json`, { cache: "no-cache" });
    if (!response.ok) throw new SiteDataError(`データの目録を取得できませんでした（${response.status}）。`);
    let value: unknown;
    try { value = await response.json(); } catch { throw new SiteDataError("データの目録をJSONとして読めませんでした。"); }
    assertManifest(value);
    return { manifest: value, fetchMs: performance.now() - started };
  })();
  return manifestCache;
}

export async function loadSearchData() {
  const started = performance.now();
  const { manifest, fetchMs: manifestFetchMs } = await loadManifest();
  const filterReceipt = manifest.outputs.artifacts.find((item) => item.kind === "filter_options");
  if (!filterReceipt) throw new SiteDataError("検索条件データが目録にありません。");
  const optionsResult = await fetchVerifiedJson<FilterOptions>(filterReceipt);
  if (optionsResult.value.build_id !== manifest.build_id || optionsResult.value.site_data_schema_version !== "0.3") {
    throw new SiteDataError("検索条件データのbuild IDまたはschema versionが一致しません。");
  }
  const receipts = manifest.outputs.artifacts.filter((item) => item.kind === "search_shard");
  const payloads = await Promise.all(receipts.map((receipt) => fetchVerifiedJson<{
    build_id: string; site_data_schema_version: string; rows: SearchRow[];
  }>(receipt)));
  if (payloads.some(({ value }) => value.build_id !== manifest.build_id || value.site_data_schema_version !== "0.3")) {
    throw new SiteDataError("検索データのbuild IDまたはschema versionが一致しません。");
  }
  const prepared = performance.now();
  const rows = payloads.flatMap(({ value }) => value.rows);
  if (rows.length !== manifest.counts.search_rows) throw new SiteDataError("検索データの件数が目録と一致しません。");
  const ready = performance.now();
  const metrics: LoadMetrics = {
    manifestFetchMs,
    filterFetchMs: optionsResult.fetchMs,
    filterHashVerifyMs: optionsResult.hashVerifyMs,
    filterJsonParseMs: optionsResult.jsonParseMs,
    searchFetchMs: Math.max(...payloads.map((item) => item.fetchMs)),
    searchHashVerifyMs: payloads.reduce((sum, item) => sum + item.hashVerifyMs, 0),
    searchJsonParseMs: payloads.reduce((sum, item) => sum + item.jsonParseMs, 0),
    clientPreparationMs: ready - prepared,
    totalPreparationMs: ready - started,
  };
  return { manifest, options: optionsResult.value, rows, metrics };
}

type DetailPayload = { build_id: string; site_data_schema_version: string; details: DetailRecord[] };
export type DetailCache = Map<string, Promise<DetailPayload>>;

export async function loadDetail(
  manifest: SiteManifest,
  row: SearchRow,
  cache?: DetailCache,
): Promise<{ detail: DetailRecord; loadMs: number }> {
  const receipt = manifest.outputs.artifacts.find((item) => item.kind === "detail_shard" && item.path === row.detail_path);
  if (!receipt) throw new SiteDataError("対応する詳細データが目録にありません。");
  const started = performance.now();
  const key = `${manifest.build_id}/${receipt.path}`;
  let pending = cache?.get(key);
  if (!pending) {
    pending = fetchVerifiedJson<DetailPayload>(receipt).then(({ value }) => value);
    cache?.set(key, pending);
  }
  let payload: DetailPayload;
  try { payload = await pending; } catch (error) { cache?.delete(key); throw error; }
  if (payload.build_id !== manifest.build_id || payload.site_data_schema_version !== "0.3") {
    cache?.delete(key);
    throw new SiteDataError("詳細データのbuild IDまたはschema versionが一致しません。");
  }
  const detail = payload.details.find((item) =>
    item.identity.source_dataset === row.source_dataset && item.identity.source_version === row.source_version && item.identity.record_id === row.record_id);
  if (!detail) throw new SiteDataError("指定された入試の詳細が見つかりません。");
  return { detail, loadMs: performance.now() - started };
}

export function resetDataCacheForTests(): void { manifestCache = null; }

export async function loadPublicDiscovery(siteManifest: SiteManifest): Promise<ProvisionalAdmission[]> {
  const response = await fetch(`${DATA_ROOT}/public_discovery_manifest.json`, { cache: "no-cache" });
  if (!response.ok) throw new SiteDataError("公開用の実施確認データ目録を取得できませんでした。");
  const manifest = await response.json() as {
    artifact: string; schema_version: string; build_id: string; sqlite_sha256: string;
    published_rows: number; output: { path: string; sha256: string; size_bytes: number };
  };
  if (manifest.artifact !== "early_admissions_public_discovery_manifest" || manifest.schema_version !== "0.1" ||
    manifest.sqlite_sha256 !== siteManifest.input.sqlite_sha256 || manifest.output?.path !== "provisional_admissions.json") {
    throw new SiteDataError("実施確認データの版または入力DBがSite-dataと一致しません。");
  }
  const result = await fetchVerifiedJson<{ artifact: string; schema_version: string; build_id: string; records: ProvisionalAdmission[] }>({
    ...manifest.output, kind: "filter_options", record_count: manifest.published_rows,
  });
  const payload = result.value;
  if (payload.artifact !== "early_admissions_public_discovery" || payload.schema_version !== "0.1" ||
    payload.build_id !== manifest.build_id || !Array.isArray(payload.records) || payload.records.length !== manifest.published_rows) {
    throw new SiteDataError("実施確認データの件数またはbuild IDが一致しません。");
  }
  return payload.records;
}
