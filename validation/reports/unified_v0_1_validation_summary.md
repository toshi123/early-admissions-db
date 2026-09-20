# Unified contract v0.1 validation summary

- Generated: `2026-09-20T08:24:30.153303+00:00`
- Status: `passed_with_findings`
- Mode: read-only; canonical and release data were not modified
- Contract version: `0.1`

## Severity totals

| Severity | Count |
|---|---:|
| error | 0 |
| warning | 686 |
| informational | 3136 |

## Dataset totals

| Dataset | Errors | Warnings | Informational | Total |
|---|---:|---:|---:|---:|
| kokkoritsu | 0 | 670 | 1341 | 2011 |
| shidai | 0 | 16 | 1795 | 1811 |

## Findings by code

| Code | Severity | Count | Dataset counts | Representative record IDs |
|---|---|---:|---|---|
| `COMMON_TEST_FIELDS_DIFFER` | informational | 108 | kokkoritsu=108 | OCHA-2027-AO-BIO, OCHA-2027-AO-CHEM, OCHA-2027-AO-CULTINFO, OCHA-2027-AO-HENV, OCHA-2027-AO-HOME |
| `COVERAGE_ZERO_MASTER_ROWS` | informational | 10 | kokkoritsu=8, shidai=2 | 国立:政策研究大学院大学, 国立:総合研究大学院大学, 国立:北陸先端科学技術大学院大学, 国立:奈良先端科学技術大学院大学, 公立:東京都立産業技術大学院大学 |
| `DATE_RAW_PARTIAL` | informational | 2948 | kokkoritsu=1194, shidai=1754 | HU-2027-F1-01, HU-2027-F1-02, HU-2027-F1-03, HU-2027-F1-04, HU-2027-F1-05 |
| `DATE_RAW_UNPARSED` | informational | 18 | kokkoritsu=15, shidai=3 | ST-2027-C-01, ST-2027-C-02, ST-2027-C-03, ST-2027-C-04, ST-2027-C-05 |
| `DETAIL_COMPLETENESS_UNMAPPED` | warning | 318 | kokkoritsu=318 | NWU-2027-PICASO-01, NWU-2027-PICASO-02, NWU-2027-PICASO-03, NWU-2027-PICASO-04, NWU-2027-PICASO-05 |
| `PROVENANCE_URL_MISSING` | warning | 19 | kokkoritsu=19 | TMU-2027-AO-01, TMU-2027-AO-02, TMU-2027-AO-03, TMU-2027-AO-04, TMU-2027-AO-05 |
| `RESEARCH_ACTIVITY_LEVEL_UNMAPPED` | warning | 281 | kokkoritsu=281 | HUE-2027-AO-SELF-01, HUE-2027-AO-SELF-02, HUE-2027-AO-SELF-03, AKITA-2027-AO1-EDU-REGCULT, YAM-2027-REC1-HSS-GLOBAL |
| `RESEARCH_DENORMALIZED_FIELD_MISMATCH` | warning | 8 | kokkoritsu=8 | OU-2027-C-06 |
| `RESEARCH_EXACT_DUPLICATE` | warning | 4 | shidai=4 | MU-2027-AO1-DS, MU-2027-AO1-SUS, MU-2027-AO1-MATH, MU-2027-AO1-ARCH |
| `RESEARCH_NOT_REQUIRED_WITH_CHILD` | informational | 52 | kokkoritsu=16, shidai=36 | FUKU-2027-AO-ENG-GEN, FUKU-2027-AO-ENG-W, HIT-2027-REC-COM, HIT-2027-REC-ECON, HIT-2027-REC-LAW |
| `RESEARCH_REQUIRED_WITHOUT_CHILD` | warning | 51 | kokkoritsu=39, shidai=12 | NWU-2027-PICASO-01, NWU-2027-PICASO-02, NWU-2027-PICASO-03, NWU-2027-PICASO-04, NWU-2027-PICASO-05 |
| `WHITESPACE_PADDING` | warning | 5 | kokkoritsu=5 | SPU-2027-REC-01, SPU-2027-REC-04, SPU-2027-REC-08, SPU-2027-REC-11, SPU-2027-REC-14 |

## Inputs

| Dataset | Table | Rows | Bytes | SHA-256 | Path |
|---|---|---:|---:|---|---|
| kokkoritsu | master | 3668 | 6005511 | `61b50442f6fa9dad6a9483b702d5d463f37c0b338c6c3154a31a33e8cb0dd2ff` | `data/canonical/kokkoritsu/master.csv` |
| kokkoritsu | coverage | 187 | 94624 | `a8db0a6d56ce92d80c1a8a4cb832fd0144de02727bdfe2bdf4b4b466cedeab07` | `data/canonical/kokkoritsu/coverage.csv` |
| kokkoritsu | research_requirements | 239 | 93314 | `9eb98576862a44fbd4535938bc70938a34faeafb051e41125ed055ee60be214f` | `data/canonical/kokkoritsu/research_requirements.csv` |
| shidai | master | 2253 | 4695215 | `bb40f2db7687f28475ac01b8118daf4565ef80de63f11dfda8e1ac322cd3294d` | `data/canonical/shidai/master.csv` |
| shidai | coverage | 72 | 49400 | `9e73c1cc2fea2830419d5ab7682d97baa7f6c5d191440fa06042714466c4bdbd` | `data/canonical/shidai/coverage.csv` |
| shidai | research_requirements | 198 | 109290 | `bb617567d26549a2798d29949afeff7cd0478c47f0fff46078a67dee938ebeaa` | `data/canonical/shidai/research_requirements.csv` |

## Crosswalk metrics

```json
{
  "crosswalks": {
    "kokkoritsu": {
      "detail_completeness_status": {
        "complete": 2544,
        "partial": 806,
        "unmapped": 318
      },
      "research_activity_level_status": {
        "none": 387,
        "null": 1328,
        "relevant": 104,
        "required": 90,
        "unknown": 1478,
        "unmapped": 281
      }
    },
    "shidai": {
      "detail_completeness_status": {
        "complete": 2137,
        "partial": 116
      },
      "research_activity_level_status": {
        "none": 1588,
        "relevant": 565,
        "required": 95,
        "unknown": 5
      }
    }
  },
  "row_counts": {
    "kokkoritsu": {
      "coverage": 187,
      "master": 3668,
      "research_requirements": 239
    },
    "shidai": {
      "coverage": 72,
      "master": 2253,
      "research_requirements": 198
    }
  }
}
```

## Boundary

This run validated source canonical data only. It did not generate unified CSV, SQLite, JSON/search data, Excel, or site artifacts, and it did not modify canonical or release data.
