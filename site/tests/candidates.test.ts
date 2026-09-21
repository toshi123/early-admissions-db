import { beforeEach, describe, expect, it, vi } from "vitest";
import { CANDIDATE_STORAGE_KEY, CandidateSelection, CandidateStore, candidateKey, resolveCandidates } from "../src/candidates";
import { candidateButton, syncCandidateControls } from "../src/candidate-controls";
import { candidateListMarkup } from "../src/candidate-page";
import { compactResultCard } from "../src/search-ui";
import { CandidateView } from "../src/candidate-view";
import { candidateRow } from "./candidate-fixtures";

beforeEach(() => { localStorage.clear(); document.body.innerHTML = ""; vi.restoreAllMocks(); });

describe("candidate persistence", () => {
  it("adds once, persists a minimal versioned snapshot, reloads and removes", () => {
    const store = new CandidateStore(localStorage);
    const row = candidateRow();
    expect(store.add(row, new Date("2026-09-21T00:00:00Z"))).toBe(true);
    expect(store.add(row)).toBe(false);
    const value = JSON.parse(localStorage.getItem(CANDIDATE_STORAGE_KEY)!);
    expect(value.schema_version).toBe("1");
    expect(Object.keys(value.items[0])).toEqual(["source_dataset", "source_version", "record_id", "saved_at", "snapshot"]);
    expect(Object.keys(value.items[0].snapshot)).toEqual(["university", "faculty_school", "department", "selection_name"]);
    const reloaded = new CandidateStore(localStorage);
    expect(reloaded.items).toEqual(store.items);
    expect(reloaded.has(row)).toBe(true);
    expect(reloaded.remove(candidateKey(row))).toBe(true);
    expect(new CandidateStore(localStorage).items).toEqual([]);
  });

  it.each(["{", '{"schema_version":"2","items":[]}', '{"schema_version":"1","items":[null]}'])("fails safely without overwriting unsupported storage: %s", (raw) => {
    localStorage.setItem(CANDIDATE_STORAGE_KEY, raw);
    const store = new CandidateStore(localStorage);
    expect(store.items).toEqual([]);
    expect(store.warning).toContain("元の保存内容は変更していません");
    expect(store.add(candidateRow())).toBe(false);
    expect(localStorage.getItem(CANDIDATE_STORAGE_KEY)).toBe(raw);
    store.clear();
    expect(store.add(candidateRow())).toBe(true);
  });

  it("keeps memory-only additions when storage is unavailable or its quota is exceeded", () => {
    for (const storage of [null, { getItem: () => null, setItem: () => { throw new Error("quota"); } }]) {
      const store = new CandidateStore(storage);
      store.add(candidateRow());
      store.add(candidateRow({ record_id: "B" }));
      expect(store.items).toHaveLength(2);
      expect(store.warning).not.toBe("");
      store.remove(candidateKey(candidateRow()));
      expect(store.items).toHaveLength(1);
    }
  });

  it("refreshes from storage events, preserves other-tab entries before a new add, and handles clear", () => {
    const first = new CandidateStore(localStorage);
    const second = new CandidateStore(localStorage);
    first.add(candidateRow());
    second.handleStorageEvent({ key: CANDIDATE_STORAGE_KEY, storageArea: localStorage });
    expect(second.items).toHaveLength(1);
    first.add(candidateRow({ record_id: "B" }));
    second.add(candidateRow({ record_id: "C" }));
    expect(second.items).toHaveLength(3);
    first.clear();
    second.handleStorageEvent({ key: null, storageArea: localStorage });
    expect(second.items).toEqual([]);
  });

  it("resumes storage synchronization after a transient write failure recovers", () => {
    const write = vi.spyOn(Storage.prototype, "setItem").mockImplementationOnce(() => { throw new Error("quota"); });
    const store = new CandidateStore(localStorage);
    store.add(candidateRow());
    expect(store.warning).not.toBe("");
    write.mockRestore();
    store.add(candidateRow({ record_id: "B" }));
    expect(store.warning).toBe("");
    new CandidateStore(localStorage).clear();
    store.handleStorageEvent({ key: CANDIDATE_STORAGE_KEY, storageArea: localStorage });
    expect(store.items).toEqual([]);
  });

  it("rejects duplicate or malformed saved entries without rewriting the original document", () => {
    const store = new CandidateStore(localStorage); store.add(candidateRow());
    const entry = store.items[0];
    for (const items of [[entry, entry], [{ ...entry, saved_at: "invalid date" }], [{ ...entry, snapshot: {} }]]) {
      const raw = JSON.stringify({ schema_version: "1", items });
      localStorage.setItem(CANDIDATE_STORAGE_KEY, raw);
      const invalid = new CandidateStore(localStorage);
      expect(invalid.items).toEqual([]); expect(invalid.warning).not.toBe("");
      expect(invalid.add(candidateRow())).toBe(false);
      expect(localStorage.getItem(CANDIDATE_STORAGE_KEY)).toBe(raw);
    }
  });

  it("resolves only the entire logical key and uses current data over its old snapshot", () => {
    const store = new CandidateStore(localStorage);
    store.add(candidateRow());
    const current = candidateRow({ university: "更新後の大学名" });
    expect(resolveCandidates(store.items, new Map([[candidateKey(current), current]]))[0].row?.university).toBe("更新後の大学名");
    const otherVersion = candidateRow({ source_version: "5.62" });
    expect(resolveCandidates(store.items, new Map([[candidateKey(otherVersion), otherVersion]]))[0].row).toBeNull();
  });
});

