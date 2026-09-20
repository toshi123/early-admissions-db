import "./styles.css";
import { loadDetail, loadSearchData, SiteDataError } from "./data";
import { displayValue, escapeHtml, safeExternalLink } from "./display";
import { inValueOrder } from "./form-options";
import { bindFloatingLiveCount, type FloatingLiveCountController } from "./floating-live-count";
import { headerSearchHref, rememberLastSearch } from "./last-search-state";
import { submitSearchNavigation } from "./navigation";
import { emptyRequest, searchRows } from "./search";
import {
  evaluateSearchDraft,
  liveSearchResult,
  liveSummaryPresentation,
  universitySuggestions,
} from "./search-ui";
import {
  expandedUniversitiesFromHistory,
  groupAdmissionsByUniversity,
  paginateUniversityGroups,
  toggleExpandedUniversity,
  UNIVERSITY_GROUP_PAGE_SIZE,
  universityGroupMarkup,
  universityResultsHistoryState,
} from "./university-groups";
import type {
  DetailRecord,
  FilterOptions,
  SearchRequest,
  SearchResult,
  SearchRow,
  SiteManifest,
} from "./types";
import {
  parseSearchParams,
  serializeRequest,
  serializeSearchFormState,
} from "./url-state";
import { registerSearchTools } from "./webmcp";

const app = document.querySelector<HTMLDivElement>("#app")!;
let rows: SearchRow[] = [];
let options: FilterOptions;
let manifest: SiteManifest;
let applied = emptyRequest();
let currentResult: SearchResult = searchRows([], applied);
let universityQuery = "";
let gpaQuery = "";
let cleanupWebMcp: () => void = () => undefined;
let floatingLiveCount: FloatingLiveCountController | null = null;
let expandedUniversities = new Set<string>();
const groupLabels = new Map<string, string>();

if ("scrollRestoration" in history) history.scrollRestoration = "manual";

const header = () => {
  const path = location.pathname.replace(/\/+$/, "") || "/";
  const searchCurrent = path === "/search" || path === "/results" || path.startsWith("/admissions/");
  const aboutCurrent = path === "/about/data";
  return `<header class="site-header"><div class="site-header__inner"><a class="brand" href="/search" data-route><strong>2027年度 早期入試検索</strong></a><nav aria-label="主要ナビゲーション"><ul class="global-nav"><li><a id="header-search-link" class="global-nav__link" href="${headerSearchHref(path, applied)}" data-route${searchCurrent ? ' aria-current="page"' : ""}>検索</a></li><li><a class="global-nav__link" href="/about/data" data-route${aboutCurrent ? ' aria-current="page"' : ""}>データについて</a></li></ul></nav></div></header>`;
};
const footer = () => `<footer>候補の絞り込み用です。出願前に最新の公式資料を必ず確認してください。</footer>`;
const selected = (field: string, value: string) => (
  (applied[field as keyof SearchRequest] as string[]) ?? []
).includes(value);

function checks(
  field: string,
  items: Array<{ value: string | null; display_label: string }>,
  labels: Record<string, string> = {},
): string {
  return `<div class="check-grid">${items
    .filter((item) => item.value !== null)
    .map((item) => `<label class="choice choice--checkbox"><span class="choice__control"><input type="checkbox" name="${field}" value="${escapeHtml(item.value!)}" ${selected(field, item.value!) ? "checked" : ""}></span><span class="choice__label">${escapeHtml(labels[item.value!] ?? item.display_label)}</span></label>`)
    .join("")}</div>`;
}

function radios(field: string, choices: Array<[string, string]>): string {
  const current = ((applied[field as keyof SearchRequest] as string[]) ?? [])[0] ?? "";
  return `<div class="radio-row">${choices
    .map(([value, label]) => `<label class="choice choice--radio"><span class="choice__control"><input type="radio" name="${field}" value="${value}" ${current === value ? "checked" : ""}></span><span class="choice__label">${label}</span></label>`)
    .join("")}</div>`;
}

