# Candidate list / deadline / detail-order QA v0.1

Date: 2026-09-21. Local implementation only, based on `a62ce1a` plus the
already-uncommitted application-condition badges/detail simplification.
No commit, push, Sites version save, or deployment update performed.

## Implemented scope

- Raw `application_end` in compact results (null hidden, no date parsing).
- Detail order: 基本情報 → 日程 → 選考方法 → 出願条件 → 研究 →
  その他の記録項目 → 出典; fallback warning retained at the top.
- Versioned localStorage candidate membership, minimal snapshots, exact triple
  resolution, stale status, synchronized add/remove controls/header count.
- `/candidates` university disclosures and independent export selection;
  CSV with BOM and real XLSX, selected rows only, fixed 19 columns.
- Storage failure/schema warnings, clear-all confirmation, XSS escaping,
  formula-safe exports, DADS keyboard focus and responsive layout.
- Privacy explanation, design contract, MIT notice distributed with the Site.

## Automated validation

| Gate | Result |
|---|---|
| `cd site && npm test` | **119/119 PASS**, 14 files, 2.01 seconds |
| Frozen Python-oracle cases in frontend suite | **25/25 PASS**, full logical-key sets and summaries |
| `PYTHONPATH=src python3 -m unittest discover -s tests` | **74/74 PASS**, 52.799 seconds |
| `./scripts/run_search_qa --report <temporary-report>` | **25/25 PASS**, SQLite SHA unchanged |
| English focused tests | **2/2 PASS** |
| Prefecture focused tests | **3/3 PASS** |
| `cd site && npm run build` | **PASS**, TypeScript + Vite, 2.48 seconds for final Vite build |
| `git diff --check` | **PASS** |
| Source canonical / releases / unified / SQLite / Site-data | **unchanged** |
| Notice in production output | byte-identical to `docs/third_party_notices.md` |

Focused tests cover add/remove/duplicate/reload, invalid/future schema, quota
failure and recovery, cross-tab storage events, full-key current/stale resolution,
same-store controls, reset confirmation, independent select/uncheck/all/none,
zero-selection disabled exports, raw dates and detail order. Export tests include
Japanese/comma/quote/newline preservation, fixed columns, stale rows, URL identity,
formula-like text, real XLSX round-trip, header/filter/freeze/links and missing or
corrupt detail fail-closed behavior. Verified shard cache tests retain exact-key
checks and retry after an integrity failure. Existing URL/header/back/floating
count/DADS/search tests remain in the passing suite.

## Browser QA

Local Vite dev preview and a separate local **production preview** were tested;
the hosted deployment was not opened or modified for this change.

| Flow / observation | Result |
|---|---|
| Desktop 1280×900: search → result add → header count → detail saved state | PASS |
| Mobile 390×844: same add/detail flow | PASS |
| Candidate list groups: 小樽商科大学 + 東京外国語大学 | PASS, independently expanded |
| Individual checkbox deselection does not remove a candidate | PASS: 2 candidates / 1 selected; later 4 / 1 |
| Clear selection disables both exports; select all restores count | PASS |
| Desktop + mobile CSV and Excel export buttons | PASS, completion statuses |
| Reload persistence | PASS: saved membership survives; selection resets to all |
| Desktop detail → browser back | PASS: Tokyo Foreign Studies disclosure open, scroll 742 → 742 |
| Mobile detail → browser back | PASS: disclosure open; no search-state reset |
| Header search link from detail/candidates | PASS: exact university URL restored into the form |
| Detail section order | PASS, observed headings; raw dates retained |
| DADS keyboard focus | PASS: 4px black outline + Yellow-300 2px ring |
| Mobile 320×740 | PASS: document scrollWidth=clientWidth=305px with a 15px scrollbar gutter |
| Production bundle: add → candidates → lazy XLSX export | PASS, actual second XLSX downloaded |
| Candidate removal UI → header/results/detail reflection | PASS: 3→2; removed GLOCAL showed `候補に追加` in results and detail; detail re-add returned 3 |
| Clear-all cancellation | PASS: confirmation cancelled; all 3 remained |
| Clear-all confirmation + reload | PASS: header/list 0; reload remained 0 |
| Re-add after clear | PASS: same 3 logical keys added again |

The final narrow-screen check found the existing `body min-width:320px` could
overflow a 320px viewport with a reserved scrollbar gutter. It was changed to
`min(320px, 100%)`, then the responsive test, full frontend suite and production
build were rerun. Header navigation uses two rows below 800px, with labels kept
intact and wrap permitted between navigation items. Screenshots were visually
reviewed in the browser; no screenshot binaries are added to Git.

