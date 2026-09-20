# AGENTS.md

## Project purpose

This repository contains the 2027 Early Admissions Database for Japanese universities.

The project currently contains two independently maintained datasets:

- kokkoritsu: national and public universities
- shidai: private universities

These datasets will eventually be unified and used for search, SQLite export, ChatGPT Sites, and other derived applications.

## Canonical data

The canonical source data is located in:

- `data/canonical/kokkoritsu/`
- `data/canonical/shidai/`

Each dataset consists of:

- `master.csv`
- `coverage.csv`
- `research_requirements.csv`

Schema definitions are located in:

- `schema/kokkoritsu/`
- `schema/shidai/`

Do not modify canonical data unless explicitly instructed.

## Important data rules

- One Master row represents one actual application unit / selection slot.
- `record_id` is the primary key.
- `ResearchRequirements.admission_id` references `Master.record_id`.
- `Unknown` is not equivalent to `No`.
- blank/null is not equivalent to `Unknown`.
- Official university sources have priority.
- Do not infer or silently fill missing admissions information.
- Preserve source provenance.
- Excel, SQLite, JSON, unified datasets, and site data are derived artifacts.

## Build philosophy

All derived artifacts should be reproducible from canonical CSV files and schema definitions.

Expected flow:

canonical data
→ validation
→ unified dataset
→ SQLite / JSON / Excel / site data

Do not hand-edit generated artifacts.

## Releases

Frozen source versions are stored under:

- `data/releases/kokkoritsu-v5.61/`
- `data/releases/shidai-v0.97/`

Do not modify release directories.

## Development priorities

1. Audit repository structure and schemas.
2. Validate kokkoritsu and shidai canonical datasets.
3. Verify schema compatibility.
4. Implement reproducible unified dataset generation.
5. Implement SQLite generation.
6. Implement JSON/search-index generation.
7. Add automated tests.
8. Build the search/site layer only after the data pipeline is stable.

## General rule

Prefer simple, reproducible code over one-off transformations.
Never change admission facts in order to make validation pass.
Report inconsistencies instead.