function searchForm(): string {
  const groups = options.academic_field_groups.map((item) => ({
    value: item.value,
    display_label: item.display_label,
  }));
  const institutionTypes = inValueOrder(options.institution_types, ["国立", "公立", "私立"]);
  const exclusive = inValueOrder(
    options.exclusive_enrollment_statuses.filter((item) => ["専願", "併願可", "条件付き", "不明"].includes(item.value ?? "")),
    ["専願", "併願可", "条件付き", "不明"],
  );
  const methods: Array<[string, string]> = [
    ["selection_interview", "面接"],
    ["selection_oral_exam", "口頭試問"],
    ["selection_presentation", "プレゼン"],
    ["selection_essay", "小論文"],
    ["selection_written_exam", "筆記試験"],
  ];
  const regions = ["北海道・東北", "関東", "中部", "近畿", "中国・四国", "九州・沖縄"];
  const prefectures = regions
    .map((region) => `<section class="prefecture-region"><h3>${region}</h3>${checks("prefecture_membership", options.prefecture_memberships.filter((item) => item.region === region))}</section>`)
    .join("");
  return `<form id="search-form" class="search-form" novalidate>
    <header class="form-intro"><h1>条件から入試を探す</h1><p>異なる項目はすべて満たすもの、同じ項目の複数選択はいずれかに一致するものを検索します。</p></header>
    <output id="live-summary" class="live-summary" aria-live="polite"></output>
    <div id="floating-live-summary" class="floating-live-summary" aria-hidden="true"><span id="floating-live-summary-text"></span></div>
    <fieldset><legend>1. 大学名</legend><label class="input-label" for="university-input">大学名を入力</label><div class="university-combobox"><input id="university-input" class="text-input" type="text" value="${escapeHtml(universityQuery)}" autocomplete="off" role="combobox" aria-autocomplete="list" aria-controls="university-suggestions" aria-expanded="false" placeholder="大学名の一部を入力"><div id="university-suggestions" class="suggestions" role="listbox" hidden></div></div><p class="help">表示された候補から1校を選択してください。</p></fieldset>
    <fieldset><legend>2. 学問分野</legend><p class="help">複数選択可</p>${checks("academic_field_group", groups)}</fieldset>
    <fieldset><legend>3. 大学種別</legend>${checks("institution_type", institutionTypes)}</fieldset>
    <fieldset><legend>4. 専願・併願</legend>${checks("exclusive_enrollment_status", exclusive, { 不明: "不明・記載確認できず" })}</fieldset>
    <fieldset><legend>5. 共通テスト</legend>${radios("common_test_required", [["", "指定なし"], ["Yes", "あり"], ["No", "なし"]])}</fieldset>
    <fieldset><legend>6. 研究業績</legend>${radios("research_requirement_required", [["", "指定なし"], ["Yes", "必要"], ["No", "必要なし"]])}</fieldset>
    <fieldset><legend>7. 英語資格</legend>${radios("english_requirement_status", [["", "指定なし"], ["required", "必要"], ["not_required", "必要なし"]])}</fieldset>
    <fieldset><legend>8. 試験内容</legend><p class="help">複数選ぶと、すべて実施する入試に絞ります。</p><div class="check-grid">${methods.map(([field, label]) => `<label class="choice choice--checkbox"><span class="choice__control"><input type="checkbox" name="${field}" value="Yes" ${selected(field, "Yes") ? "checked" : ""}></span><span class="choice__label">${label}</span></label>`).join("")}</div></fieldset>
    <fieldset><legend>9. 評定</legend><label class="input-label" for="gpa">評定値（0.0〜5.0）</label><input id="gpa" class="text-input" type="text" inputmode="decimal" value="${escapeHtml(gpaQuery)}" placeholder="例：3.8"><p class="help">単純な全体評定の数値条件のみを安全に照合します。</p></fieldset>
    <fieldset class="prefecture-fieldset"><details id="prefecture-details" class="disclosure"><summary><svg class="disclosure__icon" width="24" height="24" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="11" fill="currentcolor"/><circle class="disclosure__icon-circle" cx="12" cy="12" r="8" fill="currentcolor"/><path class="disclosure__icon-triangle" d="M17 10H7L12 15L17 10Z" fill="Canvas"/></svg><span>10. 都道府県で絞り込む <span id="prefecture-count" class="selected-count"></span></span></summary><div class="prefecture-regions">${prefectures}</div><button id="clear-prefectures" class="button button--text" type="button">選択をクリア</button></details></fieldset>
    <div id="form-error" class="notice error" role="alert" hidden></div>
    <div class="form-actions"><button class="button button--primary" type="submit">この条件で検索</button><button id="clear-form" class="button button--outline" type="button">条件をクリア</button></div>
  </form>`;
}

