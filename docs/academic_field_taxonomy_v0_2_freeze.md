# Academic-field search taxonomy v0.2 freeze

## Status and purpose

This document freezes taxonomy version `0.2` and exact mapping contract
version `0.2` for future two-level academic-field search. It is a derived
search classification and never replaces the canonical `academic_field` text.

The freeze adds no SQLite, Site-data, frontend, CLI, canonical, unified, or
release change. Taxonomy v0.1 and its current 19-group semantics remain
unchanged for backward compatibility.

## Inputs

| Authority label | Repository path | Rows | SHA-256 |
|---|---|---:|---|
| `kokkoritsu_early_admissions_2027_master_freeze_20260920_v1.csv` | `data/canonical/kokkoritsu/master.csv` | 3,668 | `61b50442f6fa9dad6a9483b702d5d463f37c0b338c6c3154a31a33e8cb0dd2ff` |
| `shidai_early_admissions_2027_master_v1_04.csv` | `data/canonical/shidai/master.csv` | 2,253 | `bb40f2db7687f28475ac01b8118daf4565ef80de63f11dfda8e1ac322cd3294d` |

Total admissions: 5,921; NULL/empty `academic_field`: 0; distinct raw values: 448; exact context tuples: 2,667.

## Broad taxonomy (30 groups)

| Section | Order | Code | Japanese label |
|---|---:|---|---|
| 人文・社会 | 1 | `humanities_culture_history` | 文学・文化・歴史・哲学 |
| 人文・社会 | 2 | `languages` | 外国語・言語 |
| 人文・社会 | 3 | `psychology` | 心理 |
| 人文・社会 | 4 | `law_politics_policy` | 法学・政治・公共政策 |
| 人文・社会 | 5 | `economics` | 経済 |
| 人文・社会 | 6 | `business_commerce` | 経営・商 |
| 人文・社会 | 7 | `sociology_community` | 社会学・地域社会 |
| 人文・社会 | 8 | `media_communication` | メディア・コミュニケーション |
| 人文・社会 | 9 | `international_regional` | 国際・地域研究 |
| 人文・社会 | 10 | `education_childcare` | 教育・保育 |
| 人文・社会 | 11 | `humanities_social_general` | 人文・社会（総合） |
| 理工・情報 | 1 | `natural_sciences` | 理学 |
| 理工・情報 | 2 | `engineering` | 工学 |
| 理工・情報 | 3 | `architecture_urban` | 建築・都市 |
| 理工・情報 | 4 | `information` | 情報・データサイエンス |
| 理工・情報 | 5 | `environment` | 環境 |
| 生命・農・医療 | 1 | `agriculture_fisheries` | 農学・水産 |
| 生命・農・医療 | 2 | `life_sciences` | 生命科学 |
| 生命・農・医療 | 3 | `food_nutrition` | 食品・栄養 |
| 生命・農・医療 | 4 | `medicine` | 医学 |
| 生命・農・医療 | 5 | `dentistry` | 歯学 |
| 生命・農・医療 | 6 | `pharmacy` | 薬学 |
| 生命・農・医療 | 7 | `nursing_health` | 看護・保健・医療 |
| 生命・農・医療 | 8 | `welfare` | 福祉 |
| 生命・農・医療 | 9 | `veterinary` | 獣医・動物 |
| 芸術・生活・その他 | 1 | `arts_design` | 芸術・デザイン |
| 芸術・生活・その他 | 2 | `home_lifestyle` | 生活・家政 |
| 芸術・生活・その他 | 3 | `sports` | スポーツ |
| 芸術・生活・その他 | 4 | `tourism_hospitality` | 観光・ホスピタリティ |
| 芸術・生活・その他 | 5 | `interdisciplinary` | 総合・学際 |

## Subcategory taxonomy (89 subcategories)

### 文学・文化・歴史・哲学 (`humanities_culture_history`)

`literature` (文学, primary), `history_folklore` (歴史・民俗, primary), `philosophy_thought` (哲学・思想, primary), `culture` (文化, primary), `religion` (宗教, hidden)

### 外国語・言語 (`languages`)

`foreign_languages` (外国語・語学, primary), `english` (英語, primary), `japanese_language` (日本語, primary), `linguistics` (言語学, hidden)

### 心理 (`psychology`)

`psychology_general` (心理学, primary), `clinical_psychology` (臨床心理, primary), `cognitive_behavioral` (認知・行動, secondary)

### 法学・政治・公共政策 (`law_politics_policy`)

`law` (法学, primary), `politics` (政治, primary), `public_policy_administration` (公共政策・行政, primary)

### 経済 (`economics`)

`economics_general` (経済学, primary), `international_economics` (国際経済, primary), `regional_public_economics` (地域・公共経済, hidden), `economics_data` (経済・データ分析, secondary)

### 経営・商 (`business_commerce`)

`management` (経営, primary), `commerce` (商学, primary), `accounting` (会計, hidden), `marketing` (マーケティング, hidden)

### 社会学・地域社会 (`sociology_community`)

