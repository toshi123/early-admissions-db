# SQLite schema v0.2

This version extends the [v0.1 design](sqlite_design_v0_1.md) for Unified contract v0.3. The v0.1 SQL and its frozen artifacts remain unchanged.

- `admissions` retains every Unified Master column in CSV order. The five special-selection flags are required SQLite `INTEGER` values constrained to `0` or `1`; the builder converts Unified `true` and `false` without filling missing values.
- `admissions`, `coverage`, and `research_requirements` accept the current source pairs `kokkoritsu`/`5.83` and `shidai`/`1.10`.
- `build_metadata.database_schema_version` is `0.2`, and `build_metadata.unified_contract_version` is `0.3`.
- The existing GPA, grade, academic-field, English, prefecture, FTS, provenance, foreign-key, and atomic-publication behavior is inherited from v0.1.

The SQLite builder verifies exact Unified column order before loading and validates row counts and retained raw values before publication. Site detail schema v0.3 publishes all five flags as booleans.