function readBaseForm(): SearchRequest {
  const form = document.querySelector<HTMLFormElement>("#search-form")!;
  const request = emptyRequest();
  for (const field of [
    "academic_field_group",
    "institution_type",
    "exclusive_enrollment_status",
    "selection_interview",
    "selection_oral_exam",
    "selection_presentation",
    "selection_essay",
    "selection_written_exam",
    "prefecture_membership",
  ] as const) {
    request[field] = [...form.querySelectorAll<HTMLInputElement>(`input[name="${field}"]:checked`)]
      .map((input) => input.value);
  }
  for (const field of [
    "common_test_required",
    "research_requirement_required",
    "english_requirement_status",
  ] as const) {
    const value = form.querySelector<HTMLInputElement>(`input[name="${field}"]:checked`)?.value ?? "";
    request[field] = value ? [value] : [];
  }
  return request;
}

function updatePrefectureCount(): void {
  const count = document.querySelectorAll('input[name="prefecture_membership"]:checked').length;
  const output = document.querySelector("#prefecture-count");
  if (output) output.textContent = count ? `（${count}件選択）` : "";
}

function renderSuggestions(): void {
  const input = document.querySelector<HTMLInputElement>("#university-input")!;
  const list = document.querySelector<HTMLElement>("#university-suggestions")!;
  const suggestions = universitySuggestions(options, input.value);
  list.innerHTML = suggestions
    .map((value) => `<button type="button" role="option" data-university="${escapeHtml(value)}">${escapeHtml(value)}</button>`)
    .join("");
  list.hidden = suggestions.length === 0 || options.universities.some((item) => item.value === input.value);
  input.setAttribute("aria-expanded", list.hidden ? "false" : "true");
}

function refreshForm(syncUrl = true): ReturnType<typeof evaluateSearchDraft> {
  const input = document.querySelector<HTMLInputElement>("#university-input")!;
  const gpa = document.querySelector<HTMLInputElement>("#gpa")!;
  const evaluation = evaluateSearchDraft(readBaseForm(), options, input.value, gpa.value);
  applied = evaluation.request;
  universityQuery = evaluation.universityQuery;
  gpaQuery = evaluation.gpaQuery;
  input.setAttribute("aria-invalid", evaluation.errors.some((error) => error.startsWith("大学名")) ? "true" : "false");
  gpa.setAttribute("aria-invalid", evaluation.errors.some((error) => error.startsWith("評定")) ? "true" : "false");
  const error = document.querySelector<HTMLElement>("#form-error")!;
  error.hidden = evaluation.errors.length === 0;
  error.textContent = evaluation.errors.join(" ");
  const result = liveSearchResult(rows, evaluation);
  const presentation = liveSummaryPresentation(result);
  const live = document.querySelector<HTMLOutputElement>("#live-summary")!;
  live.textContent = presentation.liveText;
  floatingLiveCount?.update(presentation.floatingText, presentation.invalid);
  const submit = document.querySelector<HTMLButtonElement>('#search-form button[type="submit"]')!;
  submit.disabled = evaluation.errors.length > 0;
  updatePrefectureCount();
  const headerLink = document.querySelector<HTMLAnchorElement>("#header-search-link");
  if (headerLink) headerLink.href = headerSearchHref("/search", evaluation.request);
  if (evaluation.errors.length === 0) rememberLastSearch(evaluation.request);
  if (syncUrl) {
    const query = serializeSearchFormState(evaluation.request, universityQuery, gpaQuery).toString();
    history.replaceState(history.state ?? {}, "", `/search${query ? `?${query}` : ""}`);
  }
  return evaluation;
}