`sociology` (社会学, primary), `community_regional_society` (地域社会・コミュニティ, primary)

### メディア・コミュニケーション (`media_communication`)

`media` (メディア・映像, primary), `communication` (コミュニケーション, primary), `journalism` (ジャーナリズム, hidden)

### 国際・地域研究 (`international_regional`)

`international_studies` (国際関係・国際研究, primary), `regional_studies` (地域研究, primary), `global_studies` (グローバル研究, primary)

### 教育・保育 (`education_childcare`)

`teacher_education` (教員養成, primary), `childcare_early_childhood` (保育・幼児教育, primary), `education_support` (教育支援, primary), `science_math_education` (理数教育, secondary)

### 理学 (`natural_sciences`)

`mathematics_statistics` (数学・数理・統計, primary), `physics` (物理, primary), `chemistry` (化学, primary), `biology` (生物, primary), `earth_space_science` (地球・宇宙, primary)

### 工学 (`engineering`)

`mechanical` (機械, primary), `electrical_electronic` (電気・電子, primary), `materials` (材料・物質, primary), `chemical_engineering` (化学工学・応用化学, primary), `civil_infrastructure` (土木・社会基盤, primary), `robotics_control` (ロボティクス・制御, primary), `aerospace` (航空・宇宙, primary), `nuclear_energy` (原子力・エネルギー, secondary), `biomedical_engineering` (医工学, secondary)

### 建築・都市 (`architecture_urban`)

`architecture` (建築, primary), `urban_planning` (都市・まちづくり, primary), `architectural_design` (建築デザイン, primary)

### 情報・データサイエンス (`information`)

`computer_science` (情報科学・コンピュータ, primary), `ai_machine_learning` (AI・機械学習, primary), `data_science_statistics` (データサイエンス・統計, primary), `software_systems` (情報システム・ソフトウェア, primary), `networks_communications` (通信・ネットワーク, secondary), `media_information` (メディア情報, secondary), `iot_digital` (IoT・デジタル, secondary)

### 環境 (`environment`)

`environmental_science` (環境科学, primary), `ecology_forestry` (生態・森林, primary), `environmental_engineering` (環境工学, primary), `sustainability` (サステナビリティ, primary)

### 農学・水産 (`agriculture_fisheries`)

`agriculture` (農学, primary), `fisheries_marine` (水産・海洋, primary), `forestry_resources` (森林・資源, primary), `agricultural_economics_business` (農業経済・アグリビジネス, primary)

### 生命科学 (`life_sciences`)

`biology_biotech` (生物・バイオ, primary), `biotechnology` (生命工学, primary), `microbiology_fermentation` (微生物・発酵, secondary), `medical_science` (医科学, secondary)

### 食品・栄養 (`food_nutrition`)

`nutrition` (栄養, primary), `food_science` (食品科学, primary), `fermentation_brewing` (発酵・醸造, secondary)

### 薬学 (`pharmacy`)

`pharmacy_six_year` (薬学6年制, primary), `pharmaceutical_science_drug_discovery` (薬科学・創薬, primary)

### 看護・保健・医療 (`nursing_health`)

`nursing` (看護, primary), `physical_therapy` (理学療法, primary), `occupational_therapy` (作業療法, primary), `speech_hearing` (言語聴覚, primary), `clinical_laboratory` (臨床検査, primary), `radiological_technology` (診療放射線, primary), `clinical_engineering` (臨床工学, primary), `emergency_medical` (救急救命, secondary)

### 獣医・動物 (`veterinary`)

`veterinary_medicine` (獣医, primary), `animal_science` (動物科学, primary)

### 芸術・デザイン (`arts_design`)

`fine_arts_crafts` (美術・工芸, primary), `music` (音楽, primary), `design` (デザイン, primary)

## Search Boolean semantics

- No Broad selection: no academic-field predicate.
- Broad only: the whole Broad membership is selected.
- Broad plus subcategories: `Broad AND (selected subcategory OR ...)`.
- Multiple Broad branches are ORed; a subcategory constrains only its own parent branch.

For example, `(natural_sciences AND (mathematics_statistics OR physics))`
selects the chosen science branches. Adding an engineering Broad branch
without subcategories yields `(...science branch...) OR engineering`.

## Mapping hierarchy and merge semantics

1. Raw exact crosswalk supplies safe Broad and subcategory memberships.
2. Exact program-context crosswalk uses the tuple `(source_dataset, university, faculty_school, department, academic_field)`.
3. `additive` context rows union reviewed memberships with safe raw memberships.
4. `authoritative` context rows replace an unresolved raw mapping only for that exact tuple.
5. Empty `faculty_school` or `department` is serialized as an empty CSV cell and must match exactly.
6. No trim, substring, regex, fuzzy matching, AI inference, or record-neighbor fallback is permitted.

`selection_name` and `record_id` are not mapping keys in v0.2. The current
review found no selection-level academic-field divergence requiring them.

## Review policy and coverage

Broad coverage is 5,910/5,921 (99.81%). Subcategory coverage is 5,027/5,921 (84.90%).

