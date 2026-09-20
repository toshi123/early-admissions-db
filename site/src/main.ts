import "./styles.css";
import { trapDialogTab } from "./a11y";
import { loadDetail, loadSearchData, SiteDataError } from "./data";
import { detailLink, displayValue, escapeHtml, gpaLabel, safeExternalLink, stateClass, triStateLabel } from "./display";
import { emptyRequest, MULTI_FIELDS, searchRows } from "./search";
import type { DetailRecord, FilterOptions, MultiField, OptionValue, SearchRequest, SearchResult, SearchRow, SiteManifest } from "./types";
import { parseSearchParams, serializeRequest } from "./url-state";
import { registerSearchTools } from "./webmcp";

const PAGE_SIZE = 20;
const appStarted = performance.now();
const app = document.querySelector<HTMLDivElement>("#app")!;
if (!app) throw new Error("App root is missing");

interface AppMetrics extends Record<string, unknown> { firstRenderMs?: number; firstSearchMs?: number; filterChangeMs?: number; detailLoadMs?: number; }
declare global { interface Window { __EA_METRICS__?: AppMetrics; __EA_LAST_SEARCH_MS__?: number; } }

const FIELD_LABELS: Record<string, string> = {
  university: "大学名", institution_type: "大学種別", prefecture: "都道府県", academic_field: "学問分野（原文）",
  academic_field_group: "学問分野大分類（派生）", academic_field_mapping_status: "分野mapping status",
  selection_category: "選抜区分", exclusive_enrollment_status: "専願・併願",
  school_recommendation_required: "学校推薦", academic_record_required: "調査書等",
  common_test_required: "共通テスト要件", research_requirement_required: "研究実績要件",
  research_activity_level_status: "研究活動level", selection_interview: "面接", selection_oral_exam: "口頭試問",
  selection_presentation: "プレゼン", selection_essay: "小論文", selection_written_exam: "筆記",
  selection_common_test: "選考で共通テストを利用", stem_flag: "STEM区分", gpa_tenths: "GPA",
};
const GROUP_LABELS = new Map<string, string>();
let rows: SearchRow[] = [];
let options: FilterOptions;
let manifest: SiteManifest;
let applied = emptyRequest();
let currentResult: SearchResult = searchRows([], applied);
let cleanupWebMcp: () => void = () => undefined;

function updateMetrics(values: AppMetrics): void {
  window.__EA_METRICS__ = { ...window.__EA_METRICS__, ...values };
  document.documentElement.dataset.eaMetrics = JSON.stringify(window.__EA_METRICS__);
}

function optionMarkup(items: OptionValue[]): string {
  return items.filter((item) => item.value !== null).map((item) =>
    `<option value="${escapeHtml(item.value)}">${escapeHtml(item.display_label)}（${item.unfiltered_count.toLocaleString("ja-JP")}）</option>`).join("");
}

function multiControl(field: MultiField, label: string, items: OptionValue[], size = 4, hint = "複数選択可"): string {
  return `<label for="f-${field}">${escapeHtml(label)} <span class="hint">${escapeHtml(hint)}</span></label>
    <select id="f-${field}" data-field="${field}" multiple size="${size}">${optionMarkup(items)}</select>`;
}

function header(): string {
  return `<header class="topbar">
    <a class="brand" href="/search" data-route><span>2027</span><strong>早期入試検索</strong></a>
    <nav aria-label="主要ナビゲーション"><a href="/search" data-route>検索</a><a href="/about/data" data-route>データについて</a></nav>
  </header>`;
}

