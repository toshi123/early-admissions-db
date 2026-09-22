# Unified contract v0.1 validation summary

- Generated: `2026-09-22T12:46:16.330652+00:00`
- Status: `passed_with_findings`
- Mode: read-only; canonical and release data were not modified
- Contract version: `0.1`

## Severity totals

| Severity | Count |
|---|---:|
| error | 0 |
| warning | 1167 |
| informational | 3292 |

## Dataset totals

| Dataset | Errors | Warnings | Informational | Total |
|---|---:|---:|---:|---:|
| kokkoritsu | 0 | 1149 | 1352 | 2501 |
| shidai | 0 | 18 | 1940 | 1958 |

## Findings by code

| Code | Severity | Count | Dataset counts | Representative record IDs |
|---|---|---:|---|---|
| `COMMON_TEST_FIELDS_DIFFER` | informational | 109 | kokkoritsu=109 | OCHA-2027-AO-BIO, OCHA-2027-AO-CHEM, OCHA-2027-AO-CULTINFO, OCHA-2027-AO-HENV, OCHA-2027-AO-HOME |
| `COVERAGE_ZERO_MASTER_ROWS` | informational | 10 | kokkoritsu=8, shidai=2 | 国立:政策研究大学院大学, 国立:総合研究大学院大学, 国立:北陸先端科学技術大学院大学, 国立:奈良先端科学技術大学院大学, 公立:東京都立産業技術大学院大学 |
| `DATE_RAW_PARTIAL` | informational | 3100 | kokkoritsu=1204, shidai=1896 | HU-2027-F1-01, HU-2027-F1-02, HU-2027-F1-03, HU-2027-F1-04, HU-2027-F1-05 |
| `DATE_RAW_UNPARSED` | informational | 18 | kokkoritsu=15, shidai=3 | ST-2027-C-01, ST-2027-C-02, ST-2027-C-03, ST-2027-C-04, ST-2027-C-05 |
| `DETAIL_COMPLETENESS_UNMAPPED` | warning | 767 | kokkoritsu=767 | NWU-2027-PICASO-01, NWU-2027-PICASO-02, NWU-2027-PICASO-03, NWU-2027-PICASO-04, NWU-2027-PICASO-05 |
| `PROVENANCE_URL_MISSING` | warning | 55 | kokkoritsu=55 | TMU-2027-AO-01, TMU-2027-AO-02, TMU-2027-AO-03, TMU-2027-AO-04, TMU-2027-AO-05 |
| `RESEARCH_ACTIVITY_LEVEL_UNMAPPED` | warning | 281 | kokkoritsu=281 | HUE-2027-AO-SELF-01, HUE-2027-AO-SELF-02, HUE-2027-AO-SELF-03, AKITA-2027-AO1-EDU-REGCULT, YAM-2027-REC1-HSS-GLOBAL |
| `RESEARCH_DENORMALIZED_FIELD_MISMATCH` | warning | 10 | kokkoritsu=8, shidai=2 | OU-2027-C-06, ICU-2027-SOGO-SCI, ICU-2027-SOGO-IBDP |
| `RESEARCH_EXACT_DUPLICATE` | warning | 4 | shidai=4 | MU-2027-AO1-DS, MU-2027-AO1-SUS, MU-2027-AO1-MATH, MU-2027-AO1-ARCH |
| `RESEARCH_NOT_REQUIRED_WITH_CHILD` | informational | 55 | kokkoritsu=16, shidai=39 | FUKU-2027-AO-ENG-GEN, FUKU-2027-AO-ENG-W, HIT-2027-REC-COM, HIT-2027-REC-ECON, HIT-2027-REC-LAW |
| `RESEARCH_REQUIRED_WITHOUT_CHILD` | warning | 45 | kokkoritsu=33, shidai=12 | NWU-2027-PICASO-01, NWU-2027-PICASO-02, NWU-2027-PICASO-03, NWU-2027-PICASO-04, NWU-2027-PICASO-05 |
| `WHITESPACE_PADDING` | warning | 5 | kokkoritsu=5 | SPU-2027-REC-01, SPU-2027-REC-04, SPU-2027-REC-08, SPU-2027-REC-11, SPU-2027-REC-14 |

## Inputs

| Dataset | Table | Rows | Bytes | SHA-256 | Path |
|---|---|---:|---:|---|---|
| kokkoritsu | master | 4011 | 6699552 | `d77665c27c2a4deed8f85d73ba6c546fe24fad21ded6a28719d67e2f3b490d6b` | `data/canonical/kokkoritsu/master.csv` |
| kokkoritsu | coverage | 187 | 96802 | `8bce9276537767eb4fa2285f4d398f33d3634369e4168720c7f752d964e9bc5e` | `data/canonical/kokkoritsu/coverage.csv` |
| kokkoritsu | research_requirements | 281 | 109783 | `044dba433319b482ae309952be4e765c85a412c77be1431617c8ff1584f40ec3` | `data/canonical/kokkoritsu/research_requirements.csv` |
| shidai | master | 2400 | 5103903 | `7062ae8afb09eabc9aa6118dc0fc44e6170037db8c1f069684b5cdbcd170ce0e` | `data/canonical/shidai/master.csv` |
| shidai | coverage | 73 | 50061 | `489f97680cc51374af59ab8e037e3ab399e1aff7cb00ed5fb95c043ff36b349d` | `data/canonical/shidai/coverage.csv` |
| shidai | research_requirements | 214 | 117769 | `9269bb49ca61ad7d6a0771445c5bb925821fff4e699fd4807d35cc3a33b35ac8` | `data/canonical/shidai/research_requirements.csv` |

## Crosswalk metrics

```json
{
  "crosswalks": {
    "kokkoritsu": {
      "detail_completeness_status": {
        "complete": 2458,
        "partial": 786,
        "unmapped": 767
      },
      "research_activity_level_status": {
        "none": 387,
        "null": 1246,
        "relevant": 104,
        "required": 126,
        "unknown": 1867,
        "unmapped": 281
      }
    },
    "shidai": {
      "detail_completeness_status": {
        "complete": 2175,
        "partial": 225
      },
      "research_activity_level_status": {
        "none": 1645,
        "relevant": 649,
        "required": 101,
        "unknown": 5
      }
    }
  },
  "row_counts": {
    "kokkoritsu": {
      "coverage": 187,
      "master": 4011,
      "research_requirements": 281
    },
    "shidai": {
      "coverage": 73,
      "master": 2400,
      "research_requirements": 214
    }
  }
}
```

## Boundary

This run validated source canonical data only. It did not generate unified CSV, SQLite, JSON/search data, Excel, or site artifacts, and it did not modify canonical or release data.
