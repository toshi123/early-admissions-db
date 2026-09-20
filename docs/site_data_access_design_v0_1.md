# SQLite-to-Site data access design v0.1

## 1. Decision summary

For Site v0.1, generate a deterministic, read-only Site-data projection from
the validated SQLite artifact at build time and serve it as static assets.
SQLite remains the derived-data authority and the existing structured-search
CLI remains the semantic oracle; the static projection changes only the Site
delivery mechanism.

Do not make the initial search depend on:

- opening the repository SQLite file inside the browser;
- a native SQLite/FTS extension in the hosting runtime;
- a separately operated API;
- durable database state.

This is a design decision only. No Site data, JSON index, framework, package,
or deployment is created in this phase.

## 2. Current platform evidence

The official OpenAI Sites documentation was checked on 2026-09-20. It states
that Sites is in public beta, supports hosted web experiences, offers D1 for
durable relational data and R2 for files, and does not support every framework,
database, background service, or hosting pattern. It also separates saving a
reviewable version from deploying it to production.

Source: [OpenAI Sites documentation](https://developers.openai.com/en-US/docs/sites).

The documentation does not establish that an arbitrary repository SQLite file
or its FTS5/trigram extensions can be opened natively in every Sites runtime.
The architecture therefore treats direct SQLite support as unconfirmed and
avoids making it a v0.1 dependency.

The current local artifact is 26,648,576 bytes and its build manifest records
SQLite 3.53.0 with FTS5/trigram enabled. That is a verified property of the
build environment and artifact, not evidence that the same extensions exist in
the hosted Sites runtime.

## 3. Options compared

| Criterion | Direct SQLite query | Build-time static Site data | API over SQLite |
|---|---|---|---|
| Initial implementation | Runtime-specific; native or WASM SQLite must be proven | Simple static read path | Requires server routes and query contract |
| Read-only safety | Good only if immutable access is enforced | Strong by construction; no write endpoint | Must enforce read-only DB and API methods |
| Repository fit | Uses current DB directly | Reproducible derived artifact with manifest | Adds an application service layer |
| Update flow | Replace DB and verify runtime compatibility | Rebuild projection from new validated DB | Replace DB/redeploy service or migrate storage |
| 5,921-row performance | Likely adequate, but startup/DB download may dominate | Adequate with small search projection and lazy details | Adequate; network latency per query |
| Static deployment | Browser requires SQLite/WASM or full DB download | Native fit | No |
| Hosting dependency | High | Low | High |
| FTS5/trigram | Depends on exact SQLite build | Not needed for structured v0.1 | Can preserve server SQLite capability |
| Future natural language | Requires a separate service later | Add API later behind stable response contract | Best long-term fit, but premature now |
| Operational burden | Medium | Low | Highest |

### 3.1 Direct SQLite

Advantages:

- one derived artifact remains the query authority;
- existing indexes, views, and GPA layer can be reused;
- server-side read-only queries would be expressive.

Risks:

- native SQLite and FTS5/trigram availability is runtime-specific;
- browser execution generally requires a SQLite/WASM integration and download
  of the database artifact;
- the current database is about 26.6 MB before transport compression;
- the full database contains detail/FTS content unnecessary for initial filter
  rendering;
- direct access couples the Site to SQLite schema details.

Conclusion: retain as a local development/reference-query option, not the Site
v0.1 production dependency.

### 3.2 Build-time static Site data

Advantages:

- read-only by construction;
- deployable with ordinary static assets;
- no runtime SQL or FTS requirement;
- the search projection can omit long detail text from the initial payload;
- input hashes, row counts, and versions can be validated before publication;
- output is fully regenerated after each canonical update.

Risks:

- adds another derived artifact and manifest;
- client-side filters must be implemented carefully to match CLI semantics;
- payload/sharding choices need a measured budget;
- future full-text or natural-language search may require another layer.

Conclusion: recommended for v0.1.

### 3.3 API over SQLite

Advantages:

- keeps SQL and indexes on the server;
- sends only one result page to the browser;
- provides a natural boundary for future natural-language query planning;
- can centralize access control and request limits.

Risks:

- introduces server lifecycle, error handling, availability, and security work;
- query semantics must be duplicated in and tested through an API contract;
- unnecessary operational surface for 5,921 read-only rows and structured
  client-side filters;
- publishing becomes dependent on a supported server/database shape.

Conclusion: a future phase, not v0.1.

### 3.4 D1 import

OpenAI Sites documents D1 as its durable relational-data option. Importing the
current SQLite-derived data into D1 could be viable for a later server-backed
Site, but it adds a second database schema/migration and is not needed for
read-only snapshot search. It is not recommended for v0.1.

## 4. Proposed Site-data artifact contract

Names are provisional; the implementation phase should freeze them in a
separate schema.

```text
data/derived/site/v0_1/
  build_manifest.json
  filter_options.json
  search_rows-000.json
  search_rows-001.json
  ...
  details/
    <source_dataset>/<source_version>/<record_id>.json
```

The projection has two layers.

### 4.1 Search rows

One compact row per admission containing only fields required for:

- every structured filter;
- deterministic ordering;
- result-card display;
- GPA state/match evaluation using integer tenths;
- academic-field group membership;
- fallback warning;
- detail route construction.

Long selection details, research summaries, notes, and provenance text remain
out of the initial search payload.

### 4.2 Detail rows

One record per logical admission key containing all SQLite admission fields,
all GPA derived fields, all academic-field derived fields, and all linked
ResearchRequirements rows. Child rows remain ordered and duplicate-preserved.

The Site may lazy-load a detail record only after navigation. A missing detail
file is a build/integrity error, not an empty admission.

### 4.3 Filter options

Options are generated from the same SQLite snapshot, not hard-coded. For each
filter value, the file may include a display label and unfiltered frequency.
The value used for matching remains the stored exact value or approved derived
code.

### 4.4 Serialization semantics

- SQL NULL becomes JSON `null`; it never becomes an empty string, `Unknown`, or
  `No`.
- `Yes`, `No`, `Unknown`, and `Conditional` remain distinct strings where
  allowed by the source contract.
- `stem_flag` and `fallback_previous_year` may become JSON booleans, with SQL
  NULL becoming JSON `null`; the mapping must be schema-declared and tested.
- GPA comparison values remain integer tenths.
- Raw text, dates, periods, and URLs are copied without trim or rewrite.
- Child-array order is deterministic, but ordering does not authorize
  deduplication.

## 5. Manifest contract

At minimum record:

- Site-data schema version;
- build-tool version;
- build timestamp;
- SQLite database schema version;
- unified contract version;
- GPA parser-contract version;
- academic-field mapping-contract version and crosswalk hash;
- source dataset versions;
- input SQLite path, SHA-256, and row counts;
- output file SHA-256 values and byte sizes;
- admission/detail/research row counts;
- special-state counts: NULL, Unknown, fallback, GPA dispositions, and
  academic-field mapping statuses;
- validation result and publication state.

The Site reads the manifest first and refuses to combine assets from different
build IDs.

## 6. Required projection validations

Before Site build or publication:

1. Verify SQLite SHA-256 against its build manifest.
2. Open SQLite read-only/immutable and verify schema/version metadata.
3. Confirm one search row and one detail record per admission logical key.
4. Confirm admission, coverage, and ResearchRequirements source counts.
5. Confirm all 437 current child rows are preserved, including exact
   duplicates; normal builds derive expected counts from input.
6. Confirm raw GPA, academic-field, date/period, and provenance text equality.
7. Confirm tri-state and NULL values remain distinct in serialization.
8. Confirm GPA strict-safe query regressions against SQLite results.
9. Confirm academic-field parent/child cardinality and unmapped counts.
10. Confirm deterministic sorting and byte-identical rebuild from identical
    inputs.
11. Confirm every output hash and count in the Site-data manifest.
12. Confirm no input artifact hash changed during the build.

## 7. Client-side structured-search behavior

The browser applies predicates only to fixed fields from the Site-data schema:

- OR within a filter's selected values;
- AND between filter fields;
- exact comparisons for source enums/text;
- existence membership for academic-field groups;
- integer-tenths comparison only for GPA `parsed_safe` rows;
- no parsing of raw dates or free text.

The query implementation must be tested against the existing CLI on the same
representative search suite. This makes the SQLite CLI the semantic oracle
without making production rendering depend on SQLite.

## 8. Payload and caching policy

- Measure the search projection before choosing shard count; do not hard-code a
  size estimate from the full CSV.
- Prefer a small number of cacheable, content-hashed search shards.
- Detail records are lazy-loaded and independently cacheable.
- The manifest and current build ID use revalidation/no-cache behavior so a
  new release does not mix with old long-lived assets.
- A Site version pins exactly one Site-data build ID.
- Offline caching, service workers, and client persistence are deferred until
  stale-version behavior is designed.

## 9. Update flow

```text
canonical update
  -> source validator
  -> unified rebuild + validation
  -> SQLite rebuild + validation
  -> academic-field crosswalk coverage check
  -> Site-data projection rebuild + validation
  -> Site application build/tests
  -> human content/privacy review
  -> save reviewable Sites version
  -> publish approved version
```

An updated canonical snapshot never patches the Site data in place. It creates
a complete new immutable build. Failed validation leaves the previously
published Site and artifacts untouched.

## 10. Future API migration path

The implementation should isolate search behind an internal typed interface:

```text
SearchRequest -> SearchResultPage
LogicalAdmissionKey -> AdmissionDetail
```

Site v0.1 can implement that interface with static assets. A later API can
implement the same response semantics without changing URL/filter meaning.
Natural-language search, if authorized later, should produce or suggest a
structured `SearchRequest`; it must not bypass GPA or null-semantics contracts.

## 11. Unresolved implementation decisions

- Exact Site-data JSON schema and shard count.
- Maximum initial compressed payload and target low-end device performance.
- Whether all 5,921 result summaries load once or are split by stable shards.
- Whether detail data uses one file per admission or grouped shards to avoid
  many small deployment files.
- The intended Sites audience and access policy.
- Whether a future hosted API should use Sites D1, a separately hosted service,
  or another platform.
- Whether future free-text search belongs client-side, in an API, or in a
  separately generated index.

These are implementation-phase choices. They do not change the v0.1
recommendation to keep structured search independent of runtime SQLite/FTS.