function filterPanel(): string {
  return `<div class="mobile-filter-bar"><button id="open-filters" type="button" aria-controls="filters" aria-expanded="false">条件を変更</button></div>
  <div id="filter-backdrop" class="filter-backdrop" hidden></div>
  <aside id="filters" class="filters" aria-label="検索条件">
    <div class="filters-heading"><div><p class="eyebrow">FILTER</p><h2>検索条件</h2></div><button id="close-filters" class="mobile-only" type="button" aria-label="検索条件を閉じる">閉じる</button></div>
    <details open><summary>基本</summary>
      <label for="university-search">大学名 <span class="hint">完全一致</span></label>
      <input id="university-search" type="search" list="university-list" placeholder="大学名を入力" autocomplete="off">
      <datalist id="university-list">${options.universities.map((item) => `<option value="${escapeHtml(item.value)}"></option>`).join("")}</datalist>
      ${multiControl("university", "選択中の大学", options.universities, 5, "⌘/Ctrlで複数")}
      ${multiControl("institution_type", "大学種別", options.institution_types, 3)}
      ${multiControl("prefecture", "都道府県", options.prefectures, 5)}
      ${multiControl("academic_field_group", "学問分野大分類", options.academic_field_groups, 6, "検索用の派生分類")}
      <label for="f-stem">STEM区分</label><select id="f-stem"><option value="">指定なし</option><option value="1">STEM</option><option value="0">非STEM</option></select>
      ${multiControl("selection_category", "選抜区分", options.selection_categories, 4)}
    </details>
    <details><summary>出願条件</summary>
      ${multiControl("exclusive_enrollment_status", "専願・併願", options.exclusive_enrollment_statuses)}
      ${multiControl("school_recommendation_required", "学校推薦要否", options.school_recommendation_required, 3)}
      ${multiControl("academic_record_required", "調査書等要否", options.academic_record_required, 3)}
      ${multiControl("common_test_required", "共通テスト要否", options.common_test_required)}
      ${multiControl("research_requirement_required", "研究実績要件", options.research_requirement_required)}
    </details>
    <details><summary>研究</summary>${multiControl("research_activity_level_status", "研究活動level", options.research_activity_level_status, 5)}</details>
    <details><summary>選考方法</summary>
      ${multiControl("selection_interview", "面接", options.selection_method_values.selection_interview)}
      ${multiControl("selection_oral_exam", "口頭試問", options.selection_method_values.selection_oral_exam)}
      ${multiControl("selection_presentation", "プレゼン", options.selection_method_values.selection_presentation)}
      ${multiControl("selection_essay", "小論文", options.selection_method_values.selection_essay)}
      ${multiControl("selection_written_exam", "筆記", options.selection_method_values.selection_written_exam)}
      ${multiControl("selection_common_test", "選考で共通テストを利用", options.selection_method_values.selection_common_test)}
    </details>
    <details><summary>GPA / 評定</summary>
      <label for="f-gpa">GPA（0.0〜5.0）</label><input id="f-gpa" type="number" min="0" max="5" step="0.1" inputmode="decimal">
      <label for="f-gpa-mode">表示mode</label><select id="f-gpa-mode"><option value="safe">safe：安全一致のみ</option><option value="review">review：安全一致＋要確認</option><option value="all">all：全状態</option></select>
      <p class="fine-print">全体評定の単純な数値条件だけを照合しています。出願可否や他の条件充足を示すものではありません。</p>
    </details>
    <details><summary>高度な条件</summary>
      ${multiControl("academic_field", "学問分野（原文）", options.raw_academic_fields, 7)}
      ${multiControl("academic_field_mapping_status", "分野mapping status", options.academic_field_mapping_statuses, 3)}
      <p class="fine-print">大分類は検索用の派生分類です。大学の公式分類は原文を確認してください。</p>
    </details>
    <div class="filter-actions"><button class="primary" id="apply-filters" type="button">この条件で検索</button><button id="clear-filters" type="button">条件をすべてクリア</button></div>
    <p class="sidebar-note">候補の絞り込み用です。出願資格や合格可能性を判定するものではありません。</p>
  </aside>`;
}

function selectedValues(field: MultiField): string[] {
  return [...document.querySelector<HTMLSelectElement>(`#f-${field}`)!.selectedOptions].map((option) => option.value);
}

function readControls(): SearchRequest | null {
  const request = emptyRequest();
  for (const field of MULTI_FIELDS) request[field] = selectedValues(field);
  const stem = document.querySelector<HTMLSelectElement>("#f-stem")!.value;
  request.stem_flag = stem === "1" ? true : stem === "0" ? false : null;
  const rawGpa = document.querySelector<HTMLInputElement>("#f-gpa")!.value.trim();
  if (rawGpa) {
    if (!/^(?:[0-4](?:\.\d)?|5(?:\.0)?)$/.test(rawGpa)) {
      showNotice("GPAは0.0〜5.0、小数1桁までで入力してください。", "error"); return null;
    }
    request.gpa_tenths = Math.round(Number(rawGpa) * 10);
    request.gpa_mode = document.querySelector<HTMLSelectElement>("#f-gpa-mode")!.value as SearchRequest["gpa_mode"];
  }
  return request;
}

