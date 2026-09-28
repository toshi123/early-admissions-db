# 北海道地区再監査バッチ完了（2026-09-28）

## 反映結果

- 室蘭工業大学：既存2行に追加15行、計17単位。総合型I/IIは学科×一般/女子枠、帰国生は学科別、夜間主・社会人・企業推薦は各要項上の方式別枠、私費外国人は学科別。社会人と企業推薦の出願日程・選抜方法を区別して記録。確認できない項目はUnknown。
- 帯広畜産大学：既存4行に帰国生1、社会人1、IB2の計4行を追加し計8行。私費外国人留学生要項は2027年度版が10月中旬公表予定のためcanonical未追加。UQ-2027-0048で保留。
- 旭川医科大学：既存3行を2027年度公式要項・日程と照合。選抜単位と主要詳細に差分なし。検証日・確認記録のみ更新、行追加・事実修正なし。
- 小樽商科大学：対象の2027年度詳細要項未確認。canonical変更なし。公開後の再確認条件をCoverage・UpdateQueueに記録。
- 北見工業大学：2027年度学校推薦型詳細要項未掲載。canonical変更なし。公開後の再確認条件をCoverage・UpdateQueueに記録。

## 検証

- canonical validator：PASS、errors=0（warnings=1236）
- operations validator：PASS
- Unified：PASS、Master 6,638行 / Coverage 260行 / ResearchRequirements 495行。2回の生成はbyte-identical。
- SQLite production：PASS、6,638 admissions、production_ready=true、English unmapped=0
- Site data production：PASS、search/details各6,638行、production_ready=true
- 追加19行の5特殊選抜フラグ：SQLite・Site detailで全行一致
- Python tests：149 passed
- Site tests：16 files / 158 passed
- Site frontend production build：PASS
- `run_update_acceptance_audit`：旧版比較用 `sources/incoming/2026-09-22/kokkoritsu_v5_74_superseded/kokkoritsu_early_admissions_2027_master_v5_74.csv` が存在せず完了不可。旧版比較ファイル不在は既知制約として記録し、production manifestの判定とは分離。

## Crosswalk

英語要件crosswalkはv0.3を保存したままv0.4スナップショットを追加。新規6原文を追加し、帰国生の経路別条件はreview_required、明示された不要・提出要件は公式要項に基づいて分類。English parser contractとSQLite Schemaは0.3のまま。
