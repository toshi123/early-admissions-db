# English requirement exact crosswalk v0.2

Status: active reviewed mapping contract
Reviewed on: 2026-09-22
Candidate sources: kokkoritsu 5.81 + shidai 1.08

## Scope

Version 0.2 extends the preserved v0.1 exact crosswalk with 66 distinct raw
values from the 6,411-row update candidate. Canonical, release, unified, and
admission raw text are unchanged. Runtime classification remains exact-only:
no trimming, token matching, numeric parsing, regular expressions, or frontend
inference is permitted.

The human-decision authority is
`validation/reports/update_20260922_v5_81_v1_08/english_requirement_human_review_decisions_v0_2.csv`.
The deterministic output is
`schema/english_requirement/english_requirement_crosswalk_v0_2.csv`; v0.1 is
retained for production snapshot reproduction.

## Search semantics

The question answered is whether an admission has an English qualification or
English ability-evidence condition, not whether English is the only possible
route.

- `required`: the exact reviewed admission wording contains an English
  qualification, score, test, or evidence condition. An English-or-other-
  language alternative remains `required` because English is an available
  qualifying route. A generally required English condition with narrowly
  defined exemptions also remains `required`.
- `not_required`: the exact reviewed wording establishes that an external
  English qualification is unnecessary, or merely desirable/non-binding.
- `review_required`: alternatives or branches prevent the raw text from
  establishing whether the English condition applies. It is never included in
  either binary search branch.
- `unknown`: the 2027 external requirement is unpublished or cannot be safely
  established. It is not equivalent to `not_required`.
- SQL NULL is classified as missing/unknown. A new non-NULL value absent from
  the crosswalk is `unmapped` and fails closed.

Only exact-crosswalk `required` and `not_required` are `safe_exact`.

## Review receipt

The 66 reviewed distinct values comprise 57 `required`, 3 `not_required`, 5
`review_required`, and 1 `unknown`. The review packet is retained unchanged as
history. The manifest records the previous/new hashes, review metadata, counts,
and candidate source versions.
