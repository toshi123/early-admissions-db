import { candidateKey, type CandidateSelection, type ResolvedCandidate } from "./candidates";
import { displayValue, escapeHtml } from "./display";
import { compactResultCard } from "./search-ui";
import { universityDisclosureMarkup } from "./university-groups";

export const CANDIDATE_PRIVACY_NOTICE = "候補リストはこのブラウザ・端末に保存されます。別の端末には自動同期されません。ブラウザのデータを削除すると候補リストも削除されます。";

export function candidateListMarkup(items: ResolvedCandidate[], selection: CandidateSelection, expanded: Set<string>): string {
  const groups = new Map<string, ResolvedCandidate[]>();
  for (const item of items) {
    const university = item.row?.university ?? item.saved.snapshot.university;
    groups.set(university, [...(groups.get(university) ?? []), item]);
  }
  const groupsHtml = [...groups].map(([university, items], index) => universityDisclosureMarkup(
    university, items.length, index, expanded.has(university), items.map(({ saved, row }) => {
      const key = escapeHtml(candidateKey(saved));
      const display = row ?? saved.snapshot;
      const name = [university, display.faculty_school, display.department, display.selection_name]
        .filter(Boolean).join(" ／ ");
      const controls = `<div class="candidate-row-actions"><label class="choice choice--checkbox"><span class="choice__control"><input type="checkbox" data-export-key="${key}" aria-label="出力対象：${escapeHtml(name)}"${selection.selected.has(candidateKey(saved)) ? " checked" : ""}></span><span class="choice__label">出力対象</span></label><button class="button button--text" type="button" data-candidate-remove="${key}" aria-label="候補から削除：${escapeHtml(name)}">候補から削除</button></div>`;
      if (row) return compactResultCard(row, false, false, controls);
      return `<article class="result-card stale-candidate" role="listitem"><p class="faculty-line">${displayValue(saved.snapshot.faculty_school)} ／ ${displayValue(saved.snapshot.department)}</p><p><strong>${displayValue(saved.snapshot.selection_name)}</strong></p><p class="stale-label">現在データで確認できず</p><p class="help">以前のデータ版で保存した候補です。現在のデータでは確認できません。</p>${controls}</article>`;
    }).join(""),
  )).join("");
  return `<div class="candidate-toolbar"><p id="candidate-selection-count" role="status">${items.length}件中 ${selection.selected.size}件選択</p><div class="candidate-actions"><button class="button button--text" type="button" data-candidate-select="all">すべて選択</button><button class="button button--text" type="button" data-candidate-select="none">選択を解除</button></div><p class="help" id="export-help">選択した候補を出力します</p><div class="candidate-actions"><button class="button button--primary" type="button" data-candidate-export="csv" aria-describedby="export-help"${selection.selected.size ? "" : " disabled"}>CSVで出力</button><button class="button button--outline" type="button" data-candidate-export="xlsx" aria-describedby="export-help"${selection.selected.size ? "" : " disabled"}>Excelで出力</button></div><p id="candidate-export-status" role="status"></p></div><div class="results" role="list">${groupsHtml || '<p class="candidate-empty">候補はまだありません。検索結果や個別情報ページから追加できます。</p>'}</div>`;
}
