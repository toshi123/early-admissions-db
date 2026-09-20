# Read-only structured search CLI contract v0.1

## 1. Scope

`scripts/search` is a read-only structured-search client for the published
`data/derived/sqlite/early_admissions_2027.sqlite` artifact. It is intended to
test guidance-search semantics before a Site or API is designed.

The CLI:

- opens SQLite with URI `mode=ro&immutable=1` and `PRAGMA query_only=ON`;
- validates database schema `0.1` and GPA parser contract `0.1` metadata;
- never modifies SQLite, canonical, release, or unified inputs;
- uses only fixed SQL identifiers and parameter bindings for user values;
- does not provide full-text, AI natural-language, or GPA conditional-rule
  evaluation.

## 2. Boolean composition

- Different fields are combined with AND.
- Multiple values supplied to one field are combined with OR by one
  parameterized `IN (...)` predicate.
- Text/category comparisons are exact and use the database's default binary
  collation. The CLI does not trim, normalize, expand, or infer values.
- `--stem` means `stem_flag=1`; `--non-stem` means `stem_flag=0`. SQL NULL is
  not selected by either option.

Supported structured filters are:

- `--university`
- `--institution-type`
- `--prefecture`
- `--academic-field`
- `--stem` / `--non-stem`
- `--selection-category`
- `--exclusive` / `--exclusive-enrollment-status`
- `--school-recommendation-required`
- `--academic-record-required`
- `--common-test-required`
- `--research-requirement-required`
- `--research-activity-level-status`
- `--interview` / `--selection-interview`
- `--oral-exam` / `--selection-oral-exam`
- `--presentation` / `--selection-presentation`
- `--essay` / `--selection-essay`
- `--written-exam` / `--selection-written-exam`
- `--selection-common-test`
- `--gpa` with `--gpa-mode`

Every multi-value option may be repeated. Repeated and adjacent values are
flattened into the same OR set.

## 3. GPA modes and labels

GPA input accepts `0` through `5.0` with at most one decimal place and is
converted to integer tenths before SQL comparison. The only definitive numeric
predicate is the existing `admission_search_gpa_safe` view.

When `--gpa` is given, the default mode is `safe`:

| Mode | Rows returned |
|---|---|
| `safe` | Only `parsed_safe` rows whose complete overall lower/upper bound safely matches the supplied GPA |
| `review` | Safe matches plus `conditional_review` rows; conditional rows are surfaced but not evaluated |
| `all` | All rows satisfying the other structured filters, annotated with their GPA state |

With a GPA input, result labels are:

- `safe match`: overall GPA condition safely matched;
- `safe no match`: a safely parsed rule exists but the supplied GPA does not
  match that overall rule;
- `conditional/review required`: conditional numeric content exists and must
  be reviewed;
- `not numerically evaluable`: no v0.1 numeric decision is allowed.

`safe match` never means “application eligible” or that all admission
requirements are satisfied. `--gpa-mode` without `--gpa` is an error. Without
GPA input, safely parsed rows are labeled
`safe numeric rule (GPA not supplied)` rather than as matches.

## 4. Output

The default `table` format prints a complete search summary followed by four
terminal tables. Terminal cells may be shortened for display only. The tables
cover provenance/record ID, university and admission unit, location and field,
GPA raw/derived state, requirement flags, selection methods, and raw
application dates.

`--format csv` and `--format tsv` write complete stored values without cell
shortening. Their data stream goes to stdout; the search summary goes to stderr
so the export remains machine-readable. `--limit` defaults to 20, `--offset`
supports paging, and `--all-results` explicitly removes the output limit.

The summary reports:

- total matched rows;
- GPA safe-match rows, or `n/a` when no GPA was supplied;
- GPA safe-no-match rows and safely parsed numeric-rule rows;
- GPA conditional/review rows;
- GPA not-numerically-evaluable rows;
- source-dataset counts;
- distinct university count;
- displayed row interval.

## 5. Examples

```bash
./scripts/search \
  --prefecture 東京都 神奈川県 \
  --stem \
  --gpa 3.8 \
  --exclusive 併願可 \
  --oral-exam Yes
```

```bash
./scripts/search --gpa 3.8 --gpa-mode review --format csv --all-results
```

```bash
./scripts/search \
  --selection-category 学校推薦型選抜 \
  --school-recommendation-required Yes \
  --format tsv
```

## 6. Representative QA

`scripts/run_search_qa` executes the frozen 25-query guidance-search suite and
writes `validation/reports/search_cli_qa_v0_1.md`. It compares the SQLite
SHA-256 before and after the suite and fails if the database bytes change.

## 7. Academic-field group extension

`--academic-field-group CODE [CODE ...]` filters membership in the frozen
exact-value academic-field crosswalk. Multiple codes are ORed. The predicate is
ANDed with other fields, including the existing exact raw
`--academic-field VALUE [VALUE ...]` filter.

`--academic-field-mapping-status STATUS [STATUS ...]` supports `single`,
`multi`, `review_required`, `unmapped`, and `not_applicable`. Results expose both
the raw field and the derived mapping status/group list. Unknown group codes are
rejected after reading the database taxonomy; all user values remain SQL bind
parameters.
