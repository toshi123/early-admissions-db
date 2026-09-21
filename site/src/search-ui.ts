import { detailLink, displayValue, escapeHtml } from "./display";
import { candidateButton } from "./candidate-controls";
import { searchRows } from "./search";
import type { FilterOptions, SearchRequest, SearchResult, SearchRow } from "./types";

export interface SearchDraftEvaluation {
  request: SearchRequest;
  universityQuery: string;
  gpaQuery: string;
  overallGpaQuery: string;
  errors: string[];
}

export interface LiveSummaryPresentation {
  liveText: string;
  floatingText: string;
  invalid: boolean;
}

const GPA_PATTERN = /^(?:[0-4](?:\.\d)?|5(?:\.0)?)$/;

export function universitySuggestions(
  options: FilterOptions,
  query: string,
  limit = 8,
): string[] {
  if (!query) return [];
  const needle = query.toLocaleLowerCase("ja");
  return options.universities
    .flatMap((item) => item.value === null ? [] : [item.value])
    .filter((value) => value.toLocaleLowerCase("ja").includes(needle))
    .slice(0, limit);
}

export function evaluateSearchDraft(
  baseRequest: SearchRequest,
  options: FilterOptions,
  universityQuery: string,
  overallGpaQuery: string,
): SearchDraftEvaluation {
  const request: SearchRequest = {
    ...baseRequest,
    university: [],
    overall_gpa_tenths: null,
    page: 1,
  };
  const errors: string[] = [];
  const universities = new Set(options.universities.flatMap((item) => item.value === null ? [] : [item.value]));
  if (universityQuery) {
    if (universities.has(universityQuery)) request.university = [universityQuery];
    else errors.push("大学名は候補から1校選んでください。");
  }
  if (overallGpaQuery) {
    if (request.grade_requirement_status !== "required") {
      errors.push("全体評定は「評定条件あり」を選んでから入力してください。");
    } else if (GPA_PATTERN.test(overallGpaQuery)) {
      request.overall_gpa_tenths = Math.round(Number(overallGpaQuery) * 10);
    } else {
      errors.push("全体評定は0.0〜5.0、小数1桁までで入力してください。");
    }
  }
  return { request, universityQuery, gpaQuery: "", overallGpaQuery, errors };
}

export function liveSearchResult(
  rows: SearchRow[],
  evaluation: SearchDraftEvaluation,
): SearchResult | null {
  return evaluation.errors.length ? null : searchRows(rows, evaluation.request);
}

export function liveSummaryPresentation(result: SearchResult | null): LiveSummaryPresentation {
  if (!result) {
    return {
      liveText: "入力を確認すると該当件数を表示します",
      floatingText: "条件を確認してください",
      invalid: true,
    };
  }
  const count = `${result.summary.total_matched_rows.toLocaleString("ja-JP")}件・${result.summary.university_count.toLocaleString("ja-JP")}大学`;
  return { liveText: `該当 ${count}`, floatingText: count, invalid: false };
}

const METHOD_FIELDS: Array<[keyof SearchRow, string]> = [
  ["selection_interview", "面接"],
  ["selection_oral_exam", "口頭試問"],
  ["selection_presentation", "プレゼン"],
  ["selection_essay", "小論文"],
  ["selection_written_exam", "筆記"],
  ["selection_practical", "実技"],
  ["selection_group_discussion", "グループ討論"],
  ["selection_aptitude_test", "適性検査"],
  ["selection_common_test", "共通テスト"],
];

export function selectionMethodLabels(row: SearchRow): string[] {
  return METHOD_FIELDS.filter(([field]) => row[field] === "Yes").map(([, label]) => label);
}

export function applicationConditionLabels(row: SearchRow): string[] {
  return [
    ...(row.grade_requirement_status === "required" ? ["評定"] : []),
    ...(row.english_requirement_status === "required" ? ["英語資格"] : []),
    ...(row.research_requirement_required === "Yes" ? ["研究業績"] : []),
  ];
}

const EXCLUSIVE_ENROLLMENT_LABELS: Readonly<Record<string, string>> = {
  "専願": "専願",
  "併願可": "併願可",
  "条件付き": "条件付き",
  "不明": "不明",
};

export function exclusiveEnrollmentLabel(value: string | null): string | null {
  return value === null ? null : EXCLUSIVE_ENROLLMENT_LABELS[value] ?? null;
}

export function compactResultCard(
  row: SearchRow,
  showGpaSafeMatch: boolean,
  showUniversity = true,
  actions?: string,
): string {
  const methods = selectionMethodLabels(row);
  const conditions = applicationConditionLabels(row);
  const exclusive = exclusiveEnrollmentLabel(row.exclusive_enrollment_status);
  const category = row.selection_category
    ? `<span class="selection-category">${displayValue(row.selection_category)}</span>`
    : "";
  const chips = [
    ...(methods.length
      ? methods.map((method) => `<span class="result-chip method-chip" aria-label="選考方法 ${escapeHtml(method)}">${escapeHtml(method)}</span>`)
      : ['<span class="result-chip method-chip method-chip--empty">選考方法の記載なし</span>']),
    ...(showGpaSafeMatch && row.gpa_derived_status === "safe match"
      ? ['<span class="result-chip derived-chip safe-match">評定：安全照合一致</span>']
      : []),
    ...(row.fallback_previous_year ? ['<span class="result-chip derived-chip previous-year">前年度情報</span>'] : []),
    ...conditions.map((condition) => `<span class="result-chip condition-chip" aria-label="出願条件 ${escapeHtml(condition)}">${condition === "評定" ? "評定" : `条件：${escapeHtml(condition)}`}</span>`),
    ...(exclusive ? [`<span class="result-chip exclusive-chip" aria-label="専願・併願 ${escapeHtml(exclusive)}">${escapeHtml(exclusive)}</span>`] : []),
  ];
  const detailHref = detailLink(row.source_dataset, row.source_version, row.record_id);
  const selectionName = displayValue(row.selection_name);
  const title = showUniversity
    ? `<h2><a href="${detailHref}" data-route>${escapeHtml(row.university)}</a></h2>`
    : "";
  const selection = showUniversity
    ? `<strong>${selectionName}</strong>${category}`
    : `<strong><a class="admission-detail-link" href="${detailHref}" data-route>${selectionName}</a></strong>${category}`;
  const deadline = row.application_end === null ? "" : `<p class="application-end">出願終了：<span>${escapeHtml(row.application_end)}</span></p>`;
  return `<article class="result-card" role="listitem">${title}<p class="faculty-line">${displayValue(row.faculty_school)} ／ ${displayValue(row.department)}</p><p class="selection-line">${selection}</p><div class="result-card__utility"><div class="result-chips" aria-label="選考方法・出願条件・専願併願">${chips.join("")}</div>${actions ?? candidateButton(row)}</div>${deadline}</article>`;
}
