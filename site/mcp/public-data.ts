import type { ArtifactReceipt, DetailRecord, FilterOptions, ProvisionalAdmission, SearchRow, SiteManifest, SpecialSelectionFlags } from "../src/types";

type AssetBinding = { fetch(request: Request): Promise<Response> };
type SearchPayload = { build_id: string; site_data_schema_version: string; rows: SearchRow[] };
type DetailPayload = { build_id: string; site_data_schema_version: string; details: DetailRecord[] };

export interface PublicData {
  manifest: SiteManifest;
  options: FilterOptions;
  rows: SearchRow[];
  provisional: ProvisionalAdmission[];
  detail(recordId: string): Promise<DetailRecord | null>;
  addSearchText(): Promise<void>;
}

async function verifiedJson<T>(binding: AssetBinding, origin: string, receipt: Pick<ArtifactReceipt, "path" | "sha256" | "size_bytes">): Promise<T> {
  const response = await binding.fetch(new Request(new URL(`/site-data/${receipt.path}`, origin)));
  if (!response.ok) throw new Error(`Public Site-data unavailable: ${receipt.path} (${response.status})`);
  const bytes = await response.arrayBuffer();
  const digest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))]
    .map((part) => part.toString(16).padStart(2, "0")).join("");
  if (bytes.byteLength !== receipt.size_bytes || digest !== receipt.sha256) throw new Error(`Public Site-data integrity failure: ${receipt.path}`);
  return JSON.parse(new TextDecoder().decode(bytes)) as T;
}

async function plainJson<T>(binding: AssetBinding, origin: string, path: string): Promise<T> {
  const response = await binding.fetch(new Request(new URL(`/site-data/${path}`, origin)));
  if (!response.ok) throw new Error(`Public Site-data unavailable: ${path} (${response.status})`);
  return response.json() as Promise<T>;
}

async function inBatches<T, U>(items: T[], size: number, fn: (item: T) => Promise<U>): Promise<U[]> {
  const output: U[] = [];
  for (let start = 0; start < items.length; start += size) output.push(...await Promise.all(items.slice(start, start + size).map(fn)));
  return output;
}

