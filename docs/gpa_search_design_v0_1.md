# GPA / 評定検索 derived layer contract v0.1

## 1. Status and scope

- Status: implemented as a reproducible SQLite derived layer.
- Audit source: `data/canonical/unified/master.csv`.
- Source rows: 5,921 admissions.
- Source SHA-256:
  `1df386ed99532a3dff381507978a1454d7c20113574285b2526f6ae122050279`.
- Authoritative raw field: `admissions.gpa_requirement` / unified
  `gpa_requirement`.
- Authoritative DDL:
  `schema/sqlite/admission_search_gpa_schema_v0_1.sql`.
- Parser implementation: `src/early_admissions/gpa_search.py`.
- Read-only query CLI: `scripts/search_gpa`.
- Complete distinct-value audit:
  `validation/reports/gpa_requirement_raw_value_audit_v0_1.csv`.
- Audit CSV SHA-256:
  `d111046ce752c2c5ecc4585e1551811e125b23290d4daeb14e496f4fcee24563`.

The implementation does not modify canonical data, release data, or unified
CSV. The SQLite artifact is rebuilt from scratch through the existing
temporary-database, complete-validation, atomic-publication workflow.

The objective is deliberately narrower than deciding whether a student is
eligible for an admission. The derived layer may determine whether a supplied
Japanese five-point overall GPA satisfies a safely parsed GPA rule. It must not
claim that the student satisfies graduation, recommendation, subject,
qualification, activity, residency, or other admission requirements.

## 2. Audit method

The unified CSV was scanned twice: once for bounded preflight statistics and
once to aggregate each raw value, frequency, source-dataset counts, and
representative logical record IDs. All subsequent inspection used the 554-value
aggregate (553 non-null raw values plus the null class), not the 5,921 raw rows.

Classification was conservative and overlap-aware:

- each raw value has one primary class and one numeric-safety tier;
- independent feature flags record numeric, subject, AND, OR, branching,
  upper-bound, unknown, unresolved, qualitative, and no-threshold signals;
- every `safe_numeric` raw value was individually reviewed;
- numbers in years, test scores, IB scores, subject counts, fees, or selection
  scoring were not treated as GPA thresholds;
- the published SQLite database was opened immutable/read-only only to verify
  `fallback_previous_year` and `information_year` for three historical rows.

The audit CSV is the exhaustive frequency-level result. Feature counts below
overlap and therefore must not be summed. Primary-class and safety-tier counts
are partitions and do sum to 5,921.

## 3. Dataset-level results

| Metric | All | kokkoritsu | shidai |
|---|---:|---:|---:|
| Admissions | 5,921 | 3,668 | 2,253 |
| SQL NULL / empty CSV cell | 1,243 | 912 | 331 |
| Non-null | 4,678 | 2,756 | 1,922 |
| Distinct non-null raw values | 553 | 327 | 236 |

`NULL` is 20.99% of admissions. It remains `not_applicable`; it is not
`Unknown`, no requirement, zero, or a passing value.

Non-null value length ranges from 2 to 148 Unicode characters (median 16,
90th percentile 42, 99th percentile 82). No full-width numeric digit or
full-width decimal-point form was found.

Three admissions use `fallback_previous_year=1` and `information_year=2026`:

- two have raw `学習成績概評A`;
- one has raw `2026年度参考：全体の学習成績の状況4.3以上`.

None may enter the current-year safe numeric result set.

## 4. Numeric-safety partition

| Tier | Distinct raw classes | Admissions | % of all | Meaning |
|---|---:|---:|---:|---|
| `safe_numeric` | 90 | 1,199 | 20.25% | One complete, current-year, unconditional overall lower bound can be represented losslessly |
| `conditional_numeric` | 246 | 707 | 11.94% | Numeric content exists, but subject, Boolean logic, branching, conversion, exception, or other context prevents a single safe range |
| `do_not_numeric` | 218 | 4,015 | 67.81% | NULL, unknown, unstated, qualitative, historical, non-binding, or non-admission numeric content |

Among non-null admissions, 1,199 / 4,678 (25.63%) are safe simple numeric;
707 / 4,678 (15.11%) are conditional; and 2,772 / 4,678 (59.26%) must not be
numerically evaluated.

### 4.1 Safe lower-bound distribution

Every current safe value uses an inclusive `以上` lower bound. No safe
standalone upper-bound or safe standalone range was found.

