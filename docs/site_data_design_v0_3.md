# Site data v0.3

Site data v0.3 consumes SQLite schema v0.2 and Unified contract v0.3. The v0.2 Site schemas and artifacts remain available unchanged.

The detail record's `admission` object contains all 84 Unified Master fields plus `admission_rowid`. The five special-selection flags are required booleans and retain the Unified `true`/`false` values. Search rows remain a selected search projection and do not expose these flags as filters; detail records preserve them without adding search behavior.

Manifest, filter-options, and detail schemas have v0.3 identifiers. The search-row schema remains v0.2 because the selected search fields and their constraints are unchanged. The builder validates the SQLite schema and Unified contract versions before projection and verifies the generated assets before atomic publication.
