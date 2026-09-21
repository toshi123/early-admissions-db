import { detailLink } from "./display";
import type { SearchRow } from "./types";

export const CANDIDATE_STORAGE_KEY = "early-admissions:candidate-list:v1";
export interface CandidateIdentity { source_dataset: string; source_version: string; record_id: string; }
export interface Candidate extends CandidateIdentity {
  saved_at: string;
  snapshot: Pick<SearchRow, "university" | "faculty_school" | "department" | "selection_name">;
}
export interface CandidateDocument { schema_version: "1"; items: Candidate[]; }
export interface ResolvedCandidate { saved: Candidate; row: SearchRow | null; }
type StorageAccess = Pick<Storage, "getItem" | "setItem">;

export const candidateKey = (identity: CandidateIdentity): string =>
  detailLink(identity.source_dataset, identity.source_version, identity.record_id);

function parseDocument(raw: string | null): Candidate[] {
  if (raw === null) return [];
  const document = JSON.parse(raw);
  if (document?.schema_version !== "1" || !Array.isArray(document.items)) throw new Error("unsupported");
  const keys = new Set<string>();
  return document.items.map((item: Candidate) => {
    if (!item || [item.source_dataset, item.source_version, item.record_id, item.saved_at]
      .some((value) => typeof value !== "string" || !value) || !Number.isFinite(Date.parse(item.saved_at)) ||
      typeof item.snapshot?.university !== "string" ||
      [item.snapshot.faculty_school, item.snapshot.department, item.snapshot.selection_name]
        .some((value) => value !== null && typeof value !== "string")) throw new Error("invalid");
    const key = candidateKey(item);
    if (keys.has(key)) throw new Error("duplicate");
    keys.add(key);
    // Keep only the documented minimal snapshot, even if storage contains extra fields.
    return { source_dataset: item.source_dataset, source_version: item.source_version,
      record_id: item.record_id, saved_at: item.saved_at,
      snapshot: { university: item.snapshot.university, faculty_school: item.snapshot.faculty_school,
        department: item.snapshot.department, selection_name: item.snapshot.selection_name } };
  });
}

export class CandidateStore {
  items: Candidate[] = [];
  warning = "";
  private blocked = false;
  private memoryOnly = false;
  private listeners = new Set<() => void>();
  constructor(private storage: StorageAccess | null) { this.reload(); }
  subscribe(listener: () => void): () => void { this.listeners.add(listener); return () => this.listeners.delete(listener); }
  private notify(): void { this.listeners.forEach((listener) => listener()); }
  has(identity: CandidateIdentity): boolean { return this.items.some((item) => candidateKey(item) === candidateKey(identity)); }
  reload(notify = true): void {
    if (this.memoryOnly) return;
    this.blocked = false;
    try {
      if (!this.storage) throw new Error("unavailable");
      const raw = this.storage.getItem(CANDIDATE_STORAGE_KEY);
      try { this.items = parseDocument(raw); this.warning = ""; }
      catch {
        this.items = [];
        this.blocked = true;
        this.warning = "保存済み候補の形式を読み取れません。元の保存内容は変更していません。候補リストから保存内容をリセットできます。";
      }
    } catch { this.memoryOnly = true; this.warning = "このブラウザでは候補を永続保存できません。このページを閉じると変更が失われる場合があります。"; }
    if (notify) this.notify();
  }
  private write(items: Candidate[], reset = false): boolean {
    if (this.blocked && !reset) return false;
    try {
      if (!this.storage) throw new Error("unavailable");
      this.storage.setItem(CANDIDATE_STORAGE_KEY, JSON.stringify({ schema_version: "1", items } satisfies CandidateDocument));
      this.warning = "";
      this.blocked = false;
      this.memoryOnly = false;
    } catch { this.memoryOnly = true; this.warning = "候補の変更をブラウザに保存できませんでした。現在のページ内だけで保持しています。"; }
    this.items = items;
    this.notify();
    return true;
  }
  add(row: SearchRow, now = new Date()): boolean {
    // Refresh before calculating the mutation; simultaneous writes remain last-write-wins.
    this.reload(false);
    if (this.blocked || this.has(row)) return false;
    return this.write([...this.items, { source_dataset: row.source_dataset, source_version: row.source_version,
      record_id: row.record_id, saved_at: now.toISOString(), snapshot: {
        university: row.university, faculty_school: row.faculty_school,
        department: row.department, selection_name: row.selection_name,
      } }]);
  }
  remove(key: string): boolean { this.reload(false); return this.write(this.items.filter((item) => candidateKey(item) !== key)); }
  clear(): boolean { return this.write([], true); }
  handleStorageEvent(event: Pick<StorageEvent, "key" | "storageArea">): void {
    if ((event.key === CANDIDATE_STORAGE_KEY || event.key === null) && event.storageArea === this.storage) this.reload();
  }
}

export function browserCandidateStorage(): Storage | null {
  try { return window.localStorage; } catch { return null; }
}

export function resolveCandidates(items: Candidate[], rows: ReadonlyMap<string, SearchRow>): ResolvedCandidate[] {
  return items.map((saved) => ({ saved, row: rows.get(candidateKey(saved)) ?? null }));
}

/** Ephemeral export choices are independent of persisted candidate membership. */
export class CandidateSelection {
  selected = new Set<string>();
  private known = new Set<string>();
  reconcile(items: Candidate[]): void {
    const keys = new Set(items.map(candidateKey));
    for (const key of keys) if (!this.known.has(key)) this.selected.add(key);
    for (const key of this.selected) if (!keys.has(key)) this.selected.delete(key);
    this.known = keys;
  }
  all(): void { this.selected = new Set(this.known); }
  clear(): void { this.selected.clear(); }
  set(key: string, checked: boolean): void {
    if (!this.known.has(key)) return;
    if (checked) this.selected.add(key); else this.selected.delete(key);
  }
}