| Minimum | Admissions |
|---:|---:|
| 3.0 | 72 |
| 3.2 | 54 |
| 3.3 | 11 |
| 3.4 | 12 |
| 3.5 | 341 |
| 3.6 | 30 |
| 3.7 | 38 |
| 3.8 | 185 |
| 3.9 | 3 |
| 4.0 | 378 |
| 4.1 | 5 |
| 4.2 | 10 |
| 4.3 | 59 |
| 4.5 | 1 |

Representative safe forms include `3.5以上`,
`全体の学習成績の状況3.8以上。`, and
`調査書の全体の評定平均値4.0以上`.

### 4.2 Primary-class partition

| Primary class | Distinct raw classes | Admissions | Numeric action |
|---|---:|---:|---|
| `simple_overall_minimum` | 90 | 1,199 | Safe parent `gpa_min` |
| `or_condition` | 82 | 269 | Conditional only |
| `overall_and_subject_compound` | 67 | 139 | Conditional only |
| `subject_specific_condition` | 66 | 206 | Conditional only |
| `and_condition` | 8 | 14 | Conditional only |
| `branch_condition` | 9 | 43 | Conditional only |
| `range_or_upper_condition` | 3 | 11 | Conditional only |
| `other_complex_numeric` | 11 | 25 | Conditional only |
| `non_admission_or_inoperative_numeric` | 3 | 7 | Do not numericize |
| `nonbinding_or_historical_numeric` | 6 | 15 | Do not numericize |
| `explicit_no_numeric_threshold` | 100 | 1,604 | Preserve as non-numeric status |
| `non_numeric_condition` | 74 | 349 | Do not numericize |
| `unknown` | 22 | 698 | Unknown, not No |
| `unresolved` | 12 | 99 | Unparsed/review required |
| `null` | 1 | 1,243 | Not applicable |

## 5. Requested pattern findings

Feature counts overlap because one raw expression may contain subject,
AND/OR, and branching logic simultaneously.

| Feature | Distinct raw values | Admissions | Finding |
|---|---:|---:|---|
| Decimal GPA-like numeric content | 345 | 1,928 | Only 1,199 rows are safe simple lower bounds |
| Explicit OR syntax | 100 | 299 | 83 values / 272 rows also contain decimal GPA-like numbers |
| Explicit AND / plus syntax | 131 | 337 | 121 values / 322 rows also contain decimal GPA-like numbers |
| Named-subject numeric condition | 198 | 534 | Must not be treated as overall GPA |
| Overall plus named-subject condition | 109 | 263 | A single overall threshold is insufficient |
| School/course/selection branching | 40 | 251 | 25 values / 88 rows contain decimal GPA-like numbers |
| Upper-bound language | 4 | 14 | All occurrences are embedded in compound rules; no standalone maximum |
| Explicit `不明` / `Unknown` family | 22 | 698 | Includes exact `不明` 489 rows and exact `Unknown` 1 row |
| Other unresolved wording | 21 | 174 | Primary unresolved class is 12 values / 99 rows after overlaps |
| Qualitative signal | 131 | 696 | Includes grade letters, “成績優秀”, qualifications, and unpublished criteria |

### 5.1 “No condition” is not one semantic state

The primary `explicit_no_numeric_threshold` class contains 100 raw values and
1,604 admissions. It must not be converted wholesale into “GPA condition
passed”. Overlapping subpatterns show why:

| Subpattern | Distinct | Admissions | Example meaning |
|---|---:|---:|---|
| Plain numeric-threshold absence wording | 53 | 844 | `数値による評定要件なし。` |
| Explicit no application threshold wording | 18 | 281 | GPA is not an application cutoff |
| Not stated / not confirmed wording | 32 | 454 | Absence of available evidence, not proof of no condition |
| Qualitative condition remains | 18 | 93 | “成績優秀” remains without a numeric cutoff |
| GPA used in selection/scoring | 10 | 105 | No application cutoff, but GPA still affects selection |

Examples such as `評定基準なし。調査書等は選考資料として30点で評価。`
and `数値基準なし（学科別に「成績優秀な者」等の推薦条件あり）。`
demonstrate that “no numeric threshold”, “no GPA requirement”, and “GPA not
used” are different statements.

### 5.2 Compound examples that prohibit a parent-level numeric match