Broad mapped with no safe subcategory: 883; Broad review-required: 11; Subcategory review-required: 11; unmapped: 0.

Coverage is not a correctness target. Broad-only mapping is valid, and
unsafe subcategory detail remains absent.

## Ambiguous values

- `人間科学`: both current exact tuples remain `review_required`; the labels
  do not distinguish humanities, social science, psychology, education, or health safely.
- `国際`: current contexts safely support `international_regional`; exact
  context adds `regional_studies` or language/communication only when explicit.
- `地域デザイン`: raw remains `review_required`; 宇都宮大学コミュニティデザイン
  maps to community/regional society, while 金沢大学観光デザイン maps to tourism.
- `航空・パイロット`: remains `review_required`; it is not aerospace engineering.

## Multi-membership

A program may have multiple Broad groups and multiple subcategories. Examples
include `経済・経営・情報`, `外国語・国際`, `農学・生命`,
`理工・情報`, `デザイン・データ科学`, `スポーツ工学`, and `医歯薬`.
Counts overlap and must not be summed.

## v0.1 compatibility

The compatibility CSV is documentation/migration metadata only. It is not a
runtime expansion rule. Actual v0.2 memberships come only from the reviewed
v0.2 raw/context crosswalks.

| v0.1 group | v0.2 documentation targets |
|---|---|
| `natural_sciences` | `natural_sciences` |
| `engineering` | `engineering`, `architecture_urban` |
| `information` | `information` |
| `agriculture_fisheries` | `agriculture_fisheries` |
| `life_sciences` | `life_sciences`, `food_nutrition` |
| `medicine` | `medicine` |
| `dentistry` | `dentistry` |
| `pharmacy` | `pharmacy` |
| `nursing_health_welfare` | `nursing_health`, `welfare`, `food_nutrition` |
| `veterinary` | `veterinary` |
| `humanities` | `humanities_culture_history`, `languages`, `psychology`, `humanities_social_general`, `international_regional` |
| `social_sciences` | `law_politics_policy`, `economics`, `business_commerce`, `sociology_community`, `media_communication`, `international_regional`, `humanities_social_general` |
| `education` | `education_childcare` |
| `arts_design` | `arts_design` |
| `home_lifestyle` | `home_lifestyle`, `food_nutrition` |
| `sports` | `sports` |
| `environment` | `environment` |
| `tourism_hospitality` | `tourism_hospitality` |
| `interdisciplinary` | `interdisciplinary` |

## Future update and fail-closed policy

- New raw value: `unmapped` plus warning with frequency and representative record IDs.
- Known raw requiring an authoritative context but new tuple: `review_required`/`unmapped` warning.
- Never copy a nearby program's mapping or derive one from lexical similarity.
- Update through a new reviewed, versioned freeze; do not mutate v0.1 or v0.2 in place.

## Frozen artifacts and SHA-256

| Artifact | SHA-256 |
|---|---|
| `schema/academic_field/v0_2/academic_field_broad_taxonomy_v0_2.csv` | `ba33e98fa58196a3b530b26ce47d036073bdbf929a6fd16636e2ff58afe72ebd` |
| `schema/academic_field/v0_2/academic_field_context_crosswalk_v0_2.csv` | `d6a80cc20c50e225f36eb96c0f51e8df367ffe3b2205bc1fbe5b83d5315eabf1` |
| `schema/academic_field/v0_2/academic_field_raw_crosswalk_v0_2.csv` | `bf8213c7fbe09877ed0ffd4701e985e3aad724e0cc519f6e1ba18ed53b8b83aa` |
| `schema/academic_field/v0_2/academic_field_subcategory_taxonomy_v0_2.csv` | `9813972ec7698cd923fbbfb9bbee16bff7af12b371f23f5e733f6d391b92576e` |
| `schema/academic_field/v0_2/academic_field_v0_1_to_v0_2_crosswalk.csv` | `55d3cbeebb0af7d6bcab6bb5b975616413ff8f5591cf3cab03089559913f92d7` |
| `validation/reports/academic_field_taxonomy_v0_2_audit.md` | `a486800c554bdb0cb4e1568f3c6faba361bfb752014fb945fe361f8c665f2900` |

The freeze document's own hash is intentionally omitted because embedding it
would be self-referential. Its final SHA-256 is reported by the validation run.

## Integrity and deterministic rebuild

Validation enforces code uniqueness, valid parents, display-order uniqueness,
no duplicate mapping rows, valid references, exact raw/context preservation,
contiguous membership order, no production inference rules, and unchanged inputs.
Two independent canonical serialization runs must be byte-identical before freeze.

## Remaining human decisions before Site implementation

- Confirm whether zero-count hidden subcategories should remain hidden in the first UI release.
- Decide how review-required admissions are exposed without implying a classification.
- Confirm URL parameter names and backward-compatible coexistence with v0.1.
- Review checkbox density and progressive disclosure with actual user testing.
- Decide whether broad-only records should show a neutral '細分類なし' presentation.
