# Early Admissions Search Site requirements v0.1

## 1. Status and authority

This document defines the requirements for a future read-only search Site over
the 2027 early-admissions data. It is a design contract, not an implementation.

The data authorities, in precedence order, are:

1. `docs/unified_data_contract.md` and
   `schema/unified/early_admissions_unified_schema_v0_1.json`;
2. `docs/gpa_search_design_v0_1.md` and the implemented GPA derived layer;
3. `docs/sqlite_design_v0_1.md` and the published read-only SQLite artifact;
4. this Site contract, which may define presentation and search behavior but
   may not reinterpret admission facts.

The current validated snapshot contains 5,921 admissions, 259 coverage rows,
and 437 ResearchRequirements rows. These counts describe the present snapshot;
they are not hard-coded requirements for later rebuilds.

## 2. Purpose

The Site should let guidance counselors, teachers, and students narrow the
dataset with explicit structured conditions, inspect the raw admission facts,
and follow provenance links. It should make uncertainty and non-evaluated
conditions visible.

Site v0.1 is not an eligibility engine. A result means only that the stored
fields matched the selected filters. It does not mean that the applicant can
apply or satisfies every condition.

## 3. Non-negotiable data semantics

- The Site is read-only.
- Canonical, release, unified CSV, and published SQLite artifacts are never
  edited by the Site.
- Different filter fields are combined with AND.
- Multiple selected values within one field are combined with OR.
- `NULL`, `Unknown`, and `No` remain different states.
- Raw text is not trimmed, rewritten, translated into a stronger claim, or
  filled by inference.
- Raw dates and periods are displayed as stored. Site v0.1 does not parse or
  compare dates.
- `common_test_required` and `selection_common_test` remain separate concepts.
- GPA numeric matching is limited to `parsed_safe` rules in
  `admission_search_gpa_safe`.
- ResearchRequirements child rows, including exact duplicates, remain visible
  as separate source-derived rows.
- The ResearchRequirements parent flag and child-row presence are not forced
  to agree.
- `fallback_previous_year=1` is always disclosed before a user interprets the
  row as current-year information.
- Source URLs and logical record identity remain available on the detail page.

## 4. Intended users and primary tasks

### 4.1 Guidance counselor

- Narrow a large candidate set by region, institution type, field, selection
  type, required documents, selection methods, and GPA.
- Identify records that need manual review instead of receiving a false
  definitive answer.
- Open official source pages and record provenance for follow-up guidance.

### 4.2 Teacher

- Compare admissions that require a school recommendation, academic record,
  interview, oral examination, presentation, essay, or written examination.
- Review raw wording for GPA, research activity, and selection details.

### 4.3 Student

- Find potentially relevant admissions using understandable filters.
- Understand why an admission appears in a GPA result.
- See clear warnings that other application requirements remain unchecked.

## 5. Scope of Site v0.1

### 5.1 Required

- Structured filter search over the published SQLite-derived Site dataset.
- Shareable/search-restorable filter state.
- Result count and active-filter summary.
- Paginated result list.
- Admission detail pages with raw conditions, dates, provenance, completeness,
  and fallback information.
- GPA safe/review/non-evaluable distinctions.
- Academic-field group search using a versioned exact-value crosswalk, once the
  crosswalk is reviewed and frozen.
- Direct access to the stored raw `academic_field` value on every result.
- Responsive behavior for desktop, tablet, and mobile.
- Keyboard-accessible controls and non-color-only status communication.
- Build/version information and a short data-use disclaimer.

### 5.2 Explicitly deferred

- AI or natural-language search.
- OpenAI API integration.
- FTS-dependent core search.
- Automatic evaluation of conditional GPA rules.
- Date normalization, deadline comparison, or reminder logic.
- Automatic interpretation of ResearchRequirements into new requirement types.
- User accounts, saved favorites, personal profiles, and application tracking.
- Site-side edits, annotations, or correction submissions.
- Framework selection, package installation, deployment, or hosting setup.

## 6. Structured-search requirements

The following filters are required. Values are exact contract values unless a
separate derived-layer contract is named.

