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
| master | 6553 | 12460004 | `add5dbf7b650296980ee1718eb004279c85786ae86164e8aa45fce7f197e9468` |
| coverage | 260 | 150363 | `ec1fbe59ad1218401b8a4ca4b65f381c50c45ffb0b48322a36a688ba1b1f2254` |
| research_requirements | 495 | 234228 | `f39fd7e58451350f2cc39aca8bf25567dbc951a103f7fea256890ab0434bcdb0` |

## Validation gates

- Source canonical validator: errors=0, warnings=1167, informational=3464
- Unified JSON Schema validation: passed
- Unified Master PK / ResearchRequirements FK / Coverage: passed
- Source-to-output row preservation: passed
- Source provenance preservation: passed
- Raw/copy source value preservation: passed
- ResearchRequirements duplicate preservation: passed
- Source immutability check during build: passed

## Scope boundary

This build generated only the three unified CSV tables, this manifest, and this summary. It did not generate SQLite, a JSON search index, Excel, or Site artifacts.