- Overall AND subject:
  `全体の学習成績の状況4.3以上、かつ外国語全科目...4.3以上`.
- Subject-only:
  `数学および理科...それぞれ4.0以上`.
- OR alternative:
  `全体4.0以上、又は数学及び理科...平均4.5以上`.
- Branching:
  different thresholds for ordinary, specialist, and comprehensive courses.
- Range plus another condition:
  `3.8以上4.0未満かつ...4.3以上`.
- Non-binding numeric mention:
  `3.7以上...が望ましい（出願の必須条件ではない）`.
- Non-admission number:
  GPA thresholds used only for tuition exemption.
- Historical value:
  `2026年度参考：...4.3以上`.

## 6. Why one flat range is insufficient

The requested columns are appropriate only for the safe simple subset:

- `admission_rowid`
- `gpa_min`
- `gpa_max`
- `gpa_condition_type`
- `parse_status`
- `raw_value`

A single range cannot represent “overall 3.8 AND mathematics 4.0”, “overall
4.0 OR two-subject average 4.5”, or thresholds that vary by school course.
Putting the first visible number in `gpa_min` would create the exact false
positive the design must prevent.

The proposal therefore uses:

1. `admission_search_gpa`: one conservative classification row per admission;
2. `admission_search_gpa_rule_groups`: OR alternatives and branch predicates;
3. `admission_search_gpa_clauses`: AND clauses inside each alternative.

The parent `gpa_min` / `gpa_max` is populated only for a fully parsed,
unconditional, current-year, overall-GPA rule. Conditional numeric fragments
may later be stored in clauses, but never promoted to the parent range.

For exact boundary comparison, stored search values use integer tenths
(`gpa_min_tenths=38` for 3.8). `gpa_min` and `gpa_max` remain available as
generated REAL display columns. The integer columns, not floating-point
equality, are the comparison authority.

## 7. Parent-table field contract

| Field | Contract |
|---|---|
| `admission_rowid` | PK and FK to `admissions.admission_rowid`; not an external identifier |
| `raw_value` | Exact copy of `admissions.gpa_requirement`; SQL NULL stays NULL; no trim or rewrite |
| `gpa_min_tenths` | Exact stored lower bound (`3.8` → `38`) only for `parsed_safe`; otherwise NULL |
| `gpa_min` | Generated display value `gpa_min_tenths / 10.0` |
| `gpa_min_inclusive` | `1` for current `以上` forms; paired with non-null `gpa_min` |
| `gpa_max_tenths` | Exact stored upper bound for a future safe range; NULL for every current safe row |
| `gpa_max` | Generated display value `gpa_max_tenths / 10.0` |
| `gpa_max_inclusive` | Paired with non-null `gpa_max` |
| `gpa_scale` | `japanese_5_point`, `other`, or `unknown`; safe matching requires `japanese_5_point` |
| `metric_scope` | `overall`, `subject`, `mixed`, `none`, or `unknown`; safe matching requires `overall` |
| `gpa_condition_type` | Structural meaning, separate from parse success |
| `parse_status` | `parsed_safe`, `conditional_review`, `not_numeric`, `historical_reference`, `unknown`, `unparsed`, or `not_applicable` |
| `search_disposition` | `safe_numeric`, `review_required`, or `not_searchable` |
| `source_value_status` | `current` or `previous_year_reference` |
| feature flags | Explicit subject / AND / OR / branch indicators; safe rows require all four to be false |
| `parser_contract_version` | Fixed `0.1` for reproducibility |

`gpa_condition_type` and `parse_status` are intentionally separate. For
example, an OR rule is a known condition type while still requiring review; an
unpublished criterion is unknown rather than an OR rule.

## 8. Parser contract

The parser follows this order and fails closed.

1. Copy `gpa_requirement` to `raw_value` exactly.
2. If raw is NULL, emit `not_applicable` with no numeric values.
3. If `fallback_previous_year=1` or the value is explicitly historical, emit
   `historical_reference`; never `parsed_safe`.
4. Detect unknown, unresolved, no-threshold, qualitative, non-binding, and
   non-admission-number states before attempting numeric extraction.
5. Detect OR, AND, named subjects, overall-plus-subject, course/school/selection
   branches, exceptions, conversions, ranges, and multiple numeric mentions.
6. Emit `parsed_safe` only when the complete expression is an approved,
   anchored form for one current Japanese five-point overall lower bound, with
   exactly one operative number and no unsafe feature.
