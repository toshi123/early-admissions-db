# 2027早期入試DB read-only MCP v0.1

## 目的と公開境界

既存のWeb検索を残したまま、同じ公開Site-dataと `site/src/search.ts` の判定関数を使うStreamable HTTP `/mcp` を提供する。Webは人が一覧と詳細を確認する入口、MCPはChatGPTが構造化条件で検索する入口である。MCPはCSV、SQLite、UpdateQueue、Coverage、その他の内部運用データへアクセスしない。MCP toolは書き込みも任意SQLも提供しない。

確定済みMasterの1行はactual application unit / selection slotの1件で、`record_id` で追跡する。選抜の存在だけが確認済みのprovisionalは `provisional_admissions` に分離し、`total`（確定済み募集単位数）へ加えない。provisionalにはactual application unitの `record_id` を捏造しない。`Unknown`、`No`、`null` は異なる値として維持する。前年参考は `information_year`、`fallback_previous_year`、`previous_year_source_url` で区別する。

## 構成

```text
canonical CSV → Unified → SQLite → 検証済みSite-data v0.3
                                    ├─ Vite Web UI
                                    └─ MCP Worker /mcp
                                         └─ site/src/search.ts（共通検索判定）
```

Webは引き続き静的SPAである。MCP Workerは同じSite-dataをCloudflare static assets bindingから読み、manifestのbuild ID、SHA-256、件数を確認する。検索行はWorker isolate内で一度読み込み、詳細shardは必要なものだけ読み込み最大8 shardを保持する。`free_text` の補助索引は公開詳細shardから `build:mcp` 時に再現生成する派生物で、正本データでも別管理DBでもない。既存Siteの `npm run build` と静的成果物は変更しない。MCP付き成果物は `site/dist-mcp/` に分ける。

## Tools

すべて `readOnlyHint: true`、`destructiveHint: false`。tool結果は短いtextと `structuredContent` の両方を返す。

| Tool | 入力 | 出力 |
| --- | --- | --- |
| `search_admissions` | 大学・都道府県・学問分野・評定・専願・研究・選考方法・共通テスト・締切・補助語・limit/offset | 確定済み募集単位、別枠のprovisional、件数、公式URL |
| `get_admission` | `record_id` | 公開詳細を分野別に整理した値、Site詳細URL、公式根拠URL |
| `get_research_requirements` | `record_id` | 0件以上のResearchRequirements子行 |
| `get_search_facets` | 任意の `university_query`・`academic_field_query` | 既存taxonomy・選択肢・件数・大学名と学問分野原文の候補（各最大50） |

`search_admissions` の入力は `site/mcp/service.ts` のZod schemaを正本とする。主な指定方法は次のとおり。

```json
{
  "prefectures": ["東京都", "神奈川県"],
  "academic_groups": ["information"],
  "applicant_gpa": 3.8,
  "selection_interview": "Yes",
  "exclusive_enrollment_statuses": ["併願可"],
  "limit": 20,
  "offset": 0
}
```

同じfield内はOR、異なるfield間はAND。大学名と学問分野原文は既存選択肢への完全一致を要求し、未登録値は `invalid_argument` とする。`get_search_facets` で利用可能な値を調べられる。`applicant_gpa` は受験生本人の評定平均で、3.8なら安全に判定できる3.8以下の閾値と「評定条件なし」が一致する。条件不明や科目別等の数値判定不能は `applicant_grade_status: "unknown"` として残す。特殊選抜はWebと同じくデフォルトOFFで、`special_filters` 内の複数選択はORである。学校推薦型・総合型はデフォルトで両方対象。

`free_text` は80文字以下の単純な部分一致補助検索。大学、募集方式、学部、研究要件等の公開済みテキストを対象とする。自然言語解釈、任意SQL、semantic検索ではない。JSECなどの原文検索に利用できる。`application_end_from` はWebの「出願締切が指定日以降」と同じ判定で、締切未確認は `deadline_filter_status: "unknown"` として残す。

v0.1では、Webの公開検索選択肢にない実技・集団討論・適性検査、出願開始日の範囲、締切上限、独自sortはMCP filterとして公開しない。これらの原文値は `get_admission` で取得できる。選択肢や検索意味論を推測で増やさない。

通常結果の `total`、`limit`、`offset`、`has_more` は確定済み募集単位にのみ適用する。`results[*].record_id` は常に実在するMaster ID。provisionalは `provisional_count`、`provisional_admissions` に載せ、未確定条件への適合は `condition_match: "undetermined"` とする。検索0件は正常応答。エラーは `invalid_argument`、`record_not_found`、`database_unavailable`、`internal_error` を区別する。

## ローカル実行とInspector

```bash
cd site
npm ci
npm run build:mcp
npm run dev:mcp
```

`http://127.0.0.1:8787/mcp` をMCP InspectorのStreamable HTTP欄に入力する。`initialize`、`tools/list`、4 tool、0件、limit/offset、無効入力、存在しないIDを確認する。公式手順は [OpenAIのMCP serverガイド](https://developers.openai.com/plugins/build/mcp-server) と [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector) を参照。CLIで同じhandshakeを確認する場合は別の端末で `node mcp/smoke-local.mjs` を実行する。

## デプロイとChatGPT接続

MCP付きビルドは `dist-mcp/server/index.js` と `dist-mcp/server/wrangler.json`、Webと同じ公開assetを置く `dist-mcp/client/`、Sites設定 `dist-mcp/.openai/hosting.json` を生成する。Sitesに保存するアーカイブでは `dist/server/index.js` と `dist/client/` に配置する。既存Web Siteは静的配信として維持する。

2026-09-29の公開ゲートでは、既存Siteのv21で `/search` と `/mcp` が404となり、直ちにv20へ戻した。専用Sitesプロジェクト `ea-admissions-mcp` もv1をprivateで保存・配信したが、`/mcp` は404で、Sitesのdeployment statusは `has_mcp=false` だった。このURLはMCP接続先として未承認である。二度の同系統の配信失敗後なので、Sites設定を推測して再配信しない。

別経路として、独立したCloudflare Worker `ea` のGitHub Builds設定を `site/wrangler.jsonc` と `site/mcp/DEPLOY.md` に用意した。Workerは固定した公開Site-dataのコピーを使い、既存Siteは変更しない。Cloudflareへの本番deployと `/mcp` の本番疎通確認は未実施である。

Cloudflare Workerの `/mcp` が本番で疎通した後、ChatGPT側では開発者モードのplugin接続へ実際のWorker URLを登録し、自然言語が構造化tool引数になることを確認する。現時点ではこの登録と自然言語E2Eは未実施。接続手順は [OpenAIの接続ガイド](https://developers.openai.com/plugins/deploy/connect-chatgpt) に従う。公開情報のみを扱うread-only v0.1は認証なしを想定し、内部運用データを資産へ含めない。

## 自然言語E2E inventory

1. 東京か神奈川の情報系で、評定3.8くらいでも出せて面接がある入試を探す。
2. その中で専願ではないものに絞る。
3. 研究実績を出願要件にできる理系入試を探す。
4. JSECが使える入試を探す。
5. 特定 `record_id` の選考方法を詳しく確認する。
6. 同じ `record_id` の研究実績詳細を確認する。
7. 前年参考ではなく2027年度確定情報だけを確認する。
8. 口頭試問があり共通テストがない入試を探す。

モデルが複数条件を正しく選べたかは、tool argumentsと返却したrecord ID・公式URLで評価する。検索結果は推薦順位や合格可能性を表さない。