| UI group | Filter | Match behavior |
|---|---|---|
| Basic | `university` | Exact value; typeahead may assist selection |
| Basic | `institution_type` | Multi-select exact enum |
| Basic | `prefecture` | Multi-select exact value |
| Basic | academic-field group | Multi-select derived groups; exact crosswalk only |
| Basic/advanced | raw `academic_field` | Multi-select exact raw value |
| Basic | `stem_flag` | `1`, `0`, or no filter; SQL NULL is neither |
| Basic | `selection_category` | Multi-select exact value |
| Application | `exclusive_enrollment_status` | Multi-select exact enum |
| Application | `school_recommendation_required` | Multi-select tri-state |
| Application | `academic_record_required` | Multi-select tri-state |
| Application | `common_test_required` | Multi-select enum: `Yes`, `No`, `Conditional`, `Unknown`; NULL stays separate |
| Application | `research_requirement_required` | Multi-select tri-state |
| Research | `research_activity_level_status` | Multi-select common status |
| Selection | `selection_interview` | Multi-select tri-state |
| Selection | `selection_oral_exam` | Multi-select tri-state |
| Selection | `selection_presentation` | Multi-select tri-state |
| Selection | `selection_essay` | Multi-select tri-state |
| Selection | `selection_written_exam` | Multi-select tri-state |
| Selection | `selection_common_test` | Multi-select tri-state |
| GPA | supplied GPA and mode | Existing GPA derived-layer contract |

Within a field, an explicit `Unknown` choice selects only `Unknown`; clearing a
field means no predicate. `Conditional` is also its own value where the source
contract permits it, notably `common_test_required`. Site v0.1 does not add a
hidden predicate that drops NULL, Unknown, or Conditional rows unless the
selected filter requires it.

### 6.1 GPA input and modes

The user may enter a Japanese five-point GPA with at most one decimal place.
The value is converted to integer tenths for the authoritative comparison.

The recommended modes are:

| Mode | Japanese UI label | Returned rows |
|---|---|---|
| `safe` | 安全に数値判定できるものだけ | Matching `parsed_safe` rows only |
| `review` | 安全一致＋要確認を表示 | Safe matches plus conditional/review rows; conditional rows are not evaluated |
| `all` | すべて表示して状態を確認 | All rows passing other filters, annotated with GPA state |

`safe` is the default when GPA is supplied. The UI must explain that GPA is
only one condition and that a safe match is not an eligibility determination.

### 6.2 Search result summary

For every search, display:

- total matched admissions;
- number of distinct universities;
- active filters;
- source-dataset counts;
- when GPA is supplied: safe matches, conditional/review rows, and not
  numerically evaluable rows within the selected mode;
- current page and page size.

Counts must be computed from the same filtered result set and GPA mode as the
visible list. A count must not silently include rows excluded from the list.

### 6.3 Ordering and pagination

The default order should be deterministic:

1. prefecture;
2. university;
3. faculty/school;
4. department;
5. selection category;
6. selection name;
7. logical key (`source_dataset`, `source_version`, `record_id`).

Site v0.1 may offer alternate orders such as university or application-start
raw text, but it must not label raw-date lexical ordering as chronological.

## 7. Result-list requirements

Each result must show, without requiring the detail page:

- university;
- faculty/school and department;
- selection category and selection name;
- capacity;
- prefecture;
- raw academic field and derived group chips;
- exclusive-enrollment status;
- raw GPA requirement and GPA derived status;
- common-test-required and research-requirement-required status;
- interview, oral-exam, presentation, essay, and written-exam indicators;
- raw application start and end values;
- source-dataset label;
- a fallback warning when applicable.

Long raw text may be visually collapsed in the list, but the underlying value
must not be truncated in the Site data. The detail page must expose the full
value.

## 8. Detail-page requirements

The detail page must display the complete admission unit, organized into:

- identity and institution;
- capacity and selection type;
- application conditions;
- GPA raw and derived interpretation;
- research/exploration information and all child rows;
- selection methods and their details;
- raw dates and periods;
- verification/completeness;
- current-year/fallback state;
- provenance URLs and source identity.

The page must not merge child rows solely because they are exact duplicates.
It may label their ordinal position for display. Parent/child discrepancies
are presented as source-model information, not as an error repaired by the
Site.

## 9. Presentation of special states

### 9.1 Tri-state and NULL

| Stored state | Default display | Meaning |
|---|---|---|
| `Yes` | あり / 必要 / 利用あり | Field-specific affirmative state |
| `No` | なし / 不要 / 利用なし | Explicit negative state, not Unknown |
| `Unknown` | 不明（公開資料で確認できず） | Source-level uncertainty |
| SQL `NULL` | —（未記録または非該当） | No stored value; not Unknown or No |

The exact Japanese verb should follow the field. For example,
`common_test_required=No` is “共通テスト要件なし”, while
`selection_common_test=No` is “選考での共通テスト利用なし”.

