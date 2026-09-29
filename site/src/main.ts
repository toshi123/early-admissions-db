import "./styles.css";
import { syncBroadSubcategoryVisibility, visibleSubcategories } from "./academic-field-v2-ui";
import { CandidateStore, browserCandidateStorage, candidateKey } from "./candidates";
import { detailCandidateAction } from "./candidate-controls";
import { CandidateView } from "./candidate-view";
import { loadDetail, loadPublicDiscovery, loadSearchData, SiteDataError } from "./data";
import { displayValue, escapeHtml, safeExternalLink } from "./display";
import { inValueOrder } from "./form-options";
import { bindFloatingLiveCount, type FloatingLiveCountController } from "./floating-live-count";
import { guidePage } from "./guide-page";
import {
  canonicalSearchQuery,
  detailReturnTarget,
  headerSearchHref,
  rememberLastResults,
  rememberLastSearch,
} from "./last-search-state";
import { submitSearchNavigation } from "./navigation";
import { discoverProvisional, provisionalCountLabel } from "./public-discovery";
import { emptyRequest, searchRows } from "./search";
import {
  evaluateSearchDraft,
  liveSearchResult,
  liveSummaryPresentation,
  universitySuggestions,
} from "./search-ui";
import {
  expandedUniversitiesFromHistory,
  groupPublicAdmissionsByUniversity,
  paginateUniversityGroups,
  toggleExpandedUniversity,
  UNIVERSITY_GROUP_PAGE_SIZE,
  publicUniversityGroupMarkup,
  universityResultsHistoryState,
} from "./university-groups";
import type {
  DetailRecord,
  FilterOptions,
  ProvisionalAdmission,
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
let provisionalRows: ProvisionalAdmission[] = [];
let options: FilterOptions;
let manifest: SiteManifest;
let applied = emptyRequest();
let currentResult: SearchResult = searchRows([], applied);
let universityQuery = "";
let gpaQuery = "";
let overallGpaQuery = "";
let applicantGpaQuery = "";
let deadlineQuery = "";
let cleanupWebMcp: () => void = () => undefined;
let floatingLiveCount: FloatingLiveCountController | null = null;
let expandedUniversities = new Set<string>();
const groupLabels = new Map<string, string>();
const v2BroadLabels = new Map<string, string>();
const v2SubcategoryLabels = new Map<string, string>();
const candidates = new CandidateView(new CandidateStore(browserCandidateStorage()));

if ("scrollRestoration" in history) history.scrollRestoration = "manual";

const header = () => {
  const path = location.pathname.replace(/\/+$/, "") || "/";
  const searchCurrent = path === "/search" || path === "/results" || path.startsWith("/admissions/");
  const aboutCurrent = path === "/about/data";
  return `<header class="site-header"><div class="site-header__inner"><a class="brand" href="/search" data-route><strong>2027年度 早期入試検索</strong></a><nav aria-label="主要ナビゲーション"><ul class="global-nav"><li><a id="header-search-link" class="global-nav__link" href="${headerSearchHref(path, applied)}" data-route${searchCurrent ? ' aria-current="page"' : ""}>検索</a></li><li><a id="candidate-link" class="global-nav__link" href="/candidates" data-route aria-label="候補リスト（${candidates.store.items.length}件）"${path === "/candidates" ? ' aria-current="page"' : ""}><span class="nav-label--desktop">候補リスト</span><span class="nav-label--mobile" aria-hidden="true">候補</span><span id="candidate-count">（${candidates.store.items.length}）</span></a></li><li><a class="global-nav__link" href="/guide" data-route${path === "/guide" ? ' aria-current="page"' : ""}>使い方</a></li><li><a class="global-nav__link" href="/about/data" data-route aria-label="データについて"${aboutCurrent ? ' aria-current="page"' : ""}><span class="nav-label--desktop">データについて</span><span class="nav-label--mobile" aria-hidden="true">データ</span></a></li></ul></nav></div></header><p id="candidate-storage-warning" class="storage-notice" role="status"${candidates.store.warning ? "" : " hidden"}>${escapeHtml(candidates.store.warning)}</p>`;
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

function academicFieldV2Controls(): string {
  const selectedBranches = new Map(
    applied.academic_field_v2_branches.map((branch) => [branch.group_code, branch]),
  );
  const sections = [...new Set(
    options.academic_field_v2_broad_groups.map((item) => item.ui_section),
  )];
  return `<div class="academic-field-sections">${sections.map((section) => {
    const broadGroups = options.academic_field_v2_broad_groups
      .filter((item) => item.ui_section === section)
      .sort((left, right) => left.display_order - right.display_order);
    return `<section class="academic-field-section"><h3>${escapeHtml(section)}</h3><div class="academic-field-branch-grid">${broadGroups.map((broad) => {
      const selectedBranch = selectedBranches.get(broad.group_code);
      const subcategories = visibleSubcategories(
        options.academic_field_v2_subcategories,
        broad.group_code,
      );
      const subcategoryMarkup = subcategories.length
        ? `<div class="academic-subcategory-filter" data-subcategories-for="${escapeHtml(broad.group_code)}"${selectedBranch ? "" : " hidden"}><p class="academic-subcategory-label">さらに絞る</p><div class="academic-subcategory-grid">${subcategories.map((subcategory) => `<label class="choice choice--checkbox choice--subcategory"><span class="choice__control"><input type="checkbox" name="academic_subfield_v2" value="${escapeHtml(subcategory.subcategory_code)}" data-parent-group="${escapeHtml(broad.group_code)}" ${selectedBranch?.subcategory_codes.includes(subcategory.subcategory_code) ? "checked" : ""}></span><span class="choice__label">${escapeHtml(subcategory.display_label_ja)}</span></label>`).join("")}</div></div>`
        : "";
      return `<div class="academic-field-branch"><label class="choice choice--checkbox choice--broad"><span class="choice__control"><input type="checkbox" name="academic_field_v2" value="${escapeHtml(broad.group_code)}" ${selectedBranch ? "checked" : ""}></span><span class="choice__label">${escapeHtml(broad.display_label_ja)}</span></label>${subcategoryMarkup}</div>`;
    }).join("")}</div></section>`;
  }).join("")}</div>`;
}

function searchForm(): string {
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
    <fieldset><legend>2. 学問分野</legend><p class="help">複数選択可。選んだ分野は、必要に応じて「さらに絞る」ことができます。</p>${academicFieldV2Controls()}${applied.academic_field_group.length ? `<div class="notice legacy-academic-filter"><strong>旧学問分野条件が適用されています：</strong> ${escapeHtml(applied.academic_field_group.map((value) => groupLabels.get(value) ?? value).join("、"))}</div>` : ""}</fieldset>
    <fieldset><legend>3. 大学種別</legend>${checks("institution_type", institutionTypes)}</fieldset>
    <fieldset><legend>選抜方式</legend><p class="help">学校推薦型選抜と総合型選抜を初期状態で検索します。両方を外す場合は、特別選抜を1つ以上選んでください。</p><div class="check-grid"><label class="choice choice--checkbox"><span class="choice__control"><input type="checkbox" name="selection_family" value="recommendation" ${applied.selection_families.includes("recommendation") ? "checked" : ""}></span><span class="choice__label">学校推薦型選抜</span></label><label class="choice choice--checkbox"><span class="choice__control"><input type="checkbox" name="selection_family" value="comprehensive" ${applied.selection_families.includes("comprehensive") ? "checked" : ""}></span><span class="choice__label">総合型選抜</span></label></div></fieldset>
    <fieldset class="prefecture-fieldset"><details id="special-details" class="disclosure" ${applied.special_filters.length ? "open" : ""}><summary><svg class="disclosure__icon" width="24" height="24" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="11" fill="currentcolor"/><circle class="disclosure__icon-circle" cx="12" cy="12" r="8" fill="currentcolor"/><path class="disclosure__icon-triangle" d="M17 10H7L12 15L17 10Z" fill="Canvas"/></svg><span>特別選抜を探す <span class="selected-count">${applied.special_filters.length ? `（${applied.special_filters.length}件選択）` : "（初期状態では対象外）"}</span></span></summary><p class="help">チェックした種類のいずれかに該当する選抜を表示します。選択中は上の選抜方式より特別選抜の指定を優先します。</p><div class="check-grid">${([ ["returnee_flag", "帰国生"], ["international_baccalaureate_flag", "IB"], ["private_foreign_student_flag", "私費外国人留学生"], ["adult_selection_flag", "社会人"] ] as const).map(([value,label]) => `<label class="choice choice--checkbox"><span class="choice__control"><input type="checkbox" name="special_filter" value="${value}" ${applied.special_filters.includes(value) ? "checked" : ""}></span><span class="choice__label">${label}</span></label>`).join("")}</div></details></fieldset>
    <fieldset><legend>4. 専願・併願</legend>${checks("exclusive_enrollment_status", exclusive, { 不明: "不明・記載確認できず" })}</fieldset>
    <fieldset><legend>5. 共通テスト</legend>${radios("common_test_required", [["", "指定なし"], ["Yes", "あり"], ["No", "なし"]])}</fieldset>
    <fieldset><legend>6. 研究業績</legend>${radios("research_requirement_required", [["", "指定なし"], ["Yes", "必要"], ["No", "必要なし"]])}</fieldset>
    <fieldset><legend>7. 英語資格</legend>${radios("english_requirement_status", [["", "指定なし"], ["required", "必要"], ["not_required", "必要なし"]])}</fieldset>
    <fieldset><legend>8. 試験内容</legend><p class="help">複数選ぶと、すべて実施する入試に絞ります。</p><div class="check-grid">${methods.map(([field, label]) => `<label class="choice choice--checkbox"><span class="choice__control"><input type="checkbox" name="${field}" value="Yes" ${selected(field, "Yes") ? "checked" : ""}></span><span class="choice__label">${label}</span></label>`).join("")}</div></fieldset>
    <fieldset><legend>9. 評定</legend><label class="input-label" for="applicant-gpa">あなたの評定平均</label><div class="grade-input-row"><input id="applicant-gpa" class="text-input" type="text" inputmode="decimal" value="${escapeHtml(applicantGpaQuery)}" placeholder="例：3.8"></div><p class="help">入力した値で評定条件を満たす選抜を表示します。例：3.8なら評定3.8以上、3.5以上が対象です。※科目別条件など、数値だけで判定できない条件は別途表示します。</p><details class="disclosure"><summary>評定条件ありの選抜に絞る（詳細）</summary><label class="choice choice--checkbox"><span class="choice__control"><input id="grade-requirement" type="checkbox" name="grade_requirement" value="required" ${applied.grade_requirement_status === "required" ? "checked" : ""}></span><span class="choice__label">評定条件あり</span></label><div class="nested-filter"><label class="input-label" for="overall-gpa">旧形式の全体評定条件</label><div class="grade-input-row"><input id="overall-gpa" class="text-input" type="text" inputmode="decimal" value="${escapeHtml(overallGpaQuery)}" placeholder="例：3.8" ${applied.grade_requirement_status === "required" ? "" : "disabled"}></div></div></details>${applied.gpa_tenths !== null ? `<p class="notice">旧形式の評定安全照合 ${(applied.gpa_tenths / 10).toFixed(1)} がこの共有URLに適用されています。</p>` : ""}</fieldset>
    <fieldset><legend>出願締切</legend><label class="input-label" for="deadline-on-or-after">出願締切が指定日以降</label><div class="date-filter-row"><input id="deadline-on-or-after" class="text-input" type="date" value="${escapeHtml(deadlineQuery)}"></div><p class="help">締切が未確認の選抜も、確認が必要なものとして結果に残します。</p></fieldset>
    <fieldset class="prefecture-fieldset"><details id="prefecture-details" class="disclosure"><summary><svg class="disclosure__icon" width="24" height="24" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="11" fill="currentcolor"/><circle class="disclosure__icon-circle" cx="12" cy="12" r="8" fill="currentcolor"/><path class="disclosure__icon-triangle" d="M17 10H7L12 15L17 10Z" fill="Canvas"/></svg><span>10. 都道府県で絞り込む <span id="prefecture-count" class="selected-count"></span></span></summary><div class="prefecture-regions">${prefectures}</div><button id="clear-prefectures" class="button button--text" type="button">選択をクリア</button></details></fieldset>
    <div id="form-error" class="notice error" role="alert" hidden></div>
    <div class="form-actions"><div class="submit-action"><button class="button button--primary" type="submit">この条件で検索</button></div><button id="clear-form" class="button button--outline" type="button">条件をクリア</button></div>
  </form>`;
}

function readBaseForm(): SearchRequest {
  const form = document.querySelector<HTMLFormElement>("#search-form")!;
  const request = emptyRequest();
  request.gpa_tenths = applied.gpa_tenths;
  request.gpa_mode = applied.gpa_mode;
  request.selection_families = [...form.querySelectorAll<HTMLInputElement>('input[name="selection_family"]:checked')].map((input) => input.value as "recommendation" | "comprehensive");
  request.special_filters = [...form.querySelectorAll<HTMLInputElement>('input[name="special_filter"]:checked')].map((input) => input.value as SearchRequest["special_filters"][number]);
  request.academic_field_group = [...applied.academic_field_group];
  request.academic_field_mapping_status = [
    ...applied.academic_field_mapping_status,
  ];
  for (const field of [
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
  request.academic_field_v2_branches = [
    ...form.querySelectorAll<HTMLInputElement>(
      'input[name="academic_field_v2"]:checked',
    ),
  ].map((input) => ({
    group_code: input.value,
    subcategory_codes: [
      ...form.querySelectorAll<HTMLInputElement>(
        'input[name="academic_subfield_v2"]:checked',
      ),
    ].filter((subcategory) => subcategory.dataset.parentGroup === input.value)
      .map((subcategory) => subcategory.value),
  }));
  for (const field of [
    "common_test_required",
    "research_requirement_required",
    "english_requirement_status",
  ] as const) {
    const value = form.querySelector<HTMLInputElement>(`input[name="${field}"]:checked`)?.value ?? "";
    request[field] = value ? [value] : [];
  }
  request.grade_requirement_status = form.querySelector<HTMLInputElement>(
    'input[name="grade_requirement"]:checked',
  )?.value === "required" ? "required" : null;
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
  const overallGpa = document.querySelector<HTMLInputElement>("#overall-gpa")!;
  const applicantGpa = document.querySelector<HTMLInputElement>("#applicant-gpa")!;
  const deadline = document.querySelector<HTMLInputElement>("#deadline-on-or-after")!;
  const base = readBaseForm();
  overallGpa.disabled = base.grade_requirement_status !== "required";
  if (overallGpa.disabled) overallGpa.value = "";
  const evaluation = evaluateSearchDraft(
    base, options, input.value, overallGpa.value, applicantGpa.value, deadline.value,
  );
  applied = evaluation.request;
  universityQuery = evaluation.universityQuery;
  overallGpaQuery = evaluation.overallGpaQuery;
  applicantGpaQuery = evaluation.applicantGpaQuery;
  deadlineQuery = evaluation.deadlineQuery;
  input.setAttribute("aria-invalid", evaluation.errors.some((error) => error.startsWith("大学名")) ? "true" : "false");
  overallGpa.setAttribute("aria-invalid", evaluation.errors.some((error) => error.startsWith("全体評定")) ? "true" : "false");
  applicantGpa.setAttribute("aria-invalid", evaluation.errors.some((error) => error.startsWith("あなたの評定")) ? "true" : "false");
  deadline.setAttribute("aria-invalid", evaluation.errors.some((error) => error.startsWith("出願締切日")) ? "true" : "false");
  const error = document.querySelector<HTMLElement>("#form-error")!;
  error.hidden = evaluation.errors.length === 0;
  error.textContent = evaluation.errors.join(" ");
  const result = liveSearchResult(rows, evaluation);
  const presentation = liveSummaryPresentation(result);
  if (result) {
    const discovered = discoverProvisional(provisionalRows, evaluation.request, rows);
    const pending = discovered.length;
    const total = result.summary.total_matched_rows + pending;
    presentation.liveText = `検索結果 ${total.toLocaleString("ja-JP")}件（確定済み募集単位 ${result.summary.total_matched_rows.toLocaleString("ja-JP")}件・${provisionalCountLabel(discovered)} ${pending.toLocaleString("ja-JP")}件）`;
    presentation.floatingText = `検索結果 ${total.toLocaleString("ja-JP")}件`;
  }
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
    const query = serializeSearchFormState(
      evaluation.request, universityQuery, gpaQuery, overallGpaQuery, applicantGpaQuery, deadlineQuery,
    ).toString();
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
  form.addEventListener("change", (event) => {
    const input = event.target as HTMLInputElement;
    if (input.name === "academic_field_v2") {
      syncBroadSubcategoryVisibility(form, input);
    }
    refreshForm();
  });
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
    overallGpaQuery = "";
    applicantGpaQuery = "";
    deadlineQuery = "";
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
  if (applied.academic_field_group.length) parts.push(`旧学問分野条件：${applied.academic_field_group.map((value) => groupLabels.get(value) ?? value).join("、")}`);
  if (applied.academic_field_v2_branches.length) {
    parts.push(`学問分野：${applied.academic_field_v2_branches.map((branch) => {
      const broad = v2BroadLabels.get(branch.group_code) ?? branch.group_code;
      if (!branch.subcategory_codes.length) return broad;
      return `${broad}（${branch.subcategory_codes.map((code) => v2SubcategoryLabels.get(code) ?? code).join("、")}）`;
    }).join(" または ")}`);
  }
  if (applied.institution_type.length) parts.push(`大学種別：${applied.institution_type.join("、")}`);
  if (applied.special_filters.length) parts.push(`特別選抜：${applied.special_filters.map((flag) => ({returnee_flag:"帰国生",international_baccalaureate_flag:"IB",private_foreign_student_flag:"私費外国人留学生",adult_selection_flag:"社会人"})[flag]).join(" または ")}`);
  else parts.push(`選抜方式：${applied.selection_families.map((family) => family === "recommendation" ? "学校推薦型" : "総合型").join("・")}`);
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
  if (applied.grade_requirement_status === "required") {
    parts.push(applied.overall_gpa_tenths === null
      ? "評定条件：あり"
      : `評定条件：あり ／ 全体評定：${(applied.overall_gpa_tenths / 10).toFixed(1)}以上`);
  }
  if (applied.applicant_gpa_tenths !== null) parts.push(`あなたの評定平均：${(applied.applicant_gpa_tenths / 10).toFixed(1)}`);
  if (applied.deadline_on_or_after !== null) parts.push(`出願締切：${applied.deadline_on_or_after}以降`);
  if (applied.prefecture_membership.length) parts.push(`都道府県：${applied.prefecture_membership.join("、")}`);
  return parts.length ? parts.join(" ／ ") : "条件指定なし";
}

function resultsPage(warnings: string[]): void {
  floatingLiveCount?.disconnect();
  floatingLiveCount = null;
  rememberLastSearch(applied);
  currentResult = searchRows(rows, applied);
  const discovered = discoverProvisional(provisionalRows, applied, rows);
  const universityGroups = groupPublicAdmissionsByUniversity(currentResult.rows, discovered);
  const pages = Math.max(1, Math.ceil(universityGroups.length / UNIVERSITY_GROUP_PAGE_SIZE));
  if (applied.page > pages) applied.page = pages;
  rememberLastResults(applied);
  const shown = paginateUniversityGroups(universityGroups, applied.page);
  const firstGroupIndex = (applied.page - 1) * UNIVERSITY_GROUP_PAGE_SIZE;
  const query = canonicalSearchQuery(applied);
  const previous = applied.page > 1
    ? `<button class="button button--text" data-page="${applied.page - 1}"><span aria-hidden="true">←</span> 前のページ</button>`
    : '<span class="pagination__spacer" aria-hidden="true"></span>';
  const next = applied.page < pages
    ? `<button class="button button--text" data-page="${applied.page + 1}">次のページ <span aria-hidden="true">→</span></button>`
    : '<span class="pagination__spacer" aria-hidden="true"></span>';
  const total = currentResult.summary.total_matched_rows + discovered.length;
  const deadlineUnknown = currentResult.rows.filter((row) => row.deadline_filter_status === "unknown").length + (applied.deadline_on_or_after ? discovered.length : 0);
  const gradeUnknown = currentResult.rows.filter((row) => row.applicant_grade_status === "unknown").length + (applied.applicant_gpa_tenths !== null ? discovered.length : 0);
  const unknownNotice = [applied.deadline_on_or_after && deadlineUnknown ? `出願締切未確認 ${deadlineUnknown}件` : "", applied.applicant_gpa_tenths !== null && gradeUnknown ? `評定条件未確認・数値判定不能 ${gradeUnknown}件` : ""].filter(Boolean).join(" ／ ");
  app.innerHTML = `${header()}<main id="main" class="page results-page page--with-floating-actions"><section class="results-summary"><h1>検索結果</h1><p class="result-count">検索結果 ${total.toLocaleString("ja-JP")}件（確定済み募集単位 ${currentResult.summary.total_matched_rows.toLocaleString("ja-JP")}件・${provisionalCountLabel(discovered)} ${discovered.length.toLocaleString("ja-JP")}件）</p>${unknownNotice ? `<p class="help">${unknownNotice}。未確認は条件不一致と扱っていません。</p>` : ""}<p class="active-filter-summary">${escapeHtml(summaryText())}</p></section>${warnings.map((warning) => `<div class="notice">${escapeHtml(warning)}</div>`).join("")}<div class="results university-results" role="list">${shown.length ? shown.map((group, index) => publicUniversityGroupMarkup(group, firstGroupIndex + index, expandedUniversities.has(group.university), applied)).join("") : `<section class="empty"><h2>該当する選抜はありません</h2><p>条件を減らすか、大学公式資料も確認してください。</p></section>`}</div>${pages > 1 ? `<nav class="pagination" aria-label="検索結果のページ">${previous}<span class="pagination__counter">${applied.page} / ${pages}</span>${next}</nav>` : ""}</main><nav class="floating-navigation floating-navigation--results" aria-label="検索結果の操作"><a class="button button--outline floating-navigation__action" href="/search${query ? `?${query}` : ""}" data-route data-start-at-top><span aria-hidden="true">←</span> 検索条件を変更</a></nav>${footer()}`;
  candidates.sync();
}

const sections: Array<[string, string[]]> = [
  ["基本情報", ["admission_year", "institution_type", "university", "prefecture", "faculty_school", "department", "academic_field", "selection_category", "selection_name", "slot_type", "capacity"]],
  ["日程", ["application_start", "application_end", "web_registration_period", "first_stage_result_date", "second_stage_start", "second_stage_end", "final_result_date"]],
  ["選考方法", ["selection_process", "selection_method_detail", "selection_document_review", "selection_interview", "interview_detail", "selection_oral_exam", "oral_exam_subjects", "oral_exam_detail", "selection_presentation", "presentation_detail", "selection_essay", "essay_detail", "selection_written_exam", "written_exam_detail", "selection_common_test", "selection_group_discussion", "selection_practical", "selection_aptitude_test", "documents_summary"]],
  ["出願条件", ["eligibility_graduation", "gpa_requirement", "english_requirement", "subject_prerequisites", "school_recommendation_required", "school_nomination_limit", "school_nomination_limit_total", "school_nomination_limit_rule", "exclusive_enrollment_status", "exclusive_enrollment", "common_test_required", "common_test_usage", "academic_record_required", "academic_record_type", "academic_record_detail"]],
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
    const returnTarget = detailReturnTarget(history.state, options);
    const returnAction = returnTarget.mode === "history"
      ? `<button type="button" class="button button--outline floating-navigation__action" data-detail-history-back><span aria-hidden="true">←</span> ${returnTarget.label}</button>`
      : `<a class="button button--outline floating-navigation__action" href="${escapeHtml(returnTarget.href)}" data-route data-start-at-top><span aria-hidden="true">←</span> ${returnTarget.label}</a>`;
    app.innerHTML = `${header()}<main id="main" class="page detail-page page--with-floating-actions">
      ${admission.fallback_previous_year === true ? '<div class="fallback-warning"><strong>前年度情報を参照しています。</strong> 2027年度の公式資料を確認してください。</div>' : ""}
      <header class="detail-title"><p>${displayValue(admission.prefecture as never)} ／ ${displayValue(admission.institution_type as never)}</p><h1>${displayValue(admission.university as never)}</h1><p>${displayValue(admission.faculty_school as never)} ／ ${displayValue(admission.department as never)}</p><p><strong>${displayValue(admission.selection_category as never)}</strong>　${displayValue(admission.selection_name as never)}</p></header>
      ${sections.map(([title, fields]) => `<section class="detail-section"><h2>${title}</h2>${grid(admission, fields)}${title === "研究" ? research(detail) : ""}</section>`).join("")}<section class="detail-section"><h2>その他の記録項目</h2>${grid(admission, remaining)}</section><section class="detail-section"><h2>出典</h2><div class="source-links">${safeExternalLink(admission.guideline_url, "募集要項")}${safeExternalLink(admission.source_url, "公式情報")}${safeExternalLink(admission.schedule_url, "日程")}${safeExternalLink(admission.exclusive_enrollment_evidence_url, "専願根拠")}${safeExternalLink(admission.previous_year_source_url, "前年度資料")}</div><details class="developer-details"><summary>データ識別情報</summary><p>${escapeHtml(dataset)} ／ ${escapeHtml(version)} ／ ${escapeHtml(id)}</p></details></section></main><nav class="floating-navigation floating-navigation--detail" aria-label="入試詳細の操作">${returnAction}${detailCandidateAction(row, candidates.store.has(row))}</nav>${footer()}`;
  } catch (error) {
    dataError(error instanceof SiteDataError ? error.message : "詳細データを読み込めませんでした。");
  }
}

function aboutPage(): void {
  floatingLiveCount?.disconnect();
  floatingLiveCount = null;
  app.innerHTML = `${header()}<main id="main" class="page narrow about"><h1>データについて</h1><section><h2>検索結果の意味</h2><p>条件に一致する確定済み募集単位と、大学公式情報で実施を確認した詳細確認中の選抜を表示します。後者は詳細条件への適合を判定していません。検索結果にないことだけで、選抜が存在しないとは判断できません。</p><p>出願資格・条件充足・合格可能性は大学公式資料で確認してください。</p></section><section><h2>原文と不明値</h2><p>「なし」「不明」「未記録」は区別して保持しています。学問分野の30分類と詳細分類は検索用の派生分類です。</p></section><section><h2>候補リスト</h2><p>候補はこのブラウザの端末内に保存し、サーバーへ送信しません。アカウントや他の端末とは同期しません。選択した候補をCSV・Excelで出力できます。ブラウザのデータを削除すると保存した候補も削除されます。</p></section><details class="developer-details"><summary>データ版情報</summary><p>構築ID：${escapeHtml(manifest.build_id)}</p><p>確定済み募集単位：${manifest.counts.search_rows.toLocaleString("ja-JP")}件 ／ 詳細確認中：${provisionalRows.length.toLocaleString("ja-JP")}件</p></details></main>${footer()}`;
}

function dataError(message: string): void {
  floatingLiveCount?.disconnect();
  floatingLiveCount = null;
  app.innerHTML = `${header()}<main id="main" class="page"><section class="error"><h1>データを表示できません</h1><p>${escapeHtml(message)}</p></section></main>${footer()}`;
}

async function route(replace = false): Promise<void> {
  const path = location.pathname.replace(/\/+$/, "") || "/";
  if (path === "/candidates") {
    floatingLiveCount?.disconnect();
    floatingLiveCount = null;
    candidates.expanded = expandedUniversitiesFromHistory({ expandedUniversities: history.state?.candidateExpandedUniversities });
    app.innerHTML = `${header()}${candidates.page()}${footer()}`;
    return;
  }
  if (path === "/guide") {
    floatingLiveCount?.disconnect();
    floatingLiveCount = null;
    app.innerHTML = `${header()}${guidePage()}${footer()}`;
    return;
  }
  if (path === "/about/data") { aboutPage(); return; }
  const match = path.match(/^\/admissions\/([^/]+)\/([^/]+)\/([^/]+)$/);
  if (match) { await detailPage(match.slice(1)); return; }
  if (path === "/") {
    history.replaceState({}, "", "/search");
    applied = emptyRequest();
    universityQuery = "";
    gpaQuery = "";
    overallGpaQuery = "";
    applicantGpaQuery = "";
    deadlineQuery = "";
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
  overallGpaQuery = parsed.overallGpaQuery;
  applicantGpaQuery = parsed.applicantGpaQuery;
  deadlineQuery = parsed.deadlineQuery;
  if (replace && path === "/results") {
    const query = serializeRequest(applied).toString();
    history.replaceState({}, "", `/results${query ? `?${query}` : ""}`);
  }
  if (path === "/search") {
    expandedUniversities.clear();
    searchPage(parsed.warnings);
  } else {
    if (!applied.selection_families.length && !applied.special_filters.length) {
      history.replaceState({}, "", `/search${location.search}`);
      searchPage([...parsed.warnings, "少なくとも1つ選抜方式を選択してください。"]);
      return;
    }
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
  if (candidates.handleClick(target)) return;
  const detailBack = target.closest<HTMLButtonElement>("button[data-detail-history-back]");
  if (detailBack) {
    history.back();
    return;
  }
  const link = target.closest<HTMLAnchorElement>("a[data-route]");
  if (link && link.origin === location.origin) {
    event.preventDefault();
    rememberCurrentView();
    history.pushState({ from: location.pathname + location.search }, "", link.href);
    void route().then(() => {
      if (link.hasAttribute("data-start-at-top")) {
        window.scrollTo({ top: 0, left: 0, behavior: "auto" });
      }
    });
    return;
  }
  const universityToggle = target.closest<HTMLButtonElement>("button[data-university-toggle]");
  if (universityToggle) {
    const university = universityToggle.dataset.universityToggle;
    const panelId = universityToggle.getAttribute("aria-controls");
    const panel = panelId ? document.getElementById(panelId) : null;
    if (!university || !panel) return;
    const isCandidates = location.pathname === "/candidates";
    const expanded = toggleExpandedUniversity(isCandidates ? candidates.expanded : expandedUniversities, university);
    universityToggle.setAttribute("aria-expanded", String(expanded));
    panel.hidden = !expanded;
    if (isCandidates) history.replaceState({ ...(history.state ?? {}), candidateExpandedUniversities: [...candidates.expanded] }, "", location.href);
    else persistExpandedUniversities();
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
  provisionalRows = await loadPublicDiscovery(manifest);
  for (const provisional of provisionalRows) {
    if (!options.universities.some((item) => item.value === provisional.university)) {
      options.universities.push({ value: provisional.university, display_label: provisional.university, unfiltered_count: 0 });
    }
  }
  candidates.rows = new Map(rows.map((row) => [candidateKey(row), row]));
  candidates.manifest = manifest;
  for (const group of options.academic_field_groups) groupLabels.set(group.value, group.display_label);
  for (const group of options.academic_field_v2_broad_groups) {
    v2BroadLabels.set(group.group_code, group.display_label_ja);
  }
  for (const subcategory of options.academic_field_v2_subcategories) {
    v2SubcategoryLabels.set(
      subcategory.subcategory_code,
      subcategory.display_label_ja,
    );
  }
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