function syncControls(request: SearchRequest): void {
  for (const field of MULTI_FIELDS) {
    const selected = new Set(request[field]);
    for (const option of document.querySelector<HTMLSelectElement>(`#f-${field}`)!.options) option.selected = selected.has(option.value);
  }
  document.querySelector<HTMLSelectElement>("#f-stem")!.value = request.stem_flag === null ? "" : request.stem_flag ? "1" : "0";
  document.querySelector<HTMLInputElement>("#f-gpa")!.value = request.gpa_tenths === null ? "" : (request.gpa_tenths / 10).toFixed(1);
  document.querySelector<HTMLSelectElement>("#f-gpa-mode")!.value = request.gpa_tenths === null ? "safe" : request.gpa_mode;
}

function showNotice(message: string, kind: "warning" | "error" = "warning"): void {
  const container = document.querySelector<HTMLDivElement>("#notices");
  if (container) container.innerHTML = `<div class="notice ${kind}" role="alert">${escapeHtml(message)}</div>`;
}

function activeFilters(request: SearchRequest): string {
  const groups: string[] = [];
  for (const field of MULTI_FIELDS) {
    if (!request[field].length) continue;
    const values = request[field].map((value) => field === "academic_field_group" ? (GROUP_LABELS.get(value) ?? value) : value);
    groups.push(`<div class="filter-group"><span>${escapeHtml(FIELD_LABELS[field])}：</span>${values.map((value) =>
      `<button class="filter-chip" type="button" data-remove-field="${field}" data-remove-value="${escapeHtml(value)}">${escapeHtml(value)} <span aria-hidden="true">×</span><span class="sr-only">を外す</span></button>`).join("<em>いずれか</em>")}</div>`);
  }
  if (request.stem_flag !== null) groups.push(`<div class="filter-group"><span>STEM区分：</span><button class="filter-chip" type="button" data-remove-field="stem_flag">${request.stem_flag ? "STEM" : "非STEM"} ×</button></div>`);
  if (request.gpa_tenths !== null) groups.push(`<div class="filter-group"><span>GPA：</span><button class="filter-chip" type="button" data-remove-field="gpa_tenths">${(request.gpa_tenths / 10).toFixed(1)} / ${request.gpa_mode} ×</button></div>`);
  return groups.length ? `<div class="active-filters" aria-label="適用中の条件">${groups.join("<span class=and>かつ</span>")}</div>` : `<p class="muted">条件指定なし</p>`;
}

function selectionChip(label: string, value: string | null): string {
  return `<span class="status-chip ${stateClass(value)}">${escapeHtml(label)}：${escapeHtml(triStateLabel(value, "あり", "なし"))}</span>`;
}

function resultCard(row: SearchRow): string {
  const groups = row.academic_field_groups.map((code) => GROUP_LABELS.get(code) ?? code).join(" / ") || "—";
  return `<article class="result-card">
    <div class="card-topline"><span>${displayValue(row.prefecture)} · ${escapeHtml(row.institution_type)}</span>${row.fallback_previous_year ? '<strong class="fallback-badge">前年度情報</strong>' : ""}</div>
    <h2><a href="${detailLink(row.source_dataset, row.source_version, row.record_id)}" data-route>${escapeHtml(row.university)}</a></h2>
    <p class="course">${displayValue(row.faculty_school)} <span aria-hidden="true">／</span> ${displayValue(row.department)}</p>
    <p><strong>${displayValue(row.selection_category)}</strong>　${displayValue(row.selection_name)}</p>
    <div class="card-grid">
      <div><span>募集人数</span>${displayValue(row.capacity)}</div><div><span>専願・併願</span>${displayValue(row.exclusive_enrollment_status)}</div>
      <div><span>学問分野（原文）</span>${displayValue(row.academic_field)}</div><div><span>大分類（派生）</span>${escapeHtml(groups)}</div>
      <div class="wide"><span>評定条件（原文）</span>${displayValue(row.gpa_requirement)}<small>${escapeHtml(gpaLabel(row.gpa_derived_status, row.gpa_source_value_status === "historical"))}</small></div>
      <div><span>共通テスト要件</span>${escapeHtml(triStateLabel(row.common_test_required, "必要", "なし"))}</div>
      <div><span>研究実績要件</span>${escapeHtml(triStateLabel(row.research_requirement_required, "あり", "なし"))}</div>
    </div>
    <div class="selection-chips">${selectionChip("面接", row.selection_interview)}${selectionChip("口頭試問", row.selection_oral_exam)}${selectionChip("プレゼン", row.selection_presentation)}${selectionChip("小論文", row.selection_essay)}${selectionChip("筆記", row.selection_written_exam)}</div>
    <div class="dates"><span>出願開始（原文） <strong>${displayValue(row.application_start)}</strong></span><span>出願終了（原文） <strong>${displayValue(row.application_end)}</strong></span></div>
    <a class="detail-cta" href="${detailLink(row.source_dataset, row.source_version, row.record_id)}" data-route>詳細と公式資料を確認 <span aria-hidden="true">→</span></a>
  </article>`;
}