7. Any new or unmatched raw expression becomes `unparsed`; the parser must not
   guess from the first number.
8. Conditional numeric values keep parent `gpa_min` and `gpa_max` NULL. They
   may become evaluatable only after every OR group, AND clause, subject scope,
   branch predicate, and non-GPA dependency is represented completely.
9. Letter grades (`A`, `B`) must not be converted using an assumed scale.
   Explicit raw equivalence may be separately allowlisted and tested.
10. Do not use blanket trimming or Unicode normalization to rewrite raw text.
    Matching may use a private comparison representation only if every accepted
    form has a regression fixture and the raw source remains unchanged.

The current audit found no threshold with more than one decimal place. A future
unseen precision must become `unparsed` until the scaled-integer contract is
revised. The audit also found no safe maximum, so v0.1 must not infer one from
the five-point scale. `gpa_max_tenths=NULL` means “no parsed upper bound”, not
5.0.

## 9. Safe query semantics

The caller first validates a Japanese five-point input with at most one decimal
place and binds exact integer tenths (`3.8` → `:student_gpa_tenths = 38`). The
strict numeric query is:

```sql
SELECT a.*
FROM admissions AS a
JOIN admission_search_gpa_safe AS g USING (admission_rowid)
WHERE (:student_gpa_tenths > g.gpa_min_tenths
       OR (:student_gpa_tenths = g.gpa_min_tenths
           AND g.gpa_min_inclusive = 1))
  AND (
        g.gpa_max_tenths IS NULL
        OR :student_gpa_tenths < g.gpa_max_tenths
        OR (:student_gpa_tenths = g.gpa_max_tenths
            AND g.gpa_max_inclusive = 1)
      );
```

For `:student_gpa = 3.8`, the frozen audit predicts 743 safe-simple matches.
This is a regression expectation, not a future hard-coded production count.

The result label must be “overall GPA condition safely matched”, not
“application eligible”. Conditional, no-numeric-threshold, qualitative,
unknown, historical, and unparsed rows must be returned in separate review
buckets if the UI exposes them. They must never be UNIONed into the definitive
match set under a generic `gpa_min IS NULL` rule.

## 10. Validation contract

Mandatory validation should include:

- exactly one parent derived row per admission;
- parent FK and no orphan rule groups or clauses;
- exact null/raw equality with `admissions.gpa_requirement`;
- no trim, rewrite, or Unicode normalization of `raw_value`;
- historical-source rows cannot be `parsed_safe`;
- non-safe parent rows have all stored numeric range fields NULL;
- safe rows are current, overall, Japanese five-point, single-rule rows with no
  subject/AND/OR/branch flag;
- stored tenths are integers within 0–50 and have valid range ordering;
- a conditional group is evaluatable only if the entire group is complete;
- exact input-to-derived row preservation;
- exhaustive unknown/unparsed counts and representative record IDs;
- frozen regression for the current snapshot: 1,199 safe, 707 conditional,
  4,015 do-not-numeric, and 743 strict safe matches at GPA 3.8;
- negative controls for subject, AND, OR, branch, upper/range, non-binding,
  historical, and non-admission numeric examples;
- `PRAGMA foreign_key_check` and `PRAGMA quick_check`.

## 11. Implementation and deferred decisions

- `admission_search_gpa` is populated with exactly one row per admission.
- `admission_search_gpa_rule_groups` and
  `admission_search_gpa_clauses` remain empty in v0.1. Conditional rows retain
  their exact raw value and review classification but are not evaluated.
- `admission_search_gpa_safe` is the only automatic numeric search surface.
- Query GPA values are converted to integer tenths before SQL comparison.
- Build metadata, the build manifest, and the build summary record parser
  contract version, classification counts, and safe-match regression counts.

Deferred decisions:

- Whether `no_gpa_requirement` can be safely distinguished from merely
  `no_numeric_threshold` for every source wording.
- Complete subject ontology and handling of combined subject averages versus
  per-subject minimums.
- Student-context schema for course, school type, qualifications, and other
  branch predicates.
- Whether clause evaluation belongs in SQL, application code, or both.

Until those decisions are approved, only the parent safe-simple subset is
suitable for automatic numeric filtering. The result meaning is exactly
“overall GPA condition safely matched”; it is not an application-eligibility
determination.
