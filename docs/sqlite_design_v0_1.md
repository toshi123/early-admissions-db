# Early Admissions SQLite Design Contract v0.1

## 1. Status and boundary

- Database schema version: `0.1`
- Unified input contract: `0.1`
- Status: implemented; the published database is generated only by the
  validated, atomic build pipeline.
- Authoritative DDL: `schema/sqlite/early_admissions_sqlite_schema_v0_1.sql`
- Input grain, facts, normalization, and severity semantics remain governed by:
  - `docs/unified_data_contract.md`
  - `docs/unified_field_mapping_v0_1.md`
  - `schema/unified/early_admissions_unified_schema_v0_1.json`
- SQLite is a fully reproducible derived artifact. It must be rebuilt from the
  unified CSV files and must never become an independently edited source.
- This design does not modify canonical, release, or unified CSV data.
- JSON/search index, Excel workbook, and Site implementation remain out of
  scope.

The SQLite layer may add technical identifiers, indexes, views, FTS structures,
and future search-only derived data. It must not repair, infer, deduplicate, or
reinterpret admission facts.

## 2. Frozen input snapshot used for this design

The counts below are a regression snapshot, not hard-coded production build
requirements. A future builder must calculate expected row counts from its
validated unified inputs.

| Unified input | Rows | Bytes | SHA-256 |
|---|---:|---:|---|
| `master.csv` | 5,921 | 10,874,313 | `1df386ed99532a3dff381507978a1454d7c20113574285b2526f6ae122050279` |
| `coverage.csv` | 259 | 147,685 | `b10ca3381afb0f3e8740ed2d14ddf086233151d4c6eba6e946344b12638913fb` |
| `research_requirements.csv` | 437 | 208,432 | `ba105cca34c03fee34fb7d04ce1d0818caa386d0832e7999bf9ec9bf9f135919` |

The input build manifest declares unified contract `0.1`, kokkoritsu `5.61`,
shidai `0.97`, and validation status `passed`. Its current SHA-256 is
`51a3bbeb30ba81d0a98efddbcdcd8174b0389948dd034578fc205be1b6381901`.

## 3. Design principles

1. **Lossless base tables.** Every unified CSV field is represented once in its
   corresponding base table, under the same field name and meaning.
2. **Logical keys remain authoritative.** Surrogate integer rowids are storage
   aids only. They are not admission identifiers and are not stable external IDs.
3. **No child deduplication.** Each ResearchRequirements CSV row produces one
   `research_requirements` row, including exact duplicates.
4. **Null remains distinct.** Empty CSV cells become SQL `NULL`; `Unknown`,
   `No`, and `0` remain different values.
5. **Raw values remain raw.** Text is not trimmed, Unicode-normalized, split,
   translated, or date-parsed during base-table loading.
6. **Read-oriented, full rebuild.** The intended publication workflow creates a
   new temporary database, validates it, then atomically publishes one file.
   In-place factual editing is out of scope.
7. **Portable degradation.** Structured queries continue to work if FTS5 or
   the `trigram` tokenizer is unavailable; build metadata records the profile.

