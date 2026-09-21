# Academic-field taxonomy v0.2 full audit

## 1. Scope and authority

This report records the full 5,921-admission review used to freeze the
two-level academic-field search taxonomy v0.2. It creates no SQLite,
Site-data, frontend, canonical, unified, or release artifact.

The task-supplied authority labels correspond to the repository's read-only
canonical copies as follows:

| Authority label | Repository path | Rows | SHA-256 |
|---|---|---:|---|
| `kokkoritsu_early_admissions_2027_master_freeze_20260920_v1.csv` | `data/canonical/kokkoritsu/master.csv` | 3,668 | `61b50442f6fa9dad6a9483b702d5d463f37c0b338c6c3154a31a33e8cb0dd2ff` |
| `shidai_early_admissions_2027_master_v1_04.csv` | `data/canonical/shidai/master.csv` | 2,253 | `bb40f2db7687f28475ac01b8118daf4565ef80de63f11dfda8e1ac322cd3294d` |

The original authority filenames are not present as separate files in this
repository. The canonical copies match the requested row regressions and
the hashes recorded by the current unified build manifest.

## 2. Input inventory

| Measure | Count |
|---|---:|
| Kokkoritsu admissions | 3,668 |
| Shidai admissions | 2,253 |
| Total admissions | 5,921 |
| `academic_field` NULL/empty | 0 |
| Distinct raw values | 448 |
| Distinct exact program-context tuples | 2,667 |

## 3. Freeze size and coverage

| Measure | Count |
|---|---:|
| Broad groups | 30 |
| Subcategories | 89 |
| Raw crosswalk rows / keys | 796 / 448 |
| Context crosswalk rows / tuples | 824 / 718 |
| Broad-search coverage | 5,910 / 5,921 (99.81%) |
| Subcategory-search coverage | 5,027 / 5,921 (84.90%) |
| Broad mapped, no safe subcategory | 883 |
| Broad review-required admissions | 11 |
| Subcategory review-required admissions | 11 |
| Unmapped admissions | 0 |

Coverage is intentionally not forced to 100%. A broad-only classification is
valid when the source identifies a field such as `工学` but does not safely
identify a subcategory. Membership counts overlap and must not be summed.

## 4. Mapping usage and cardinality

| Measure | Admissions |
|---|---:|
| Raw-only exact mapping | 4,443 |
| Exact context tuple consulted | 1,478 |
| Exact context tuple added/resolved membership | 1,467 |
| Final single Broad membership | 3,871 |
| Final multi Broad membership | 2,039 |
| Final single subcategory membership | 3,462 |
| Final multi subcategory membership | 1,565 |

Raw crosswalk key statuses: `multi=284`, `review_required=3`, `single=161`. Context tuple statuses: `multi=96`, `review_required=3`, `single=619`.

## 5. Broad-group membership counts

| UI section | Broad group | Label | Admissions |
|---|---|---|---:|
| 人文・社会 | `humanities_culture_history` | 文学・文化・歴史・哲学 | 137 |
| 人文・社会 | `languages` | 外国語・言語 | 128 |
| 人文・社会 | `psychology` | 心理 | 25 |
| 人文・社会 | `law_politics_policy` | 法学・政治・公共政策 | 81 |
| 人文・社会 | `economics` | 経済 | 150 |
| 人文・社会 | `business_commerce` | 経営・商 | 169 |
| 人文・社会 | `sociology_community` | 社会学・地域社会 | 121 |
| 人文・社会 | `media_communication` | メディア・コミュニケーション | 59 |
| 人文・社会 | `international_regional` | 国際・地域研究 | 160 |
| 人文・社会 | `education_childcare` | 教育・保育 | 787 |
| 人文・社会 | `humanities_social_general` | 人文・社会（総合） | 212 |
| 理工・情報 | `natural_sciences` | 理学 | 702 |
| 理工・情報 | `engineering` | 工学 | 1,642 |
| 理工・情報 | `architecture_urban` | 建築・都市 | 172 |
| 理工・情報 | `information` | 情報・データサイエンス | 865 |
| 理工・情報 | `environment` | 環境 | 244 |
| 生命・農・医療 | `agriculture_fisheries` | 農学・水産 | 450 |
| 生命・農・医療 | `life_sciences` | 生命科学 | 596 |
| 生命・農・医療 | `food_nutrition` | 食品・栄養 | 139 |
| 生命・農・医療 | `medicine` | 医学 | 151 |
| 生命・農・医療 | `dentistry` | 歯学 | 36 |
| 生命・農・医療 | `pharmacy` | 薬学 | 173 |
| 生命・農・医療 | `nursing_health` | 看護・保健・医療 | 649 |
| 生命・農・医療 | `welfare` | 福祉 | 61 |
| 生命・農・医療 | `veterinary` | 獣医・動物 | 71 |
| 芸術・生活・その他 | `arts_design` | 芸術・デザイン | 179 |
| 芸術・生活・その他 | `home_lifestyle` | 生活・家政 | 7 |
| 芸術・生活・その他 | `sports` | スポーツ | 45 |
| 芸術・生活・その他 | `tourism_hospitality` | 観光・ホスピタリティ | 18 |
| 芸術・生活・その他 | `interdisciplinary` | 総合・学際 | 46 |