export async function loadPublicData(binding: AssetBinding, origin: string): Promise<PublicData> {
  const manifest = await plainJson<SiteManifest>(binding, origin, "build_manifest.json");
  if (manifest.artifact !== "early_admissions_site_data" || manifest.site_data_schema_version !== "0.3" || manifest.validation?.status !== "passed") {
    throw new Error("Unsupported or unvalidated public Site-data manifest");
  }
  const receipts = manifest.outputs.artifacts;
  const optionsReceipt = receipts.find((item) => item.kind === "filter_options");
  if (!optionsReceipt) throw new Error("Public Site-data filter options missing");
  const options = await verifiedJson<FilterOptions>(binding, origin, optionsReceipt);
  if (options.build_id !== manifest.build_id) throw new Error("Public Site-data filter build mismatch");
  const searchReceipts = receipts.filter((item) => item.kind === "search_shard");
  const shards = await inBatches(searchReceipts, 4, (item) => verifiedJson<SearchPayload>(binding, origin, item));
  if (shards.some((item) => item.build_id !== manifest.build_id || item.site_data_schema_version !== "0.3")) throw new Error("Public search build mismatch");
  const rows = shards.flatMap((item) => item.rows);
  if (rows.length !== manifest.counts.search_rows || new Set(rows.map((row) => row.record_id)).size !== rows.length) throw new Error("Public search row count or ID mismatch");

  const specialManifest = await plainJson<{ artifact: string; schema_version: string; sqlite_sha256: string; rows: number; build_id: string; output: ArtifactReceipt }>(binding, origin, "special_selection_manifest.json");
  if (specialManifest.artifact !== "early_admissions_special_selection_manifest" || specialManifest.schema_version !== "0.1" ||
      specialManifest.sqlite_sha256 !== manifest.input.sqlite_sha256 || specialManifest.rows !== rows.length) throw new Error("Public special-selection index mismatch");
  const special = await verifiedJson<{ artifact: string; build_id: string; records: Array<{ source_dataset: string; source_version: string; record_id: string; flags: SpecialSelectionFlags }> }>(binding, origin, specialManifest.output);
  if (special.artifact !== "early_admissions_special_selection_index" || special.build_id !== specialManifest.build_id || special.records.length !== rows.length) throw new Error("Public special-selection payload mismatch");
  const specialById = new Map(special.records.map((item) => [item.record_id, item.flags]));
  if (specialById.size !== rows.length) throw new Error("Public special-selection IDs are duplicated");
  for (const row of rows) {
    const flags = specialById.get(row.record_id);
    if (!flags) throw new Error(`Public special-selection ID missing: ${row.record_id}`);
    row.special_flags = flags;
  }

  const discoveryManifest = await plainJson<{ artifact: string; schema_version: string; sqlite_sha256: string; published_rows: number; build_id: string; output: ArtifactReceipt }>(binding, origin, "public_discovery_manifest.json");
  if (discoveryManifest.artifact !== "early_admissions_public_discovery_manifest" || discoveryManifest.schema_version !== "0.2" ||
      discoveryManifest.sqlite_sha256 !== manifest.input.sqlite_sha256) throw new Error("Public discovery manifest mismatch");
  const discovery = await verifiedJson<{ artifact: string; build_id: string; records: ProvisionalAdmission[] }>(binding, origin, discoveryManifest.output);
  if (discovery.artifact !== "early_admissions_public_discovery" || discovery.build_id !== discoveryManifest.build_id ||
      discovery.records.length !== discoveryManifest.published_rows) throw new Error("Public discovery payload mismatch");

  const byId = new Map(rows.map((row) => [row.record_id, row]));
  const detailCache = new Map<string, Promise<DetailPayload>>();
  let textReady: Promise<void> | null = null;
  return {
    manifest, options, rows, provisional: discovery.records,
    async detail(recordId) {
      const row = byId.get(recordId);
      if (!row) return null;
      const receipt = receipts.find((item) => item.kind === "detail_shard" && item.path === row.detail_path);
      if (!receipt) throw new Error(`Public detail receipt missing: ${row.detail_path}`);
      let pending = detailCache.get(receipt.path);
      if (!pending) {
        pending = verifiedJson<DetailPayload>(binding, origin, receipt);
        detailCache.set(receipt.path, pending);
        if (detailCache.size > 8) detailCache.delete(detailCache.keys().next().value!);
      }
      let payload: DetailPayload;
      try { payload = await pending; } catch (error) { detailCache.delete(receipt.path); throw error; }
      if (payload.build_id !== manifest.build_id || payload.site_data_schema_version !== "0.3") throw new Error("Public detail build mismatch");
      return payload.details.find((item) => item.identity.record_id === recordId &&
        item.identity.source_dataset === row.source_dataset && item.identity.source_version === row.source_version) ?? null;
    },
    async addSearchText() {
      if (!textReady) textReady = (async () => {
        const indexManifest = await plainJson<{ artifact: string; build_id: string; output: ArtifactReceipt }>(binding, origin, "mcp_text_index_manifest.json");
        if (indexManifest.artifact !== "early_admissions_mcp_text_index_manifest" || indexManifest.build_id !== manifest.build_id ||
          indexManifest.output.path !== "mcp_text_index.json") throw new Error("Public MCP text index manifest mismatch");
        const index = await verifiedJson<{ build_id: string; records: Array<{ record_id: string; text: string }> }>(binding, origin, indexManifest.output);
        if (index.build_id !== manifest.build_id || index.records.length !== rows.length) throw new Error("Public MCP text index mismatch");
        const textById = new Map(index.records.map((item) => [item.record_id, item.text]));
        if (textById.size !== rows.length) throw new Error("Public MCP text index duplicate IDs");
        for (const row of rows) {
          const value = textById.get(row.record_id);
          if (value === undefined) throw new Error(`Public MCP text index missing: ${row.record_id}`);
          row.search_text = value;
        }
      })().catch((error) => { textReady = null; throw error; });
      await textReady;
    },
  };
}
