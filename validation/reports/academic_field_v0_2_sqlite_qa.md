# Academic-field v0.2 SQLite QA

- Database: `data/derived/sqlite/early_admissions_2027.sqlite`
- Database SHA-256: `a83055bfab2d9e32b7078f3ee12ea0673392abdc06c32c14b8900e30ec67c624`
- Mapping/taxonomy version: `0.2` / `0.2`
- Validation: `passed`
- Independent frozen-input membership reconciliation: `passed`
- Branch logical-key rows: 1796
- Branch logical-key SHA-256: `9bc31b1aae6fccb0eff51cf21f0696187884da1e6907666b36b2faf71e8864b5`
- Branch logical-key artifact: `validation/reports/academic_field_v0_2_branch_logical_keys.tsv`

## Build counts

- Broad taxonomy: 30
- Subcategory taxonomy: 89
- Parent rows: 5921
- Broad membership rows: 8275
- Subcategory membership rows: 6880
- Raw crosswalk: 448 keys / 796 rows
- Context crosswalk: 718 tuples / 824 rows
- Raw-only admissions: 4443
- Context consulted: 1478
- Context effective: 1467
- Raw mismatch: 0

## Mapping status counts

- Broad: `{"multi":2039,"not_applicable":0,"review_required":11,"single":3871,"unmapped":0}`
- Subcategory: `{"multi":1565,"none":883,"not_applicable":0,"review_required":11,"single":3462,"unmapped":0}`
- Context effects: `{"additive":1464,"authoritative":3,"none":4454}`

## Broad membership counts

| Code | Label | Admissions |
|---|---|---:|
| `humanities_culture_history` | 文学・文化・歴史・哲学 | 137 |
| `languages` | 外国語・言語 | 128 |
| `psychology` | 心理 | 25 |
| `law_politics_policy` | 法学・政治・公共政策 | 81 |
| `economics` | 経済 | 150 |
| `business_commerce` | 経営・商 | 169 |
| `sociology_community` | 社会学・地域社会 | 121 |
| `media_communication` | メディア・コミュニケーション | 59 |
| `international_regional` | 国際・地域研究 | 160 |
| `education_childcare` | 教育・保育 | 787 |
| `humanities_social_general` | 人文・社会（総合） | 212 |
| `natural_sciences` | 理学 | 702 |
| `engineering` | 工学 | 1642 |
| `architecture_urban` | 建築・都市 | 172 |
| `information` | 情報・データサイエンス | 865 |
| `environment` | 環境 | 244 |
| `agriculture_fisheries` | 農学・水産 | 450 |
| `life_sciences` | 生命科学 | 596 |
| `food_nutrition` | 食品・栄養 | 139 |
| `medicine` | 医学 | 151 |
| `dentistry` | 歯学 | 36 |
| `pharmacy` | 薬学 | 173 |
| `nursing_health` | 看護・保健・医療 | 649 |
| `welfare` | 福祉 | 61 |
| `veterinary` | 獣医・動物 | 71 |
| `arts_design` | 芸術・デザイン | 179 |
| `home_lifestyle` | 生活・家政 | 7 |
| `sports` | スポーツ | 45 |
| `tourism_hospitality` | 観光・ホスピタリティ | 18 |
| `interdisciplinary` | 総合・学際 | 46 |

## Subcategory membership counts

