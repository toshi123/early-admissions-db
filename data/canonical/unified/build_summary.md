# Unified dataset v0.1 build summary

- Build status: `passed`
- Contract/schema version: `0.2`
- Canonical source mode: read-only
- Determinism: two builds were byte-identical
- Serialization: UTF-8, LF, no BOM

## Source versions

| Dataset | Version |
|---|---|
| kokkoritsu | `5.82` |
| shidai | `1.09` |

## Output tables

| Table | Rows | Bytes | SHA-256 |
|---|---:|---:|---|
| master | 6526 | 12376984 | `17d0e155257fa6ffc6f354a68aac74d3212f423a3ea2d8e898a91178485b006c` |
| coverage | 260 | 150388 | `5e45e4fe7e32dcb6120eb28606cee0296cd814c060cfb7b22af9e1346aeb38d4` |
| research_requirements | 495 | 234228 | `4187d01258c83e035fc49fc29238980481bf652d29031077e1a2c1733791a6ba` |

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
