# Early Admissions Search Site implementation v0.1

## Scope

This document describes the local, read-only Site implementation. It does not
change the Site-data projection or SQLite search semantics. It does not use D1,
R2, an API server, runtime SQLite, the OpenAI API, accounts, or persistent user
state.

## Stack and hosting profile

- Vite 6.4.3, vanilla TypeScript 5.8.3, and semantic HTML/CSS.
- The deployable output is the static `site/dist/` directory.
- `site/.openai/hosting.json` declares `static.directory = "dist"` and contains
  no invented `project_id`.
- Client routes are `/search`,
  `/admissions/:source_dataset/:source_version/:record_id`, and `/about/data`.
  `/` normalizes to `/search`.
- `site/public/_redirects` requests an `index.html` fallback for direct entry to
  client routes. Direct-route behavior must be confirmed again in a Sites
  review version before deployment.

The small framework-free client avoids a runtime server and keeps the UI bundle
independent of the 8.9 MB expanded search projection.

## Data flow and integrity

`npm run dev`, `npm test`, and `npm run build` first run
`site/scripts/sync-site-data.mjs`. The script reads the existing validated
projection at `data/derived/site/v0_1/`, requires schema `0.1` and a passed
manifest, and copies the manifest plus assets to the ignored
`site/public/site-data/` directory. Vite then includes that directory in the
deployable `dist/` output.

Both `site/public/site-data/` and `site/dist/` are reproducible generated
artifacts and are ignored by Git. Source-controlled inputs are the frontend
source, lockfile, sync/oracle scripts, tests, docs, and hosting configuration.

At runtime the client loads in this order:

1. `build_manifest.json` and its schema/build status;
2. the manifest-named filter options, checked against size and SHA-256;
3. all eight manifest-named search shards, checked against size, SHA-256,
   schema version, build ID, and total row count;
4. one manifest-named detail shard only after a detail route is opened.

A missing/corrupt artifact, cross-build asset, row-count mismatch, or missing
detail produces a data-error view. It is never represented as zero matches.

## Frozen search behavior

`site/src/search.ts` mirrors `early_admissions.site_search`:

- different fields are AND;
- multiple values within a field are OR;
- values are exact, with no fuzzy or substring interpretation;
- broad academic-field groups use membership intersection only;
- GPA uses integer tenths and the frozen `parsed_safe` bounds;
- `safe`, `review`, and `all` have the same fail-closed meaning as the Python
  oracle;
- `No`, `Unknown`, and null remain distinct.

The browser displays 20 results per page. Repeated query parameters preserve OR
values. Invalid parameter names or values are ignored with a visible warning.

## Routes and UI

### Search

The first screen is the search interface. Desktop uses a sticky filter column;
tablet and mobile use a full-height filter drawer. It includes all v0.1
structured filters, GPA mode, applied-filter removal, summaries, and pagination.
Result cards show raw academic field and GPA values beside derived labels.

### Detail

The public identity uses only `(source_dataset, source_version, record_id)`.
The detail page retains the full admission projection, GPA and academic-field
derived layers, all ResearchRequirements rows (including exact duplicates),
fallback warnings, and stored provenance URLs. Missing URLs are shown as
`URL未記録`; no URL is inferred.

### Data guide

`/about/data` shows manifest versions and counts, GPA and academic-field
semantics, the distinction among No/Unknown/null, fallback meaning, and the
requirement to check current official sources.

## Accessibility and agent interaction

Controls have programmatic labels, headings are semantic, focus is visible,
status chips include text, and the mobile drawer supports Escape, focus return,
and a Tab focus trap. External links state that they leave the Site.

When supported, the page registers two imperative WebMCP tools:

- `apply_admission_search_filters` applies a bounded subset through the same
  visible state and URL as the UI and rejects invalid input before mutation;
- `read_admission_search_summary` reads the current counts and shareable URL.

The Site remains fully usable when WebMCP is unavailable.

## Local commands

From `site/`:

```text
npm install
npm run dev
npm test
npm run build
```

No command above provisions, saves, or deploys a ChatGPT Site.
