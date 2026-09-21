# Academic-field v0.2 SQLite derived search design

Version: 0.2

Status: implementation contract
Authority: the frozen artifacts under `schema/academic_field/v0_2/`

## Scope and compatibility

This layer adds the production-frozen academic-field taxonomy v0.2 to the
derived SQLite database. It is parallel to the v0.1 tables and does not change
the meaning of `academic_field_taxonomy`, `admission_search_academic_fields`,
`admission_search_academic_field_groups`, or their existing CLI options.

The canonical, release, unified, and frozen taxonomy files remain read-only.
The SQLite database is rebuilt from zero in a temporary file and is published
only after all validations pass.

## Tables

- `academic_field_v2_broad_taxonomy`: all 30 frozen broad groups, including UI
  section and ordering metadata.
- `academic_field_v2_subcategory_taxonomy`: all 89 frozen subcategories,
  including zero-count categories and the parent broad-group foreign key.
- `admission_search_academic_fields_v2`: exactly one derived parent row per
  admission, preserving `admissions.academic_field` byte-for-byte at the SQL
  text-value level and recording broad/subcategory status plus context use.
- `admission_search_academic_field_broad_memberships_v2`: zero or more broad
  memberships per admission.
- `admission_search_academic_field_subcategory_memberships_v2`: zero or more
  subcategory memberships per admission. Its composite foreign key requires
  the matching parent broad membership for the same admission.

All tables are `STRICT`. Membership primary keys prevent duplicates. Order is
contiguous from 1 and follows the frozen taxonomy row order. The basis is one
of `raw_exact`, `context_exact`, or `raw_and_context`.

## Exact mapping and merge contract

Runtime classification performs exact lookup only. It does not trim or
normalize raw values and does not use substring, regular expression, fuzzy,
nearest-program, faculty-name, department-name, or AI inference.

Context lookup uses the exact tuple:

`(source_dataset, university, faculty_school, department, academic_field)`

Database NULL for faculty or department is serialized as the empty string for
this lookup, matching the freeze artifact contract.

- `additive`: frozen context memberships are unioned with raw memberships;
  raw memberships are not removed.
- `authoritative`: allowed only where the frozen raw mapping is
  `review_required`; the frozen context memberships replace the unresolved raw
  result.

An exact context tuple with no safe membership remains `review_required`.
Unknown raw values fail closed as `unmapped`. A safe broad mapping without a
safe subcategory is the normal `subcategory_mapping_status=none` state.

## Integrity and validation

The build validates frozen SHA-256 values before loading and rechecks every
input immediately before publication. Validation covers taxonomy and parent
row counts, raw equality, mapping versions, status/cardinality relationships,
membership foreign keys, parent broad membership for every subcategory,
contiguous deterministic order, exact membership totals, context counts,
`PRAGMA foreign_key_check`, and `PRAGMA quick_check`.

The build manifest records all five freeze hashes, all taxonomy and membership
counts, status counts, context-use counts, representative review/unmapped
logical keys, and validation status. Core `build_metadata` records the same
contract identity, hashes, and principal counts.

## Indexes

Two lookup indexes support the primary search paths:

- broad `(group_code, admission_rowid)`
- subcategory `(subcategory_code, admission_rowid)`

Two status indexes support audit/review queries. No additional low-cardinality
indexes are introduced. The existing builder runs `ANALYZE` and `PRAGMA
optimize` after loading.

## Structured search contract

CLI examples:

```text
./scripts/search --academic-field-v2 natural_sciences
./scripts/search \
  --academic-field-v2 natural_sciences engineering \
  --academic-subfield-v2 natural_sciences=mathematics_statistics,physics
```

Every `--academic-subfield-v2` value is `BROAD=SUB[,SUB...]`. The broad code
must also be listed with `--academic-field-v2`, and every subcategory must have
that frozen parent; otherwise the request fails validation.

Each broad code forms a branch. A branch without subcategories matches the
whole broad group. A branch with subcategories matches the broad group AND any
listed subcategory. Branches are ORed:

`(broad A AND (sub A1 OR sub A2)) OR broad B`

All other structured-search fields are ANDed with this branch predicate. v0.1
and v0.2 academic-field filters may be supplied together and are ANDed, but
routine clients should use one taxonomy version at a time. All user values are
SQL bound parameters; none become SQL identifiers or syntax.

## Future Site-data boundary

This change does not project v0.2 into Site-data and does not change the
frontend. A future projection may consume the taxonomy and membership tables,
but must preserve this branch semantics and must not reclassify raw text.
