# Hokkaido University of Education: 2027 application-unit reaudit

Audit date: 2026-09-28
Branch: `reaudit-2027-v0.1`

## Confirmed application units

The 2027 Teacher Training Special Entrance Examination guide says an applicant may apply to only one campus. Within Sapporo, the application form accepts up to five ranked preferred majors/fields; within Asahikawa, it accepts only one first preference. The preference entries are therefore choices inside one campus application, not multiple applications. Two campus-level rows were added, one for Sapporo and one for Asahikawa. No campus-wide numeric capacity was published; the guide states that capacity is limited by major/field and describes it as “a small number,” so `capacity` remains blank.

The five special-selection flags are retained on both rows. They are all `No`; this examination does not establish IB, private-foreign-student, returnee, regional-quota, or adult-selection status.

## Deliberately not added

The current 2027 download index listed the Teacher Training Special guide but did not list the School Recommendation guide as of this audit. The 2027 admissions outline schedules the School Recommendation (general and region-designated) guide for late September. The outline distinguishes those selection types and states that eligible Kushiro applicants may also apply to the region-designated selection, but the 2027 application forms, Web input fields, and treatment of course/field preferences were not available on the index. The Master unit count and forms are therefore not inferred for School Recommendation (general/region-designated), or for Iwamizawa Music Culture course-specific slots. `UQ-2027-0046` requests a check from 2026-10-01.

The exact English-qualification raw value is `外部英語資格要件の明示なし。`, which is present in the existing v0.3 crosswalk as `review_required`. The rows do not assert that no English-related condition exists.

## Files and counts

- Hokkaido University of Education Master: 4 → 6 rows; 2 campus application units added.
- Canonical Coverage `master_rows`: 6.
- `coverage_reaudit_2027.csv`: official outline/index, schedule and Master comparison checked; audit remains `追加確認待ち` because the detailed recommendation documents are pending.
- UpdateQueue: one open item, `UQ-2027-0046`.
- Correction ledger: `CC-2027-0010`, partial application with the unresolved recommendation group preserved.
- No canonical schema, release data, or crosswalk was changed.

## Validation and production artifacts

- Canonical validation: PASS; errors=0. Unified build: PASS; master=6,619, coverage=260, research requirements=495. The final Python regression suite also verified deterministic Unified output for the current canonical inputs.
- Operations validation: PASS.
- Python tests: 148 passed.
- Site tests: 16 files / 158 tests passed.
- Site frontend build: PASS (Vite reports the existing large candidate-XLSX chunk warning).
- SQLite production: PASS; admissions=6,619, coverage=260, research requirements=495; `production_ready=true`.
- Site-data production: PASS; search=6,619, details=6,619, research=495; `production_ready=true`.
- Unified/SQLite/Site retain all five special-selection flag columns. Both new rows carry `false` through Unified, SQLite, and Site details.

`run_update_acceptance_audit` could not complete because its configured old comparison input is absent: `sources/incoming/2026-09-22/kokkoritsu_v5_74_superseded/kokkoritsu_early_admissions_2027_master_v5_74.csv`. Per the existing audit decision, this legacy comparison limitation is recorded as non-blocking; production readiness was verified directly by the production-profile builders and test suites.

## Official evidence

- 2027 download index and available application documents: https://www.hokkyodai.ac.jp/exam/faculties/exam/download/
- 2027 Teacher Training Special application guide: https://www.hokkyodai.ac.jp/files/00000200/00000285/%E4%BB%A4%E5%92%8C%EF%BC%99%E5%B9%B4%E5%BA%A6%E5%AD%A6%E7%94%9F%E5%8B%9F%E9%9B%86%E8%A6%81%E9%A0%85%EF%BC%88%E6%95%99%E5%93%A1%E9%A4%8A%E6%88%90%E7%89%B9%E5%88%A5%E5%85%A5%E8%A9%A6%EF%BC%89.pdf
- 2027 admissions outline and publication schedule: https://www.hokkyodai.ac.jp/files/00000200/00000285/%E4%BB%A4%E5%92%8C%EF%BC%99%E5%B9%B4%E5%BA%A6%E5%85%A5%E5%AD%A6%E8%80%85%E9%81%B8%E6%8A%9C%E8%A6%81%E9%A0%85%20.pdf
