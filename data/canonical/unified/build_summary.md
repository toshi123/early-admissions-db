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
| master | 6511 | 12349762 | `0fdaef0ea27932da7d064538a28f64d590b266ae7843baa405bd5dbe89d2c380` |
| coverage | 260 | 150508 | `09cf0fb9a7a0ee4180fc87b69222d41bf82b9df259be64a1a257a4be5b7d39fc` |
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