function pagination(total: number, page: number): string {
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (pages <= 1) return "";
  return `<nav class="pagination" aria-label="検索結果ページ"><button type="button" data-page="${page - 1}" ${page <= 1 ? "disabled" : ""}>前へ</button><span>${page} / ${pages}ページ</span><button type="button" data-page="${page + 1}" ${page >= pages ? "disabled" : ""}>次へ</button></nav>`;
}

function renderResults(warnings: string[] = []): void {
  const started = performance.now();
  currentResult = searchRows(rows, applied);
  const pages = Math.max(1, Math.ceil(currentResult.rows.length / PAGE_SIZE));
  if (applied.page > pages) applied.page = pages;
  const pageRows = currentResult.rows.slice((applied.page - 1) * PAGE_SIZE, applied.page * PAGE_SIZE);
  const summary = currentResult.summary;
  document.querySelector("#notices")!.innerHTML = warnings.map((warning) => `<div class="notice warning" role="status">${escapeHtml(warning)}</div>`).join("");
  document.querySelector("#search-summary")!.innerHTML = `<p class="eyebrow">SEARCH RESULTS</p><div class="summary-line"><h1>${summary.total_matched_rows.toLocaleString("ja-JP")}件</h1><p>${summary.university_count.toLocaleString("ja-JP")}大学</p></div>
    ${applied.gpa_tenths === null ? "" : `<div class="gpa-summary"><span>安全一致 <strong>${summary.gpa_safe_match_rows}</strong></span><span>要確認 <strong>${summary.gpa_conditional_review_rows}</strong></span><span>数値判定不可 <strong>${summary.gpa_not_numerically_evaluable_rows}</strong></span></div>`}
    ${activeFilters(applied)}`;
  document.querySelector("#results")!.innerHTML = pageRows.length ? pageRows.map(resultCard).join("") : `<section class="empty"><h2>該当する入試がありません</h2><p>適用中の条件を1つずつ外して、もう一度確認してください。近似候補は自動生成していません。</p><button id="empty-clear" type="button">条件をすべてクリア</button></section>`;
  document.querySelector("#pagination")!.innerHTML = pagination(summary.total_matched_rows, applied.page);
  const elapsed = performance.now() - started;
  window.__EA_LAST_SEARCH_MS__ = elapsed;
  updateMetrics({ firstSearchMs: window.__EA_METRICS__?.firstSearchMs ?? elapsed });
}

function openFilters(): void {
  const panel = document.querySelector<HTMLElement>("#filters")!;
  panel.classList.add("open"); panel.setAttribute("role", "dialog"); panel.setAttribute("aria-modal", "true");
  document.querySelector<HTMLElement>("#filter-backdrop")!.hidden = false;
  document.querySelector<HTMLButtonElement>("#open-filters")!.setAttribute("aria-expanded", "true");
  panel.querySelector<HTMLElement>("button, input, select")?.focus();
}
function closeFilters(): void {
  const panel = document.querySelector<HTMLElement>("#filters")!;
  panel.classList.remove("open"); panel.removeAttribute("role"); panel.removeAttribute("aria-modal");
  document.querySelector<HTMLElement>("#filter-backdrop")!.hidden = true;
  document.querySelector<HTMLButtonElement>("#open-filters")!.setAttribute("aria-expanded", "false");
  document.querySelector<HTMLButtonElement>("#open-filters")!.focus();
}

function updateUrl(replace = false): void {
  const query = serializeRequest(applied).toString();
  const url = `/search${query ? `?${query}` : ""}`;
  history[replace ? "replaceState" : "pushState"]({}, "", url);
}

function clearSearch(): void { applied = emptyRequest(); syncControls(applied); updateUrl(); renderResults(); closeFilters(); }

