# 2027年度公開検索 baseline v0.1 — 2026-09-29

対象: `reaudit-2027-v0.1`、Coverage台帳260大学一巡時点。canonical Masterの追加・修正はこの公開ポリシー作業では0件。Unified contract v0.3、SQLite v0.3、既存Site-data v0.3のSchemaは変更なし。

## 公開設計

`docs/public_discovery_policy_v0_1.md` を正式仕様とする。確定済み6,699募集単位をSQLite→Site-data v0.3として保持し、個別審査した存在確認済み選抜10件を公開専用CSVから別manifest付きJSONへ生成する。公開状態は `details_pending` 4、`previous_year_reference` 5、`publication_pending` 1。UpdateQueueからの自動公開は行わない。

代表例: 北海道教育大学の学校推薦型選抜（一般・地域指定）は2027年度公式入学者選抜要項で存在を確認。各校・分野等のactual application unitと併願・志望順位は未確定のため、canonicalへ追加せず `details_pending` として検索画面に掲載。帯広畜産大学・小樽商科大学・琉球大学は前年資料を参考表示し、当年度確定条件には使わない。金沢大学医学類特別枠は認可申請中・公表待ちと明示する。

## 本番生成と検証

| 項目 | 結果 |
| --- | --- |
| canonical validation | PASS、exit 0 |
| operations validation（公開用CSV検証を含む） | PASS |
| Unified build | PASS、Master 6,699行 |
| SQLite production build | PASS、admissions 6,699行 |
| Site-data production build | PASS、確定検索6,699件・詳細6,699件、production_ready=true |
| 公開用provisional生成 | PASS、入力10件・掲載10件・重複抑制0件 |
| Python tests | 151 tests PASS |
| Site tests | 17 files / 162 tests PASS |
| Site production build | PASS。現行Site-dataと公開用provisionalを `site/dist/site-data` へ同期 |
| 出力照合 | 276ファイル。Site manifest参照先の欠落0。公開用JSONとmanifestのSHA-256一致、SQLite SHA-256がSite manifestと一致 |

最初のSite production buildは、`site/public/site-data` に残った旧生成物1,349ファイル・約285 MBをViteが全コピーして停滞したため中断した。Vite本体のビルド後、現行生成物276ファイル・約60 MBだけを本番出力へ同期するようコピー工程を修正し、次のビルドは約5秒で完了した。既存の公開ディレクトリに残る旧ファイルは本番 `dist` へ含めず、manifestも参照しない。

ブラウザで確認した表示: 北海道教育大学は評定5.0の安全照合で確定行0件でも暫定掲載1件が見え、詳細条件への適合は未判定と表示された。帯広畜産大学は「前年実績（2026年度）であり、2027年度は変更される可能性があります」と2026年度公式資料リンクを表示。金沢大学は「2027年度実施予定・募集要項公開待ち」、認可後公表と大学公式リンクを表示。確定行は従来どおり大学別結果に表示された。

## 残範囲

UpdateQueue未解決105件の全件を公開用CSVへ移したわけではない。既存Masterと重なるQueue、公式資料の本文を確認できないQueue、複数方式を一つの作業項目にまとめたQueueは、公開対象と粒度を個別に審査する必要がある。今回の10件で公開検索の欠落問題を扱う構造と代表実例を実装したが、全大学・全選抜の網羅性を保証する段階ではない。次の拡充では公開候補の大学公式根拠、既存Masterとの包含関係、選抜名を確認し、版付きCSVに追記する。

旧v5.74比較CSVの欠落は既知の制約。この作業のcanonical/operations/Unified/SQLite/Site受入結果には影響しない。