function bindForm(): void {
  const form = document.querySelector<HTMLFormElement>("#search-form")!;
  const university = document.querySelector<HTMLInputElement>("#university-input")!;
  floatingLiveCount = bindFloatingLiveCount(
    document.querySelector<HTMLOutputElement>("#live-summary")!,
    document.querySelector<HTMLElement>("#floating-live-summary")!,
    document.querySelector<HTMLElement>("#floating-live-summary-text")!,
  );
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const evaluation = refreshForm(false);
    if (evaluation.errors.length) return;
    rememberCurrentView();
    await submitSearchNavigation(evaluation.request, {
      pushState: history.pushState.bind(history),
      render: () => route(),
      scrollTo: (settings) => window.scrollTo(settings),
    });
  });
  form.addEventListener("change", () => refreshForm());
  form.addEventListener("input", (event) => {
    if (event.target === university) renderSuggestions();
    refreshForm();
  });
  university.addEventListener("focus", renderSuggestions);
  university.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      const list = document.querySelector<HTMLElement>("#university-suggestions")!;
      list.hidden = true;
      university.setAttribute("aria-expanded", "false");
    }
    if (event.key === "ArrowDown") {
      const first = document.querySelector<HTMLButtonElement>("#university-suggestions button");
      if (first) {
        event.preventDefault();
        first.focus();
      }
    }
  });
  document.querySelector("#university-suggestions")!.addEventListener("click", (event) => {
    const button = (event.target as HTMLElement).closest<HTMLButtonElement>("button[data-university]");
    if (!button) return;
    university.value = button.dataset.university ?? "";
    renderSuggestions();
    refreshForm();
    university.focus();
  });
  document.querySelector("#clear-form")!.addEventListener("click", () => {
    applied = emptyRequest();
    universityQuery = "";
    gpaQuery = "";
    history.replaceState(history.state ?? {}, "", "/search");
    searchPage([]);
  });
  document.querySelector("#clear-prefectures")!.addEventListener("click", () => {
    document.querySelectorAll<HTMLInputElement>('input[name="prefecture_membership"]:checked')
      .forEach((input) => { input.checked = false; });
    refreshForm();
  });
  refreshForm(false);
  const details = document.querySelector<HTMLDetailsElement>("#prefecture-details");
  if (details && history.state?.prefectureOpen === true) details.open = true;
}

function searchPage(warnings: string[]): void {
  floatingLiveCount?.disconnect();
  floatingLiveCount = null;
  app.innerHTML = `${header()}<main id="main" class="page search-page">${warnings.map((warning) => `<div class="notice">${escapeHtml(warning)}</div>`).join("")}${searchForm()}</main>${footer()}`;
  bindForm();
}

function summaryText(): string {
  const parts: string[] = [];
  if (applied.university.length) parts.push(`大学：${applied.university[0]}`);
  if (applied.academic_field_group.length) parts.push(`学問分野：${applied.academic_field_group.map((value) => groupLabels.get(value) ?? value).join("、")}`);
  if (applied.institution_type.length) parts.push(`大学種別：${applied.institution_type.join("、")}`);
  if (applied.exclusive_enrollment_status.length) parts.push(`専願・併願：${applied.exclusive_enrollment_status.join("、")}`);
  if (applied.common_test_required.length) parts.push(`共通テスト：${applied.common_test_required[0] === "Yes" ? "あり" : "なし"}`);
  if (applied.research_requirement_required.length) parts.push(`研究業績：${applied.research_requirement_required[0] === "Yes" ? "必要" : "必要なし"}`);
  if (applied.english_requirement_status.length) parts.push(`英語資格：${applied.english_requirement_status[0] === "required" ? "必要" : "必要なし"}`);
  const methods: Array<[keyof SearchRequest, string]> = [
    ["selection_interview", "面接"],
    ["selection_oral_exam", "口頭試問"],
    ["selection_presentation", "プレゼン"],
    ["selection_essay", "小論文"],
    ["selection_written_exam", "筆記"],
  ];
  const selectedMethods = methods.filter(([field]) => (applied[field] as string[]).length).map(([, label]) => label);
  if (selectedMethods.length) parts.push(`試験：${selectedMethods.join("、")}`);
  if (applied.gpa_tenths !== null) parts.push(`評定：${(applied.gpa_tenths / 10).toFixed(1)}（安全照合）`);
  if (applied.prefecture_membership.length) parts.push(`都道府県：${applied.prefecture_membership.join("、")}`);
  return parts.length ? parts.join(" ／ ") : "条件指定なし";
}