function bindSearchEvents(): void {
  document.querySelector("#apply-filters")!.addEventListener("click", () => {
    const started = performance.now(); const next = readControls(); if (!next) return;
    applied = next; updateUrl(); renderResults(); closeFilters();
    updateMetrics({ filterChangeMs: performance.now() - started });
    document.querySelector<HTMLElement>("#search-summary")?.focus();
  });
  document.querySelector("#clear-filters")!.addEventListener("click", clearSearch);
  document.querySelector("#open-filters")!.addEventListener("click", openFilters);
  document.querySelector("#close-filters")!.addEventListener("click", closeFilters);
  document.querySelector("#filter-backdrop")!.addEventListener("click", closeFilters);
  document.querySelector<HTMLInputElement>("#university-search")!.addEventListener("change", (event) => {
    const input = event.currentTarget as HTMLInputElement;
    const select = document.querySelector<HTMLSelectElement>("#f-university")!;
    const exact = [...select.options].find((option) => option.value === input.value);
    if (exact) { exact.selected = true; input.value = ""; } else showNotice("一覧にある大学名を完全一致で選択してください。");
  });
  document.addEventListener("keydown", (event) => {
    const panel = document.querySelector<HTMLElement>("#filters");
    if (!panel?.classList.contains("open")) return;
    if (event.key === "Escape") { event.preventDefault(); closeFilters(); return; }
    trapDialogTab(panel, event);
  });
}

function searchPage(warnings: string[] = []): void {
  app.innerHTML = `${header()}<div class="search-shell">${filterPanel()}<main id="main" class="search-main"><div id="notices"></div><section id="search-summary" class="summary" tabindex="-1" aria-live="polite"></section><div id="results" class="results"></div><div id="pagination"></div></main></div><footer>2027年度早期入試データ · 最新の公式資料を必ず確認してください。</footer>`;
  syncControls(applied); bindSearchEvents(); renderResults(warnings);
}

const DETAIL_SECTIONS: Array<[string, string[]]> = [
  ["基本情報", ["admission_year", "institution_type", "university", "prefecture", "faculty_school", "department", "academic_field", "stem_flag", "selection_category", "selection_name", "slot_type", "capacity"]],
  ["出願条件", ["eligibility_graduation", "gpa_requirement", "english_requirement", "subject_prerequisites", "school_recommendation_required", "school_nomination_limit", "school_nomination_limit_total", "school_nomination_limit_rule", "exclusive_enrollment_status", "exclusive_enrollment", "common_test_required", "common_test_usage", "academic_record_required", "academic_record_type", "academic_record_detail"]],
  ["研究・探究", ["research_requirement_required", "research_requirement_summary", "research_activity_level_status", "research_activity_level_raw", "research_activity_detail"]],
  ["選考方法", ["selection_process", "selection_method_detail", "selection_document_review", "selection_interview", "interview_detail", "selection_oral_exam", "oral_exam_subjects", "oral_exam_detail", "selection_presentation", "presentation_detail", "selection_essay", "essay_detail", "selection_written_exam", "written_exam_detail", "selection_common_test", "selection_group_discussion", "selection_practical", "selection_aptitude_test", "documents_summary"]],
  ["日程", ["application_start", "application_end", "web_registration_period", "first_stage_result_date", "second_stage_start", "second_stage_end", "final_result_date"]],
  ["検証・公開状況", ["information_year", "publication_status", "current_year_release_expected", "source_status", "verification_grade", "verified_on", "detail_completeness_status", "detail_completeness_raw", "fallback_previous_year", "fallback_note", "notes"]],
];

