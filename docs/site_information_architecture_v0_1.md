# Early Admissions Search Site information architecture v0.1

## 1. Design objective

The information architecture prioritizes a short structured-search path and a
traceable detail view. It keeps raw values and warnings close to any derived
label so that a counselor can verify the basis of a result.

The proposed experience is read-only and has four public information spaces:

```text
Home / Search
  -> Search results
       -> Admission detail
  -> Data guide / limitations
```

No page makes an application-eligibility determination.

## 2. Route model

| Route | Purpose |
|---|---|
| `/` | Short introduction and primary search entry |
| `/search` | Full filters, result summary, and paginated results |
| `/admissions/:source_dataset/:source_version/:record_id` | One logical admission unit |
| `/about/data` | Data versions, semantics, limitations, and provenance policy |

All three logical-key components in the detail route are URL-encoded. A
display-only SQLite `admission_rowid` must not be used as the durable public
identifier.

Search state should be encoded in query parameters so that a result can be
reloaded and shared. Repeated parameters represent OR values within a field.
For example:

```text
/search?prefecture=東京都&prefecture=神奈川県&stem=1&gpa=3.8&gpa_mode=safe
```

Unknown parameter names or enum values are rejected or ignored with a visible
notice; they are never interpolated into executable query syntax.

## 3. Search-page layout

### 3.1 Desktop

```text
┌──────────────────────┬─────────────────────────────────────────────┐
│ Search filters       │ 5,921件中 66件                              │
│                      │ Active filters / GPA status summary         │
│ Basic                ├─────────────────────────────────────────────┤
│ Application          │ Result card                                 │
│ Selection            │ Result card                                 │
│ Research             │ Result card                                 │
│ GPA                  │ ...                                         │
│                      │ Pagination                                  │
│ [Apply] [Clear]      │                                             │
└──────────────────────┴─────────────────────────────────────────────┘
```

The filter column remains visible while scrolling where viewport size permits.
“Apply” performs one coherent search; changing a checkbox need not issue a
request immediately.

### 3.2 Tablet

Filters occupy a collapsible panel above the results. The active-filter chips
and result count remain visible. Result content uses two-column cards when
space permits.

### 3.3 Mobile

The page opens with a compact summary and a “条件を変更” button. Filters open
as a full-height dialog or sheet with a persistent apply button. Results use
single-column cards. Raw GPA and fallback warnings are never hidden solely due
to viewport width.

## 4. Filter organization

### 4.1 Basic

- University: searchable multi-select; exact values only.
- Institution type: national, public, private values from the contract.
- Prefecture: multi-select, grouped by region for navigation only.
- Academic field: derived broad-group multi-select.
- Detailed academic field: optional exact raw-value multi-select.
- STEM: STEM / non-STEM / no filter. NULL is exposed under advanced state
  inspection if present in a future dataset.
- Selection category: multi-select exact values.

### 4.2 Application conditions

- Exclusive-enrollment status.
- School recommendation required.
- Academic record required.
- Common-test requirement, including the separate `Conditional` value.
- Research-requirement flag.

Each tri-state control provides `Yes`, `No`, and `Unknown` as separate choices.
“No filter” is the empty selection; it is not a fourth stored value.
`common_test_required` is not restricted to that tri-state set: its current
contract also permits `Conditional`, which receives a separate option and
Japanese label “条件付き”. SQL NULL remains distinct from all four values.

### 4.3 Selection methods

- Interview.
- Oral examination.
- Presentation.
- Essay.
- Written examination.
- Common-test use.

The common-test use filter is labeled “選考で共通テストを利用” and is not
merged with “共通テストが出願要件”.

### 4.4 Research/exploration

- Research-requirement flag.
- Research-activity-level common status.

The raw research-activity-level value is shown on detail pages. Site v0.1 does
not infer `required`, `alternative`, or `relevant` classes from child rows.

### 4.5 GPA

The GPA control contains:

1. numeric input from 0.0 to 5.0, at most one decimal place;
2. mode selector (`safe`, `review`, `all`);
3. always-visible explanation of what is and is not evaluated.

Recommended Japanese mode labels:

- `safe`: 安全に数値判定できるものだけ
- `review`: 安全一致＋要確認を表示
- `all`: すべて表示して状態を確認

The result summary separates:

- 全体評定の数値条件に安全一致;
- 複合・条件付きのため要確認;
- 数値では判定できません.

No control or message uses “出願可能” or “出願資格を満たす”.

## 5. Active-filter and empty-state behavior

- Each active predicate is rendered as a removable chip.
- Multiple values in one field are grouped with “いずれか”.
- Different fields are linked visually with “かつ”.
- “条件をすべてクリア” restores an unfiltered search and removes GPA mode.
- Zero results show the active predicates and suggest removing a condition;
  the Site does not invent near matches.
- Invalid or stale shared parameters show which values were ignored.
- A missing Site-data shard is a data error, not a zero-result state.

## 6. Result card contract

### 6.1 Primary block

- `university`
- `faculty_school`
- `department`
- `selection_category`
- `selection_name`
- `capacity`

### 6.2 Context block

- `prefecture`
- raw `academic_field`
- derived academic-field groups and mapping status
- `institution_type`
- `exclusive_enrollment_status`

### 6.3 Conditions block

- full `gpa_requirement`, collapsed visually only when long
- GPA derived-state label for the supplied GPA, if any
- `common_test_required`
- `research_requirement_required`

### 6.4 Selection-method chips

- `selection_interview`
- `selection_oral_exam`
- `selection_presentation`
- `selection_essay`
- `selection_written_exam`

Show `Unknown` distinctly. A missing/NULL value is not rendered as “なし”.

### 6.5 Dates and trust block

