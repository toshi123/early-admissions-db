# 公開検索UI v0.2 検証記録 — 2026-09-29

ブランチ: `reaudit-2027-v0.1`。起点: `f9d4571`。canonical Master、Coverage、UpdateQueue、Unified contract、SQLite Schema、Site-data v0.3 Schemaは変更なし。旧provisional v0.1入力・Schemaも保存し、版付きv0.2へ移行した。

## 生成物と件数

- Site-data production build: PASS、production_ready=true。確定検索・詳細とも6,699行。
- provisional: 10件掲載。内訳 `details_pending` 4、`previous_year_reference` 5、`publication_pending` 1。元の10件の存在・公式URLは変更なし。方式・特殊選抜タグのみ公式で確認済みの名称・概要に対応させた。
- 特殊選抜索引: 6,699件、4フラグをSQLiteから欠落なく投影。`returnee_flag` 337、`international_baccalaureate_flag` 44、`private_foreign_student_flag` 152、`adult_selection_flag` 30 の真値。複数フラグを持つ行はそれぞれに算入する。
- Site manifest、provisional manifest、特殊選抜索引manifestのSQLite SHA-256一致。両JSONの実ファイルSHA-256一致。Siteの読み込み時にも件数・行IDを照合する。

## 検証

| 項目 | 結果 |
| --- | --- |
| operations validation | PASS（provisional v0.2を含む） |
| Python tests | 153件 PASS |
| Site tests | 18 files / 170 tests PASS。旧25件Python検索オラクルも一致 |
| Site production build | PASS。既知のExcel出力bundleサイズ警告のみ |
| canonical差分 | なし |

ブラウザ: ローカル`vite preview`で北海道教育大学を検索し、同じ大学グループ内に確定6件と`details_pending` 1件、計7件を確認。provisionalには2027年度公式リンク、前年参考の明示、詳細確認中の状態表示がある。公式リンクのリンク先ページで、2027年度入学者選抜要項と学校推薦型選抜募集要項の掲載を確認した。評定3.8・締切2026-10-01では確定3件＋暫定1件を表示し、暫定行に締切・評定未確認の注記が出る。帰国生とIBの複数選択で検索結果総数が338件から382件へ増えること、方式を両方OFFにすると検索送信が無効になり案内が出ることを確認した。Chrome 390×844相当では検索・結果ページとも横はみ出しなし、見出しと件数が折り返されることを確認した。

公開中の `https://ea.ussapao.chatgpt.site/search` は現在Googleログイン画面へ遷移するため、未認証状態での検索結果UIの直接比較はできなかった。ログイン画面の現行アクセス状態とローカルSiteの表示差を確認した。認証済み本番UIとの比較は別途必要。production deployは行っていない。

残範囲: 旧UpdateQueue未解決候補のprovisional追加審査、留学生一般を私費外国人留学生以外も含めて安全に分類する根拠設計、provisionalの候補リスト／Excel出力対応は未実装。今回の候補リストとExcel出力は従来どおり確定募集単位に限定し、既存Siteテストで回帰確認した。

## 検索画面のモバイルUI微調整

同日、特別選抜の折りたたみに都道府県と同じ回転矢印を追加し、390px幅以下を含むモバイル表示で検索ボタンを画面下部のセーフエリア対応バーに固定した。フォーム末尾とフッターの余白により「条件をクリア」と本文が固定バーに隠れないことを確認した。出願締切の「今日以降」ショートカットを削除し、指定日の入力だけを残した。データと検索判定は変更していない。

追加した回帰テストを含むSite testsは18 files / 173 tests PASS、Site production build PASS。Chromeの390×844px表示で矢印の180度回転、固定ボタン、横はみ出しなし、ページ末尾の重なりなし、固定ボタンから検索結果への遷移を確認した。実スマートフォンのソフトキーボード表示時は未確認。
