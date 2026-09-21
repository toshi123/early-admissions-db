import { CandidateSelection, CandidateStore, candidateKey, resolveCandidates } from "./candidates";
import { syncCandidateControls } from "./candidate-controls";
import { candidateListMarkup, CANDIDATE_PRIVACY_NOTICE } from "./candidate-page";
import { loadDetail, type DetailCache } from "./data";
import type { SearchRow, SiteManifest } from "./types";

export class CandidateView {
  readonly selection = new CandidateSelection();
  expanded = new Set<string>();
  rows = new Map<string, SearchRow>();
  manifest!: SiteManifest;
  private exporting = false;
  constructor(readonly store: CandidateStore) {
    store.subscribe(() => this.sync());
    window.addEventListener("storage", (event) => store.handleStorageEvent(event));
    document.addEventListener("change", (event) => {
      const checkbox = event.target as HTMLInputElement;
      if (checkbox.matches("input[data-export-key]")) {
        this.selection.set(checkbox.dataset.exportKey!, checkbox.checked);
        this.syncSelection();
      }
    });
  }
  page(): string {
    this.selection.reconcile(this.store.items);
    return `<main id="main" class="page candidates-page"><h1>候補リスト</h1><p class="help">${CANDIDATE_PRIVACY_NOTICE}</p><div id="candidate-list-content">${this.content()}</div><div class="candidate-clear"><button class="button button--text" type="button" data-candidate-clear>候補をすべて削除</button></div></main>`;
  }
  private content(): string {
    return candidateListMarkup(resolveCandidates(this.store.items, this.rows), this.selection, this.expanded);
  }
  sync(): void {
    syncCandidateControls(document, new Set(this.store.items.map(candidateKey)), this.store.warning);
    this.selection.reconcile(this.store.items);
    const content = document.querySelector("#candidate-list-content");
    if (content) {
      const active = document.activeElement as HTMLElement | null;
      const focusKey = active?.getAttribute("data-candidate-remove");
      content.innerHTML = this.content();
      this.syncSelection();
      if (focusKey) {
        const next = [...content.querySelectorAll<HTMLButtonElement>("[data-candidate-remove]")]
          .find((button) => button.dataset.candidateRemove === focusKey);
        (next ?? document.querySelector<HTMLButtonElement>("[data-candidate-select='all']"))?.focus({ preventScroll: true });
      }
    }
  }
  private syncSelection(): void {
    const label = document.querySelector("#candidate-selection-count");
    if (label) label.textContent = `${this.store.items.length}件中 ${this.selection.selected.size}件選択`;
    document.querySelectorAll<HTMLInputElement>("[data-export-key]").forEach((input) => { input.checked = this.selection.selected.has(input.dataset.exportKey!); });
    document.querySelectorAll<HTMLButtonElement>("[data-candidate-export]").forEach((button) => { button.disabled = this.exporting || !this.selection.selected.size; });
  }
  handleClick(target: HTMLElement): boolean {
    const toggle = target.closest<HTMLElement>("[data-candidate-toggle]");
    if (toggle) {
      const key = toggle.dataset.candidateToggle!;
      const row = this.rows.get(key);
      if (row) { if (this.store.has(row)) this.store.remove(key); else this.store.add(row); }
      this.sync();
      return true;
    }
    const remove = target.closest<HTMLElement>("[data-candidate-remove]");
    if (remove) { this.store.remove(remove.dataset.candidateRemove!); return true; }
    if (target.closest("[data-candidate-clear]")) {
      if (window.confirm("保存した候補をすべて削除します。よろしいですか？")) this.store.clear();
      return true;
    }
    const select = target.closest<HTMLElement>("[data-candidate-select]");
    if (select) {
      if (select.dataset.candidateSelect === "all") this.selection.all(); else this.selection.clear();
      this.syncSelection();
      return true;
    }
    const output = target.closest<HTMLElement>("[data-candidate-export]");
    if (output) { void this.export(output.dataset.candidateExport as "csv" | "xlsx"); return true; }
    return false;
  }
  private async export(format: "csv" | "xlsx"): Promise<void> {
    if (this.exporting || !this.selection.selected.size) return;
    this.exporting = true;
    this.syncSelection();
    const status = document.querySelector("#candidate-export-status");
    if (status) status.textContent = "出力ファイルを作成しています…";
    const selection = new Set(this.selection.selected);
    const candidates = resolveCandidates(this.store.items, this.rows);
    try {
      const { candidateExportRows, candidateCsv, downloadExport, exportFilename } = await import("./candidate-export");
      const detailCache: DetailCache = new Map();
      const values = await candidateExportRows(candidates, selection, location.origin,
        async (row) => (await loadDetail(this.manifest, row, detailCache)).detail).finally(() => detailCache.clear());
      let blob: Blob;
      if (format === "xlsx") {
        const { candidateXlsx } = await import("./candidate-xlsx");
        const bytes = await candidateXlsx(values);
        blob = new Blob([bytes as Uint8Array<ArrayBuffer>], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
      } else blob = new Blob([candidateCsv(values)], { type: "text/csv;charset=utf-8" });
      downloadExport(blob, exportFilename(format));
      if (status?.isConnected) status.textContent = `${values.length}件を出力しました。`;
    } catch {
      if (status?.isConnected) status.textContent = "出力できませんでした。データ取得・ブラウザの保存設定を確認してください。Excelの文字数上限を超える場合はCSVをご利用ください。";
    } finally { this.exporting = false; this.syncSelection(); }
  }
}
