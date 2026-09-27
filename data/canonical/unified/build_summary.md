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
| master | 6569 | 12496688 | `0f527b664ee45351e48fa1982e83cda820003b1394221cb81f5a9d05e9bf1d90` |
| coverage | 260 | 150295 | `d6b4c5444844af2097366ae3f3690035df07d264f8b721fabe43d6a937add58c` |
| research_requirements | 495 | 234228 | `f39fd7e58451350f2cc39aca8bf25567dbc951a103f7fea256890ab0434bcdb0` |

## Validation gates

- Source canonical validator: errors=0, warnings=1167, informational=3472
- Unified JSON Schema validation: passed
- Unified Master PK / ResearchRequirements FK / Coverage: passed
- Source-to-output row preservation: passed
- Source provenance preservation: passed
- Raw/copy source value preservation: passed
- ResearchRequirements duplicate preservation: passed
- Source immutability check during build: passed

## Scope boundary

This build generated only the three unified CSV tables, this manifest, and this summary. It did not generate SQLite, a JSON search index, Excel, or Site artifacts.