| Code | Label | Admissions |
|---|---|---:|
| `literature` | 文学 | 14 |
| `history_folklore` | 歴史・民俗 | 7 |
| `philosophy_thought` | 哲学・思想 | 1 |
| `culture` | 文化 | 92 |
| `religion` | 宗教 | 0 |
| `foreign_languages` | 外国語・語学 | 117 |
| `english` | 英語 | 1 |
| `japanese_language` | 日本語 | 10 |
| `linguistics` | 言語学 | 0 |
| `psychology_general` | 心理学 | 20 |
| `clinical_psychology` | 臨床心理 | 2 |
| `cognitive_behavioral` | 認知・行動 | 3 |
| `law` | 法学 | 42 |
| `politics` | 政治 | 5 |
| `public_policy_administration` | 公共政策・行政 | 41 |
| `economics_general` | 経済学 | 147 |
| `international_economics` | 国際経済 | 2 |
| `regional_public_economics` | 地域・公共経済 | 0 |
| `economics_data` | 経済・データ分析 | 3 |
| `management` | 経営 | 161 |
| `commerce` | 商学 | 14 |
| `accounting` | 会計 | 0 |
| `marketing` | マーケティング | 0 |
| `sociology` | 社会学 | 27 |
| `community_regional_society` | 地域社会・コミュニティ | 89 |
| `media` | メディア・映像 | 58 |
| `communication` | コミュニケーション | 1 |
| `journalism` | ジャーナリズム | 0 |
| `international_studies` | 国際関係・国際研究 | 151 |
| `regional_studies` | 地域研究 | 8 |
| `global_studies` | グローバル研究 | 6 |
| `teacher_education` | 教員養成 | 680 |
| `childcare_early_childhood` | 保育・幼児教育 | 21 |
| `education_support` | 教育支援 | 4 |
| `science_math_education` | 理数教育 | 15 |
| `mathematics_statistics` | 数学・数理・統計 | 107 |
| `physics` | 物理 | 87 |
| `chemistry` | 化学 | 231 |
| `biology` | 生物 | 152 |
| `earth_space_science` | 地球・宇宙 | 58 |
| `mechanical` | 機械 | 332 |
| `electrical_electronic` | 電気・電子 | 282 |
| `materials` | 材料・物質 | 105 |
| `chemical_engineering` | 化学工学・応用化学 | 134 |
| `civil_infrastructure` | 土木・社会基盤 | 81 |
| `robotics_control` | ロボティクス・制御 | 49 |
| `aerospace` | 航空・宇宙 | 22 |
| `nuclear_energy` | 原子力・エネルギー | 42 |
| `biomedical_engineering` | 医工学 | 51 |
| `architecture` | 建築 | 148 |
| `urban_planning` | 都市・まちづくり | 75 |
| `architectural_design` | 建築デザイン | 7 |
| `computer_science` | 情報科学・コンピュータ | 408 |
| `ai_machine_learning` | AI・機械学習 | 21 |
| `data_science_statistics` | データサイエンス・統計 | 97 |
| `software_systems` | 情報システム・ソフトウェア | 97 |
| `networks_communications` | 通信・ネットワーク | 62 |
| `media_information` | メディア情報 | 64 |
| `iot_digital` | IoT・デジタル | 15 |
| `environmental_science` | 環境科学 | 85 |
| `ecology_forestry` | 生態・森林 | 20 |
| `environmental_engineering` | 環境工学 | 22 |
| `sustainability` | サステナビリティ | 2 |
| `agriculture` | 農学 | 400 |
| `fisheries_marine` | 水産・海洋 | 84 |
| `forestry_resources` | 森林・資源 | 23 |
| `agricultural_economics_business` | 農業経済・アグリビジネス | 14 |
| `biology_biotech` | 生物・バイオ | 541 |
| `biotechnology` | 生命工学 | 52 |
| `microbiology_fermentation` | 微生物・発酵 | 8 |
| `medical_science` | 医科学 | 18 |
| `nutrition` | 栄養 | 70 |
| `food_science` | 食品科学 | 77 |
| `fermentation_brewing` | 発酵・醸造 | 4 |
| `pharmacy_six_year` | 薬学6年制 | 111 |
| `pharmaceutical_science_drug_discovery` | 薬科学・創薬 | 61 |
| `nursing` | 看護 | 279 |
| `physical_therapy` | 理学療法 | 67 |
| `occupational_therapy` | 作業療法 | 57 |
| `speech_hearing` | 言語聴覚 | 16 |
| `clinical_laboratory` | 臨床検査 | 31 |
| `radiological_technology` | 診療放射線 | 34 |
| `clinical_engineering` | 臨床工学 | 23 |
| `emergency_medical` | 救急救命 | 15 |
| `veterinary_medicine` | 獣医 | 56 |
| `animal_science` | 動物科学 | 20 |
| `fine_arts_crafts` | 美術・工芸 | 63 |
| `music` | 音楽 | 27 |
| `design` | デザイン | 131 |

## Representative broad queries

| Code | Expected | Actual |
|---|---:|---:|
| `law_politics_policy` | 81 | 81 |
| `economics` | 150 | 150 |
| `business_commerce` | 169 | 169 |
| `psychology` | 25 | 25 |
| `languages` | 128 | 128 |
| `natural_sciences` | 702 | 702 |
| `engineering` | 1642 | 1642 |
| `information` | 865 | 865 |

## Representative subcategory queries

| Broad | Subcategory | Expected | Actual |
|---|---|---:|---:|
| `law_politics_policy` | `law` | 42 | 42 |
| `economics` | `economics_general` | 147 | 147 |
| `business_commerce` | `management` | 161 | 161 |
| `psychology` | `psychology_general` | 20 | 20 |
| `natural_sciences` | `mathematics_statistics` | 107 | 107 |
| `natural_sciences` | `physics` | 87 | 87 |
| `engineering` | `mechanical` | 332 | 332 |
| `nursing_health` | `nursing` | 279 | 279 |

## Branch semantics

The executed predicate was `(natural_sciences AND (mathematics_statistics OR physics)) OR engineering`. It returned 1796 logical keys. The complete sorted key set is saved in the companion TSV and its SHA-256 is recorded above.

