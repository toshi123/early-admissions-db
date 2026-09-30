# 2027 Early Admissions Database

This repository contains independently maintained canonical datasets for Japanese national/public universities (`kokkoritsu`) and private universities (`shidai`). Canonical and release data are immutable inputs to the derived-data pipeline.

## Read-only validation

Run the unified contract v0.1 validator from the repository root:

```bash
./scripts/validate
```

Without the wrapper, the equivalent development command is:

```bash
PYTHONPATH=src python3 -m early_admissions.validate
```

After installing the package, this also works:

```bash
python3 -m early_admissions.validate
```

Default reports:

- `validation/reports/unified_v0_1_validation_summary.md`
- `validation/reports/unified_v0_1_validation_report.json`

The validator reads canonical data and writes reports only. It does not generate unified data or modify canonical/release files.

## Unified dataset build

Build the unified contract v0.1 CSV files from validated canonical inputs:

```bash
./scripts/build_unified
```

Without the wrapper, the equivalent development command is:

```bash
PYTHONPATH=src python3 -m early_admissions.build_unified
```

The build runs the read-only source validator, validates generated rows against
the unified JSON Schema and cross-table constraints, checks row/provenance
preservation, and performs two independent writes to require byte-identical
CSV output before publication. Expected output row counts are calculated from
the current kokkoritsu and shidai canonical inputs; frozen release counts are
checked separately by regression tests. It writes only:

- `data/canonical/unified/master.csv`
- `data/canonical/unified/coverage.csv`
- `data/canonical/unified/research_requirements.csv`
- `data/canonical/unified/build_manifest.json`
- `data/canonical/unified/build_summary.md`

Canonical source and release data are never rewritten by the build.

## SQLite derived build

Build the SQLite v0.1 artifact from the validated unified CSV snapshot:

```bash
./scripts/build_sqlite
```

Without the wrapper, the equivalent development command is:

```bash
PYTHONPATH=src python3 -m early_admissions.build_sqlite
```

The builder verifies the unified build manifest and CSV SHA-256 values, probes
the active SQLite library for `STRICT`, FTS5, and tokenizer support, creates a
new temporary database, and publishes only after relational, losslessness,
view, integrity, FTS (when enabled), and representative structured-query gates
pass. FTS is optional; structured SQL remains available in the portable no-FTS
profile. It writes only:

- `data/derived/sqlite/early_admissions_2027.sqlite`
- `data/derived/sqlite/build_manifest.json`
- `data/derived/sqlite/build_summary.md`

The unified CSV, canonical, and release inputs are read-only.

## GPA strict-safe search

The SQLite build also creates the fail-closed GPA derived layer governed by
`docs/gpa_search_design_v0_1.md`. Search a Japanese five-point GPA with:

```bash
./scripts/search_gpa 3.8
```

The query uses integer tenths and returns only the audited simple, current-year,
overall-GPA minimum subset. Its result meaning is `overall GPA condition safely
matched`; it is not an application-eligibility determination. Conditional,
subject-specific, AND/OR, branch, historical, non-binding, unknown, and
unapproved expressions are never automatically matched.

## Structured read-only search

Use the general structured-search CLI for guidance-oriented combinations:

```bash
./scripts/search \
  --prefecture 東京都 神奈川県 \
  --academic-field-group engineering information \
  --gpa 3.8 \
  --exclusive 併願可 \
  --oral-exam Yes
```

Different fields are ANDed and multiple values within one field are ORed. GPA
defaults to strict-safe filtering; `--gpa-mode review` exposes conditional rows
without evaluating them, while `--gpa-mode all` retains all GPA states. CSV and
TSV output preserve complete values:

```bash
./scripts/search --gpa 3.8 --format csv --all-results
```

Broad academic-field groups come only from the frozen exact-value crosswalk in
`schema/academic_field/`. The exact raw `--academic-field` filter remains
available, and `--academic-field-mapping-status review_required` exposes values
deliberately held for review.

The full contract is in `docs/search_cli_v0_1.md`. Run the frozen 25-query
field QA set with:

```bash
./scripts/run_search_qa
```

Run the automated tests with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Local Early Admissions Search Site

The static TypeScript frontend is under `site/`. It consumes only the validated
Site-data projection and does not open SQLite in the browser. From that
directory:

```bash
npm install
npm run dev
npm test
npm run build
```

The in-site usage guide is available at `/guide`. Its screenshots are generated
from the current UI and validated Site-data projection with the installed
Chrome/Chromium browser. Regenerate all guide images and verify the two-row
Excel example with:

```bash
cd site
npm run capture-guide
```

The command starts an isolated local Vite server and temporary browser profile;
it does not change canonical data or the browser's existing saved candidates.
Set `GUIDE_CHROME_PATH` only when Chrome/Chromium is installed outside the
standard locations, or `GUIDE_BASE_URL` to capture from an already running
local server.

Each command that needs data synchronizes the current projection into ignored
`site/public/site-data/`; the deployable but ignored build is `site/dist/`.
Implementation and local QA details are in
`docs/site_implementation_v0_1.md` and
`validation/reports/site_frontend_qa_v0_1.md`. The public Site is hosted at
`https://ea.ussapao.chatgpt.site`.

## Read-only MCP access

The MCP extension shares the public Site-data and `site/src/search.ts` search
semantics with the Web UI. See `docs/mcp.md` for its four tools, local
Streamable HTTP setup, validation, deployment, and ChatGPT connection steps.
It does not expose canonical or operational files and cannot update records.