function resultsPage(warnings: string[]): void {
  floatingLiveCount?.disconnect();
  floatingLiveCount = null;
  rememberLastSearch(applied);
  currentResult = searchRows(rows, applied);
  const universityGroups = groupAdmissionsByUniversity(currentResult.rows);
  const pages = Math.max(1, Math.ceil(universityGroups.length / UNIVERSITY_GROUP_PAGE_SIZE));
  if (applied.page > pages) applied.page = pages;
  const shown = paginateUniversityGroups(universityGroups, applied.page);
  const firstGroupIndex = (applied.page - 1) * UNIVERSITY_GROUP_PAGE_SIZE;
  const query = serializeRequest({ ...applied, page: 1 }).toString();
  const previous = applied.page > 1
    ? `<button class="button button--text" data-page="${applied.page - 1}"><span aria-hidden="true">←</span> 前のページ</button>`
    : '<span class="pagination__spacer" aria-hidden="true"></span>';
  const next = applied.page < pages
    ? `<button class="button button--text" data-page="${applied.page + 1}">次のページ <span aria-hidden="true">→</span></button>`
    : '<span class="pagination__spacer" aria-hidden="true"></span>';
  app.innerHTML = `${header()}<main id="main" class="page results-page"><section class="results-summary"><h1>検索結果</h1><p class="result-count">${currentResult.summary.total_matched_rows.toLocaleString("ja-JP")}件・${currentResult.summary.university_count.toLocaleString("ja-JP")}大学</p><p class="active-filter-summary">${escapeHtml(summaryText())}</p><a href="/search${query ? `?${query}` : ""}" data-route>検索条件を変更</a></section>${warnings.map((warning) => `<div class="notice">${escapeHtml(warning)}</div>`).join("")}<div class="results university-results" role="list">${shown.length ? shown.map((group, index) => universityGroupMarkup(group, firstGroupIndex + index, expandedUniversities.has(group.university), applied.gpa_tenths !== null)).join("") : '<section class="empty"><h2>該当する入試がありません</h2><p>条件を減らして検索してください。</p></section>'}</div>${pages > 1 ? `<nav class="pagination" aria-label="検索結果のページ">${previous}<span class="pagination__counter">${applied.page} / ${pages}</span>${next}</nav>` : ""}</main>${footer()}`;
}

