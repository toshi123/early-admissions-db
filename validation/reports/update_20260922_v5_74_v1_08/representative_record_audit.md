# Representative record audit

## `RIKKYO-2027-SCI-03`

- The record exists in both shidai v0.97 and the incoming v1.08 master.
- Stable identity/display fields remain unchanged: university, faculty, department,
  selection category, and selection name.
- `fallback_previous_year=False` and `information_year=2027` remain unchanged.
- `research_requirement_required=No` remains unchanged.
- `verified_on` changes from `2026-09-20` to `2026-09-21`.
- The GPA raw value changed from the production-reviewed exact string to:
  `全体の評定平均値3.8以上。出願条件5(a)では学科指定科目の評定平均値4.5以上（高卒同等資格の一部は評定条件なし）。`
- The English-requirement raw value also changed.

Both changed raw strings fail closed because neither is an exact key in the
current production crosswalk. The existing strict-safe GPA and grade-requirement
semantic fixtures were not altered. Human review is required before this record
can regain a derived numeric/status classification in a future crosswalk version.