## 6. Subcategory membership and UI sizing

The `ui_status` field is presentation metadata, not search meaning.
Zero-count categories remain in the taxonomy as `hidden` candidates;
low-count but independently meaningful student intents may remain primary.

### 文学・文化・歴史・哲学 (`humanities_culture_history`)

Broad admissions: 137; subcategories: 5.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `literature` | 文学 | 14 | `primary` |
| `history_folklore` | 歴史・民俗 | 7 | `primary` |
| `philosophy_thought` | 哲学・思想 | 1 | `primary` |
| `culture` | 文化 | 92 | `primary` |
| `religion` | 宗教 | 0 | `hidden` |

### 外国語・言語 (`languages`)

Broad admissions: 128; subcategories: 4.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `foreign_languages` | 外国語・語学 | 117 | `primary` |
| `english` | 英語 | 1 | `primary` |
| `japanese_language` | 日本語 | 10 | `primary` |
| `linguistics` | 言語学 | 0 | `hidden` |

### 心理 (`psychology`)

Broad admissions: 25; subcategories: 3.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `psychology_general` | 心理学 | 20 | `primary` |
| `clinical_psychology` | 臨床心理 | 2 | `primary` |
| `cognitive_behavioral` | 認知・行動 | 3 | `secondary` |

### 法学・政治・公共政策 (`law_politics_policy`)

Broad admissions: 81; subcategories: 3.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `law` | 法学 | 42 | `primary` |
| `politics` | 政治 | 5 | `primary` |
| `public_policy_administration` | 公共政策・行政 | 41 | `primary` |

### 経済 (`economics`)

Broad admissions: 150; subcategories: 4.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `economics_general` | 経済学 | 147 | `primary` |
| `international_economics` | 国際経済 | 2 | `primary` |
| `regional_public_economics` | 地域・公共経済 | 0 | `hidden` |
| `economics_data` | 経済・データ分析 | 3 | `secondary` |

### 経営・商 (`business_commerce`)

Broad admissions: 169; subcategories: 4.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `management` | 経営 | 161 | `primary` |
| `commerce` | 商学 | 14 | `primary` |
| `accounting` | 会計 | 0 | `hidden` |
| `marketing` | マーケティング | 0 | `hidden` |

### 社会学・地域社会 (`sociology_community`)

Broad admissions: 121; subcategories: 2.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `sociology` | 社会学 | 27 | `primary` |
| `community_regional_society` | 地域社会・コミュニティ | 89 | `primary` |

### メディア・コミュニケーション (`media_communication`)

Broad admissions: 59; subcategories: 3.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `media` | メディア・映像 | 58 | `primary` |
| `communication` | コミュニケーション | 1 | `primary` |
| `journalism` | ジャーナリズム | 0 | `hidden` |

### 国際・地域研究 (`international_regional`)

Broad admissions: 160; subcategories: 3.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `international_studies` | 国際関係・国際研究 | 151 | `primary` |
| `regional_studies` | 地域研究 | 8 | `primary` |
| `global_studies` | グローバル研究 | 6 | `primary` |

### 教育・保育 (`education_childcare`)

