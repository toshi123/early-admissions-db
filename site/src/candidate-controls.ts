import { candidateKey, type CandidateIdentity } from "./candidates";
import { escapeHtml } from "./display";

export function candidateButton(row: CandidateIdentity, saved = false): string {
  return `<button type="button" class="button button--outline candidate-toggle" data-candidate-toggle="${escapeHtml(candidateKey(row))}" aria-pressed="${saved}">${saved ? "候補から外す" : "候補に追加"}</button>`;
}

export function syncCandidateControls(root: ParentNode, keys: ReadonlySet<string>, warning: string): void {
  root.querySelectorAll<HTMLButtonElement>("[data-candidate-toggle]").forEach((button) => {
    const saved = keys.has(button.dataset.candidateToggle!);
    button.setAttribute("aria-pressed", String(saved));
    button.textContent = saved ? "候補から外す" : "候補に追加";
  });
  const count = root.querySelector("#candidate-count");
  if (count) count.textContent = `（${keys.size.toLocaleString("ja-JP")}）`;
  const notice = root.querySelector<HTMLElement>("#candidate-storage-warning");
  if (notice) { notice.textContent = warning; notice.hidden = !warning; }
}