The destructive QA used only candidates created for this localhost test.
Single-delete, clear cancellation, confirmed clear, reload-at-zero and re-add
were all exercised through the real Chrome UI; no hosted candidate state,
canonical fact or generated database was changed.

Examples checked:

- `OUC-2027-AO-GLOCAL`: 出願終了 `2026-10-20`, English condition badge,
  oral exam + group discussion, saved from result and confirmed in detail.
- `OUC-2027-REC-DAY`: 出願終了 `2027-01-21`, common-test selection method.
- `TUFS-2027-REC-LC-ITA` and `TUFS-2027-REC-LC-CHI`: 出願終了 `2026-11-05`,
  English condition badge, interview + essay; desktop/mobile navigation.

## Actual downloaded files

Chrome downloaded `early-admissions-candidates-2026-09-21.csv` (894 bytes) and
`.xlsx` (8,137 bytes). Both were opened in Microsoft Excel without a repair
error; both had Japanese headers and exactly one selected admission,
`OUC-2027-AO-GLOCAL`, in range A1:S2. The CSV import wizard detected UTF-8;
comma delimiter produced the correct 19 columns. CSV bytes begin `EF BB BF`.
Excel may infer dates/numbers when importing CSV; use text import or XLSX when
preserving cell types is important. The downloaded CSV itself was not rewritten.

The XLSX inspection verified `候補リスト`, frozen row 1, autofilter A1:S2,
wrapped condition text, readable column widths, and text/hyperlink values in
the two URL columns. The Site URL used the running origin and complete triple,
not a hard-coded deployed address. A separate production-preview download also
completed successfully. Chrome console diagnostics contained an unrelated
extension-origin `version_footer` error, not an application-origin failure.

After destructive QA, the three re-added candidates were exported again.
The newest CSV was 2,035 bytes with BOM `EF BB BF`; the newest XLSX was 8,600
bytes with range A1:S4, 19 columns, frozen row 1 and autofilter A1:S4. Its IDs
were exactly `OUC-2027-REC-DAY`, `OUC-2027-AO-GLOCAL`, and
`OUC-2027-REC-NIGHT` in saved order.

## Bundle / dependency impact

| Output | Bytes | gzip bytes | Load timing |
|---|---:|---:|---|
| Initial JavaScript | 54,464 | 17,804 | normal startup |
| CSS | 15,107 | 3,789 | normal startup |
| Candidate export helper | 2,178 | 1,351 | first export |
| Excel chunk | 1,082,620 | 311,502 | **Excel export only** |

Recorded pre-change initial JS was approximately 41.49KB / 13.70KB gzip;
the initial gzip increment is about 4.1KB. Vite reports a large-chunk warning
for the deliberately lazy Excel chunk; the warning threshold was not raised.
MIT notices are copied into the distribution. `@protobi/exceljs` is pinned;
the lockfile is committed source, but no dependency directory is tracked.

`npm audit`: **2 moderate entries, no high/critical**, both from one uuid
advisory. See `docs/third_party_notices.md` for the used-API reachability review
and residual risk. This is **not** a clean audit, and a uuid lockfile override
would not patch the prebuilt browser bundle. No force-fix was used.

## Preservation and boundaries

- SQLite SHA-256:
  `8fb343257d75ff3a001679c0c55f60c85fcb7ac7a38893271ee444ce99bd6354`
- Unified master SHA-256:
  `1df386ed99532a3dff381507978a1454d7c20113574285b2526f6ae122050279`
- Unified coverage SHA-256:
  `b10ca3381afb0f3e8740ed2d14ddf086233151d4c6eba6e946344b12638913fb`
- Unified research SHA-256:
  `ba105cca34c03fee34fb7d04ce1d0818caa386d0832e7999bf9ec9bf9f135919`
- Site-data build ID: `2f77f8f2b14343d803fd` (unchanged).
- Canonical/release/schema/.worktreeinclude have no diff.
- Generated Site-data, notices copy, dist, node_modules and caches stay ignored.
- Application implementation is frozen. Only the QA report was added after
  final validation. One full repository test run; two production builds, the
  second solely for the verified small-viewport fix. No bulk data regeneration.

Remaining limitations: local-only storage (no synchronization across devices),
last-write-wins simultaneous tab mutations, visible memory-only fallback when
storage fails, and the noted moderate dependency advisory. None is hidden by
changing canonical facts or tests.
