# DADS UI migration and header search-state QA v0.1

## Outcome

Status: **PASS for local implementation and production build**

QA date: 2026-09-21 (Asia/Tokyo)

Base source commit: `65dff2320be743d078c5a7a3e50109ca72ad76da`

No commit, push, ChatGPT Sites Version save, or deployment update was
performed.

## Reference provenance

- DADS: Digital Agency Design System beta v2.18.0 (2026-09-09)
- User-supplied Markdown archive SHA-256:
  `9373051a82547f8563660ada46be10d4b08eb0003b5ec93dc832f7c4ce8e0212`
- Official vanilla HTML/CSS snippet commit:
  `af8b6656c8d864a22ef444d088e5568f3416f6aa`
- Snippet license: MIT; copyright and permission notice preserved in
  `docs/third_party_notices.md`
- Component and foundation decisions:
  `docs/dads_ui_mapping_v0_1.md`

## Automated validation

- Focused UI/state tests: 17/17 passed.
- Frontend tests: 70/70 passed across 11 files.
- Repository Python tests: 74/74 passed.
- Frozen structured-search regression: 25/25 passed.
- SQLite SHA-256 before/after frozen search QA:
  `8fb343257d75ff3a001679c0c55f60c85fcb7ac7a38893271ee444ce99bd6354`.
- TypeScript compile: passed.
- Production build: passed with Vite 6.4.3.
- Production frontend output:
  - HTML: 0.67 kB (gzip 0.49 kB)
  - CSS: 12.29 kB (gzip 3.31 kB)
  - JavaScript: 38.98 kB (gzip 13.03 kB)
- `git diff --check`: passed.

## Browser QA

The local Vite Site was exercised in Chromium at the default desktop viewport
and a 390 x 844 mobile viewport.

Verified routes and behaviors:

- `/search`: one-column form, DADS header navigation, checkbox/radio anatomy,
  input and validation states, disclosure, primary/secondary buttons, normal
  live count, and floating live count.
- `/results`: compact Resource List treatment, title-only result links,
  preserved result facts/order, and DADS-style page navigation.
- `/admissions/...`: preserved section order, Description List treatment,
  source links, and non-eligibility notice.
- `/about/data`: preserved content, responsive typography, and active header
  navigation.
- DADS Yellow-300 plus black double focus indicator was visually checked on
  the skip link, GPA input, checkbox, and links.
- University combobox remained exact-selection-only and keyboard-exposed as an
  ARIA combobox.
- Mobile search, results, detail, and about views reflowed without observed
  horizontal overflow; the two-link header remained readable.
- Floating count appeared after the normal count left the viewport, updated
  from `2,575件・81大学` to `2,074件・79大学` after a filter change, and replaced
  the old count with `条件を確認してください` for the intermediate GPA `3.`.
- The normal live output remained the only `aria-live` region.
- Results to detail to browser-back returned to the prior result-list position.

## Header search-state QA

- `/search` form changes immediately updated the header search `href`.
- `/results` exposed the canonical result query in the header search `href`.
- Detail and About used the session-scoped last valid search query.
- A fresh browsing session without stored search state used `/search`.
- Search form state was fully reconstructed from the header destination URL.
- `page`, unknown parameters, unsupported values, and invalid draft-only
  university/GPA text were excluded by automated tests.
- The header navigation behavior remained independent of browser-back history
  and scroll restoration.

## Screenshot QA

Current Desktop search, Desktop results, Desktop detail, Mobile search, Mobile
results, Mobile detail, Mobile About, focus, floating-count, and invalid-state
screenshots were captured and inspected in the browser QA session. Existing
pre-migration screenshots under `validation/screenshots/` remain unchanged.
No new generated screenshot file was added to the repository in this run.

## Data and deployment boundary

- Canonical, release, unified, and SQLite artifacts were not modified.
- Generated `site/public/site-data`, `site/dist`, caches, and dependencies remain
  outside the source changes.
- Existing deployment and access scope were not touched.