const DETAIL_LABELS: Record<string, string> = {
  admission_year: "入試年度", institution_type: "大学種別", university: "大学", prefecture: "都道府県", faculty_school: "学部等", department: "学科等", academic_field: "学問分野（原文）", stem_flag: "STEM", selection_category: "選抜区分", selection_name: "選抜名称", slot_type: "枠・型", capacity: "募集人数",
  eligibility_graduation: "卒業等の要件", gpa_requirement: "評定条件（原文）", english_requirement: "英語要件", subject_prerequisites: "科目等の前提", school_recommendation_required: "学校推薦要否", school_nomination_limit: "学校別推薦人数", school_nomination_limit_total: "推薦人数合計", school_nomination_limit_rule: "推薦人数規則", exclusive_enrollment_status: "専願・併願status", exclusive_enrollment: "専願等の詳細", common_test_required: "共通テスト要件", common_test_usage: "共通テストの扱い", academic_record_required: "調査書等要否", academic_record_type: "調査書等の種類", academic_record_detail: "調査書等の詳細",
  research_requirement_required: "研究実績要件", research_requirement_summary: "研究実績要件概要", research_activity_level_status: "研究活動level（共通）", research_activity_level_raw: "研究活動level（原値）", research_activity_detail: "研究活動詳細",
  selection_process: "選考過程", selection_method_detail: "選考方法詳細", selection_document_review: "書類審査", selection_interview: "面接", interview_detail: "面接詳細", selection_oral_exam: "口頭試問", oral_exam_subjects: "口頭試問科目", oral_exam_detail: "口頭試問詳細", selection_presentation: "プレゼン", presentation_detail: "プレゼン詳細", selection_essay: "小論文", essay_detail: "小論文詳細", selection_written_exam: "筆記", written_exam_detail: "筆記詳細", selection_common_test: "選考で共通テストを利用", selection_group_discussion: "グループ討論", selection_practical: "実技", selection_aptitude_test: "適性検査", documents_summary: "提出書類概要",
  application_start: "出願開始（原文）", application_end: "出願終了（原文）", web_registration_period: "Web登録期間（原文）", first_stage_result_date: "第1段階結果（原文）", second_stage_start: "第2段階開始（原文）", second_stage_end: "第2段階終了（原文）", final_result_date: "最終結果（原文）",
  information_year: "情報年度", publication_status: "公開status", current_year_release_expected: "当年度公開見込", source_status: "source status", verification_grade: "検証grade", verified_on: "検証日", detail_completeness_status: "詳細充足status", detail_completeness_raw: "詳細充足（原値）", fallback_previous_year: "前年度fallback", fallback_note: "fallback注記", notes: "注記",
};

function recordGrid(record: Record<string, unknown>, fields: string[]): string {
  return `<dl class="detail-grid">${fields.map((field) => `<div><dt>${escapeHtml(DETAIL_LABELS[field] ?? field)}</dt><dd>${displayValue(record[field] as never)}</dd></div>`).join("")}</dl>`;
}

function researchRows(detail: DetailRecord): string {
  if (!detail.research_requirements.length) return `<p>構造化されたResearchRequirements子行はありません。</p>`;
  const keys = detail.research_requirements.map((row) => JSON.stringify(Object.fromEntries(Object.entries(row).filter(([key]) => key !== "research_rowid"))));
  const totals = new Map<string, number>(); keys.forEach((key) => totals.set(key, (totals.get(key) ?? 0) + 1));
  const seen = new Map<string, number>();
  return detail.research_requirements.map((row, index) => {
    const key = keys[index]; const total = totals.get(key)!; const ordinal = (seen.get(key) ?? 0) + 1; seen.set(key, ordinal);
    return `<article class="child-row"><h3>ResearchRequirements ${index + 1}${total > 1 ? ` <span>同一内容の原データ行 ${ordinal}/${total}</span>` : ""}</h3>${recordGrid(row, Object.keys(row))}</article>`;
  }).join("");
}