Broad admissions: 787; subcategories: 4.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `teacher_education` | 教員養成 | 680 | `primary` |
| `childcare_early_childhood` | 保育・幼児教育 | 21 | `primary` |
| `education_support` | 教育支援 | 4 | `primary` |
| `science_math_education` | 理数教育 | 15 | `secondary` |

### 人文・社会（総合） (`humanities_social_general`)

Broad admissions: 212; subcategories: 0.

No v0.2 subcategory is defined.

### 理学 (`natural_sciences`)

Broad admissions: 702; subcategories: 5.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `mathematics_statistics` | 数学・数理・統計 | 107 | `primary` |
| `physics` | 物理 | 87 | `primary` |
| `chemistry` | 化学 | 231 | `primary` |
| `biology` | 生物 | 152 | `primary` |
| `earth_space_science` | 地球・宇宙 | 58 | `primary` |

### 工学 (`engineering`)

Broad admissions: 1,642; subcategories: 9.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `mechanical` | 機械 | 332 | `primary` |
| `electrical_electronic` | 電気・電子 | 282 | `primary` |
| `materials` | 材料・物質 | 105 | `primary` |
| `chemical_engineering` | 化学工学・応用化学 | 134 | `primary` |
| `civil_infrastructure` | 土木・社会基盤 | 81 | `primary` |
| `robotics_control` | ロボティクス・制御 | 49 | `primary` |
| `aerospace` | 航空・宇宙 | 22 | `primary` |
| `nuclear_energy` | 原子力・エネルギー | 42 | `secondary` |
| `biomedical_engineering` | 医工学 | 51 | `secondary` |

### 建築・都市 (`architecture_urban`)

Broad admissions: 172; subcategories: 3.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `architecture` | 建築 | 148 | `primary` |
| `urban_planning` | 都市・まちづくり | 75 | `primary` |
| `architectural_design` | 建築デザイン | 7 | `primary` |

### 情報・データサイエンス (`information`)

Broad admissions: 865; subcategories: 7.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `computer_science` | 情報科学・コンピュータ | 408 | `primary` |
| `ai_machine_learning` | AI・機械学習 | 21 | `primary` |
| `data_science_statistics` | データサイエンス・統計 | 97 | `primary` |
| `software_systems` | 情報システム・ソフトウェア | 97 | `primary` |
| `networks_communications` | 通信・ネットワーク | 62 | `secondary` |
| `media_information` | メディア情報 | 64 | `secondary` |
| `iot_digital` | IoT・デジタル | 15 | `secondary` |

### 環境 (`environment`)

Broad admissions: 244; subcategories: 4.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `environmental_science` | 環境科学 | 85 | `primary` |
| `ecology_forestry` | 生態・森林 | 20 | `primary` |
| `environmental_engineering` | 環境工学 | 22 | `primary` |
| `sustainability` | サステナビリティ | 2 | `primary` |

### 農学・水産 (`agriculture_fisheries`)

Broad admissions: 450; subcategories: 4.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `agriculture` | 農学 | 400 | `primary` |
| `fisheries_marine` | 水産・海洋 | 84 | `primary` |
| `forestry_resources` | 森林・資源 | 23 | `primary` |
| `agricultural_economics_business` | 農業経済・アグリビジネス | 14 | `primary` |

### 生命科学 (`life_sciences`)

Broad admissions: 596; subcategories: 4.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `biology_biotech` | 生物・バイオ | 541 | `primary` |
| `biotechnology` | 生命工学 | 52 | `primary` |
| `microbiology_fermentation` | 微生物・発酵 | 8 | `secondary` |
| `medical_science` | 医科学 | 18 | `secondary` |

### 食品・栄養 (`food_nutrition`)

Broad admissions: 139; subcategories: 3.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `nutrition` | 栄養 | 70 | `primary` |
| `food_science` | 食品科学 | 77 | `primary` |
| `fermentation_brewing` | 発酵・醸造 | 4 | `secondary` |

### 医学 (`medicine`)

Broad admissions: 151; subcategories: 0.

No v0.2 subcategory is defined.

### 歯学 (`dentistry`)

Broad admissions: 36; subcategories: 0.

No v0.2 subcategory is defined.

### 薬学 (`pharmacy`)

