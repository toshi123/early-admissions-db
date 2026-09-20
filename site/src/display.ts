import type { GpaDerivedStatus, Scalar } from "./types";

export function escapeHtml(value: unknown): string {
  return String(value).replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  }[character]!));
}

export function displayValue(value: Scalar | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  if (value === true) return "Yes（あり）";
  if (value === false) return "No（なし）";
  return escapeHtml(value);
}

export function triStateLabel(value: string | null, yes: string, no: string): string {
  if (value === "Yes") return yes;
  if (value === "No") return no;
  if (value === "Unknown") return "不明";
  if (value === "Conditional") return "条件付き";
  return "—";
}

export function stateClass(value: string | null | boolean): string {
  if (value === "Yes" || value === true) return "state-yes";
  if (value === "No" || value === false) return "state-no";
  if (value === "Unknown") return "state-unknown";
  if (value === null) return "state-null";
  return "state-neutral";
}

export function gpaLabel(status: GpaDerivedStatus | undefined, historical = false): string {
  if (historical) return "前年度参考値のため数値判定対象外";
  if (status === "safe match") return "全体評定の数値条件に安全一致";
  if (status === "safe no match") return "全体評定の数値条件に安全不一致";
  if (status === "safe numeric rule (GPA not supplied)") return "安全に数値照合できる条件";
  if (status === "conditional/review required") return "複合・条件付きのため要確認";
  return "数値では判定できません";
}

export function detailLink(dataset: string, version: string, recordId: string): string {
  return `/admissions/${encodeURIComponent(dataset)}/${encodeURIComponent(version)}/${encodeURIComponent(recordId)}`;
}

export function safeExternalLink(value: Scalar | undefined, label: string): string {
  if (typeof value !== "string" || !value) return `<span>${escapeHtml(label)}：URL未記録</span>`;
  try {
    const url = new URL(value);
    if (!['http:', 'https:'].includes(url.protocol)) throw new Error();
    return `<a href="${escapeHtml(url.href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}（外部サイト）</a>`;
  } catch { return `<span>${escapeHtml(label)}：URL形式エラー</span>`; }
}
