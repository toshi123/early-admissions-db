# Academic-field derived search design v0.1

## 1. Status and scope

This document defines the derived search contract for `academic_field`. The
production v0.1 taxonomy and exact-value crosswalk are frozen in
`schema/academic_field/`; review evidence and hashes are recorded in
`docs/academic_field_mapping_freeze_v0_1.md`.

The raw field remains authoritative and unchanged:

```text
admissions.academic_field
```

Audit evidence is in
`validation/reports/academic_field_audit_v0_1.md`.

## 2. Design decision

Do not add one forced scalar `academic_field_group`. Use:

1. one parent classification row per admission; and
2. zero or more broad-group child rows.

This permits `理工・情報` to participate in natural-science, engineering, and
information searches without deleting its raw wording or choosing an arbitrary
primary group.

## 3. Proposed taxonomy

| Stable code | Japanese display label | Intended scope |
|---|---|---|
| `natural_sciences` | 理学 | Mathematics, physics, chemistry, earth/natural science |
| `engineering` | 工学・建築 | Engineering, architecture, civil, mechanical, electrical, materials |
| `information` | 情報・データサイエンス | Information science, computing, AI, data science |
| `agriculture_fisheries` | 農学・水産 | Agriculture, forestry, fisheries, agricultural resources |
| `life_sciences` | 生命科学 | Life science, biology, biotechnology, food/fermentation science |
| `medicine` | 医学 | Human medicine |
| `dentistry` | 歯学 | Dentistry |
| `pharmacy` | 薬学 | Pharmacy and pharmaceutical science |
| `nursing_health_welfare` | 看護・保健・医療・福祉 | Nursing, allied health, rehabilitation, health and welfare |
| `veterinary` | 獣医・動物 | Veterinary and animal-focused programs |
| `humanities` | 人文 | Literature, languages, history, philosophy, culture, religion |
| `social_sciences` | 社会科学 | Law, politics, economics, management, policy, sociology |
| `education` | 教育・保育 | Teacher education, pedagogy, childcare, early childhood |
| `arts_design` | 芸術・デザイン | Art, music, design, image, performance, craft |
| `home_lifestyle` | 生活・家政 | Home economics, clothing, housing, lifestyle science |
| `sports` | スポーツ | Sport, physical education, martial arts |
| `environment` | 環境 | Environment and sustainability-oriented fields |
| `tourism_hospitality` | 観光・ホスピタリティ | Tourism and hospitality |
| `interdisciplinary` | 総合・学際 | Explicit integrated/interdisciplinary programs |

“未分類・要確認” is a UI status, not a broad academic group. The design does
not create an `other` bucket that silently absorbs unknown values.

The taxonomy is a search aid, not an official classification of a university
program. The raw field is always displayed alongside it.

## 4. Authoritative mapping source

The implementation uses a source-controlled, versioned exact-value crosswalk
with these logical columns:

| Field | Contract |
|---|---|
| `mapping_contract_version` | Version of this taxonomy/crosswalk |
| `raw_value` | Exact `academic_field` string, with no trim or normalization |
| `mapping_status` | `single`, `multi`, or `review_required` |
| `group_code` | One taxonomy code; repeated rows implement many-to-many mapping |
| `group_order` | Stable display order for multiple groups |
| `review_note` | Short human-reviewed rationale or unresolved issue |

The crosswalk must have one of these complete states for every reviewed raw
value:

- one group and status `single`;
- two or more groups and status `multi`;
- zero groups and status `review_required`.

No substring fallback is allowed. A raw value newly introduced by a canonical
update and absent from the crosswalk becomes `unmapped` in the generated layer.
It remains available through raw search and receives no group membership.

## 5. Proposed SQLite realization

### 5.1 Parent table

```sql
CREATE TABLE admission_search_academic_fields (
    admission_rowid INTEGER PRIMARY KEY
        REFERENCES admissions(admission_rowid) ON DELETE CASCADE,
    raw_value TEXT,
    mapping_status TEXT NOT NULL
        CHECK (mapping_status IN (
            'single',
            'multi',
            'review_required',
            'unmapped',
            'not_applicable'
        )),
    mapping_contract_version TEXT NOT NULL,
    review_note TEXT,
    CHECK (
        (raw_value IS NULL AND mapping_status = 'not_applicable')
        OR
        (raw_value IS NOT NULL AND mapping_status <> 'not_applicable')
    )
) STRICT;
```

`raw_value` must equal `admissions.academic_field` byte-for-byte at the text
value level. Current data has no NULL academic field, but `not_applicable`
keeps future null semantics explicit.

