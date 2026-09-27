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
| master | 6585 | 12540190 | `85f42bec7b1f2a19e8ce319c0335308dd1759654eb2bdff340b21486269c3af8` |
| coverage | 260 | 150562 | `cbbda71b0bc62e53ba53a069ff665c4ed8a63793e03fc4cee7a2fec07db18a92` |
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