- `application_start`
- `application_end`
- source-dataset display label
- fallback warning when `fallback_previous_year=1`

The raw date strings are labeled “原文”. Site v0.1 does not sort or filter
them as normalized dates.

## 7. Admission detail-page contract

The page starts with the identity, fallback banner, and a short warning that
the Site does not determine eligibility. The rest is divided as follows.

### 7.1 Identity and institution

- `source_dataset`, `source_version`, `record_id`
- `admission_year`, `institution_type`
- `university`, `prefecture`
- `faculty_school`, `department`
- raw `academic_field`, derived groups and mapping status
- `stem_flag`
- `selection_category`, `selection_name`, `slot_type`, `capacity`

### 7.2 Application conditions

- `eligibility_graduation`
- `gpa_requirement`
- GPA derived fields: parse status, disposition, condition type, safe bound
  when allowed, feature flags, and parser-contract version
- `english_requirement`
- `subject_prerequisites`
- `school_recommendation_required`
- `school_nomination_limit`
- `school_nomination_limit_total`
- `school_nomination_limit_rule`
- `exclusive_enrollment_status`
- `exclusive_enrollment`
- `common_test_required`
- `common_test_usage`
- `academic_record_required`
- `academic_record_type`
- `academic_record_detail`

### 7.3 Research and exploration

- `research_activity_level_status`
- `research_activity_level_raw`
- `research_requirement_required`
- `research_activity_detail`
- `research_requirement_summary`

Then display every linked ResearchRequirements row in stored order. Each child
shows:

- `admission_id`
- `requirement_code`
- `program_or_competition`
- `required_level`
- `requirement_detail`
- `alternative_allowed`
- `evidence_required`
- child `source_url`
- child `verified_on`

`research_rowid` is retained in the Site detail data to preserve row identity
and exact duplicates, but it is a technical surrogate and is not presented as
a stable public identifier.

The denormalized child university/faculty/department/selection-name values may
be shown under a “source row identity” disclosure when they differ from the
parent. Exact duplicate child rows remain separate and may be labeled “同一内容
の原データ行 1/2” without deduplication.

If the parent flag is `Yes` and no child exists, show “詳細子行なし”. If the
flag is `No` and children exist, show both without changing either value. These
states are informational, not Site validation errors.

### 7.4 Selection methods

- `documents_summary`
- `selection_process`
- `selection_document_review`
- `selection_interview`
- `selection_oral_exam`
- `selection_presentation`
- `selection_essay`
- `selection_written_exam`
- `selection_practical`
- `selection_group_discussion`
- `selection_aptitude_test`
- `selection_common_test`
- `interview_detail`
- `oral_exam_subjects`
- `oral_exam_detail`
- `presentation_detail`
- `essay_detail`
- `written_exam_detail`
- `selection_method_detail`

### 7.5 Dates and periods

- `application_start`
- `application_end`
- `web_registration_period`
- `first_stage_result_date`
- `second_stage_start`
- `second_stage_end`
- `final_result_date`

All values are displayed exactly as stored and marked as raw source wording.

### 7.6 Verification and completeness

- `source_status`
- `detail_completeness_status`
- `detail_completeness_raw`
- `verification_grade`
- `verified_on`
- `notes`

The common completeness status and source raw value are adjacent but not
collapsed into one field.

### 7.7 Publication and fallback

- `information_year`
- `publication_status`
- `fallback_previous_year`
- `current_year_release_expected`
- `fallback_note`
- `previous_year_source_url`

When fallback is active, this section is also summarized in the banner at the
top of the page.

### 7.8 Provenance

- `source_url`
- `guideline_url`
- `schedule_url`
- `exclusive_enrollment_evidence`
- `exclusive_enrollment_evidence_page`
- `exclusive_enrollment_evidence_url`

Null links are labeled as not stored, not as unavailable on the university
website.

## 8. Japanese state labels

Use context-specific labels but preserve state identity:

| State | Short chip | Expanded help |
|---|---|---|
| `Yes` | あり / 必要 | 元データの肯定値 |
| `No` | なし / 不要 | 元データの明示的な否定値 |
| `Unknown` | 不明 | 公開資料から確認できない状態 |
| SQL `NULL` | — | 未記録または非該当。不明・なしとは異なる |
| fallback | 前年度情報 | 指定年度の確定情報ではないため公式資料を要確認 |

Tooltips alone are insufficient; essential meaning must be visible or
available through an accessible disclosure.

## 9. Navigation and provenance affordances

- The result card links to one admission detail, not directly to an external
  site.
- The detail page contains labeled official-source links.
- Browser back/forward preserves search filters and page position when
  practical.
- A “検索結果へ戻る” control preserves the full query string.
- `/about/data` explains versions, rebuild date, hashes, GPA limits, fallback,
  Unknown/NULL/No, and the no-eligibility guarantee.

## 10. Loading and error states

| State | Required behavior |
|---|---|
| Initial | Show controls and a neutral invitation to search, or the full unfiltered count |
| Loading | Preserve filters; mark results as updating |
| Zero results | Show active conditions; no inferred alternatives |
| Invalid query | Identify invalid values and keep valid filters |
| Missing detail | Report data inconsistency with logical key; do not show another record |
| Manifest mismatch | Refuse to search and show a dataset-version error |
| External link missing | Show “URL未記録”; do not fabricate a university URL |

## 11. Recommended v0.1 page sequence

1. User opens `/search`.
2. User selects one or more structured filters.
3. If GPA is entered, the mode defaults to strict safe matching.
4. The Site displays result counts and explicit filter logic.
5. The user reviews raw GPA/fallback/status information on cards.
6. The user opens one logical admission detail.
7. The user verifies full conditions and follows official-source links.

This sequence deliberately places official verification after narrowing but
before any real application decision.
