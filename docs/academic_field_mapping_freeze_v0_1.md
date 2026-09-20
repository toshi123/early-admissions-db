# Academic-field exact mapping freeze v0.1

## Status and authority

This document freezes the production `academic_field` mapping contract and
taxonomy at version `0.1`. The authoritative machine-readable artifacts are:

- `schema/academic_field/academic_field_taxonomy_v0_1.csv`
- `schema/academic_field/academic_field_crosswalk_v0_1.csv`

The crosswalk key is the exact, unmodified raw `academic_field` text. Production
builds must not classify with substring, regex, morphological, fuzzy, first-token,
AI, whitespace-trimming, or normalization logic. A non-NULL value absent from the
crosswalk is published as `unmapped` with zero group rows. SQL NULL is
`not_applicable` with zero group rows.

## Frozen taxonomy decision

All 19 proposed broad groups are retained without code or label changes. Review
of all 448 current raw values found no search domain that required a twentieth
group and no pair whose merger would preserve important user intent. `environment`
remains independent because actual values combine it with natural science,
engineering, agriculture, life science, and social science. `interdisciplinary`
is reserved for raw values that explicitly indicate integration, not as a catch-all.
There is no `other` group.

The taxonomy is a search aid, not a replacement for the university's raw label.
Every result must retain the raw value.

## Current freeze snapshot

The figures below are derived from the frozen unified master and crosswalk, not
normal-build row-count gates.

| Measure | Value |
|---|---:|
| Unified admissions | 5,921 |
| Non-NULL admissions | 5,921 |
| Distinct raw values in input | 448 |
| Distinct raw values in crosswalk | 448 |
| Crosswalk rows including repeated multi memberships | 728 |
| Single raw values | 199 |
| Multi raw values | 245 |
| Review-required raw values | 4 |
| Current unmapped raw values | 0 |
| Single admissions | 4,069 |
| Multi admissions | 1,833 |
| Review-required admissions | 19 |
| Current unmapped admissions | 0 |
| Current not-applicable admissions | 0 |
| Classified admissions | 5,902 / 5,921 (99.68%) |
| Group membership rows | 7,952 |

The final multi count is higher than the provisional design audit because the
freeze review explicitly retained all safely supported memberships for combined
labels such as `理工・情報`, nutrition/food, pharmaceutical science, and
environmental engineering. This is an intentional review outcome, not a build-time
inference.

## Membership counts by group

Membership counts are admissions, so one admission may appear in several rows.

| Group code | Admissions |
|---|---:|
| `natural_sciences` | 702 |
| `engineering` | 1,750 |
| `information` | 852 |
| `agriculture_fisheries` | 423 |
| `life_sciences` | 631 |
| `medicine` | 154 |
| `dentistry` | 36 |
| `pharmacy` | 173 |
| `nursing_health_welfare` | 778 |
| `veterinary` | 71 |
| `humanities` | 334 |
| `social_sciences` | 608 |
| `education` | 787 |
| `arts_design` | 232 |
| `home_lifestyle` | 76 |
| `sports` | 45 |
| `environment` | 238 |
| `tourism_hospitality` | 16 |
| `interdisciplinary` | 46 |

## Values frozen as review-required

| Exact raw value | Admissions | Reason |
|---|---:|---|
| `人間科学` | 7 | Current institutions use the same broad label for materially different programs; the raw label alone cannot safely distinguish humanities, social science, health, or education. |
| `国際` | 5 | Current contexts span international studies, regional studies, and communication; the raw label alone does not safely identify humanities, social science, language, tourism, or interdisciplinarity. |
| `地域デザイン` | 3 | The same raw value covers community design and tourism design contexts, so an exact raw-only group would be misleading. |
| `航空・パイロット` | 4 | Pilot training is not safely equivalent to engineering or tourism/hospitality from the raw value alone. |

`科学コミュニケーション` was re-reviewed in its current Tokyo University of
Science context and frozen as `interdisciplinary`. No institution-specific rule
is used at build time: its exact raw value has one reviewed crosswalk entry.

## High-risk boundary decisions

- `理学療法`, `言語聴覚`, and related therapy values map to
  `nursing_health_welfare`, never to natural sciences or humanities because of a
  contained token.
- Human medicine, dentistry, pharmacy, allied health, and veterinary groups stay
  separate. Biomedical engineering values use engineering plus allied health,
  not human medicine.
- Pharmaceutical-science/創薬 values may carry `life_sciences` plus `pharmacy`;
  six-year `薬学` remains pharmacy only.
- Nutrition is searchable through `nursing_health_welfare` and
  `home_lifestyle`; food/life wording adds `life_sciences` only when the exact
  reviewed value supports it.
- Environmental engineering is multi-valued; `environment` is never added merely
  because a surrounding institution might have an environmental emphasis.
- `国際` is never a classification token by itself. Explicit combined raw values
  are mapped only to the other reviewed concepts in that exact value.

## Integrity and future updates

Each frozen raw value is in exactly one complete state: `single` has one child,
`multi` has at least two, and `review_required` has zero. Generated `unmapped`
and `not_applicable` states also have zero children. Group order follows taxonomy
display order. The SQLite builder verifies parent coverage, raw equality,
cardinality, group foreign keys, versions, hashes, and deterministic loading.

Canonical updates do not require code changes. A newly observed value remains
searchable by raw value but is fail-closed as `unmapped` until this source-controlled
crosswalk is explicitly reviewed and versioned.

## Freeze hashes

| Artifact | SHA-256 |
|---|---|
| Crosswalk v0.1 | `8f2c8034395cf7ceebb9675b966d34b638b94cb50569bb90bc426091bac4e762` |
| Taxonomy v0.1 | `f1f52d0282618eb5b22d3c420010718eb30f4ec14ad889dd574f218a5743a9f2` |
| Unified `master.csv` input | `1df386ed99532a3dff381507978a1454d7c20113574285b2526f6ae122050279` |

## Review assumptions

- Mapping decisions use only the current 448 exact raw labels and bounded
  university/faculty/department context for human review.
- Context was used to decide whether an exact raw value can be frozen, not as a
  runtime key or fallback rule.
- Multi membership means “include in any of these broad search facets,” not that
  every program teaches all facets equally.
- Ambiguity is preserved as `review_required`; coverage was not optimized by
  forcing values into a broad group.
