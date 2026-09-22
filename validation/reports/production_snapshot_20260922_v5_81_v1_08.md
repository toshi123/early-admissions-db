# Production snapshot promotion receipt — 2026-09-22

Status: `production_promoted`

This receipt records the reproducible promotion of kokkoritsu `5.81` and shidai `1.08`. The previous production releases, kokkoritsu `5.61` and shidai `0.97`, remain immutable. The superseded kokkoritsu `5.74` source bundle was not used.

## Human-review decision gate

All 8 representative checks passed across the human decision artifact, versioned crosswalk, and candidate database:

1. `RIKKYO-2027-SCI-03`: Grade required; overall GPA floor 3.8; additional grade conditions true; strict GPA `conditional_review`; English required.
2. 九州大学 経済学部 経済工学科: Broad `economics`; no `engineering` membership.
3. 金沢大学 人間社会学域 地域創造学類: Broad `sociology_community`; Subcategory `community_regional_society`.
4. 慶應義塾大学 法学部 政治学科: Broad `law_politics_policy`; Subcategory `politics`; no `law` membership.
5. 慶應義塾大学 法学部 法律学科: Broad `law_politics_policy`; Subcategory `law`; no `politics` membership.
6. 明治大学 文学部 地理学専攻: Broad `humanities_culture_history`; no `history_folklore` membership.
7. 法政大学 文学部 地理学科: Broad `humanities_culture_history`; no `regional_studies` membership.
8. `RIKKYO-2027-LIT-EDU`: 「英語資格または他言語資格」をEnglish `required`として保持。

## Production sources

| Dataset | Version | Master | Coverage | ResearchRequirements |
|---|---:|---:|---:|---:|
| kokkoritsu | 5.81 | 4,011 | 187 | 281 |
| shidai | 1.08 | 2,400 | 73 | 214 |
| Total | — | 6,411 | 260 | 495 |

Universities: 250. Canonical CSVs are byte-identical to their new versioned release files.

Source validation: errors 0, warnings 1,167, informational 3,292. Warnings remain a known quality backlog; no source fact or severity was changed. Warning counts are `DETAIL_COMPLETENESS_UNMAPPED=767`, `PROVENANCE_URL_MISSING=55`, `RESEARCH_ACTIVITY_LEVEL_UNMAPPED=281`, `RESEARCH_DENORMALIZED_FIELD_MISMATCH=10`, `RESEARCH_EXACT_DUPLICATE=4`, `RESEARCH_REQUIRED_WITHOUT_CHILD=45`, and `WHITESPACE_PADDING=5`.

## Crosswalk contracts

| Layer | Version | SHA-256 |
|---|---:|---|
| GPA | 0.2 | `bc6a5416f4b4efe3ce86ed10947e52f556d2a370d6472a2397bd8dbb6c887ffe` |
| Grade | 0.2 | `6095c2eebfa37a2a97359fa91f270e6a092bb77b06d23dad805a959710aa57c3` |
| English | 0.2 | `5dc097fed020fd2f1c6c3ae963ffa82f7487eca22993c7b2430a8d764aedbaff` |
| Academic-field v0.1 compatibility | 0.2 | `74162005e676a89c515a95d24bb78548df7ce6709fb04eb28c3ff14b57c99ab8` |
| Academic-field v0.2 raw mapping | 0.3 | `e59a29c0bfadd5a4e633d2cf64ec9f2a2ae1b969b8a6302d6f2886a5a5a01a7b` |
| Academic-field v0.2 context mapping | 0.3 | `12eaf7a9e4870f5bf7c2381445abc007c5e00f3be5f601ad9198c60a14e0a5a8` |
| Prefecture taxonomy | 0.1 | `d91fe231cde5698b074a8c86328dd61499aeccac32da2472e36a0e184457f906` |
| Prefecture crosswalk | 0.1 | `46a5c032e2fc79cd2d1cbfbc33b1dac5952e70300b557fd1884558d52153481c` |

Academic-field taxonomy remains v0.2: Broad SHA `ba33e98fa58196a3b530b26ce47d036073bdbf929a6fd16636e2ff58afe72ebd`; Subcategory SHA `9813972ec7698cd923fbbfb9bbee16bff7af12b371f23f5e733f6d391b92576e`.

## Rebuilt artifacts

| Artifact | Rows / size | SHA-256 or Build ID |
|---|---|---|
| Unified Master | 6,411 | `2af3a834bb00fd93235f711c0f50896c4158b633d550d333b1aad9667bf5985e` |
| Unified Coverage | 260 | `4457e7cddb9b9bde8a5aa414dcbadeda9ac6d05ed45ef0794354b2883c837e2b` |
| Unified ResearchRequirements | 495 | `0aae717876bef3c1ba8645fcbf7e15190ce9bc8521badb83d5f154b6e3782fd9` |
| Unified manifest | — | `66431d3ee6dca98bdb462a6838366017a8d02d25ce138e810844987f43b65eba` |
| SQLite | 37,318,656 bytes | `3f7cda8c9788f601c86991b7d0ccb19fc516638ef9c19d91447fd71d2ab0bbe7` |
| Site-data | search 6,411; details 6,411; research 495 | Build ID `f23d7efe23536453f276` |
| Site-data manifest | — | `27a7ab931f71ccbd701b92c3210f226ec3b4fac39d7433c94696cea95b6c497a` |

Unified and Site-data deterministic rebuilds passed. The SQLite SHA/size and Site-data Build ID/manifest SHA exactly match the isolated strict-production receipts.

## Strict validation

- Master PK duplicates 0; Coverage mismatches 0; Research orphan FKs 0.
- Research exact duplicate excess rows 4 preserved.
- Raw/provenance equality and tri-state validation passed.
- SQLite `quick_check=ok`; `foreign_key_check=0`; STRICT, FTS5, and trigram passed on SQLite 3.53.0.
- Unmapped counts: Grade 0; English 0; Academic-field v0.1 0; Academic-field v0.2 0; Prefecture 0; new GPA 0; Academic-field context review 0.
- GPA unparsed 227 remains an accepted, fail-closed contract state.

## Derived counts

- English: required 467; not_required 1,265; review_required 296; unknown 4,383; unmapped 0.
- Grade: required 2,373; not_required 707; review_required 1,404; unknown 1,910; not_applicable 17; unmapped 0.
- GPA strict-safe: 3.0=72; 3.5=499; 3.8=763; 4.0=1,175; 4.5=1,258.
- Academic-field v0.2: Broad coverage 6,400/6,411; Subcategory coverage 5,317/6,411.

## Search and application validation

- Frozen structured search: 25/25 PASS; database bytes unchanged.
- Representative counts: GPA 3.8 strict-safe 763; Grade required 2,373; Overall GPA 3.8 871; English required 467.
- Academic Broad counts: law_politics_policy 114; economics 173; business_commerce 191; psychology 31; languages 197; natural_sciences 762; engineering 1,696; information 892.
- Repository tests: 141/141 PASS.
- Frontend tests: 151/151 PASS.
- Responsive focused tests: 11/11 PASS.
- Production frontend build: PASS.

## Atomicity and scope

A local rollback checkpoint was created before promotion. Derived SQLite and Site-data were published only after validation, with no WAL/SHM sidecars. Generated large artifacts remain ignored. No ChatGPT Sites Version was saved, no deployment was updated, and no access or sharing setting was changed.
