# Unified dataset v0.1 build summary

- Build status: `passed`
- Contract/schema version: `0.1`
- Canonical source mode: read-only
- Determinism: two builds were byte-identical
- Serialization: UTF-8, LF, no BOM

## Source versions

| Dataset | Version |
|---|---|
| kokkoritsu | `5.61` |
| shidai | `0.97` |

## Output tables

| Table | Rows | Bytes | SHA-256 |
|---|---:|---:|---|
| master | 5921 | 10874313 | `1df386ed99532a3dff381507978a1454d7c20113574285b2526f6ae122050279` |
| coverage | 259 | 147685 | `b10ca3381afb0f3e8740ed2d14ddf086233151d4c6eba6e946344b12638913fb` |
| research_requirements | 437 | 208432 | `ba105cca34c03fee34fb7d04ce1d0818caa386d0832e7999bf9ec9bf9f135919` |

## Validation gates

- Source canonical validator: errors=0, warnings=686, informational=3136
- Unified JSON Schema validation: passed
- Unified Master PK / ResearchRequirements FK / Coverage: passed
- Source-to-output row preservation: passed
- Source provenance preservation: passed
- Raw/copy source value preservation: passed
- ResearchRequirements duplicate preservation: passed
- Source immutability check during build: passed

## Scope boundary

This build generated only the three unified CSV tables, this manifest, and this summary. It did not generate SQLite, a JSON search index, Excel, or Site artifacts.