const sections: Array<[string, string[]]> = [
  ["基本情報", ["admission_year", "institution_type", "university", "prefecture", "faculty_school", "department", "academic_field", "selection_category", "selection_name", "slot_type", "capacity"]],
  ["選考方法", ["selection_process", "selection_method_detail", "selection_document_review", "selection_interview", "interview_detail", "selection_oral_exam", "oral_exam_subjects", "oral_exam_detail", "selection_presentation", "presentation_detail", "selection_essay", "essay_detail", "selection_written_exam", "written_exam_detail", "selection_common_test", "selection_group_discussion", "selection_practical", "selection_aptitude_test", "documents_summary"]],
  ["出願条件", ["eligibility_graduation", "gpa_requirement", "english_requirement", "subject_prerequisites", "school_recommendation_required", "school_nomination_limit", "school_nomination_limit_total", "school_nomination_limit_rule", "exclusive_enrollment_status", "exclusive_enrollment", "common_test_required", "common_test_usage", "academic_record_required", "academic_record_type", "academic_record_detail"]],
  ["日程", ["application_start", "application_end", "web_registration_period", "first_stage_result_date", "second_stage_start", "second_stage_end", "final_result_date"]],
  ["研究", ["research_requirement_required", "research_requirement_summary", "research_activity_level_status", "research_activity_level_raw", "research_activity_detail"]],
];
const labels: Record<string, string> = {
  admission_year: "入試年度", institution_type: "大学種別", university: "大学", prefecture: "都道府県", faculty_school: "学部等", department: "学科等", academic_field: "学問分野（原文）", selection_category: "選抜区分", selection_name: "選抜名称", slot_type: "枠・型", capacity: "募集人数", selection_process: "選考過程", selection_method_detail: "選考方法詳細", selection_document_review: "書類審査", selection_interview: "面接", interview_detail: "面接詳細", selection_oral_exam: "口頭試問", oral_exam_subjects: "口頭試問科目", oral_exam_detail: "口頭試問詳細", selection_presentation: "プレゼン", presentation_detail: "プレゼン詳細", selection_essay: "小論文", essay_detail: "小論文詳細", selection_written_exam: "筆記", written_exam_detail: "筆記詳細", selection_common_test: "共通テスト利用", selection_group_discussion: "グループ討論", selection_practical: "実技", selection_aptitude_test: "適性検査", documents_summary: "提出書類", eligibility_graduation: "卒業等の要件", gpa_requirement: "評定条件（原文）", english_requirement: "英語資格・検定条件（原文）", subject_prerequisites: "科目等の前提", school_recommendation_required: "学校推薦", school_nomination_limit: "学校別推薦人数", school_nomination_limit_total: "推薦人数合計", school_nomination_limit_rule: "推薦人数規則", exclusive_enrollment_status: "専願・併願", exclusive_enrollment: "専願等の詳細", common_test_required: "共通テスト", common_test_usage: "共通テストの扱い", academic_record_required: "調査書等", academic_record_type: "調査書等の種類", academic_record_detail: "調査書等の詳細", application_start: "出願開始（原文）", application_end: "出願終了（原文）", web_registration_period: "ウェブ登録期間（原文）", first_stage_result_date: "第1段階結果（原文）", second_stage_start: "第2段階開始（原文）", second_stage_end: "第2段階終了（原文）", final_result_date: "最終結果（原文）", research_requirement_required: "研究実績要件", research_requirement_summary: "研究実績要件概要", research_activity_level_status: "研究活動水準", research_activity_level_raw: "研究活動水準（原文）", research_activity_detail: "研究活動詳細",
};
Object.assign(labels, { stem_flag: "理系区分", exclusive_enrollment_evidence: "専願・併願の根拠", exclusive_enrollment_evidence_page: "根拠ページ", source_status: "情報源の状態", detail_completeness_status: "詳細情報の充足状況", detail_completeness_raw: "詳細情報の充足状況（原文）", verification_grade: "確認水準", verified_on: "確認日", notes: "注記", information_year: "情報年度", publication_status: "公開状況", current_year_release_expected: "当年度公開見込み", fallback_previous_year: "前年度情報", fallback_note: "前年度情報の注記" });
const formatted = (value: unknown) => value === "Yes" ? "あり" : value === "No" ? "なし" : value === "Unknown" ? "不明" : displayValue(value as never);
const grid = (record: Record<string, unknown>, fields: string[]) => `<dl class="detail-grid">${fields.map((field) => `<div><dt>${escapeHtml(labels[field] ?? "記録項目")}</dt><dd>${formatted(record[field])}</dd></div>`).join("")}</dl>`;
function research(detail: DetailRecord): string {
  return detail.research_requirements.length
    ? detail.research_requirements.map((row, index) => `<article class="child-row"><h3>詳細 ${index + 1}</h3>${grid(row, Object.keys(row).filter((key) => key !== "research_rowid"))}</article>`).join("")
    : "<p>構造化された研究要件の詳細行はありません。</p>";
}

