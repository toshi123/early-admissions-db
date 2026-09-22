# Structured search CLI v0.1 representative QA

- Generated: `2026-09-22T12:51:38Z`
- SQLite: `data/derived/sqlite/early_admissions_2027.sqlite`
- SQLite SHA-256 before/after: `3f7cda8c9788f601c86991b7d0ccb19fc516638ef9c19d91447fd71d2ab0bbe7` / `3f7cda8c9788f601c86991b7d0ccb19fc516638ef9c19d91447fd71d2ab0bbe7`
- Queries: 25
- Access: URI `mode=ro&immutable=1` plus `PRAGMA query_only=ON`
- GPA meaning: `safe match` means `overall GPA condition safely matched`; it is not an application-eligibility determination.

## Results

| # | Query and command | Total | GPA safe match | Conditional/review | Not numerically evaluable | Sources | Universities | Representative results |
|---:|---|---:|---:|---:|---:|---|---:|---|
| 1 | 東京＋理系<br><code>./scripts/search --prefecture '東京都' --stem --limit 3</code> | 932 | — | 222 | 602 | kokkoritsu=209, shidai=723 | 48 | OCHA-2027-AO-HENV (お茶の水女子大学, not numerically evaluable); OCHA-2027-REC-CULTINFO (お茶の水女子大学, not numerically evaluable); OCHA-2027-RETURN-CULTINFO (お茶の水女子大学, not numerically evaluable) |
| 2 | 東京＋理系＋評定3.8<br><code>./scripts/search --prefecture '東京都' --stem --gpa 3.8 --limit 3</code> | 67 | 67 | 0 | 0 | kokkoritsu=2, shidai=65 | 12 | CHUO-2027-SDR-01 (中央大学, safe match); SOKA-2027-BASIC-HEIGAN-GREEN (創価大学, safe match); SOKA-2027-BASIC-HEIGAN-ISE (創価大学, safe match) |
| 3 | 東京＋理系＋評定3.8＋研究活動関連<br><code>./scripts/search --prefecture '東京都' --stem --gpa 3.8 --research-activity-level-status required relevant --limit 3</code> | 15 | 15 | 0 | 0 | shidai=15 | 3 | CHUO-2027-SDR-01 (中央大学, safe match); NODAI-2027-FAM-16 (東京農業大学, safe match); NODAI-2027-FAM-19 (東京農業大学, safe match) |
| 4 | 東京/神奈川＋併願可<br><code>./scripts/search --prefecture '東京都' '神奈川県' --exclusive '併願可' --limit 3</code> | 538 | — | 72 | 397 | kokkoritsu=4, shidai=534 | 30 | CHUO-2027-SDB-SPORTS-MGMT (中央大学, conditional/review required); CHUO-2027-SDB-DS-PRO (中央大学, conditional/review required); CHUO-2027-SDB-DS-WOMEN (中央大学, conditional/review required) |
| 5 | 学校推薦型＋推薦必要<br><code>./scripts/search --selection-category '学校推薦型選抜' --school-recommendation-required Yes --limit 3</code> | 2911 | — | 375 | 1634 | kokkoritsu=2354, shidai=557 | 222 | OCHA-2027-REC-CULTINFO (お茶の水女子大学, not numerically evaluable); OCHA-2027-REC-HUM (お茶の水女子大学, not numerically evaluable); OCHA-2027-REC-SOC (お茶の水女子大学, not numerically evaluable) |
| 6 | 共通テスト不要<br><code>./scripts/search --common-test-required No --limit 3</code> | 4934 | — | 702 | 3171 | kokkoritsu=2542, shidai=2392 | 233 | OCHA-2027-REC-CULTINFO (お茶の水女子大学, not numerically evaluable); OCHA-2027-RETURN-CULTINFO (お茶の水女子大学, not numerically evaluable); OCHA-2027-REC-HUM (お茶の水女子大学, not numerically evaluable) |
| 7 | 口頭試問あり<br><code>./scripts/search --oral-exam Yes --limit 3</code> | 1764 | — | 274 | 1151 | kokkoritsu=926, shidai=838 | 128 | OCHA-2027-AO-HENV (お茶の水女子大学, not numerically evaluable); OCHA-2027-REC-CULTINFO (お茶の水女子大学, not numerically evaluable); OCHA-2027-RETURN-CULTINFO (お茶の水女子大学, not numerically evaluable) |
| 8 | プレゼンあり<br><code>./scripts/search --presentation Yes --limit 3</code> | 641 | — | 74 | 485 | kokkoritsu=379, shidai=262 | 114 | OCHA-2027-AO-PHYS (お茶の水女子大学, not numerically evaluable); OCHA-2027-AO-BIO (お茶の水女子大学, not numerically evaluable); OCHA-2027-AO-NUTRI (お茶の水女子大学, not numerically evaluable) |
| 9 | 面接＋小論文<br><code>./scripts/search --interview Yes --essay Yes --limit 3</code> | 1875 | — | 270 | 954 | kokkoritsu=1126, shidai=749 | 184 | OCHA-2027-REC-CULTINFO (お茶の水女子大学, not numerically evaluable); OCHA-2027-RETURN-CULTINFO (お茶の水女子大学, not numerically evaluable); OCHA-2027-REC-HUM (お茶の水女子大学, not numerically evaluable) |
| 10 | GPA 3.5 strict-safe<br><code>./scripts/search --gpa 3.5 --limit 3</code> | 499 | 499 | 0 | 0 | kokkoritsu=255, shidai=244 | 63 | IOT-2027-REC-PUB1-CON (ものつくり大学, safe match); IOT-2027-REC-PUB2-CON (ものつくり大学, safe match); IOT-2027-REC-PUB3-CON (ものつくり大学, safe match) |
| 11 | GPA 3.8 strict-safe<br><code>./scripts/search --gpa 3.8 --limit 3</code> | 763 | 763 | 0 | 0 | kokkoritsu=437, shidai=326 | 107 | IOT-2027-REC-PUB1-CON (ものつくり大学, safe match); IOT-2027-REC-PUB2-CON (ものつくり大学, safe match); IOT-2027-REC-PUB3-CON (ものつくり大学, safe match) |
| 12 | GPA 4.0 strict-safe<br><code>./scripts/search --gpa 4.0 --limit 3</code> | 1175 | 1175 | 0 | 0 | kokkoritsu=778, shidai=397 | 142 | IOT-2027-REC-PUB1-CON (ものつくり大学, safe match); IOT-2027-REC-PUB2-CON (ものつくり大学, safe match); IOT-2027-REC-PUB3-CON (ものつくり大学, safe match) |
| 13 | 国公立＋研究実績要件あり<br><code>./scripts/search --institution-type '国立' '公立' --research-requirement-required Yes --limit 3</code> | 174 | — | 7 | 162 | kokkoritsu=174 | 33 | OCHA-2027-AO-NUTRI (お茶の水女子大学, not numerically evaluable); MIE-2027-AO-MED (三重大学, safe numeric rule (GPA not supplied)); MIE-2027-REC-ENG-FEMALE (三重大学, conditional/review required) |
| 14 | 私立＋共通テスト不要＋併願可<br><code>./scripts/search --institution-type '私立' --common-test-required No --exclusive '併願可' --limit 3</code> | 840 | — | 126 | 603 | shidai=840 | 42 | IOT-2027-REC-PUB1-CON (ものつくり大学, safe numeric rule (GPA not supplied)); IOT-2027-REC-PUB2-CON (ものつくり大学, safe numeric rule (GPA not supplied)); IOT-2027-REC-PUB3-CON (ものつくり大学, safe numeric rule (GPA not supplied)) |
| 15 | 東京/神奈川＋工学/情報＋GPA 4.0<br><code>./scripts/search --prefecture '東京都' '神奈川県' --academic-field '工学' '情報' --gpa 4.0 --limit 3</code> | 11 | 11 | 0 | 0 | shidai=11 | 5 | KOGEI-2027-ALUMNI-INFO (東京工芸大学, safe match); KOGEI-2027-REC-PUB-INFO (東京工芸大学, safe match); TOYO-2027-REC-INFO-SYSTEM (東洋大学, safe match) |
| 16 | GPA 3.8 review mode<br><code>./scripts/search --gpa 3.8 --gpa-mode review --limit 3</code> | 1510 | 763 | 747 | 0 | kokkoritsu=694, shidai=816 | 156 | IOT-2027-REC-PUB1-CON (ものつくり大学, safe match); IOT-2027-REC-PUB2-CON (ものつくり大学, safe match); IOT-2027-REC-PUB3-CON (ものつくり大学, safe match) |
| 17 | GPA 3.8 all mode<br><code>./scripts/search --gpa 3.8 --gpa-mode all --limit 3</code> | 6411 | 763 | 747 | 4406 | kokkoritsu=4011, shidai=2400 | 250 | OCHA-2027-AO-HENV (お茶の水女子大学, not numerically evaluable); OCHA-2027-REC-CULTINFO (お茶の水女子大学, not numerically evaluable); OCHA-2027-RETURN-CULTINFO (お茶の水女子大学, not numerically evaluable) |
| 18 | 面接＋筆記試験＋共通テスト不要<br><code>./scripts/search --interview Yes --written-exam Yes --common-test-required No --limit 3</code> | 1270 | — | 218 | 813 | kokkoritsu=658, shidai=612 | 126 | OCHA-2027-RETURN-INFO (お茶の水女子大学, not numerically evaluable); OCHA-2027-RETURN-BIO (お茶の水女子大学, not numerically evaluable); HIT-2027-FOREIGN-COM (一橋大学, not numerically evaluable) |
| 19 | 東京＋工学group<br><code>./scripts/search --prefecture '東京都' --academic-field-group engineering --limit 3</code> | 357 | — | 128 | 201 | kokkoritsu=89, shidai=268 | 29 | OCHA-2027-AO-HENV (お茶の水女子大学, not numerically evaluable); OCHA-2027-RETURN-CULTINFO (お茶の水女子大学, not numerically evaluable); SOPHIA-2027-KOBO-04 (上智大学, conditional/review required) |
| 20 | 東京＋情報group<br><code>./scripts/search --prefecture '東京都' --academic-field-group information --limit 3</code> | 169 | — | 60 | 97 | kokkoritsu=37, shidai=132 | 26 | OCHA-2027-REC-CULTINFO (お茶の水女子大学, not numerically evaluable); OCHA-2027-RETURN-CULTINFO (お茶の水女子大学, not numerically evaluable); OCHA-2027-AO-CULTINFO (お茶の水女子大学, not numerically evaluable) |
| 21 | 東京/神奈川＋工学OR情報group＋GPA 3.8<br><code>./scripts/search --prefecture '東京都' '神奈川県' --academic-field-group engineering information --gpa 3.8 --limit 3</code> | 75 | 75 | 0 | 0 | shidai=75 | 11 | CHUO-2027-SDR-01 (中央大学, safe match); SOKA-2027-BASIC-HEIGAN-GREEN (創価大学, safe match); SOKA-2027-BASIC-HEIGAN-ISE (創価大学, safe match) |
| 22 | 医学group<br><code>./scripts/search --academic-field-group medicine --limit 3</code> | 170 | — | 15 | 109 | kokkoritsu=130, shidai=40 | 62 | MIE-2027-REC-MED-GEN (三重大学, not numerically evaluable); MIE-2027-REC-MED-REGA (三重大学, not numerically evaluable); MIE-2027-REC-MED-REGB (三重大学, not numerically evaluable) |
| 23 | 医歯薬group<br><code>./scripts/search --academic-field-group medicine dentistry pharmacy --limit 3</code> | 370 | — | 25 | 285 | kokkoritsu=202, shidai=168 | 82 | MIE-2027-REC-MED-GEN (三重大学, not numerically evaluable); MIE-2027-REC-MED-REGA (三重大学, not numerically evaluable); MIE-2027-REC-MED-REGB (三重大学, not numerically evaluable) |
| 24 | 農学OR生命科学group<br><code>./scripts/search --academic-field-group agriculture_fisheries life_sciences --limit 3</code> | 794 | — | 114 | 520 | kokkoritsu=391, shidai=403 | 105 | OCHA-2027-AO-NUTRI (お茶の水女子大学, not numerically evaluable); MIE-2027-REC-BIO-I-MAR (三重大学, safe numeric rule (GPA not supplied)); MIE-2027-REC-BIO-II-MAR (三重大学, safe numeric rule (GPA not supplied)) |
| 25 | 要確認academic field<br><code>./scripts/search --academic-field-mapping-status review_required --limit 3</code> | 40 | — | 1 | 31 | kokkoritsu=22, shidai=18 | 14 | SOPHIA-2027-KOBO-FLA (上智大学, safe numeric rule (GPA not supplied)); SOPHIA-2027-KOBO-INTLAW (上智大学, safe numeric rule (GPA not supplied)); KYUSHU-2027-EDU-INTL (九州大学, not numerically evaluable) |

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