describe("candidate controls and export selection", () => {
  it("synchronizes result/detail buttons and header count from one store", () => {
    const row = candidateRow();
    document.body.innerHTML = `<span id="candidate-count"></span>${candidateButton(row)}${candidateButton(row)}`;
    const store = new CandidateStore(localStorage);
    store.subscribe(() => syncCandidateControls(document, new Set(store.items.map(candidateKey)), store.warning));
    store.add(row);
    expect(document.querySelector("#candidate-count")?.textContent).toBe("（1）");
    expect([...document.querySelectorAll("button")].every((b) => b.textContent === "候補から外す" && b.getAttribute("aria-pressed") === "true")).toBe(true);
    store.remove(candidateKey(row));
    expect([...document.querySelectorAll("button")].every((b) => b.textContent === "候補に追加")).toBe(true);
  });

  it("defaults to all selected, keeps unchecks on rerender, and never removes a saved candidate on deselection", () => {
    const store = new CandidateStore(localStorage);
    store.add(candidateRow()); store.add(candidateRow({ record_id: "B" }));
    const selection = new CandidateSelection(); selection.reconcile(store.items);
    expect(selection.selected.size).toBe(2);
    selection.set(candidateKey(store.items[0]), false); selection.reconcile(store.items);
    expect(selection.selected.size).toBe(1);
    expect(store.items.length).toBe(2);
    selection.clear(); expect(selection.selected.size).toBe(0);
    selection.all(); expect(selection.selected.size).toBe(2);
    store.remove(candidateKey(store.items[0])); selection.reconcile(store.items);
    expect(selection.selected.size).toBe(1);
  });

  it("reuses university disclosures and keeps checkbox selection independent of disclosure state", () => {
    const store = new CandidateStore(localStorage); const row = candidateRow(); store.add(row);
    const selection = new CandidateSelection(); selection.reconcile(store.items); selection.clear();
    document.body.innerHTML = candidateListMarkup(resolveCandidates(store.items, new Map([[candidateKey(row), row]])), selection, new Set([row.university]));
    expect(document.querySelector('[data-university-toggle]')?.getAttribute("aria-expanded")).toBe("true");
    expect(document.querySelector("#candidate-selection-count")?.textContent).toBe("1件中 0件選択");
    expect([...document.querySelectorAll<HTMLButtonElement>("[data-candidate-export]")].every((button) => button.disabled)).toBe(true);
    expect(document.querySelector("input")?.getAttribute("aria-label")).toContain("出力対象：東京大学");
    (document.querySelector("input") as HTMLInputElement).click();
    expect(document.querySelector('[data-university-toggle]')?.getAttribute("aria-expanded")).toBe("true");
  });

  it("shows a stale snapshot, a stale status, and removal without linking to a replacement", () => {
    const store = new CandidateStore(localStorage); store.add(candidateRow());
    const selection = new CandidateSelection(); selection.reconcile(store.items);
    const html = candidateListMarkup(resolveCandidates(store.items, new Map()), selection, new Set());
    expect(html).toContain("現在データで確認できず");
    expect(html).toContain("情報学科");
    expect(html).toContain("data-candidate-remove");
    expect(html).not.toContain("admission-detail-link");
  });

  it("escapes saved snapshot text instead of rendering markup from storage", () => {
    const store = new CandidateStore(localStorage);
    store.add(candidateRow({ university: '<img src=x onerror="alert(1)">', selection_name: '<script>alert(1)</script>' }));
    const selection = new CandidateSelection(); selection.reconcile(store.items);
    document.body.innerHTML = candidateListMarkup(resolveCandidates(store.items, new Map()), selection, new Set());
    expect(document.querySelector("img, script")).toBeNull();
    expect(document.body.textContent).toContain('<script>alert(1)</script>');
  });

  it("does not backfill a current null field with its older snapshot in accessible labels", () => {
    const store = new CandidateStore(localStorage); store.add(candidateRow());
    const current = candidateRow({ department: null });
    const selection = new CandidateSelection(); selection.reconcile(store.items);
    document.body.innerHTML = candidateListMarkup(resolveCandidates(store.items, new Map([[candidateKey(current), current]])), selection, new Set());
    expect(document.querySelector("[data-export-key]")?.getAttribute("aria-label")).not.toContain("情報学科");
  });

  it("requires confirmation for clear-all and preserves entries when cancelled", () => {
    const store = new CandidateStore(localStorage); store.add(candidateRow());
    const view = new CandidateView(store);
    document.body.innerHTML = '<button data-candidate-clear>候補をすべて削除</button>';
    vi.spyOn(window, "confirm").mockReturnValue(false);
    view.handleClick(document.querySelector("button")!); expect(store.items).toHaveLength(1);
    vi.mocked(window.confirm).mockReturnValue(true);
    view.handleClick(document.querySelector("button")!); expect(store.items).toHaveLength(0);
  });

  it("displays deadline raw wording losslessly, without guessing when null", () => {
    document.body.innerHTML = compactResultCard(candidateRow(), false, false);
    expect(document.querySelector(".application-end span")?.textContent).toBe(candidateRow().application_end);
    expect(compactResultCard(candidateRow({ application_end: null }), false)).not.toContain('class="application-end"');
  });
});
