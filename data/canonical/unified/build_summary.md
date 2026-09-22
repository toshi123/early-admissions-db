# Unified dataset v0.1 build summary

- Build status: `passed`
- Contract/schema version: `0.1`
- Canonical source mode: read-only
- Determinism: two builds were byte-identical
- Serialization: UTF-8, LF, no BOM

## Source versions

| Dataset | Version |
|---|---|
| kokkoritsu | `5.81` |
| shidai | `1.08` |

## Output tables

| Table | Rows | Bytes | SHA-256 |
|---|---:|---:|---|
| master | 6411 | 12001153 | `2af3a834bb00fd93235f711c0f50896c4158b633d550d333b1aad9667bf5985e` |
| coverage | 260 | 150535 | `4457e7cddb9b9bde8a5aa414dcbadeda9ac6d05ed45ef0794354b2883c837e2b` |
| research_requirements | 495 | 234228 | `0aae717876bef3c1ba8645fcbf7e15190ce9bc8521badb83d5f154b6e3782fd9` |

## Validation gates

- Source canonical validator: errors=0, warnings=1167, informational=3292
- Unified JSON Schema validation: passed
- Unified Master PK / ResearchRequirements FK / Coverage: passed
- Source-to-output row preservation: passed
- Source provenance preservation: passed
- Raw/copy source value preservation: passed
- ResearchRequirements duplicate preservation: passed
- Source immutability check during build: passed

## Scope boundary

This build generated only the three unified CSV tables, this manifest, and this summary. It did not generate SQLite, a JSON search index, Excel, or Site artifacts.
