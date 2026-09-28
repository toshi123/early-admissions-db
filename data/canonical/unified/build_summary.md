# Unified dataset v0.1 build summary

- Build status: `passed`
- Contract/schema version: `0.3`
- Canonical source mode: read-only
- Determinism: two builds were byte-identical
- Serialization: UTF-8, LF, no BOM

## Source versions

| Dataset | Version |
|---|---|
| kokkoritsu | `5.83` |
| shidai | `1.10` |

## Output tables

| Table | Rows | Bytes | SHA-256 |
|---|---:|---:|---|
| master | 6588 | 12548995 | `37aee98825f626cef294b5bd44ed60c885b102ed18cbd09fc25fcb6665970ca1` |
| coverage | 260 | 150692 | `a4d9c3ccdc6541150293cf075e8b360a7c585d789a3ce46e3e1b4cf999a2389e` |
| research_requirements | 495 | 234228 | `f39fd7e58451350f2cc39aca8bf25567dbc951a103f7fea256890ab0434bcdb0` |

## Validation gates

- Source canonical validator: errors=0, warnings=1183, informational=3472
- Unified JSON Schema validation: passed
- Unified Master PK / ResearchRequirements FK / Coverage: passed
- Source-to-output row preservation: passed
- Source provenance preservation: passed
- Raw/copy source value preservation: passed
- ResearchRequirements duplicate preservation: passed
- Source immutability check during build: passed

## Scope boundary

This build generated only the three unified CSV tables, this manifest, and this summary. It did not generate SQLite, a JSON search index, Excel, or Site artifacts.
