# Early Admissions static Site-data projection contract v0.1

## 1. Status and authority

This document freezes Site-data schema version `0.1`. The projection is a
read-only, reproducible derivative of the validated SQLite database. It does
not reinterpret admission facts and is not a Site UI or an eligibility engine.

Authority remains, in order, the unified contract, the GPA and academic-field
derived-layer contracts, the SQLite design/schema, and then this delivery
contract. The machine-readable Site schemas are:

- `schema/site/site_data_manifest_schema_v0_1.json`
- `schema/site/site_search_row_schema_v0_1.json`
- `schema/site/site_detail_schema_v0_1.json`
- `schema/site/site_filter_options_schema_v0_1.json`

The builder is `src/early_admissions/site_data_builder.py`; the independent
static search implementation is `src/early_admissions/site_search.py`.

## 2. Input and read-only boundary

The only factual input is
`data/derived/sqlite/early_admissions_2027.sqlite`, accompanied by its SQLite
build manifest. Before projection the builder verifies the database byte size
and SHA-256 against that manifest and verifies the SQLite schema, unified, GPA,
academic-field mapping, and taxonomy versions against `build_metadata`.

SQLite is opened with URI `mode=ro&immutable=1` and `PRAGMA query_only=ON`.
Its SHA-256 is checked again before publication. Canonical, release, unified,
and SQLite inputs are never written.

## 3. Published directory

```text
data/derived/site/v0_1/
  build_manifest.json
  assets/<build_id>/
    filter_options.json
    search/search_rows-NNN.json
    details/details-NNN.json
```

`build_id` is the first 20 hex characters of SHA-256 over canonical JSON that
contains the SQLite SHA-256, Site-data schema and builder versions, GPA parser
version, and academic-field mapping/taxonomy versions. Every asset repeats the
build ID. A runtime reads the manifest first and must not mix assets with a
different build ID.

The builder writes a new sibling temporary directory, completes every
validation, and only then replaces the publication directory. On a failed
build, the prior published directory is retained. No stale files from an older
build are copied into the new directory.

## 4. JSON serialization

- Encoding is UTF-8 without BOM, LF-terminated, compact deterministic JSON.
- Object keys are sorted; shard rows have deterministic logical-key order.
- SQL `NULL` becomes JSON `null`.
- `Unknown`, `No`, `Yes`, and `Conditional` remain distinct strings.
- Only SQLite `stem_flag` and `fallback_previous_year` are converted from
  `0`/`1`/`NULL` to JSON `false`/`true`/`null` in admissions data.
- GPA and other derived boolean flags likewise round-trip explicitly as JSON
  boolean/null; GPA comparison bounds remain integer tenths.
- Raw text, dates, periods, URLs, notes, and source wording are copied without
  trimming, normalization, parsing, or rewriting.

## 5. Search-row contract

There is exactly one search row per admission logical key. It contains:

- identity: `source_dataset`, `source_version`, `record_id`;
- display/filter fields: `institution_type`, `university`, `prefecture`,
  `faculty_school`, `department`, `selection_category`, `selection_name`,
  `slot_type`, `capacity`, raw `academic_field`, and `stem_flag`;
- academic-field derived data: mapping status, stable group-code array, and
  mapping-contract version;
- application fields: exclusive-enrollment status, recommendation, academic
  record, Common Test requirement, research requirement, and research-activity
  level status;
- six selection-method fields, keeping `common_test_required` and
  `selection_common_test` separate;
- raw GPA plus SQLite-derived parse status, search disposition, lower/upper
  integer-tenths bounds and inclusivity, and source-value status;
- raw `application_start` / `application_end`;
- fallback disclosure fields: `fallback_previous_year`, `information_year`,
  and `publication_status`;
- deterministic `detail_path`.

Long selection/research detail, provenance text, notes, and child rows are not
duplicated in search rows.

## 6. Detail contract

There is exactly one detail record per admission logical key. It contains:

```text
identity
admission                  # every admissions column, including technical rowid
gpa_derived                # every admission_search_gpa column
academic_field_derived     # parent plus every ordered group row
research_requirements[]    # every linked child row in research_rowid order
```