## Combined existing filters

| Query | Rows |
|---|---:|
| 東京都 AND 法学・政治・公共政策 | 9 |
| 東京都 AND 工学 AND 評定条件あり | 156 |
| 東京都/神奈川県 membership AND 情報 AND overall GPA 3.8 | 29 |

## Ambiguous and contained-token fixtures

| Raw | Broad status | Broad membership | Subcategory membership |
|---|---|---|---|
| 人間科学 | `review_required` | `none` | `none` |
| 航空・パイロット | `review_required` | `none` | `none` |
| 理学療法 | `single` | `nursing_health` | `physical_therapy` |
| 言語聴覚 | `single` | `nursing_health` | `speech_hearing` |
| 獣医学 | `single` | `veterinary` | `veterinary_medicine` |

Exact context fixtures for 地域デザイン and 国際, plus substring negative fixtures, are covered by automated tests. No runtime trim, substring, fuzzy, or inferred classification is used.

## Query plans

- broad: `SCAN a USING INDEX idx_admissions_selection_category / SEARCH g USING INTEGER PRIMARY KEY (rowid=?) / SEARCH af USING INTEGER PRIMARY KEY (rowid=?) / SEARCH er USING INTEGER PRIMARY KEY (rowid=?) / SEARCH gr USING INTEGER PRIMARY KEY (rowid=?) / SEARCH b2 EXISTS USING COVERING INDEX sqlite_autoindex_admission_search_academic_field_broad_memberships_v2_1 (admission_rowid=? AND group_code=?) / CORRELATED SCALAR SUBQUERY 2 / CO-ROUTINE ordered / SEARCH afg USING INDEX sqlite_autoindex_admission_search_academic_field_groups_2 (admission_rowid=?) / SCAN ordered / USE TEMP B-TREE FOR ORDER BY`
- subcategory: `SCAN a USING INDEX idx_admissions_university / SEARCH g USING INTEGER PRIMARY KEY (rowid=?) / SEARCH af USING INTEGER PRIMARY KEY (rowid=?) / SEARCH er USING INTEGER PRIMARY KEY (rowid=?) / SEARCH gr USING INTEGER PRIMARY KEY (rowid=?) / SEARCH b2 EXISTS USING COVERING INDEX sqlite_autoindex_admission_search_academic_field_broad_memberships_v2_1 (admission_rowid=? AND group_code=?) / SEARCH s2 EXISTS USING INDEX idx_academic_field_v2_subcategory_lookup (subcategory_code=? AND admission_rowid=?) / CORRELATED SCALAR SUBQUERY 2 / CO-ROUTINE ordered / SEARCH afg USING INDEX sqlite_autoindex_admission_search_academic_field_groups_2 (admission_rowid=?) / SCAN ordered / USE TEMP B-TREE FOR LAST 5 TERMS OF ORDER BY`
- multi_branch: `SCAN a USING INDEX idx_admissions_university / CORRELATED SCALAR SUBQUERY 3 / SEARCH b2 USING COVERING INDEX sqlite_autoindex_admission_search_academic_field_broad_memberships_v2_1 (admission_rowid=? AND group_code=?) / CORRELATED SCALAR SUBQUERY 4 / SEARCH s2 USING INDEX idx_academic_field_v2_subcategory_lookup (subcategory_code=? AND admission_rowid=?) / CORRELATED SCALAR SUBQUERY 5 / SEARCH b2 USING COVERING INDEX sqlite_autoindex_admission_search_academic_field_broad_memberships_v2_1 (admission_rowid=? AND group_code=?) / SEARCH g USING INTEGER PRIMARY KEY (rowid=?) / SEARCH af USING INTEGER PRIMARY KEY (rowid=?) / SEARCH er USING INTEGER PRIMARY KEY (rowid=?) / SEARCH gr USING INTEGER PRIMARY KEY (rowid=?) / CORRELATED SCALAR SUBQUERY 2 / CO-ROUTINE ordered / SEARCH afg USING INDEX sqlite_autoindex_admission_search_academic_field_groups_2 (admission_rowid=?) / SCAN ordered / USE TEMP B-TREE FOR LAST 5 TERMS OF ORDER BY`

## v0.1 coexistence and validation

- v0.1 mapping counts: `{"multi":1833,"not_applicable":0,"review_required":19,"single":4069,"unmapped":0}`
- v0.1 group rows: 7952
- v0.1 validation: `passed`
- Supplying v0.1 and v0.2 filters together uses AND semantics.
- v0.2 foreign hierarchy failures: 0
- v0.2 order failures: 0
- PRAGMA foreign_key_check rows: 0
- PRAGMA quick_check: `ok`

## Scope boundary

Site-data and frontend were not changed. This receipt validates the SQLite derived layer and the structured-search oracle only.