### 5.2 Child table

```sql
CREATE TABLE admission_search_academic_field_groups (
    admission_rowid INTEGER NOT NULL
        REFERENCES admission_search_academic_fields(admission_rowid)
        ON DELETE CASCADE,
    group_code TEXT NOT NULL,
    group_order INTEGER NOT NULL CHECK (group_order >= 1),
    mapping_basis TEXT NOT NULL DEFAULT 'exact_crosswalk'
        CHECK (mapping_basis = 'exact_crosswalk'),
    PRIMARY KEY (admission_rowid, group_code),
    UNIQUE (admission_rowid, group_order)
) STRICT;
```

The production SQL schema constrains `group_code` through the
`academic_field_taxonomy` lookup table and a foreign key.

### 5.3 Integrity rules

- Every admission has exactly one parent classification row.
- `single` has exactly one child group.
- `multi` has at least two child groups.
- `review_required`, `unmapped`, and `not_applicable` have zero child groups.
- Every parent raw value exactly equals the admission raw value, including
  whitespace.
- Every generated row carries one mapping-contract version.
- The build manifest records status counts, membership counts, input hashes,
  taxonomy version, and crosswalk SHA-256.

## 6. Search semantics

For one or more selected group codes, use existence membership:

```sql
EXISTS (
  SELECT 1
  FROM admission_search_academic_field_groups afg
  WHERE afg.admission_rowid = admissions.admission_rowid
    AND afg.group_code IN (?, ...)
)
```

Selected group codes use OR. The academic-group predicate uses AND with every
other filter field. Parameter binding is mandatory.

Examples:

- Selecting only `engineering` includes raw `工学`, `理工・情報`, and
  `デザイン工学` when those exact values are approved for engineering.
- Selecting `engineering` and `information` means engineering OR information,
  not a requirement that a record belong to both.
- `review_required` and `unmapped` are not returned by a group selection, but
  remain findable by raw value and by a dedicated “未分類・要確認” status filter.

## 7. Site UI behavior

- Primary academic-field filter: broad group checkboxes/chips.
- Advanced filter: exact raw `academic_field` values.
- Result card: raw field first, then derived group chips.
- Multi-group record: display all groups.
- Review/unmapped record: display raw value plus “大分類は要確認”.
- Help text: “大分類は検索用の派生分類です。大学の公式分類は原文を確認
  してください。”

The Site must not replace the raw label with the derived label.

## 8. Audit coverage and release gate

The completed freeze review found:

| Candidate status | Admissions |
|---|---:|
| Single group | 4,069 |
| Multiple groups | 1,833 |
| Review required | 19 |
| Total | 5,921 |

Frozen classified coverage is 5,902/5,921 (99.68%). The 19 review rows are not
failures and are not forced into a group.

Before implementation, the exact crosswalk must be checked in and independently
reviewed. A future build should validate the current snapshot counts as a
regression, while deriving expected row counts from its actual input for normal
rebuilds.

Recommended build policy for new raw values:

- preserve and publish the admission row;
- emit `mapping_status='unmapped'` with zero groups;
- issue a validation warning and list frequencies/representative logical keys;
- do not infer a group;
- require explicit crosswalk review before claiming full group-search coverage.

## 9. Values deliberately held for review

The current candidate holds these exact values:

- `人間科学` (7 admissions)
- `国際` (5)
- `地域デザイン` (3)
- `航空・パイロット` (4)

Their ambiguity is a property of the available label, not a parser defect to
be hidden by an `other` category.

## 10. Validation contract for a future implementation

At minimum validate:

- one parent row per admission;
- parent FK integrity;
- exact raw-value equality;
- crosswalk version and SHA-256;
- child-group enum and FK integrity;
- `single`/`multi`/review cardinality rules;
- no substring-generated memberships;
- deterministic row ordering and byte-identical rebuild;
- row counts and status counts in a build manifest;
- representative queries for single, multi, and review-required values;
- Site projection preserves every raw value and derived status.

## 11. Deferred decisions

- Review and version any exact raw values introduced by a future canonical update.
- Whether `environment` should remain independent or only co-occur with a
  disciplinary group.
- Whether animal science without explicit veterinary wording belongs solely to
  `veterinary` or additionally to agriculture/life science.
- Whether food/nutrition labels require simultaneous life-science,
  health/welfare, or home/lifestyle membership.
- Whether `tourism_hospitality` should be independent from social sciences.
- Japanese display ordering of the 19 groups.

These decisions must be resolved in crosswalk review, not by adding broader
parser heuristics.
