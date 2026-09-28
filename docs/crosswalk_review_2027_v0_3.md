# 2027 canonical raw-value crosswalk review (2026-09-28)

The current candidate-audit SQLite artifact was used only as a read-only inventory of unregistered exact raw strings. Canonical CSV, Unified contract v0.3, and the prior crosswalk versions were not edited. Per-value decisions, affected row counts, representative record IDs, and official-source URLs are in [`raw_decisions.csv`](../validation/reports/crosswalk_20270928_v0_3/raw_decisions.csv). The URLs are the provenance retained on the canonical admission rows; this review classifies the preserved raw text and does not assert new admission facts from the linked pages.

| Layer | New distinct raw strings | Affected admission rows | Safe existing classification | `review_required` | Other explicit status |
| --- | ---: | ---: | ---: | ---: | ---: |
| English requirement | 10 | 118 | 7 (6 `required`, 1 `not_required`) | 3 | 0 |
| Grade requirement | 6 | 131 | 0 | 4 | 2 `unknown` |
| Academic field v0.1 | 2 | 5 | 0 | 2 | 0 |
| Academic field v0.2 taxonomy layer | Same 2 | Same 5 | 0 | 2 | 0 |

The explicit TOEFL/TOEIC score or required score-submission phrases map to `required`; “外部英語資格の必須要件なし。” maps to `not_required`. “詳細学生募集要項で確認待ち。” and an external qualification whose necessity awaits the detailed guide remain `review_required`. Grade phrases that only say no *numeric* threshold is stated remain `review_required`, with no GPA floor. A detailed guide not yet checked or announced for later publication remains `unknown`. “環境・農学” and “生命・バイオ” have no safe unique mapping from the raw label alone, so both academic-field layers keep zero memberships and `review_required`.

Versioned replacements: English and grade crosswalk v0.3, academic field v0.1-layer crosswalk v0.3, academic field v0.2-taxonomy raw/context crosswalk v0.4, SQLite schema v0.3 and corresponding child table SQL revisions, Site search-row schema v0.3 and detail schema v0.4. The previous versions remain intact. Existing exact mappings are copied unchanged except for the new contract-version value. The Site data format remains v0.3; its search-row and detail validators accept the new mapping versions.