async function detailPage(parts: string[]): Promise<void> {
  floatingLiveCount?.disconnect();
  floatingLiveCount = null;
  const [dataset, version, id] = parts.map(decodeURIComponent);
  const row = rows.find((item) => item.source_dataset === dataset && item.source_version === version && item.record_id === id);
  if (!row) { dataError("指定された入試が見つかりません。"); return; }
  app.innerHTML = `${header()}<main id="main" class="page">読み込んでいます…</main>`;
  try {
    const { detail } = await loadDetail(manifest, row);
    const admission = detail.admission;
    const assigned = new Set(sections.flatMap(([, fields]) => fields));
    const hidden = new Set(["admission_rowid", "source_url", "guideline_url", "schedule_url", "exclusive_enrollment_evidence_url", "previous_year_source_url"]);
    const remaining = Object.keys(admission).filter((field) => !assigned.has(field) && !hidden.has(field));
    app.innerHTML = `${header()}<main id="main" class="page detail-page"><p><a href="${history.state?.from ?? "/results"}" data-route>← 検索結果へ戻る</a></p>${admission.fallback_previous_year === true ? '<div class="fallback-warning"><strong>前年度情報を参照しています。</strong> 2027年度の公式資料を確認してください。</div>' : ""}<header class="detail-title"><p>${displayValue(admission.prefecture as never)} ／ ${displayValue(admission.institution_type as never)}</p><h1>${displayValue(admission.university as never)}</h1><p>${displayValue(admission.faculty_school as never)} ／ ${displayValue(admission.department as never)}</p><p><strong>${displayValue(admission.selection_category as never)}</strong>　${displayValue(admission.selection_name as never)}</p></header><p class="eligibility-note">このページは出願資格や合格可能性を判定しません。</p>${sections.map(([title, fields]) => `<section class="detail-section"><h2>${title}</h2>${grid(admission, fields)}${title === "研究" ? research(detail) : ""}</section>`).join("")}<section class="detail-section"><h2>その他の記録項目</h2>${grid(admission, remaining)}</section><section class="detail-section"><h2>出典</h2><div class="source-links">${safeExternalLink(admission.guideline_url, "募集要項")}${safeExternalLink(admission.source_url, "公式情報")}${safeExternalLink(admission.schedule_url, "日程")}${safeExternalLink(admission.exclusive_enrollment_evidence_url, "専願根拠")}${safeExternalLink(admission.previous_year_source_url, "前年度資料")}</div><details class="developer-details"><summary>データ識別情報</summary><p>${escapeHtml(dataset)} ／ ${escapeHtml(version)} ／ ${escapeHtml(id)}</p></details></section></main>${footer()}`;
  } catch (error) {
    dataError(error instanceof SiteDataError ? error.message : "詳細データを読み込めませんでした。");
  }
}

function aboutPage(): void {
  floatingLiveCount?.disconnect();
  floatingLiveCount = null;
  app.innerHTML = `${header()}<main id="main" class="page narrow about"><h1>データについて</h1><section><h2>検索結果の意味</h2><p>条件に一致する候補を絞り込むためのもので、出願資格・条件充足・合格可能性を判定しません。</p><p>評定は単純な全体評定の数値条件だけ、英語資格は監査済みの完全一致表現だけを安全に検索します。</p></section><section><h2>原文と不明値</h2><p>「なし」「不明」「未記録」は区別して保持しています。学問分野の19分類は検索用の派生分類です。</p></section><details class="developer-details"><summary>データ版情報</summary><p>構築ID：${escapeHtml(manifest.build_id)}</p><p>件数：${manifest.counts.search_rows.toLocaleString("ja-JP")}</p></details></main>${footer()}`;
}

function dataError(message: string): void {
  floatingLiveCount?.disconnect();
  floatingLiveCount = null;
  app.innerHTML = `${header()}<main id="main" class="page"><section class="error"><h1>データを表示できません</h1><p>${escapeHtml(message)}</p></section></main>${footer()}`;
}

