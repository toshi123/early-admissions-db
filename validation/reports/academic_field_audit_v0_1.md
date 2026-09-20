# `academic_field` search-design audit v0.1

## 1. Scope

This report audits the current 5,921 unified admissions for the design of a
future Site search field. It does not change `academic_field`, create a frozen
crosswalk, or modify any database artifact.

Inputs inspected read-only:

- `data/canonical/unified/master.csv`
  - SHA-256:
    `1df386ed99532a3dff381507978a1454d7c20113574285b2526f6ae122050279`
- `data/derived/sqlite/early_admissions_2027.sqlite`
  - SHA-256:
    `18ddaa9cb1cb55a8e37dcf39afc182e934119baa418fedba74d8feea8f8dff5e`

The SQLite manifest confirms 5,921 admission rows and the unified-input hash.
The database was opened with `mode=ro&immutable=1`.

## 2. Inventory

| Metric | Count |
|---|---:|
| Admissions | 5,921 |
| Non-null `academic_field` rows | 5,921 |
| SQL NULL rows | 0 |
| Distinct raw values | 448 |

The most frequent values are:

| Raw value | Admissions |
|---|---:|
| 教育・教員養成 | 670 |
| 工学 | 535 |
| 情報 | 256 |
| 農学・生命 | 208 |
| 看護 | 203 |
| 理学 | 182 |
| 人文・社会 | 138 |
| 医学 | 138 |
| 工学・機械 | 91 |
| 経済 | 80 |
| 理工・情報 | 73 |
| 建築 | 71 |
| 薬学（6年制） | 67 |
| 教育 | 57 |
| 生命科学 | 57 |
| 看護・医療 | 56 |
| 工学・化学 | 55 |
| 外国語・国際 | 52 |
| 工学・電気電子 | 52 |
| 社会・地域 | 52 |
| 情報・メディア | 49 |
| 福祉 | 49 |
| 機械工学 | 47 |
| 経営 | 46 |
| 情報・工学 | 44 |

This distribution confirms that the field mixes at least four levels:

- broad domains, such as `工学`, `情報`, and `医学`;
- subfields, such as `工学・機械` and `薬学（6年制）`;
- explicit cross-domain labels, such as `農学・生命`, `人文・社会`, and
  `理工・情報`;
- labels whose domain cannot be fixed safely from wording alone.

## 3. Why generic substring parsing is rejected

A first lexical pass exposed systematic false classifications:

- `理学療法` contains `理学` but is a health-profession field;
- `言語聴覚` contains `言語` but is a health-profession field;
- `獣医学` contains `医学` but should not silently become human medicine;
- `国際看護` contains `国際`, but that modifier does not necessarily create a
  social-science membership;
- `航空マネジメント` and `航空技術` share “航空” but belong to different
  broad search intents.

Therefore a production build must not infer groups with substring, regular
expression, morphological, or “first recognized token” logic. A versioned
exact raw-value crosswalk is required.

## 4. Provisional design-review classification

All 448 distinct raw values were reviewed as an aggregate. A provisional
phrase-aware classification was used only to estimate the shape of a future
crosswalk. It is not an implemented or authoritative mapping.

| Candidate status | Distinct raw values | Admissions | % of admissions |
|---|---:|---:|---:|
| Single broad group candidate | 246 | 4,454 | 75.22% |
| Multiple broad groups candidate | 198 | 1,450 | 24.49% |
| Review required | 4 | 17 | 0.29% |
| Total | 448 | 5,921 | 100.00% |

Thus 5,904/5,921 rows (99.71%) have a provisional single- or multi-group
candidate. This is candidate coverage, not approved production coverage. The
exact crosswalk still requires a separate review/freeze step.

The four values deliberately left unclassified are:

| Raw value | Admissions | Reason |
|---|---:|---|
| 人間科学 | 7 | Used by institutions for materially different humanities, social, health, and interdisciplinary programs |
| 国際 | 5 | Does not identify whether the program is language, culture, policy, business, or another domain |
| 科学コミュニケーション | 1 | Cross-domain label; assigning science or humanities alone would be misleading |
| 航空・パイロット | 4 | Occupational program label; engineering or transport/business membership is not safely implied |

These rows should remain searchable by raw value and appear under a special
“未分類・要確認” UI state until an approved mapping decision exists. They must
not be forced into `その他` merely to reach 100% coverage.

## 5. Candidate broad-group membership

Because multi-group records contribute to every applicable group, the
membership counts below overlap and must not be summed.

| Proposed group code | Japanese label | Candidate admissions | Distinct raw values |
|---|---|---:|---:|
| `engineering` | 工学・建築 | 1,622 | 128 |
| `information` | 情報・データサイエンス | 845 | 80 |
| `education` | 教育・保育 | 787 | 13 |
| `nursing_health_welfare` | 看護・保健・医療・福祉 | 781 | 62 |
| `life_sciences` | 生命科学 | 568 | 61 |
| `social_sciences` | 社会科学 | 564 | 62 |
| `natural_sciences` | 理学 | 530 | 54 |
| `agriculture_fisheries` | 農学・水産 | 395 | 31 |
| `humanities` | 人文 | 331 | 28 |
| `environment` | 環境 | 286 | 59 |
| `arts_design` | 芸術・デザイン | 178 | 31 |
| `pharmacy` | 薬学 | 173 | 12 |
| `medicine` | 医学 | 154 | 4 |
| `veterinary` | 獣医・動物 | 71 | 9 |
| `sports` | スポーツ | 45 | 11 |
| `dentistry` | 歯学 | 36 | 4 |
| `interdisciplinary` | 総合・学際 | 36 | 9 |
| `tourism_hospitality` | 観光・ホスピタリティ | 16 | 5 |
| `home_lifestyle` | 生活・家政 | 2 | 1 |

These counts are directional sizing evidence. They should be recomputed from
the final checked-in crosswalk rather than frozen as parser rules.

## 6. Representative multi-group cases

| Raw value | Candidate groups |
|---|---|
| 農学・生命 | 農学・水産 + 生命科学 |
| 人文・社会 | 人文 + 社会科学 |
| 理工・情報 | 理学 + 工学・建築 + 情報・データサイエンス |
| デザイン・データ科学 | 芸術・デザイン + 情報・データサイエンス |
| スポーツ工学 | スポーツ + 工学・建築 |
| アグリビジネス | 農学・水産 + 社会科学 |
| 数理科学・統計 | 理学 + 情報・データサイエンス |
| 医歯薬 | 医学 + 歯学 + 薬学 |

A single `academic_field_group` column would either lose information or force
an arbitrary primary group for these values. A parent/child many-to-many
derived layer is therefore preferred.

## 7. Reproducible raw audit query

The raw inventory can be reproduced against the published database without
loading admission text into application memory:

```sql
SELECT academic_field, COUNT(*) AS admissions
FROM admissions
GROUP BY academic_field
ORDER BY admissions DESC, academic_field;
```

Production classification counts must instead be calculated by joining that
inventory to the reviewed exact-value crosswalk. No approximate lexical rule
is accepted as the source of truth.

## 8. Audit conclusion

- Preserve `academic_field` exactly on every admission.
- Add a many-to-many derived search layer, not a replacement scalar field.
- Use exact-value mappings with a mapping-contract version.
- Keep new, missing, or disputed values fail-closed as `unmapped` or
  `review_required`.
- Expose raw-value search for all 5,921 current rows.
- Treat 99.71% as provisional candidate coverage only; implementation must
  publish its own manifest counts after crosswalk review.
