# Academic-field v0.2 Site integration design

Version: 0.2
Status: implementation contract
Authority: frozen academic-field v0.2 CSVs and the validated SQLite v0.2 layer

## Site-data schema decision

The current frontend requires new membership arrays and taxonomy options, so
this is a breaking static-data contract change. Site-data is therefore bumped
from `0.1` to `0.2` and published under `data/derived/site/v0_2/`. The v0.1
schemas and generated directory remain separate; assets from the two versions
must never be mixed.

Each search row adds the v0.2 broad/subcategory mapping statuses, stable-code
membership arrays, mapping-contract version, and taxonomy version. Each detail
record adds the complete v0.2 derived parent plus ordered broad and
subcategory membership rows. Raw `academic_field` remains unchanged.

`filter_options.json` retains all 30 Broad and all 89 Subcategory taxonomy
rows. Broad options contain code, Japanese label, UI section, section-local
display order, and unfiltered count. Subcategory options contain code, label,
parent code, display order, frozen `ui_status`, and unfiltered count. Labels,
order, parent relations, and visibility metadata are never hard-coded in the
frontend.

The manifest copies the SQLite academic-field v0.2 authority receipt,
including all five frozen-input SHA-256 values, taxonomy/status/membership
counts, review/unmapped counts, and validation status. It also records the
input SQLite and SQLite-manifest SHA-256 values.

## Search request and branch semantics

The pure Site search request uses:

```text
academic_field_v2_branches = [
  {group_code, subcategory_codes[]},
  ...
]
```

One branch matches the Broad membership and, when children are selected, at
least one selected child membership. Branches are ORed. Other filters are
ANDed. Therefore:

```text
(natural_sciences AND (mathematics_statistics OR physics))
OR engineering
```

is represented by a constrained `natural_sciences` branch and an unconstrained
`engineering` branch. The frontend does not flatten this to independent Broad
and Subcategory lists.

Legacy v0.1 `academic_field_group` remains supported. When both versions are
present, the v0.1 predicate and the complete v0.2 branch predicate are ANDed.

## URL contract

- Broad: repeated `academic_field_v2=<group_code>`
- Subcategory: repeated
  `academic_subfield_v2=<parent_group_code>:<subcategory_code>`

A Subcategory is valid only when its exact parent Broad appears in the same
URL. Unknown codes, parent mismatches, and orphan children are ignored with a
visible invalid-query notice; a missing parent is never synthesized.
Duplicates are removed. Canonical URLs follow Broad taxonomy order and then
the Subcategory order within each parent. Page and scroll state are not part
of the remembered search query.

Legacy v0.1 URL parameters retain their original meaning and are not converted
to v0.2. Because the normal form no longer shows the v0.1 selector, an active
legacy filter is shown explicitly in the form and result summary. Header
search-state memory includes both v0.1 and v0.2 canonical parameters.

## Search UI

The normal form shows the 30 Broad options grouped by the four frozen UI
sections. Selecting a Broad reveals only its child options near that Broad.
The child area uses visible indentation, a border, and a subtle background so
the parent relation is understandable without color.

All 89 Subcategory rows remain in Site-data. The general UI hides a child when
its unfiltered count is zero or its frozen `ui_status` is `hidden`; this is a
presentation rule, not taxonomy deletion. A later data build can reveal an
eligible child without code changes. Unchecking a Broad immediately clears
all selected children for that Broad so no latent filter remains.

Broad/subcategory changes use the same pure search function as submitted
results, the normal live count, and the floating live count. Review-required
admissions have no safe v0.2 memberships and are not included by normal v0.2
checkbox searches; raw academic-field text remains available in detail data.

## Validation

The build validates schemas, logical-key completeness, raw equality, v0.2
membership equality, 30/89 taxonomy retention, artifact receipts, and atomic
publication. It compares Site-data and SQLite logical-key sets for frozen
Broad/Subcategory examples, five combined queries, and the frozen 1,796-row
branch query. The latter must also equal
`validation/reports/academic_field_v0_2_branch_logical_keys.tsv`.

Two independent builds from identical SQLite/schema/freeze inputs must produce
byte-identical assets and identical manifests after removal of execution time.
Client-side scanning remains the search architecture for 5,921 rows unless
measured performance demonstrates a regression that needs a smaller change.

## Current-snapshot performance

Local measurements use the validated 5,921-row projection and a warm localhost
development server. They are regression indicators, not production-network or
low-end-device guarantees.

| Metric | Site-data v0.1 | Site-data v0.2 |
|---|---:|---:|
| Search projection, uncompressed JSON | 12,254,865 bytes | 14,210,412 bytes |
| Search projection, gzip | 693,228 bytes | 797,884 bytes |
| Filter options, uncompressed JSON | 79,758 bytes | 99,955 bytes |
| Detail projection, uncompressed JSON | 33,520,791 bytes | 37,822,700 bytes |
| Detail projection, gzip equivalent | 4,455,174 bytes | 4,867,844 bytes |

The search projection increase is 1,955,547 uncompressed bytes (15.96%) and
104,656 gzip bytes (15.10%). A local Node/V8 warm-parse benchmark across all
16 v0.2 search shards had a median of 25.5 ms. The same runtime measured the
pure search function at 29.3 ms for an unfiltered first search, 4.5 ms for a
Broad filter, 2.2 ms for a Subcategory filter, and 9.8 ms for the frozen
two-branch query.

Browser readiness from navigation to the visible initial count was 253 ms at
1440x900 and 177 ms at 390x844. The computer-use interaction envelope was
880/631 ms for the first Broad update, 417/419 ms for the first Subcategory
update, and 3,100/3,114 ms until the submitted results route was visible
(desktop/mobile). Those interaction figures include automation action-settling
overhead and are upper bounds, not pure application compute time. The pure
search timings do not justify replacing the existing client-side scan.

The current production bundle is 63,615 bytes of main JavaScript (19,899 gzip)
and 17,075 bytes of CSS (4,183 gzip). The XLSX exporter remains a separate lazy
chunk and is not part of initial search parsing.
