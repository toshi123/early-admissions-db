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
| master | 6699 | 12915529 | `e79f59a5acf1a0883a3b16fe09daa0a18ee92c62817b6c44c5941e1acb2fa24b` |
| coverage | 260 | 157304 | `bf48c8f2eee3baab7eba3223f899187ccd0383ab7ae59519b3888263c26a2904` |
| research_requirements | 495 | 234228 | `f39fd7e58451350f2cc39aca8bf25567dbc951a103f7fea256890ab0434bcdb0` |

## Validation gates

- Source canonical validator: errors=0, warnings=1238, informational=3552
- Unified JSON Schema validation: passed
- Unified Master PK / ResearchRequirements FK / Coverage: passed
- Source-to-output row preservation: passed
- Source provenance preservation: passed
- Raw/copy source value preservation: passed
- ResearchRequirements duplicate preservation: passed
- Source immutability check during build: passed

## Scope boundary

This build generated only the three unified CSV tables, this manifest, and this summary. It did not generate SQLite, a JSON search index, Excel, or Site artifacts.
