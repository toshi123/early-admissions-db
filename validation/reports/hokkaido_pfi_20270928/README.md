# 北海道大学 私費外国人留学生（学部）入試 再監査完了（2026-09-28）

新baseline: `production_20270928_hokkaido_pfi`。構造化receiptは `production_baseline.json`。

## 募集単位の確定

2027年度募集要項p.1-2の募集人員表に基づく25単位を追加した。内訳は文学・教育・法・経済各1、理学6、医学6、歯1、薬1、工学4、農1、獣医1、水産1。理学の専修分野と医学部保健学科の専攻は個別、工学は4学科単位で各コースを独立募集単位に数えず、農・薬・水産は学部単位とした。全単位の募集人員は「若干名」。

2026-08-13の改組告知は奨学支援担当の部署名変更のみで、募集単位には影響しない。

## 反映・確認

- 北海道大学Master: 49→74行、私費外国人留学生選抜25行。5フラグはPFIのみYes。他4フラグは独立募集単位でないためNo。
- 出願資格、EJU科目・得点、英語提出条件、成績関係書類、書類審査・第2次選考方法、出願日程、入学手続期限を公式要項から反映。数値評定要件は記載がなく、成績証明書を選考資料として使う旨を保持。
- Coverage、UpdateQueue UQ-2027-0045、correction ledger CC-2027-0009、candidate-fields pilotを更新。
- canonical validation / operations validation PASS。Unified 6,617 / Coverage 260 / ResearchRequirements 495。Unifiedの2ビルドはバイト一致。
- SQLite production_ready=true、Site production_ready=true、5フラグと25 record_idの層間保持を確認。Python 148 tests PASS、Site 158 tests PASS、Site production bundle build PASS。

詳細な歴史差分を監査する `run_update_acceptance_audit` は、参照するsuperseded v5.74 Masterがrepository内にないため完了できなかった。SQLite/Siteそれぞれのproduction profile検証は完了し、production_ready=trueを確認した。
