# 北海道大学・再監査完了チェックポイント（2026-09-28）

北海道大学の私費外国人留学生（学部）入試を公式募集要項まで再監査し、新しいproduction baselineを作成した。詳細は [`production_baseline.json`](../hokkaido_pfi_20270928/production_baseline.json) と [`README.md`](../hokkaido_pfi_20270928/README.md)。

- 既存Master49行と照合し、私費外国人留学生入試の実出願単位25件を確定・追加。北海道大学合計74行。
- 募集表の粒度は学部・学科等別。理学の専修分野と医学部保健学科の専攻を分け、工学は4学科単位（コースは下位記載）、農・薬・水産は学部単位。
- 5フラグは私費外国人留学生のみYes。IB、帰国生、地域枠、社会人はそれぞれ独立募集枠でない根拠を訂正台帳に記録。
- 出願資格、EJU科目・最低得点、英語提出条件、成績証明書等、選考方法、出願日程・入学手続期限を反映。2026-08-13の組織変更は奨学支援部署名のみ。
- canonical / operations validation PASS。Unified 6,617行・2回のビルドがバイト一致。SQLiteとSiteのproduction profileは両方production_ready=true。
- Python 148 tests、Site 158 tests、本番Site bundle build PASS。25 record_idと5フラグをcanonical→Unified→SQLite→Site詳細で確認。
- 歴史差分用の `run_update_acceptance_audit` は、参照先のsuperseded v5.74 Masterがrepository内にないため未完了。production profileの受入結果とは区別して記録。
