import { detailLink, displayValue, escapeHtml } from "./display";
import { searchRows } from "./search";
import type { FilterOptions, SearchRequest, SearchResult, SearchRow } from "./types";

export interface SearchDraftEvaluation {
  request: SearchRequest;
  universityQuery: string;
  gpaQuery: string;
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
  gpaQuery: string,
): SearchDraftEvaluation {
  const request: SearchRequest = {
    ...baseRequest,
    university: [],
    gpa_tenths: null,
    gpa_mode: "all",
    page: 1,
  };
  const errors: string[] = [];
  const universities = new Set(options.universities.flatMap((item) => item.value === null ? [] : [item.value]));
  if (universityQuery) {
    if (universities.has(universityQuery)) request.university = [universityQuery];
    else errors.push("大学名は候補から1校選んでください。");
  }
  if (gpaQuery) {
    if (GPA_PATTERN.test(gpaQuery)) {
      request.gpa_tenths = Math.round(Number(gpaQuery) * 10);
      request.gpa_mode = "safe";
    } else {
      errors.push("評定は0.0〜5.0、小数1桁までで入力してください。");
    }
  }
  return { request, universityQuery, gpaQuery, errors };
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

export function compactResultCard(
  row: SearchRow,
  showGpaSafeMatch: boolean,
  showUniversity = true,
): string {
  const methods = selectionMethodLabels(row);
  const category = row.selection_category
    ? `<span class="selection-category">${displayValue(row.selection_category)}</span>`
    : "";
  const badges = [
    ...methods.map((method) => `<span>${escapeHtml(method)}</span>`),
    ...(showGpaSafeMatch && row.gpa_derived_status === "safe match"
      ? ['<span class="safe-match">評定：安全照合一致</span>']
      : []),
    ...(row.fallback_previous_year ? ['<span class="previous-year">前年度情報</span>'] : []),
  ];
  const detailHref = detailLink(row.source_dataset, row.source_version, row.record_id);
  const selectionName = displayValue(row.selection_name);
  const title = showUniversity
    ? `<h2><a href="${detailHref}" data-route>${escapeHtml(row.university)}</a></h2>`
    : "";
  const selection = showUniversity
    ? `<strong>${selectionName}</strong>${category}`
    : `<strong><a class="admission-detail-link" href="${detailHref}" data-route>${selectionName}</a></strong>${category}`;
  return `<article class="result-card" role="listitem">${title}<p class="faculty-line">${displayValue(row.faculty_school)} ／ ${displayValue(row.department)}</p><p class="selection-line">${selection}</p><div class="method-badges" aria-label="選考方法">${badges.length ? badges.join("") : "<span>選考方法の記載なし</span>"}</div></article>`;
}