The ordinary tables use SQLite `STRICT` mode. `STRICT` provides rigid storage
type checks and requires SQLite 3.37.0 or newer; `PRAGMA quick_check` also checks
the stored types of strict tables. See the official
[SQLite STRICT tables documentation](https://www.sqlite.org/stricttables.html).

## 4. Type and serialization mapping

| Unified logical value | SQLite representation | Rule |
|---|---|---|
| nullable string | `TEXT` or `NULL` | Empty CSV cell becomes `NULL`; nonblank text is copied exactly |
| required string | `TEXT NOT NULL` | Empty input is a build error |
| integer | `INTEGER` | `admission_year`, `information_year`, and `master_rows` only |
| nullable boolean | `INTEGER` `0`, `1`, or `NULL` | Only `stem_flag` and `fallback_previous_year` |
| tri-state | `TEXT` or `NULL` | Exact `Yes`, `No`, `Unknown`, or `NULL`; never converted to boolean |
| source-specific raw field | `TEXT` or `NULL` | No common enum is inferred |
| raw date/period | `TEXT` or `NULL` | No base-layer date conversion |

Default `BINARY` collation is intentional for keys and enums. The builder must
bind native Python/SQLite values rather than interpolating SQL text. It must not
use `COALESCE`, empty-string sentinels, or truthiness to collapse null states.

## 5. Base and supporting tables

### 5.1 `admissions`

- Source: unified `master.csv`.
- Grain: one actual application unit / selection slot.
- Technical key: `admission_rowid INTEGER PRIMARY KEY`.
- Logical key: `UNIQUE(source_dataset, source_version, record_id)`.
- All 79 unified Master fields are retained under their contract names.
- `stem_flag` and `fallback_previous_year` use `0`/`1`/`NULL`; all other
  `Yes`/`No`/`Unknown` fields remain text.
- The allowed source-version pair and source/institution-type relationship are
  enforced by `CHECK` constraints.

`admission_rowid` should be assigned in deterministic unified CSV order. A row
reordering may change it; callers must persist or exchange the logical key, not
the rowid.

### 5.2 `coverage`

- Source: unified `coverage.csv`.
- Grain: one university coverage state in one source snapshot.
- Technical key: `coverage_rowid INTEGER PRIMARY KEY`.
- Logical key:
  `UNIQUE(source_dataset, source_version, institution_type, university)`.
- All 12 unified Coverage fields are retained.
- `master_rows = 0` is valid.

The required equality between `coverage.master_rows` and matching admissions
cannot be expressed as a row-local `CHECK`; it remains a mandatory post-load
validation query. Coverage has no foreign key to admissions because a valid
coverage row may intentionally have zero admissions.

### 5.3 `research_requirements`

- Source: unified `research_requirements.csv`.
- Grain: one source child row.
- Technical key: `research_rowid INTEGER PRIMARY KEY`.
- No factual or natural UNIQUE constraint is added.
- Logical foreign key:
  `(source_dataset, source_version, admission_id)` references
  `admissions(source_dataset, source_version, record_id)`.
- All 15 unified child fields are retained.

Exact child duplicates receive different `research_rowid` values and remain
independently queryable. No `required / alternative / relevant` class is added.
Parent flag/child existence disagreements retain the unified validator severity;
they are not database constraint violations.

### 5.4 `build_metadata`

`build_metadata` contains exactly one row (`singleton_id = 1`) and records:

- database schema version;
- unified contract version and schema ID;
- UTC build timestamp;
- builder version;
- SQLite library version;
- selected FTS capability/tokenizer profile;
- canonical JSON mapping source datasets to source versions;
- canonical JSON mapping the three unified CSV names to SHA-256 values;
- SHA-256 of the input unified build manifest;
- SHA-256 of the SQLite schema contract;
- row counts for `admissions`, `coverage`, and `research_requirements`.
- GPA parser contract version, GPA DDL/crosswalk SHA-256 values, the three GPA
  safety classification counts, and the GPA 3.8 strict-safe regression count.

Recommended JSON shapes are:

```json
{"kokkoritsu":"5.61","shidai":"0.97"}
```

```json
{
  "coverage.csv":"b10ca3381afb0f3e8740ed2d14ddf086233151d4c6eba6e946344b12638913fb",
  "master.csv":"1df386ed99532a3dff381507978a1454d7c20113574285b2526f6ae122050279",
  "research_requirements.csv":"ba105cca34c03fee34fb7d04ce1d0818caa386d0832e7999bf9ec9bf9f135919"
}
```

The builder validates those JSON objects before commit. The table deliberately
does not require `json_valid()` so the core database does not depend on a JSON
extension being compiled separately.

### 5.5 Reserved `admission_search_dates`

Raw date and period fields stay in `admissions`. A separate tall table is
reserved for a later approved normalization contract:

- one row per (`admission_rowid`, `source_field`);
- `date_start` and `date_end` as ISO `YYYY-MM-DD` text;
- `parse_status` as `parsed`, `partial`, `unparsed`, or `not_applicable`;
- a single date is represented by equal start and end values.

The SQLite v0.1 builder must leave this table empty until parsing rules and
ambiguous-value handling are separately approved. This avoids giving raw date
strings false chronological semantics while allowing a future range index
without changing `admissions` or overwriting source evidence.

### 5.6 GPA derived search layer

The separately versioned
`schema/sqlite/admission_search_gpa_schema_v0_1.sql` adds:

- `admission_search_gpa`, exactly one fail-closed classification row per
  admission;
- `admission_search_gpa_rule_groups` and
  `admission_search_gpa_clauses`, retained empty in v0.1 for future complete
  conditional-rule representation;
- `admission_search_gpa_safe`, the only automatic numeric search view.

`admissions.gpa_requirement` remains authoritative. `raw_value` is an exact
copy, integer tenths are the comparison authority, and only approved simple
current-year overall minimums receive numeric bounds. The full parser and
query semantics are governed by `docs/gpa_search_design_v0_1.md`.

## 6. Views

### 6.1 `admissions_search`

Grain remains one row per admission. The view contains `admissions.*`, selected
coverage fields (including `master_rows`, status, source URL, and notes) with a
`coverage_` prefix, and two derived child-presence fields:

- `research_detail_rows`: exact child row count, including duplicates;
- `has_research_details`: `1` when one or more child rows exist, otherwise `0`.

`has_research_details` is a search convenience only. It does not modify or
reinterpret `research_requirement_required`.

### 6.2 `admissions_with_research`

This is a non-aggregating left join. It returns one row for each
admission/ResearchRequirements pair and one row with null `research_*` columns
for admissions without children. The `research_rowid` remains visible, so exact
duplicate children are not collapsed. Child display fields and provenance use a
`research_` prefix rather than overwriting parent values.

For the current snapshot, its expected row-count formula is:

```text
admissions + research child rows - admissions having at least one child
= 5,921 + 437 - 232
= 6,126
```

The builder must calculate, not hard-code, this value.

## 7. Structured index policy

Current `admissions` has only 5,921 rows. Many requested filters have two to five
values, so one index per boolean/tri-state field would add build/storage cost
without reliably improving plans. The v0.1 proposal uses a small set of
query-shaped and narrow covering indexes, followed by `ANALYZE` after loading.

| Search dimension | Proposed index | Intended query prefix |
|---|---|---|
| university and faculty drill-down | `idx_admissions_university` | `university`, then faculty/department |
| institution type, prefecture | `idx_admissions_institution_prefecture` | type; type + prefecture; university within region |
| STEM and academic field | `idx_admissions_stem_academic` | STEM; STEM + field; field via low-cardinality skip-scan |
| selection category | `idx_admissions_selection_category` | category + type |
| exclusive enrollment | `idx_admissions_exclusive_enrollment` | status + type/location |
| school recommendation and academic record | `idx_admissions_recommendation_record` | recommendation flag, optionally academic-record flag |
| Common Test and research requirement | `idx_admissions_common_research` | Common Test flag, optionally research flag |
| interview/oral/presentation | `idx_admissions_interview_oral_presentation` | common selection-method combinations |
| Common Test/essay/written selection | `idx_admissions_common_essay_written` | Common Test flag, then related method combinations |
| child lookup/FK join | `idx_research_requirements_admission` | parent logical key |
| future application-date range | `idx_admission_search_dates_range` | source field + start/end date |

This covers every requested dimension either as a leading key or within a
narrow low-cardinality covering index. SQLite can sometimes use skip-scan for a
later index column, but it needs statistics from `ANALYZE`; without statistics,
that behavior must not be assumed. See the official
[SQLite optimizer overview](https://www.sqlite.org/optoverview.html#the_skip_scan_optimization).

The builder must run `ANALYZE` only after the complete load, then verify planned
representative queries with `EXPLAIN QUERY PLAN`. If real query telemetry later
shows repeated standalone filtering on a non-leading method flag, the next
schema revision may add a small partial index such as `WHERE selection_oral_exam
= 'Yes'`. v0.1 does not pre-create one index per low-cardinality flag.

Raw `application_start`, `application_end`, and period strings are not given a
chronological B-tree index. Equality indexing raw prose would not implement date
search and could encourage incorrect range comparisons.

## 8. Full-text search

### 8.1 Environment probe

In-memory capability checks produced the following results on the current host:

| Runtime | SQLite version | FTS5 | `trigram` |
|---|---:|---|---|
| Python `sqlite3` used by the future builder | 3.53.0 | available | available |
| `/usr/bin/sqlite3` | 3.51.0 | available | available |

The Python build has no `ENABLE_ICU` compile option. `unicode61`, `ascii`,
`porter`, and `trigram` virtual tables could all be created, but only `trigram`
matched Japanese substrings in the bounded probe:

| Query against `東京都立大学 総合型選抜 理工学部` | `unicode61` | `trigram` |
|---|---:|---:|
| `東京都立大学` | match | match |
| `都立大` | no match | match |
| `総合型` | no match | match |
| `理工` | no match | no match |

The last result is expected: trigram full-text queries require at least three
Unicode characters. SQLite documents trigram substring behavior, short-query
limits, external-content tables, triggers, and integrity checks in the official
[FTS5 documentation](https://www.sqlite.org/fts5.html).

### 8.2 Recommended profile

The schema therefore defines an external-content `admissions_fts` table using
`tokenize='trigram'`. It indexes the 20 requested descriptive fields and uses
`admission_rowid` to join back to `admissions`. The base table remains the only
copy of source text; the FTS object stores the search index.

Insert/update/delete triggers keep the external-content index aligned with the
base table. A full builder still loads into a new database and validates the
external-content index before publication.

Example query shape:

```sql
SELECT a.*, bm25(admissions_fts) AS rank
FROM admissions_fts
JOIN admissions AS a ON a.admission_rowid = admissions_fts.rowid
WHERE admissions_fts MATCH :fts_query
ORDER BY rank, a.university, a.record_id;
```

Application code must bind parameters and treat FTS query syntax separately
from literal text. Result ranking is a UI/search policy and is not an admission
fact.

### 8.3 Portable fallback

Before applying the optional FTS block, a future builder must probe the same
SQLite library that will create the database:

1. **FTS5 + trigram available:** use the schema's recommended profile.
2. **FTS5 available, trigram unavailable:** use `unicode61`, record that choice,
   and use escaped `LIKE` for Japanese substring search. `unicode61` alone is
   not presented as equivalent Japanese substring search.
3. **FTS5 unavailable:** omit the marked optional FTS table/triggers, record
   `fts5_enabled=0` and `fts_tokenizer='none'`, and use escaped `LIKE` over an
   explicitly bounded field set.

For queries shorter than three Unicode characters, including `理工`, use a
parameterized `LIKE` fallback even under the trigram profile. Literal `%`, `_`,
and the chosen escape character must be escaped. At the current 5,921-row scale,
this bounded fallback is preferable to adding an unapproved external Japanese
morphological tokenizer.

ResearchRequirements child text is not included in FTS v0.1. A future revision
must choose explicitly between a separate child-level FTS table and a clearly
identified per-admission aggregate. It must not deduplicate child text silently.

## 9. Null, Unknown, No, and boolean semantics

| Unified meaning | SQLite value | Search predicate example |
|---|---|---|
| blank/not applicable | `NULL` | `field IS NULL` |
| explicit unknown tri-state | text `'Unknown'` | `field = 'Unknown'` |
| affirmative negative | text `'No'` | `field = 'No'` |
| boolean false | integer `0` | `stem_flag = 0` |
| boolean true | integer `1` | `stem_flag = 1` |

Only `stem_flag` and `fallback_previous_year` use SQLite boolean integers.
`common_test_required` and `selection_common_test` remain separate columns and
are never synchronized. An absent child row is not converted into `No`.

The loader must reject an empty string in a required field and convert an empty
CSV cell in a nullable field to SQL `NULL`. It must preserve whitespace-padded
nonblank strings exactly; validation findings are not a license to trim them.

## 10. Provenance

The following provenance remains in `admissions` without rewriting:

- `source_dataset`, `source_version`, and `record_id`;
- `source_url`, `schedule_url`, and `guideline_url`;
- `exclusive_enrollment_evidence_url` and its evidence/page fields;
- `verified_on`, source status, fallback fields, previous-year source URL,
  notes, and other unified source fields.

Research child and Coverage provenance remains in their own tables. Views alias
child/coverage fields rather than selecting one source URL over another. The
database-level metadata additionally identifies exact unified input files.

## 11. Build and validation contract

The builder executes these phases against a temporary path:

1. Run the existing unified/source validation gates.
2. Verify the unified CSV SHA-256 values and row counts against
   `build_manifest.json`; fail closed on a mismatch.
3. Probe SQLite version, `STRICT`, FTS5, and tokenizer capability in memory.
4. Create a new database, enable `PRAGMA foreign_keys=ON`, and apply the selected
   schema profile.
5. Load CSV rows in deterministic order inside a transaction, applying only the
   type mapping in section 4.
6. Insert one `build_metadata` row.
7. Run all validations below; roll back and publish nothing on failure.
8. Run `ANALYZE`, re-check representative query plans, and use
   `PRAGMA optimize` as appropriate.
9. Use a single-file journal mode for distribution and ensure no `-wal` or
   `-shm` sidecars remain.
10. Atomically replace the published database only after every gate passes.

Mandatory validation includes:

- base-table counts equal current unified CSV input counts;
- Master logical key uniqueness;
- Coverage logical key uniqueness;
- ResearchRequirements composite FK resolution;
- Coverage `master_rows` equals joined admissions counts;
- exact source pair and institution-type constraints;
- null/boolean/tri-state type and value checks;
- exact duplicate child multiplicity equals the input multiset;
- raw/copy field equality and provenance equality against CSV inputs;
- `COUNT(*)` from `admissions_search` equals `admissions`;
- `admissions_with_research` satisfies the dynamic left-join count formula;
- GPA parent rows equal admissions rows and preserve exact raw/null values;
- only `parsed_safe` rows have numeric bounds, conditional groups/clauses stay
  empty, and approved boundary-query counts match parser output;
- `PRAGMA foreign_key_check` returns no rows;
- `PRAGMA quick_check` returns `ok`;
- when FTS is enabled,
  `INSERT INTO admissions_fts(admissions_fts, rank)
  VALUES('integrity-check', 1)` succeeds and representative Japanese searches
  resolve to the expected admission rowids;
- build metadata hashes/counts match the database contents.

The generated database is logically reproducible from the same inputs, schema,
builder, and capability profile. Byte-identical SQLite files are not promised
in v0.1 because the build timestamp, SQLite library version, page layout, and
maintenance operations are recorded or environment-dependent.

## 12. Distribution and access

- Publish one closed SQLite file, never a live database accompanied by WAL/SHM
  files.
- Treat distributed copies as read-only.
- Consumers that might write must enable `PRAGMA foreign_keys=ON` per connection;
  foreign-key enforcement is a connection setting.
- Google Drive is a distribution/storage channel, not a concurrent SQLite
  query service. A consumer should download or copy a completed artifact before
  opening it.
- ChatGPT Sites or another service should use parameterized queries and a
  read-only connection. Structured filters and FTS ranking remain application
  policy, not source-data corrections.

## 13. Open decisions before implementation

1. Approve a normalized-date parser contract before populating
   `admission_search_dates`; v0.1 leaves it empty.
2. Benchmark representative Sites queries after loading and `ANALYZE`. Add
   per-flag partial indexes only when query plans or latency justify them.
3. Decide whether ResearchRequirements needs child-level FTS or a documented
   admission aggregate in a later schema version.
4. Confirm the SQLite/FTS capability of the final hosting runtime. The current
   local host supports trigram, but that does not prove every deployment does.
5. Define the external API's FTS query escaping, two-character fallback fields,
   ranking weights, pagination, and result-limit policy.
6. Decide whether a future release requires byte-level deterministic SQLite
   files in addition to logical reproducibility.

## 14. Academic-field exact-crosswalk extension v0.1

The production academic-field derived layer is defined by
`docs/academic_field_search_design_v0_1.md`,
`docs/academic_field_mapping_freeze_v0_1.md`, and
`schema/sqlite/admission_search_academic_field_schema_v0_1.sql`.

The builder loads one `admission_search_academic_fields` parent per admission
and zero or more `admission_search_academic_field_groups` children. Group codes
reference `academic_field_taxonomy`. Only an exact frozen raw-value lookup may
create group rows. Unknown non-NULL values are `unmapped`; NULL is
`not_applicable`; both have zero children. This extension preserves the base
`admissions.academic_field` value exactly.

Build metadata records mapping/taxonomy versions, schema/taxonomy/crosswalk
SHA-256 values, status counts, group-row count, and raw-mismatch count. These
artifacts participate in the unchanged-input gate before atomic publication.