async function route(replace = false): Promise<void> {
  const path = location.pathname.replace(/\/+$/, "") || "/";
  if (path === "/about/data") { aboutPage(); return; }
  const match = path.match(/^\/admissions\/([^/]+)\/([^/]+)\/([^/]+)$/);
  if (match) { await detailPage(match.slice(1)); return; }
  if (path === "/") {
    history.replaceState({}, "", "/search");
    applied = emptyRequest();
    universityQuery = "";
    gpaQuery = "";
    searchPage([]);
    return;
  }
  if (path !== "/search" && path !== "/results") {
    dataError("ページが見つかりません。");
    return;
  }
  const parsed = parseSearchParams(new URLSearchParams(location.search), options);
  applied = parsed.request;
  universityQuery = parsed.universityQuery;
  gpaQuery = parsed.gpaQuery;
  if (replace && path === "/results") {
    const query = serializeRequest(applied).toString();
    history.replaceState({}, "", `/results${query ? `?${query}` : ""}`);
  }
  if (path === "/search") {
    expandedUniversities.clear();
    searchPage(parsed.warnings);
  } else {
    expandedUniversities = replace
      ? new Set()
      : expandedUniversitiesFromHistory(history.state);
    resultsPage(parsed.warnings);
  }
}

function rememberCurrentView(): void {
  const prefectureOpen = document.querySelector<HTMLDetailsElement>("#prefecture-details")?.open ?? false;
  const state = location.pathname === "/results"
    ? universityResultsHistoryState(history.state, expandedUniversities, window.scrollY, prefectureOpen)
    : { ...(history.state ?? {}), scrollY: window.scrollY, prefectureOpen };
  history.replaceState(
    state,
    "",
    location.href,
  );
}

function persistExpandedUniversities(): void {
  history.replaceState(
    { ...(history.state ?? {}), expandedUniversities: [...expandedUniversities] },
    "",
    location.href,
  );
}

function restoreCurrentView(): void {
  const savedScroll = history.state?.scrollY;
  if (typeof savedScroll !== "number") return;
  requestAnimationFrame(() => window.scrollTo({ top: savedScroll, left: 0, behavior: "auto" }));
}

document.addEventListener("click", (event) => {
  const target = event.target as HTMLElement;
  const link = target.closest<HTMLAnchorElement>("a[data-route]");
  if (link && link.origin === location.origin) {
    event.preventDefault();
    rememberCurrentView();
    history.pushState({ from: location.pathname + location.search }, "", link.href);
    void route();
    return;
  }
  const universityToggle = target.closest<HTMLButtonElement>("button[data-university-toggle]");
  if (universityToggle) {
    const university = universityToggle.dataset.universityToggle;
    const panelId = universityToggle.getAttribute("aria-controls");
    const panel = panelId ? document.getElementById(panelId) : null;
    if (!university || !panel) return;
    const expanded = toggleExpandedUniversity(expandedUniversities, university);
    universityToggle.setAttribute("aria-expanded", String(expanded));
    panel.hidden = !expanded;
    persistExpandedUniversities();
    return;
  }
  const page = target.closest<HTMLButtonElement>("button[data-page]");
  if (page) {
    rememberCurrentView();
    applied.page = Number(page.dataset.page);
    expandedUniversities.clear();
    const query = serializeRequest(applied).toString();
    history.pushState({}, "", `/results?${query}`);
    resultsPage([]);
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }
});
window.addEventListener("popstate", () => {
  void route().then(restoreCurrentView);
});

try {
  const loaded = await loadSearchData();
  rows = loaded.rows;
  options = loaded.options;
  manifest = loaded.manifest;
  for (const group of options.academic_field_groups) groupLabels.set(group.value, group.display_label);
  await route(true);
  cleanupWebMcp();
  cleanupWebMcp = registerSearchTools(async (partial) => {
    applied = { ...emptyRequest(), ...partial, page: 1 } as SearchRequest;
    if (applied.gpa_tenths !== null) applied.gpa_mode = "safe";
    const query = serializeRequest(applied).toString();
    expandedUniversities.clear();
    history.pushState({}, "", `/results${query ? `?${query}` : ""}`);
    resultsPage([]);
    return {
      total: currentResult.summary.total_matched_rows,
      universities: currentResult.summary.university_count,
    };
  }, () => ({
    total: currentResult.summary.total_matched_rows,
    universities: currentResult.summary.university_count,
    url: location.href,
  }));
} catch (error) {
  dataError(error instanceof SiteDataError ? error.message : "データの読み込み中に問題が発生しました。");
}
