# Candidate list design v0.1

## Scope and preserved contracts

Browser-only candidate membership and exports; no account, API, database,
server persistence, search semantics change, or conditional-rule evaluation.
Canonical/release/unified/SQLite/Site-data remain read-only inputs. The current
logical triple `(source_dataset, source_version, record_id)` is never relaxed.
Existing URL state, header search memory, results disclosure/pagination,
floating counts, browser history and scroll restoration remain authoritative.

Results show `application_end` with the label `出願終了`, escaped but otherwise
unchanged (including whitespace/newlines); null is hidden. No date parser,
sort key, deadline classification or expiry inference is introduced.
Detail sections are 基本情報 → 日程 → 選考方法 → 出願条件 → 研究 →
その他の記録項目 → 出典. The previous-year warning stays above the title.

## Storage contract

Key: `early-admissions:candidate-list:v1`. JSON document:

```json
{
  "schema_version": "1",
  "items": [{
    "source_dataset": "kokkoritsu",
    "source_version": "5.61",
    "record_id": "OUC-2027-AO-GLOCAL",
    "saved_at": "2026-09-21T00:00:00.000Z",
    "snapshot": {
      "university": "小樽商科大学",
      "faculty_school": "商学部",
      "department": "昼間コース",
      "selection_name": "グローカル総合入試"
    }
  }]
}
```

Only the logical key, save timestamp and four display fields are persisted.
No raw admissions, personal student information, export selection, scroll
position, or search query is copied into this document. Membership is unique
by the whole triple. The URI-escaped detail path is an internal key encoding,
not a new data identifier. Insertion order is stable; duplicate add is a no-op.

One store synchronizes result/detail buttons and the header count. Before
mutations it rereads storage, and `storage` events update other tabs. Truly
simultaneous writes are last-write-wins; this is not a multi-user database.
Invalid JSON, malformed/duplicate items and unsupported schema versions block
writes and preserve the original bytes. The warning offers an explicit reset;
only the confirmed clear-all action can overwrite an unreadable document.
Unavailable storage or quota failure keeps working state in memory with a
visible warning; persistent writes resuming also restores cross-tab sync.

Storage is origin/browser/device-specific. Clearing browser data removes it.
Another browser, hosted preview origin or device does not automatically share
candidates. `/about/data` and the list explain this limitation. There is no
upload/synchronization endpoint; exports may fetch normal static detail shards.

## Resolution, route and interaction

`/candidates` and header `候補リスト（N）` use the shared store. Each saved key
resolves against current, hash-verified Site-data. Matching rows display current
information, not snapshot facts. An absent exact triple remains **stale** with
its snapshot and `現在データで確認できず`; it is not rebound to another source
version and has no replacement detail link. It can still be removed/exported.

University groups reuse the DADS disclosure. Candidate-group expansion is
stored separately from results-group expansion in history state. Buttons,
checkboxes and links remain separate controls with visible labels, native
keyboard behavior, yellow/black focus and mobile wrapping. Add/remove has
`aria-pressed`; export checkboxes identify the full university/admission name.
All-delete requires confirmation. Membership is not coupled to export choice.

Export selection is ephemeral: initially all candidates selected, retained
through same-session rerenders, new candidates selected, removed keys pruned.
Each row can be unchecked; select-all/clear-selection update the live selected
count. Both export buttons are disabled at zero and during export. Opening a
university does not alter selection. A full reload starts with all selected.

## Export contract

Both formats contain selected rows only and exactly the following 19 columns:

1. 大学名
2. 学部
3. 学科
4. 選抜区分
5. 選抜名称
6. 大学種別
7. 都道府県
8. 出願終了日
9. 評定条件
10. 英語資格条件
11. 研究業績要件
12. 選考方法
13. 公式情報URL
14. Site詳細URL
15. データ状態
16. 保存日時
17. source_dataset
18. source_version
19. record_id

Dates/GPA/English use raw text. Research uses raw summary when available,
otherwise the parent flag's readable label (`必要`/`要件なし`/`不明`/blank).
Selection methods join only the existing nine Yes flags; no inference.
Official URL uses source_url, then guideline_url if null. The Site link uses
runtime origin plus the complete escaped logical triple, never a local path or
hard-coded deployment. Stale rows export only their saved snapshot/identity,
save timestamp, durable old detail URL and stale label; other facts are blank.
A current row's missing/corrupt/mismatched detail fails the complete export,
never silently producing blank source facts or relabeling it stale.

Filenames: `early-admissions-candidates-YYYY-MM-DD.csv` / `.xlsx` (local date).
CSV is UTF-8 with BOM, CRLF records and RFC 4180 quotes (embedded raw newlines
preserved). Spreadsheet-formula-like cells gain a leading apostrophe to prevent
execution. This documented transport escape does not modify source data;
XLSX preserves these raw strings exactly as text cells. Null becomes blank in
the spreadsheet, while textual Unknown/No remain distinct literal values.
Excel may apply its own date/number inference when importing CSV; import as
text or use XLSX to preserve raw-looking dates and version strings as text.

XLSX is real OOXML via dynamically imported `@protobi/exceljs`, not a renamed
CSV. One sheet `候補リスト`, frozen first row, bold headers, autofilter,
column widths, wrapped text and HTTP(S)-only clickable URL cells. Values over
Excel's 32,767-character cell limit fail rather than truncate (use CSV).
No formulas or external workbook imports are accepted. CSV/Excel generation
and download stay in-browser. Object URLs are revoked after the download.

## Resource / dependency boundaries

Excel code is loaded only after Excel export, not during search startup or
CSV export. Detail receipts/SHA/build IDs are verified with the existing loader.
One export-scoped cache fetches each needed detail shard once, then clears on
success/failure; it does not become a persistent whole-detail-data cache.
Only one export runs at a time. There is no prefetch of all details.

See [third-party notices](third_party_notices.md) for MIT attribution, exact
dependency, maintenance review and the explicitly retained moderate audit
finding. Production sync includes the notice text in the distributed Site.
Bundle sizes and validation receipts are recorded in
[candidate-list QA](../validation/reports/candidate_list_qa_v0_1.md).

## Tests and limits

Tests cover storage add/remove/deduplication/reload, schema fail-closed behavior,
cross-tab updates/recovery, exact-key/stale resolution, escaping, shared buttons,
independent selection and clear confirmation, raw deadlines, detail ordering,
verified shard caching, selected-only exports, CSV quoting/BOM, real XLSX
round-trip, filter/freeze/hyperlinks/text safety and export failure behavior.
Browser QA covers desktop/mobile plus real downloaded files. Existing frozen
search oracle, English/Prefecture regressions and repository tests remain gates.
No commit, push, Sites version save or deployment is part of this change.