### 9.2 GPA labels

| Derived state | Japanese label |
|---|---|
| safe match | 全体評定の数値条件に安全一致 |
| safe no match | 全体評定の数値条件には一致せず |
| conditional/review required | 複合・条件付きのため要確認 |
| not numerically evaluable | 数値では判定できません |
| historical reference | 前年度参考値のため数値判定対象外 |
| no GPA supplied, safe rule | 全体評定の数値条件あり（GPA未入力） |

Every safe-match label must be accompanied by: “全体評定の単純な数値条件
だけを照合しています。出願可否や他の条件充足を示しません。”

### 9.3 Previous-year fallback

For `fallback_previous_year=1`, display a prominent warning in the list and at
the top of the detail page:

> 前年度情報を参照しています。2027年度の公開状況と最新の公式資料を
> 必ず確認してください。

Show `information_year`, `current_year_release_expected`, `fallback_note`, and
`previous_year_source_url` when present. Do not blend previous-year values into
current-year labels without this warning.

## 10. Provenance and trust

- Every detail route uses the logical key
  (`source_dataset`, `source_version`, `record_id`).
- Show `source_url`, `guideline_url`, `schedule_url`, and
  `exclusive_enrollment_evidence_url` as separate links when present.
- Show `information_year`, `publication_status`, `verified_on`,
  `verification_grade`, and completeness status/raw.
- External links open with a visible external-link affordance and safe browser
  attributes.
- The Site footer identifies the unified contract version, SQLite schema
  version, source versions, Site-data build timestamp, and input hashes.
- No admission fact is hard-coded in page source or UI components; facts come
  from the generated Site data.

## 11. Accessibility and responsive behavior

- All filters have programmatic labels and keyboard operation.
- Status is communicated by text and icon, not color alone.
- Focus order follows visual order; a “results” heading receives focus after a
  submitted search when appropriate.
- Tables that overflow on mobile become labeled cards or horizontal regions
  without dropping fields.
- Touch targets are at least comfortably tappable; filter sections are
  collapsible on small screens.
- Japanese text remains selectable and is not embedded in images.
- Links expose their destination type (“募集要項”, “日程”, etc.).

## 12. Performance and read-only safety

- Initial search controls should become usable without loading all detail text.
- Search rows and detail rows should be separate Site-data projections.
- Page changes and filter changes must not mutate server data.
- Site code has no SQL write path and no artifact upload/edit endpoint.
- Generated Site data is content-addressed or manifest-verified before publish.
- The Site build must fail if row counts, logical keys, input hashes, or schema
  versions do not match its declared inputs.

## 13. Rebuild and publication flow

The required flow is:

```text
canonical
  -> source validation
  -> unified CSV build and validation
  -> SQLite build and validation
  -> Site-data projection build and validation
  -> Site build
  -> human review
  -> save a deployment candidate
  -> publish
```

The Site-data projection is always rebuilt from the published SQLite input; it
is never hand-edited. Publication is permitted only after its manifest and
representative structured-query regressions pass.

## 14. Acceptance criteria for a future v0.1 implementation

- All required filters are available and obey AND-between/OR-within semantics.
- GPA 3.8 strict-safe results equal the validated SQLite helper semantics.
- Unknown and NULL can be distinguished in both display and filter behavior.
- A record with fallback data cannot be mistaken for confirmed current-year
  data in list or detail views.
- Every SQLite admission logical key appears exactly once in the Site detail
  projection.
- All ResearchRequirements rows appear under the correct logical parent and
  exact duplicates remain count-preserved.
- Raw GPA, academic-field, date/period, and provenance values round-trip
  exactly from SQLite into the Site data.
- Core structured search works with FTS disabled.
- No canonical, release, unified, or SQLite artifact changes during Site build.
- Automated tests cover search composition, GPA modes, special-state display,
  fallback, detail routing, and corrupt/mismatched manifest rejection.

## 15. Decisions required before implementation

1. Approve the academic-field taxonomy and its exact-value crosswalk.
2. Choose whether the initial audience is workspace-only, invited users, or
   public; this changes privacy and publication review requirements.
3. Approve the static Site-data file shape and maximum initial payload budget.
4. Decide whether raw academic-field filtering is visible by default or under
   advanced filters.
5. Decide whether Site v0.1 needs CSV export; it is not required by this
   contract.
6. Confirm the desired default GPA mode (`safe` is recommended).
7. Confirm whether non-GPA search should show GPA state chips by default.
