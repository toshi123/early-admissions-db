# Structured search CLI v0.1 representative QA

- Generated: `2026-09-20T14:30:24Z`
- SQLite: `data/derived/sqlite/early_admissions_2027.sqlite`
- SQLite SHA-256 before/after: `8fb343257d75ff3a001679c0c55f60c85fcb7ac7a38893271ee444ce99bd6354` / `8fb343257d75ff3a001679c0c55f60c85fcb7ac7a38893271ee444ce99bd6354`
- Queries: 25
- Access: URI `mode=ro&immutable=1` plus `PRAGMA query_only=ON`
- GPA meaning: `safe match` means `overall GPA condition safely matched`; it is not an application-eligibility determination.

## Results

| # | Query and command | Total | GPA safe match | Conditional/review | Not numerically evaluable | Sources | Universities | Representative results |
|---:|---|---:|---:|---:|---:|---|---:|---|
| 1 | 東京＋理系<br><code>./scripts/search --prefecture '東京都' --stem --limit 3</code> | 891 | — | 219 | 570 | kokkoritsu=168, shidai=723 | 48 | OCHA-2027-AO-HENV (お茶の水女子大学, not numerically evaluable); OCHA-2027-REC-CULTINFO (お茶の水女子大学, not numerically evaluable); OCHA-2027-AO-CULTINFO (お茶の水女子大学, not numerically evaluable) |
| 2 | 東京＋理系＋評定3.8<br><code>./scripts/search --prefecture '東京都' --stem --gpa 3.8 --limit 3</code> | 66 | 66 | 0 | 0 | kokkoritsu=2, shidai=64 | 11 | CHUO-2027-SDR-01 (中央大学, safe match); SOKA-2027-BASIC-HEIGAN-GREEN (創価大学, safe match); SOKA-2027-BASIC-HEIGAN-ISE (創価大学, safe match) |
| 3 | 東京＋理系＋評定3.8＋研究活動関連<br><code>./scripts/search --prefecture '東京都' --stem --gpa 3.8 --research-activity-level-status required relevant --limit 3</code> | 14 | 14 | 0 | 0 | shidai=14 | 2 | CHUO-2027-SDR-01 (中央大学, safe match); NODAI-2027-FAM-16 (東京農業大学, safe match); NODAI-2027-FAM-19 (東京農業大学, safe match) |
| 4 | 東京/神奈川＋併願可<br><code>./scripts/search --prefecture '東京都' '神奈川県' --exclusive '併願可' --limit 3</code> | 459 | — | 69 | 342 | shidai=459 | 29 | CHUO-2027-SDB-SPORTS-MGMT (中央大学, conditional/review required); CHUO-2027-SDB-DS-PRO (中央大学, conditional/review required); CHUO-2027-SDB-DS-WOMEN (中央大学, conditional/review required) |
| 5 | 学校推薦型＋推薦必要<br><code>./scripts/search --selection-category '学校推薦型選抜' --school-recommendation-required Yes --limit 3</code> | 2804 | — | 360 | 1573 | kokkoritsu=2272, shidai=532 | 221 | OCHA-2027-REC-CULTINFO (お茶の水女子大学, not numerically evaluable); OCHA-2027-REC-HUM (お茶の水女子大学, not numerically evaluable); OCHA-2027-REC-SOC (お茶の水女子大学, not numerically evaluable) |
| 6 | 共通テスト不要<br><code>./scripts/search --common-test-required No --limit 3</code> | 4518 | — | 665 | 2838 | kokkoritsu=2273, shidai=2245 | 228 | OCHA-2027-REC-CULTINFO (お茶の水女子大学, not numerically evaluable); OCHA-2027-REC-HUM (お茶の水女子大学, not numerically evaluable); OCHA-2027-REC-SOC (お茶の水女子大学, not numerically evaluable) |
| 7 | 口頭試問あり<br><code>./scripts/search --oral-exam Yes --limit 3</code> | 1577 | — | 258 | 989 | kokkoritsu=756, shidai=821 | 127 | OCHA-2027-AO-HENV (お茶の水女子大学, not numerically evaluable); OCHA-2027-REC-CULTINFO (お茶の水女子大学, not numerically evaluable); OCHA-2027-REC-HUM (お茶の水女子大学, not numerically evaluable) |
| 8 | プレゼンあり<br><code>./scripts/search --presentation Yes --limit 3</code> | 601 | — | 73 | 449 | kokkoritsu=349, shidai=252 | 112 | OCHA-2027-AO-PHYS (お茶の水女子大学, not numerically evaluable); OCHA-2027-AO-BIO (お茶の水女子大学, not numerically evaluable); OCHA-2027-AO-NUTRI (お茶の水女子大学, not numerically evaluable) |
| 9 | 面接＋小論文<br><code>./scripts/search --interview Yes --essay Yes --limit 3</code> | 1734 | — | 266 | 831 | kokkoritsu=1020, shidai=714 | 178 | OCHA-2027-REC-CULTINFO (お茶の水女子大学, not numerically evaluable); OCHA-2027-REC-HUM (お茶の水女子大学, not numerically evaluable); OCHA-2027-REC-SOC (お茶の水女子大学, not numerically evaluable) |
| 10 | GPA 3.5 strict-safe<br><code>./scripts/search --gpa 3.5 --limit 3</code> | 490 | 490 | 0 | 0 | kokkoritsu=251, shidai=239 | 59 | IOT-2027-REC-PUB1-CON (ものつくり大学, safe match); IOT-2027-REC-PUB2-CON (ものつくり大学, safe match); IOT-2027-REC-PUB3-CON (ものつくり大学, safe match) |
| 11 | GPA 3.8 strict-safe<br><code>./scripts/search --gpa 3.8 --limit 3</code> | 743 | 743 | 0 | 0 | kokkoritsu=433, shidai=310 | 103 | IOT-2027-REC-PUB1-CON (ものつくり大学, safe match); IOT-2027-REC-PUB2-CON (ものつくり大学, safe match); IOT-2027-REC-PUB3-CON (ものつくり大学, safe match) |
| 12 | GPA 4.0 strict-safe<br><code>./scripts/search --gpa 4.0 --limit 3</code> | 1124 | 1124 | 0 | 0 | kokkoritsu=764, shidai=360 | 136 | IOT-2027-REC-PUB1-CON (ものつくり大学, safe match); IOT-2027-REC-PUB2-CON (ものつくり大学, safe match); IOT-2027-REC-PUB3-CON (ものつくり大学, safe match) |
| 13 | 国公立＋研究実績要件あり<br><code>./scripts/search --institution-type '国立' '公立' --research-requirement-required Yes --limit 3</code> | 138 | — | 7 | 126 | kokkoritsu=138 | 31 | OCHA-2027-AO-NUTRI (お茶の水女子大学, not numerically evaluable); MIE-2027-AO-MED (三重大学, safe numeric rule (GPA not supplied)); MIE-2027-REC-ENG-FEMALE (三重大学, conditional/review required) |
| 14 | 私立＋共通テスト不要＋併願可<br><code>./scripts/search --institution-type '私立' --common-test-required No --exclusive '併願可' --limit 3</code> | 765 | — | 123 | 552 | shidai=765 | 41 | IOT-2027-REC-PUB1-CON (ものつくり大学, safe numeric rule (GPA not supplied)); IOT-2027-REC-PUB2-CON (ものつくり大学, safe numeric rule (GPA not supplied)); IOT-2027-REC-PUB3-CON (ものつくり大学, safe numeric rule (GPA not supplied)) |
| 15 | 東京/神奈川＋工学/情報＋GPA 4.0<br><code>./scripts/search --prefecture '東京都' '神奈川県' --academic-field '工学' '情報' --gpa 4.0 --limit 3</code> | 11 | 11 | 0 | 0 | shidai=11 | 5 | KOGEI-2027-ALUMNI-INFO (東京工芸大学, safe match); KOGEI-2027-REC-PUB-INFO (東京工芸大学, safe match); TOYO-2027-REC-INFO-SYSTEM (東洋大学, safe match) |
| 16 | GPA 3.8 review mode<br><code>./scripts/search --gpa 3.8 --gpa-mode review --limit 3</code> | 1450 | 743 | 707 | 0 | kokkoritsu=684, shidai=766 | 152 | IOT-2027-REC-PUB1-CON (ものつくり大学, safe match); IOT-2027-REC-PUB2-CON (ものつくり大学, safe match); IOT-2027-REC-PUB3-CON (ものつくり大学, safe match) |
| 17 | GPA 3.8 all mode<br><code>./scripts/search --gpa 3.8 --gpa-mode all --limit 3</code> | 5921 | 743 | 707 | 4015 | kokkoritsu=3668, shidai=2253 | 249 | OCHA-2027-AO-HENV (お茶の水女子大学, not numerically evaluable); OCHA-2027-REC-CULTINFO (お茶の水女子大学, not numerically evaluable); OCHA-2027-AO-CULTINFO (お茶の水女子大学, not numerically evaluable) |
| 18 | 面接＋筆記試験＋共通テスト不要<br><code>./scripts/search --interview Yes --written-exam Yes --common-test-required No --limit 3</code> | 1098 | — | 202 | 672 | kokkoritsu=550, shidai=548 | 114 | MIE-2027-AO-HUM-LAW (三重大学, not numerically evaluable); MIE-2027-AO-ENG-EE (三重大学, safe numeric rule (GPA not supplied)); MCN-2027-REC-GENERAL (三重県立看護大学, safe numeric rule (GPA not supplied)) |
| 19 | 東京＋工学group<br><code>./scripts/search --prefecture '東京都' --academic-field-group engineering --limit 3</code> | 344 | — | 127 | 191 | kokkoritsu=76, shidai=268 | 29 | OCHA-2027-AO-HENV (お茶の水女子大学, not numerically evaluable); SOPHIA-2027-KOBO-04 (上智大学, conditional/review required); SOPHIA-2027-KOBO-03 (上智大学, conditional/review required) |
| 20 | 東京＋情報group<br><code>./scripts/search --prefecture '東京都' --academic-field-group information --limit 3</code> | 162 | — | 59 | 93 | kokkoritsu=33, shidai=129 | 25 | OCHA-2027-REC-CULTINFO (お茶の水女子大学, not numerically evaluable); OCHA-2027-AO-CULTINFO (お茶の水女子大学, not numerically evaluable); OCHA-2027-AO-INFO (お茶の水女子大学, not numerically evaluable) |
| 21 | 東京/神奈川＋工学OR情報group＋GPA 3.8<br><code>./scripts/search --prefecture '東京都' '神奈川県' --academic-field-group engineering information --gpa 3.8 --limit 3</code> | 75 | 75 | 0 | 0 | shidai=75 | 11 | CHUO-2027-SDR-01 (中央大学, safe match); SOKA-2027-BASIC-HEIGAN-GREEN (創価大学, safe match); SOKA-2027-BASIC-HEIGAN-ISE (創価大学, safe match) |
| 22 | 医学group<br><code>./scripts/search --academic-field-group medicine --limit 3</code> | 154 | — | 14 | 95 | kokkoritsu=114, shidai=40 | 59 | MIE-2027-REC-MED-GEN (三重大学, not numerically evaluable); MIE-2027-REC-MED-REGA (三重大学, not numerically evaluable); MIE-2027-REC-MED-REGB (三重大学, not numerically evaluable) |
| 23 | 医歯薬group<br><code>./scripts/search --academic-field-group medicine dentistry pharmacy --limit 3</code> | 341 | — | 24 | 258 | kokkoritsu=173, shidai=168 | 80 | MIE-2027-REC-MED-GEN (三重大学, not numerically evaluable); MIE-2027-REC-MED-REGA (三重大学, not numerically evaluable); MIE-2027-REC-MED-REGB (三重大学, not numerically evaluable) |
| 24 | 農学OR生命科学group<br><code>./scripts/search --academic-field-group agriculture_fisheries life_sciences --limit 3</code> | 780 | — | 114 | 507 | kokkoritsu=377, shidai=403 | 104 | OCHA-2027-AO-NUTRI (お茶の水女子大学, not numerically evaluable); MIE-2027-REC-BIO-I-MAR (三重大学, safe numeric rule (GPA not supplied)); MIE-2027-REC-BIO-II-MAR (三重大学, safe numeric rule (GPA not supplied)) |
| 25 | 要確認academic field<br><code>./scripts/search --academic-field-mapping-status review_required --limit 3</code> | 19 | — | 1 | 14 | kokkoritsu=8, shidai=11 | 7 | CIS-2027-PILOT-Ⅰ期 (千葉科学大学, not numerically evaluable); CIS-2027-PILOT-Ⅱ期 (千葉科学大学, not numerically evaluable); CIS-2027-PILOT-Ⅲ期 (千葉科学大学, not numerically evaluable) |

## Search friction observed

- Broad academic-field group search is derived from the frozen exact-value crosswalk. Raw `academic_field` remains visible and separately searchable; review/unmapped rows require the mapping-status filter.
- `application_start` and `application_end` remain lossless raw text; the intentionally empty normalized-date layer means chronological range filtering is not available in v0.1.
- `capacity` is raw text rather than a normalized integer, so capacity range searches are not safe.
- `research_activity_level_status` includes `required`, `relevant`, `none`, `unknown`, `unmapped`, and SQL NULL. A broad “research related” search must state explicitly whether it means `required`, `relevant`, or both.
- `common_test_required` and `selection_common_test` are separate concepts and must remain separate filters; `common_test_required` also contains `Conditional` in the current snapshot.
- GPA conditional rules remain review-only. The CLI can expose them with `--gpa-mode review` or `all`, but never evaluates them automatically.
- v0.1 uses exact categorical matching and does not provide vocabulary discovery, partial university-name matching, or NULL-specific filter switches.

## Scope boundary

No SQLite, canonical, release, or unified input was modified. This QA did not create a Site, JSON search index, AI natural-language search, or conditional-GPA evaluator.