All source/unified admission fields and provenance are retained. Technical
rowids are included only to preserve storage identity and ordering; the public
durable identity remains `(source_dataset, source_version, record_id)`.
ResearchRequirements rows are never deduplicated. Exact duplicate multiplicity
and denormalized child fields remain intact.

## 7. Filter options

`filter_options.json` is generated from the same SQLite snapshot. Each option
has exact `value`, `display_label`, and `unfiltered_count`; SQL NULL is a
separate `value: null` option. It contains universities, institution types,
prefectures, raw academic fields, mapping statuses, selection categories,
application-condition enums, research status, and each selection-method
tri-state vocabulary.

Academic-field group codes, Japanese labels, descriptions, and display order
come from the approved SQLite taxonomy. No admission option value is
hard-coded or inferred.

## 8. Sharding decision

A bounded 512-row sample measured approximately 1.42 KB per search row and
5.06 KB per detail record. Extrapolated current totals were about 8.4 MB search
JSON (0.27 MB gzip) and 30.0 MB detail JSON (1.19 MB gzip).

One search file would minimize requests but require one large parse and provide
poor cache granularity. One detail file per admission would provide ideal lazy
loading but create roughly 5,921 deployment files. The selected middle ground
is deterministic grouped sharding:

- search target: 1,250,000 uncompressed bytes per shard;
- detail target: 256,000 uncompressed bytes per shard;
- shard count: next power of two above measured total serialized record bytes
  divided by the target;
- assignment: SHA-256 of canonical logical-key JSON modulo shard count.

This produces stable paths for identical input, balanced shards, a small file
count, independently cacheable detail loads, and no page-number coupling. The
current exact counts and sizes are recorded in the build manifest and QA
report rather than hard-coded here.

## 9. Static search semantics

`SearchRequest -> SearchResultPage` is a pure in-memory interface independent
of a browser framework. It implements:

- OR within one field and AND between different fields;
- exact matching only for raw/categorical values;
- academic group membership OR, while raw academic field remains a separate
  ANDed field;
- `stem_flag=true/false` without treating null as false;
- GPA `safe`, `review`, and `all` modes exclusively from SQLite-derived fields;
- no raw GPA parsing, date parsing, free-text/FTS, or conditional-rule
  evaluation.

`safe match` means only “overall GPA condition safely matched.” It never means
application eligibility. Default ordering follows the Site requirements:
prefecture, university, faculty/school, department, selection category,
selection name, then logical key. Because the existing CLI orders university
first, the equivalence gate compares complete logical-key sets and summaries,
not presentation ordering.

## 10. Validation and reproducibility

Publication requires all of the following:

1. SQLite manifest SHA/size/version and metadata agreement.
2. JSON Schema validation of every search row, detail record, filter file, and
   final manifest.
3. One unique search row and one unique detail record per SQLite admission.
4. Search/detail/admission logical-key set equality and complete detail routes.
5. Exact equality for projected raw, date/period, GPA raw, academic-field raw,
   URL, notes, and provenance values.
6. SQL NULL, boolean, tri-state, GPA integer-tenths, fallback, and
   review-required preservation.
7. ResearchRequirements row-order and exact-multiset preservation.
8. Every artifact's SHA-256, byte size, and record count.
9. The frozen 25-query suite: complete logical-key set, total count, source
   counts, university count, and GPA status-count equality with SQLite.
10. Dynamic GPA and academic-field regressions derived from the SQLite input.
11. Input SQLite SHA-256 unchanged after the build.

The timestamp is execution metadata. With it removed, two builds from identical
inputs must have identical manifest content, file lists, asset bytes, and
hashes. The manifest does not hash itself; it receipts every other Site-data
asset. The externally reported manifest SHA-256 identifies the complete
publication receipt.

## 11. Scope boundary

This contract does not implement a Site UI, frontend framework, deployment,
API/D1 service, natural-language or FTS core search, conditional GPA evaluator,
normalized dates, parsed capacity, ResearchRequirements reclassification,
accounts, favorites, or saved searches.