async function detailPage(parts: string[]): Promise<void> {
  app.innerHTML = `${header()}<main id="main" class="page"><p><a href="${history.state?.from ?? "/search"}" data-route>← 検索結果へ戻る</a></p><div class="loading" role="status">詳細データを読み込んでいます…</div></main>`;
  const [dataset, version, recordId] = parts.map((part) => decodeURIComponent(part));
  const row = rows.find((item) => item.source_dataset === dataset && item.source_version === version && item.record_id === recordId);
  if (!row) { dataError("指定された入試は検索データにありません。"); return; }
  try {
    const { detail, loadMs } = await loadDetail(manifest, row);
    updateMetrics({ detailLoadMs: loadMs });
    const admission = detail.admission;
    const assigned = new Set(DETAIL_SECTIONS.flatMap(([, fields]) => fields));
    const remaining = Object.keys(admission).filter((field) => !assigned.has(field) && !["admission_rowid", "source_url", "guideline_url", "schedule_url", "exclusive_enrollment_evidence_url", "previous_year_source_url"].includes(field));
    app.innerHTML = `${header()}<main id="main" class="page detail-page"><p><a href="/search${location.search}" data-route>← 検索へ戻る</a></p>
      ${admission.fallback_previous_year === true ? '<div class="fallback-warning" role="alert"><strong>前年度情報を参照しています。</strong>2027年度の公開状況と最新の公式資料を必ず確認してください。</div>' : ""}
      <header class="detail-title"><p class="eyebrow">${escapeHtml(String(admission.prefecture ?? "—"))} · ${escapeHtml(String(admission.institution_type ?? "—"))}</p><h1>${displayValue(admission.university as never)}</h1><p>${displayValue(admission.faculty_school as never)} ／ ${displayValue(admission.department as never)}</p><p><strong>${displayValue(admission.selection_category as never)}</strong>　${displayValue(admission.selection_name as never)}</p><p class="identity">${escapeHtml(dataset)} · v${escapeHtml(version)} · ${escapeHtml(recordId)}</p></header>
      <div class="eligibility-note">このページは出願資格や合格可能性を判定しません。原文と最新の公式資料を確認してください。</div>
      ${DETAIL_SECTIONS.map(([title, fields]) => `<section class="detail-section"><h2>${title}</h2>${recordGrid(admission, fields)}${title === "出願条件" ? `<h3>GPA derived layer</h3>${recordGrid(detail.gpa_derived, Object.keys(detail.gpa_derived))}` : ""}${title === "基本情報" ? `<h3>学問分野 derived layer</h3>${recordGrid(detail.academic_field_derived, Object.keys(detail.academic_field_derived).filter((key) => key !== "groups"))}<p>groups: ${escapeHtml(JSON.stringify(detail.academic_field_derived.groups ?? []))}</p>` : ""}</section>`).join("")}
      ${remaining.length ? `<section class="detail-section"><h2>その他の記録項目</h2>${recordGrid(admission, remaining)}</section>` : ""}
      <section class="detail-section"><h2>ResearchRequirements</h2><p>親flagと子行数は別の情報として表示し、一致を補正しません。</p>${researchRows(detail)}</section>
      <section class="detail-section"><h2>出典</h2><div class="source-links">${safeExternalLink(admission.guideline_url, "募集要項")}${safeExternalLink(admission.source_url, "公式情報")}${safeExternalLink(admission.schedule_url, "日程")}${safeExternalLink(admission.exclusive_enrollment_evidence_url, "専願根拠")}${safeExternalLink(admission.previous_year_source_url, "前年度資料")}</div></section>
    </main>${footer()}`;
  } catch (error) { dataError(error instanceof SiteDataError ? error.message : "詳細データを読み込めませんでした。"); }
}

function footer(): string { return `<footer>このSiteは候補の絞り込み用です。最新の公式資料を必ず確認してください。</footer>`; }

function aboutPage(): void {
  const sources = Object.entries(manifest.input.source_versions).map(([name, version]) => `<li>${escapeHtml(name)}：${escapeHtml(version)}</li>`).join("");
  app.innerHTML = `${header()}<main id="main" class="page about"><p class="eyebrow">DATA GUIDE</p><h1>データについて</h1>
    <section><h2>versionとbuild</h2><dl class="detail-grid"><div><dt>Site-data schema</dt><dd>${manifest.site_data_schema_version}</dd></div><div><dt>build ID</dt><dd>${manifest.build_id}</dd></div><div><dt>build日時（UTC）</dt><dd>${escapeHtml(manifest.build_timestamp_utc)}</dd></div><div><dt>入試件数</dt><dd>${manifest.counts.search_rows.toLocaleString("ja-JP")}</dd></div></dl><h3>source versions</h3><ul>${sources}</ul></section>
    <section><h2>検索結果の意味</h2><p>このSiteは条件に一致する候補を絞り込むためのもので、出願資格・条件充足・合格可能性を判定しません。</p><p>GPAは、現在年度の全体評定に対する単純な数値条件として安全に解釈できる行だけを自動照合します。複合条件、科目別、分岐、前年度参考値などは自動判定しません。</p></section>
    <section><h2>学問分野</h2><p>19の大分類は検索用の派生分類です。大学の公式分類は結果と詳細にある原文を確認してください。review_required / unmappedを推測で分類しません。</p></section>
    <section><h2>No / Unknown / null</h2><ul><li><strong>No</strong>：なし・不要と明示</li><li><strong>Unknown</strong>：不明</li><li><strong>—（null）</strong>：未記録または非該当</li></ul><p>これらは相互に置き換えません。</p></section>
    <section><h2>前年度情報と公式確認</h2><p>「前年度情報」は2027年度の情報ではないfallbackです。必ず最新の公開状況と公式資料を確認してください。</p></section>
  </main>${footer()}`;
}

