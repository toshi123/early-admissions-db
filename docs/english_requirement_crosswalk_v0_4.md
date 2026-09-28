# English requirement crosswalk snapshot v0.4

This is a versioned snapshot of the v0.3 English requirement mapping contract. It preserves every v0.3 decision and adds six exact raw values surfaced by the 2027 Muroran Institute of Technology and Obihiro University reaudit. The SQLite parser contract remains `0.3`; no SQLite schema or canonical raw text was changed to accommodate these mappings.

| Raw value | Mapping | Basis |
| --- | --- | --- |
| 個別の英語資格要件なし。 | not_required | Muroran 2027 comprehensive-selection guide states no individual English qualification requirement. |
| 英語資格要件の詳細は募集要項の資格経路別条件を参照。Unknown。 | review_required | Muroran 2027 returnee guide has eligibility-path-specific routes; a single English status is not established. |
| TOEFL iBT 32点以上（旧スコア換算、2024年12月～2026年12月受験、My Best Scores不可）。 | required | Muroran 2027 private-foreign-student guide specifies a score floor. |
| TOEFL又はIELTS Academic-moduleのスコア提出（2024-04-01以降受験）。 | required | Obihiro 2027 returnee guide requires an external score submission. |
| TOEIC L&R（公開テスト）のスコア提出。100点換算（スコア÷6.5、650点以上は100点）。 | required | Obihiro 2027 social-selection guide specifies the score submission and scoring formula. |
| TOEFL又はIELTSの外部英語試験成績を提出（英語母語者を除く）。 | required | Obihiro 2027 IB guide requires the external score except for native English speakers. |

Official sources:

- Muroran comprehensive/returnee guide: https://muroran-it.ac.jp/uploads/sites/6/2026/08/2027tokubetsu-1.pdf
- Muroran private-foreign-student guide: https://muroran-it.ac.jp/uploads/sites/6/2026/08/2027shihiyoukou-1.pdf
- Obihiro returnee guide: https://www.obihiro.ac.jp/wp/wp-content/uploads/2026/08/R9kikoku.pdf
- Obihiro social-selection guide: https://www.obihiro.ac.jp/wp/wp-content/uploads/2026/08/R9syakai.pdf
- Obihiro IB guide: https://www.obihiro.ac.jp/wp/wp-content/uploads/2026/08/R9Baccalaureate.pdf
