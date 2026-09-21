import { candidateKey, type ResolvedCandidate } from "./candidates";
import { selectionMethodLabels } from "./search-ui";
import type { DetailRecord, SearchRow } from "./types";

export const EXPORT_COLUMNS = ["大学名", "学部", "学科", "選抜区分", "選抜名称", "大学種別", "都道府県",
  "出願終了日", "評定条件", "英語資格条件", "研究業績要件", "選考方法", "公式情報URL", "Site詳細URL",
  "データ状態", "保存日時", "source_dataset", "source_version", "record_id"] as const;
export type ExportRow = Array<string | null>;

const text = (value: unknown): string | null => value === null || value === undefined ? null : String(value);
const researchLabel = (value: unknown): string | null => value === "Yes" ? "必要" : value === "No" ? "要件なし" : value === "Unknown" ? "不明" : text(value);

export async function candidateExportRows(
  candidates: ResolvedCandidate[], selected: ReadonlySet<string>, origin: string,
  getDetail: (row: SearchRow) => Promise<DetailRecord>,
): Promise<ExportRow[]> {
  const result: ExportRow[] = [];
  for (const { saved, row } of candidates) {
    if (!selected.has(candidateKey(saved))) continue;
    const siteUrl = new URL(candidateKey(saved), origin).href;
    if (!row) {
      const s = saved.snapshot;
      result.push([s.university, s.faculty_school, s.department, null, s.selection_name, null, null,
        null, null, null, null, null, null, siteUrl, "stale：現在データで確認できず", saved.saved_at,
        saved.source_dataset, saved.source_version, saved.record_id]);
      continue;
    }
    // Missing/corrupt detail is an export failure, never a stale record or silently blank facts.
    const detail = await getDetail(row);
    if (candidateKey(detail.identity) !== candidateKey(saved)) throw new Error("候補の詳細データが一致しません。");
    const a = detail.admission;
    result.push([row.university, row.faculty_school, row.department, row.selection_category, row.selection_name,
      row.institution_type, row.prefecture, row.application_end, row.gpa_requirement, row.english_requirement,
      text(a.research_requirement_summary) ?? researchLabel(row.research_requirement_required),
      selectionMethodLabels(row).join("・") || null, text(a.source_url) ?? text(a.guideline_url), siteUrl,
      row.fallback_previous_year ? "current：前年度情報を参照" : "current：現行データ", saved.saved_at,
      saved.source_dataset, saved.source_version, saved.record_id]);
  }
  return result;
}

export function csvCell(value: string | null): string {
  const raw = value ?? "";
  // CSV cannot declare a cell's type. Protect spreadsheet formula interpretation;
  // XLSX retains the exact value as an explicit text cell.
  const safe = /^[\s\uFEFF]*[=+@-]/u.test(raw) || /^[\t\r\n]/u.test(raw) ? `'${raw}` : raw;
  return `"${safe.replace(/"/g, '""')}"`;
}
export function candidateCsv(rows: ExportRow[]): string {
  return "\uFEFF" + [EXPORT_COLUMNS, ...rows].map((row) => row.map(csvCell).join(",")).join("\r\n") + "\r\n";
}
export function exportFilename(format: "csv" | "xlsx", now = new Date()): string {
  const date = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  return `early-admissions-candidates-${date}.${format}`;
}
export function downloadExport(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
