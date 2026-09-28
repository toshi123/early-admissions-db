# Unified contract v0.1 validation summary

- Generated: `2026-09-28T14:18:16.208799+00:00`
- Status: `passed_with_findings`
- Mode: read-only; canonical and release data were not modified
- Contract version: `0.3`

## Severity totals

| Severity | Count |
|---|---:|
| error | 0 |
| warning | 1238 |
| informational | 3535 |

## Dataset totals

| Dataset | Errors | Warnings | Informational | Total |
|---|---:|---:|---:|---:|
| kokkoritsu | 0 | 1220 | 1578 | 2798 |
| shidai | 0 | 18 | 1957 | 1975 |

## Findings by code

| Code | Severity | Count | Dataset counts | Representative record IDs |
|---|---|---:|---|---|
| `COMMON_TEST_FIELDS_DIFFER` | informational | 109 | kokkoritsu=109 | OCHA-2027-AO-BIO, OCHA-2027-AO-CHEM, OCHA-2027-AO-CULTINFO, OCHA-2027-AO-HENV, OCHA-2027-AO-HOME |
| `COVERAGE_ZERO_MASTER_ROWS` | informational | 10 | kokkoritsu=8, shidai=2 | 国立:政策研究大学院大学, 国立:総合研究大学院大学, 国立:北陸先端科学技術大学院大学, 国立:奈良先端科学技術大学院大学, 公立:東京都立産業技術大学院大学 |
| `DATE_RAW_PARTIAL` | informational | 3191 | kokkoritsu=1282, shidai=1909 | OCHA-2027-AO-BIO, OCHA-2027-AO-CHEM, OCHA-2027-AO-CULTINFO, OCHA-2027-AO-HENV, OCHA-2027-AO-HOME |
| `DATE_RAW_UNPARSED` | informational | 170 | kokkoritsu=163, shidai=7 | NU-2027-NCT-01, NU-2027-NCT-02, TGU-2027-FOR-A-ART, TGU-2027-FOR-A-EARLY, TGU-2027-FOR-A-ENG |
| `DETAIL_COMPLETENESS_UNMAPPED` | warning | 836 | kokkoritsu=836 | OCHA-2027-PFI-BIO, OCHA-2027-PFI-CHEM, OCHA-2027-PFI-CULTINFO, OCHA-2027-PFI-DANCE, OCHA-2027-PFI-HENV |
| `PROVENANCE_URL_MISSING` | warning | 55 | kokkoritsu=55 | TMU-2027-AO-01, TMU-2027-AO-02, TMU-2027-AO-03, TMU-2027-AO-04, TMU-2027-AO-05 |
| `RESEARCH_ACTIVITY_LEVEL_UNMAPPED` | warning | 283 | kokkoritsu=283 | OCHA-2027-AO-BIO, HIT-2027-REC-COM, HIT-2027-REC-ECON, HIT-2027-REC-LAW, HIT-2027-REC-SDS |
| `RESEARCH_DENORMALIZED_FIELD_MISMATCH` | warning | 10 | kokkoritsu=8, shidai=2 | OU-2027-C-06, ICU-2027-SOGO-SCI, ICU-2027-SOGO-IBDP |
| `RESEARCH_EXACT_DUPLICATE` | warning | 4 | shidai=4 | MU-2027-AO1-DS, MU-2027-AO1-SUS, MU-2027-AO1-MATH, MU-2027-AO1-ARCH |
| `RESEARCH_NOT_REQUIRED_WITH_CHILD` | informational | 55 | kokkoritsu=16, shidai=39 | HIT-2027-REC-COM, HIT-2027-REC-ECON, HIT-2027-REC-LAW, HIT-2027-REC-SDS, HIT-2027-REC-SOC |
| `RESEARCH_REQUIRED_WITHOUT_CHILD` | warning | 45 | kokkoritsu=33, shidai=12 | WAK-2027-06, WAK-2027-07, OMU-2027-SPECIAL-SSH, OMU-2027-SPECIAL-UNESCO, NWU-2027-PICASO-01 |
| `WHITESPACE_PADDING` | warning | 5 | kokkoritsu=5 | SPU-2027-REC-01, SPU-2027-REC-04, SPU-2027-REC-08, SPU-2027-REC-11, SPU-2027-REC-14 |

## Inputs

| Dataset | Table | Rows | Bytes | SHA-256 | Path |
|---|---|---:|---:|---|---|
| kokkoritsu | master | 4261 | 7373515 | `a82e95bcb4f9fa1f165854f676c06ed9d3e55266d0e1cf6cec607ce63cc1d343` | `data/canonical/kokkoritsu/master.csv` |
| kokkoritsu | coverage | 187 | 103147 | `904bd52292dc809f404235eb523102e110b1d703c5a4756ea76af0a5e56b2ec3` | `data/canonical/kokkoritsu/coverage.csv` |
| kokkoritsu | research_requirements | 281 | 109783 | `044dba433319b482ae309952be4e765c85a412c77be1431617c8ff1584f40ec3` | `data/canonical/kokkoritsu/research_requirements.csv` |
| shidai | master | 2421 | 5184649 | `a7328bbe992fb8f68a6f7dba3b9f918e689c56d15e3613cd07da29e3a74cba6b` | `data/canonical/shidai/master.csv` |
| shidai | coverage | 73 | 50741 | `6d9c1f333a8420138cd41889eb220e8ad15c1ada06b3e8a672b332fbd9723dd8` | `data/canonical/shidai/coverage.csv` |
| shidai | research_requirements | 214 | 117769 | `9269bb49ca61ad7d6a0771445c5bb925821fff4e699fd4807d35cc3a33b35ac8` | `data/canonical/shidai/research_requirements.csv` |

## Crosswalk metrics

```json
{
  "crosswalks": {
    "kokkoritsu": {
      "detail_completeness_status": {
        "complete": 2517,
        "partial": 908,
        "unmapped": 836
      },
      "research_activity_level_status": {
        "none": 390,
        "null": 1249,
        "relevant": 108,
        "required": 126,
        "unknown": 2105,
        "unmapped": 283
      }
    },
    "shidai": {
      "detail_completeness_status": {
        "complete": 2193,
        "partial": 228
      },
      "research_activity_level_status": {
        "none": 1662,
        "null": 4,
        "relevant": 649,
        "required": 101,
        "unknown": 5
      }
    }
  },
  "row_counts": {
    "kokkoritsu": {
      "coverage": 187,
      "master": 4261,
      "research_requirements": 281
    },
    "shidai": {
      "coverage": 73,
      "master": 2421,
      "research_requirements": 214
    }
  }
}
```

## Boundary

This run validated source canonical data only. It did not generate unified CSV, SQLite, JSON/search data, Excel, or site artifacts, and it did not modify canonical or release data.