Broad admissions: 173; subcategories: 2.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `pharmacy_six_year` | 薬学6年制 | 111 | `primary` |
| `pharmaceutical_science_drug_discovery` | 薬科学・創薬 | 61 | `primary` |

### 看護・保健・医療 (`nursing_health`)

Broad admissions: 649; subcategories: 8.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `nursing` | 看護 | 279 | `primary` |
| `physical_therapy` | 理学療法 | 67 | `primary` |
| `occupational_therapy` | 作業療法 | 57 | `primary` |
| `speech_hearing` | 言語聴覚 | 16 | `primary` |
| `clinical_laboratory` | 臨床検査 | 31 | `primary` |
| `radiological_technology` | 診療放射線 | 34 | `primary` |
| `clinical_engineering` | 臨床工学 | 23 | `primary` |
| `emergency_medical` | 救急救命 | 15 | `secondary` |

### 福祉 (`welfare`)

Broad admissions: 61; subcategories: 0.

No v0.2 subcategory is defined.

### 獣医・動物 (`veterinary`)

Broad admissions: 71; subcategories: 2.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `veterinary_medicine` | 獣医 | 56 | `primary` |
| `animal_science` | 動物科学 | 20 | `primary` |

### 芸術・デザイン (`arts_design`)

Broad admissions: 179; subcategories: 3.

| Subcategory | Label | Admissions | UI status |
|---|---|---:|---|
| `fine_arts_crafts` | 美術・工芸 | 63 | `primary` |
| `music` | 音楽 | 27 | `primary` |
| `design` | デザイン | 131 | `primary` |

### 生活・家政 (`home_lifestyle`)

Broad admissions: 7; subcategories: 0.

No v0.2 subcategory is defined.

### スポーツ (`sports`)

Broad admissions: 45; subcategories: 0.

No v0.2 subcategory is defined.

### 観光・ホスピタリティ (`tourism_hospitality`)

Broad admissions: 18; subcategories: 0.

No v0.2 subcategory is defined.

### 総合・学際 (`interdisciplinary`)

Broad admissions: 46; subcategories: 0.

No v0.2 subcategory is defined.

## 7. Ambiguous and fail-closed values

| Raw value | Admissions | Frozen handling |
|---|---:|---|
| `人間科学` | 7 | Two current exact tuples remain semantically mixed; Broad and subcategory stay `review_required`. |
| `国際` | 5 | Current five contexts safely support `international_regional`; exact context adds regional/language detail only where explicit. |
| `地域デザイン` | 3 | Raw stays `review_required`; exact context maps community design to `sociology_community` and tourism design to `tourism_hospitality`. |
| `航空・パイロット` | 4 | Remains `review_required`; pilot training is not aerospace engineering. |

Contained tokens are never used at runtime. In particular, `理学療法`
does not become physics, `言語聴覚` does not become languages,
`獣医学` does not become human medicine, and pilot/management/maintenance
programs are not collapsed into aerospace engineering.

## 8. Representative multi-membership examples

| Raw value | Frozen Broad memberships |
|---|---|
| `経済・経営・情報` | `business_commerce`, `economics`, `information` |
| `外国語・国際` | `international_regional`, `languages` |
| `農学・生命` | `agriculture_fisheries`, `life_sciences` |
| `理工・情報` | `engineering`, `information`, `natural_sciences` |
| `デザイン・データ科学` | `arts_design`, `information` |
| `スポーツ工学` | `engineering`, `sports` |
| `医歯薬` | `dentistry`, `medicine`, `pharmacy` |

## 9. Integrity checks

All checks passed:

- unique Broad and subcategory codes;
- valid parent groups and contiguous display order;
- no exact duplicate mapping rows;
- valid group/subcategory references;
- exact raw values preserved without trimming;
- exact context tuple determinism and contiguous membership order;
- no substring, regex, fuzzy, AI, or normalization rule in the runtime contract;
- canonical inputs unchanged during validation.

## 10. New-data fail-closed behavior

A new raw value is `unmapped`. A known raw value appearing in a new context
continues to receive only its safe raw mapping; when that raw requires an
authoritative context, the new tuple is `review_required`/`unmapped` and
must emit a build warning with frequencies and representative record IDs.
No nearby program or lexical token may be used as an automatic fallback.