function dataError(message: string): void {
  app.innerHTML = `${header()}<main id="main" class="page"><section class="error" role="alert"><p class="eyebrow">DATA ERROR</p><h1>データを表示できません</h1><p>${escapeHtml(message)}</p><p>検索結果0件とは区別しています。Site-dataのmanifest、build ID、artifactを確認してください。</p><a href="/search" data-route>検索画面へ戻る</a></section></main>${footer()}`;
}

async function route(replace = false): Promise<void> {
  const path = location.pathname.replace(/\/+$/, "") || "/";
  if (path === "/about/data") { aboutPage(); return; }
  const match = path.match(/^\/admissions\/([^/]+)\/([^/]+)\/([^/]+)$/);
  if (match) { await detailPage(match.slice(1)); return; }
  if (path !== "/" && path !== "/search") { app.innerHTML = `${header()}<main id="main" class="page"><h1>ページが見つかりません</h1><a href="/search" data-route>検索へ</a></main>${footer()}`; return; }
  const parsed = parseSearchParams(new URLSearchParams(location.search), options);
  applied = parsed.request;
  if (path === "/" || replace) updateUrl(true);
  searchPage(parsed.warnings);
}

document.addEventListener("click", (event) => {
  const target = event.target as HTMLElement;
  const link = target.closest<HTMLAnchorElement>("a[data-route]");
  if (link && link.origin === location.origin) { event.preventDefault(); history.pushState({ from: location.pathname + location.search }, "", link.href); void route(); return; }
  const page = target.closest<HTMLButtonElement>("button[data-page]");
  if (page) { applied.page = Number(page.dataset.page); updateUrl(); renderResults(); document.querySelector<HTMLElement>("#search-summary")?.focus(); return; }
  const remove = target.closest<HTMLButtonElement>("button[data-remove-field]");
  if (remove) {
    const field = remove.dataset.removeField!;
    if (field === "stem_flag") applied.stem_flag = null;
    else if (field === "gpa_tenths") { applied.gpa_tenths = null; applied.gpa_mode = "all"; }
    else {
      const typed = field as MultiField; const raw = remove.dataset.removeValue!;
      const value = typed === "academic_field_group" ? [...GROUP_LABELS].find(([, label]) => label === raw)?.[0] ?? raw : raw;
      applied[typed] = applied[typed].filter((item) => item !== value);
    }
    applied.page = 1; syncControls(applied); updateUrl(); renderResults(); return;
  }
  if (target.closest("#empty-clear")) clearSearch();
});
window.addEventListener("popstate", () => { void route(); });

try {
  const loaded = await loadSearchData();
  rows = loaded.rows; options = loaded.options; manifest = loaded.manifest;
  for (const group of options.academic_field_groups) GROUP_LABELS.set(group.value, group.display_label);
  updateMetrics({ ...loaded.metrics });
  await route(true);
  updateMetrics({ firstRenderMs: performance.now() - appStarted });
  cleanupWebMcp();
  cleanupWebMcp = registerSearchTools(async (partial) => {
    if (!location.pathname.startsWith("/search")) { history.pushState({}, "", "/search"); await route(); }
    const allowedPrefectures = new Set(options.prefectures.flatMap((item) => item.value === null ? [] : [item.value]));
    const allowedInstitutionTypes = new Set(options.institution_types.flatMap((item) => item.value === null ? [] : [item.value]));
    if (partial.prefecture?.some((value) => !allowedPrefectures.has(value))) throw new Error("unknown prefecture");
    if (partial.institution_type?.some((value) => !allowedInstitutionTypes.has(value))) throw new Error("unknown institution_type");
    const next = { ...applied, ...partial, page: 1 } as SearchRequest;
    if (next.gpa_tenths !== null && next.gpa_mode === "all" && partial.gpa_mode === undefined) next.gpa_mode = "safe";
    applied = next; syncControls(applied); updateUrl(); renderResults();
    return { total: currentResult.summary.total_matched_rows, universities: currentResult.summary.university_count };
  }, () => ({ total: currentResult.summary.total_matched_rows, universities: currentResult.summary.university_count, url: location.href }));
} catch (error) {
  dataError(error instanceof SiteDataError ? error.message : "Site-dataの読み込み中に問題が発生しました。");
}
