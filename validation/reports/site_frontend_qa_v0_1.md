# Early Admissions Search Site frontend QA v0.1

## Outcome

Status: **PASS for local implementation and review build**

Data build: `bbffbaee7aadbdb0ae43`

Site-data schema: `0.1`

Rows: 5,921 admissions, 249 universities

QA date: 2026-09-20

No ChatGPT Site was provisioned, saved, or deployed during this QA run.

## Automated results

- Frontend: 39/39 tests passed across 5 files.
- Frozen 25-query oracle: 25/25 logical-key sets passed.
- The same 25 cases also matched source counts, university counts, GPA safe
  match counts, conditional/review counts, and not-numerically-evaluable counts.
- Repository Python regression: 69/69 tests passed in 46.492 seconds.
- Production build: PASS with Vite 6.4.3 and TypeScript 5.8.3.
- Dependency audit: 0 known vulnerabilities.

## 25-query equivalence summary

| # | Query | Rows | Universities | Source rows (kokkoritsu/shidai) |
|---:|---|---:|---:|---:|
| 1 | 東京＋理系 | 891 | 48 | 168 / 723 |
| 2 | 東京＋理系＋評定3.8 | 66 | 11 | 2 / 64 |
| 3 | 東京＋理系＋評定3.8＋研究活動関連 | 14 | 2 | 0 / 14 |
| 4 | 東京/神奈川＋併願可 | 459 | 29 | 0 / 459 |
| 5 | 学校推薦型＋推薦必要 | 2,804 | 221 | 2,272 / 532 |
| 6 | 共通テスト不要 | 4,518 | 228 | 2,273 / 2,245 |
| 7 | 口頭試問あり | 1,577 | 127 | 756 / 821 |
| 8 | プレゼンあり | 601 | 112 | 349 / 252 |
| 9 | 面接＋小論文 | 1,734 | 178 | 1,020 / 714 |
| 10 | GPA 3.5 strict-safe | 490 | 59 | 251 / 239 |
| 11 | GPA 3.8 strict-safe | 743 | 103 | 433 / 310 |
| 12 | GPA 4.0 strict-safe | 1,124 | 136 | 764 / 360 |
| 13 | 国公立＋研究実績要件あり | 138 | 31 | 138 / 0 |
| 14 | 私立＋共通テスト不要＋併願可 | 765 | 41 | 0 / 765 |
| 15 | 東京/神奈川＋工学/情報＋GPA 4.0 | 11 | 5 | 0 / 11 |
| 16 | GPA 3.8 review mode | 1,450 | 152 | 684 / 766 |
| 17 | GPA 3.8 all mode | 5,921 | 249 | 3,668 / 2,253 |
| 18 | 面接＋筆記試験＋共通テスト不要 | 1,098 | 114 | 550 / 548 |
| 19 | 東京＋工学group | 344 | 29 | 76 / 268 |
| 20 | 東京＋情報group | 162 | 25 | 33 / 129 |
| 21 | 東京/神奈川＋工学OR情報group＋GPA 3.8 | 75 | 11 | 0 / 75 |
| 22 | 医学group | 154 | 59 | 114 / 40 |
| 23 | 医歯薬group | 341 | 80 | 173 / 168 |
| 24 | 農学OR生命科学group | 780 | 104 | 377 / 403 |
| 25 | 要確認academic field | 19 | 7 | 8 / 11 |

The GPA 3.8 regressions were also preserved: strict-safe 743, review 1,450
(743 safe + 707 conditional), and all 5,921 (including 4,015 not numerically
evaluable).

## Browser and responsive QA

Local Vite preview was exercised in the Codex in-app Chromium browser.

| Viewport | Result |
|---|---|
| Desktop 1440×900 | sticky filters, two-column cards, detail sections and provenance visually checked |
| Tablet 820×1024 | collapsible filter drawer, 20-card pagination, 805 px client/scroll widths (no horizontal overflow) |
| Mobile 390×844 | one-column cards, full-height drawer, 375 px client/scroll widths (no horizontal overflow) |

Verified interactions: repeated URL filters, safe GPA summary, pagination,
removable active filters, detail navigation, browser navigation, mobile drawer,
Escape close/focus return, fallback banner, two preserved duplicate child rows,
About page, zero-result guidance, two visible invalid-parameter warnings, and a
missing-detail data-error view.

WebMCP registered both intended tools. A representative valid call produced 465
rows across 38 universities. A GPA value outside 0.0–5.0 was rejected before
mutation and the URL remained unchanged.

## Performance measurements

These are local-browser timings, not production network benchmarks. Desktop was
measured at 1440×900 and mobile at 390×844. The localhost cache was warm for
some requests; artifact SHA-256 verification remained active.

| Metric (ms) | Desktop | Mobile |
|---|---:|---:|
| Manifest fetch | 4.7 | 5.6 |
| Filter options fetch | 4.1 | 4.8 |
| Filter JSON parse | 0.2 | 0.2 |
| Search shard fetch (parallel critical path) | 29.6 | 27.5 |
| Search shard SHA verification (sum) | 6.1 | 5.3 |
| Search shard JSON parse (sum) | 25.7 | 16.6 |
| Client data preparation | 0.0 | 0.1 |
| Total preparation | 49.9 | 41.2 |
| First search | 39.6 | 33.7 |
| First rendered result view | 107.5 | 87.7 |
| Representative filter change | 29.4 | — |
| Detail shard lazy-load | 32.6 | — |

Locally recompressing the exact production assets with gzip level 9 produced:

- manifest + filter options + 8 search shards: 495,252 bytes;
- frontend JS + CSS + HTML plus initial Site-data: 511,245 bytes;
- expanded initial Site-data JSON: 8,983,502 bytes.

No special CPU-throttling capability was available in the selected browser, so
a low-end CPU claim is intentionally not made. The measured parse/search/render
times did not justify adding an index or lazy search-shard architecture in v0.1.

## Accessibility checks

- keyboard-operable native controls and buttons;
- programmatic labels and semantic heading order;
- visible focus ring with non-color status labels;
- mobile focus trap, Escape close, and focus return;
- link/button distinction and external-link labels;
- contrast and responsive card readability checked visually.

The keyboard focus trap also has an automated regression test. A formal WCAG
conformance audit and assistive-technology matrix remain outside v0.1.

## Review gate and remaining limitations

Before deployment, create a reviewable Sites version from `site/`, confirm the
static route fallback on direct detail URLs in the hosted preview, repeat the
main desktop/mobile flows, and review official-source external links. The raw
academic-field advanced selector contains 448 exact values and is deliberately
dense; it remains secondary to the 19-group primary filter.
