# threads-auto-post-template

Threadsの投稿運用を **PDCAごとエージェント化** し、Claude APIで完全自動化するテンプレートです。
GitHub Actionsだけで動くので、サーバー不要・人の操作ゼロで回せます。

## PDCAエージェント構成

各タスクを1つのエージェント(Pythonモジュール)に分け、`pdca_manager.py` / `measure.py` が統括します。

| 段階 | エージェント | 役割 |
|------|------------|------|
| **P** リサーチ | `agents/research.py` | Web検索で分野の最新情報・競合の切り口を調べ、4枠分の投稿ネタを出す |
| **D** 作成 | `agents/writer.py` | リサーチを元に **5ツリー型** (メイン+返信4) を4枠ぶん生成 |
| **D** 校正 | `agents/proofreader.py` | 誤字脱字・AIっぽい言い回し・不要な記号をチェックして修正 |
| **D** 投稿 | `post_threads.py` | 毎日 **7:00 / 12:00 / 19:00 / 21:00** の4投稿を完全自動化 |
| **C+A** 計測 | `agents/analytics.py` | Threadsインサイトを取得し、数値の良い投稿の傾向を抽出 |
| **A** 反映 | (同上) | 傾向を `prompts/learnings.md` に自動保存 → 次回の生成へ自動反映 |

3つのGitHub Actionsが時間で連動します。

| ワークフロー | 起動 | 中身 |
|------|------|------|
| `pdca-generate.yml` | 毎日 05:00 JST | リサーチ→作成→校正 で当日4枠を生成 |
| `post-scheduled.yml` | 毎時0分 | 予約時刻に到達した枠をツリー投稿 |
| `measure.yml` | 毎日 22:00 JST | インサイト取得→ `learnings.md` 更新 |

業種別の8サンプルプロンプト同梱、`prompts/research.md` を書き換えれば自分の分野に対応。
手動投稿(任意テキスト)もActions画面から可能です。

---

## ⚠️ 動作前提・購入前にご確認ください

### 動作確認日

2026年4月時点 のThreads API・Claude APIで動作確認しています。
両APIは仕様変更が入りやすい領域です。半年〜1年スパンで部分的な手直しが必要になる前提でご利用ください。

### 必要な環境・条件

| 項目 | 内容 |
|------|------|
| GitHubアカウント | 無料プランでOK (Public運用なら無制限) |
| Threadsアカウント | Threads APIが有効化されている地域のアカウント (※後述) |
| Meta開発者アカウント | 無料登録、Threads APIアプリ作成 |
| Anthropic APIアカウント | クレジットカード登録が必要 (従量課金) |

### Threads API地域制限について (重要)

Threads APIは段階的展開中で、地域によって利用可否が異なります。
日本のアカウントは利用可能ですが、アクセストークン発行時に "API access not available in your region" のような表示が出る場合は、Meta側の解禁を待つ必要があります。
購入前に <https://developers.facebook.com/docs/threads/> で最新の対応状況をご確認ください。

### 想定費用

| 内訳 | 月額目安 |
|------|---------|
| GitHub Actions | 0円 (Publicリポなら無制限) |
| Anthropic API (1日: リサーチ+作成+校正+計測 ≒ 4コール) | $1〜$4 (約150〜600円) |
| Anthropic Web Search ツール | 検索回数に応じた従量 (1日1リサーチ想定で少額) |
| Threads API | 0円 |
| **合計** | **数百円〜/月** |

※ 1日4投稿×5ツリー・Web検索ありの構成です。モデル(既定 `claude-sonnet-4-6`)やプロンプト長で変動します。
※ `CLAUDE_MODEL` 環境変数でモデルを変更できます。Anthropic Consoleで利用上限 (例: $10/月) を設定しておくのを推奨します。

### サポート範囲

- 本テンプレートは **2026年4月時点の動作確認** をもって配布しています
- API仕様変更による不具合は、無料アップデートではなく **個別ご相談** とさせていただきます
- ご自身でのリポジトリ運用・GitHub Secrets管理は購入者の責任で行ってください
- アクセストークン・APIキーの値は私(配布者)に共有しないでください

---

## 1. 必要なもの

- GitHubアカウント (無料プランでOK)
- Threadsアカウント
- Meta開発者アカウント (Threads API用、無料)
- Anthropic APIキー (Claude API用、従量課金)

---

## 2. セットアップ手順

### 2-1. このリポジトリをFork (またはテンプレ利用)

GitHub上で右上の **Use this template** から自分のアカウントに新規リポジトリを作成します。
リポジトリ名は何でも構いません。

### 2-2. Forkしたリポジトリで GitHub Actions を有効化する (重要)

GitHubの仕様上、Forkまたは Use this template した直後はワークフローが無効化されています。
以下の手順で有効化してください。

1. 自分のリポジトリの **Actions** タブを開く
2. 「I understand my workflows, go ahead and enable them」のような黄色いバナーが出るのでクリック
3. これで `.github/workflows/*.yml` 配下のすべてのワークフローが有効化される

⚠️ この手順を飛ばすと、cronも手動実行も一切動きません。失敗報告のNo.1がここです。

また、ワークフローがリポジトリにコミット (drafts/ への書き込み) を行うため、書き込み権限を確認してください。

1. **Settings → Actions → General** を開く
2. 一番下の **Workflow permissions** セクションで **Read and write permissions** を選択
3. **Save** を押す

### 2-3. Threads APIのアクセストークンを取得

1. <https://developers.facebook.com/> で開発者登録
2. **My Apps → Create App → Use case: Access the Threads API** で新規アプリ作成
3. 左メニュー **Use cases → Threads → Customize** でPermissionsに `threads_basic`、`threads_content_publish`、`threads_manage_insights` を追加
   - `threads_manage_insights` は計測エージェント(インサイト取得)に必須です
4. **App Roles → Roles** で自分自身を **Threads Tester** として登録
5. <https://www.threads.net/> で同じMetaアカウントにログインし、招待を承認
6. **Tools → Graph API Explorer** で先ほど作ったアプリを選択し、Get Access Token → Threads Tester の権限を付与してShort-lived tokenを取得
7. 下記URLをブラウザで叩いてLong-livedトークン (60日有効) に交換:

   ```
   https://graph.threads.net/access_token?grant_type=th_exchange_token&client_secret={APP_SECRET}&access_token={SHORT_TOKEN}
   ```

8. 同時にユーザーIDを取得:

   ```
   https://graph.threads.net/v1.0/me?fields=id,username&access_token={LONG_TOKEN}
   ```

   返ってくる `id` がそのまま `THREADS_USER_ID` です。

> 詳細は[Meta Threads API公式ドキュメント](https://developers.facebook.com/docs/threads/)を参照。

### 2-4. Anthropic APIキーを取得

<https://console.anthropic.com/> でアカウントを作り、API Keysから新規キーを発行します。
**Settings → Limits** で月額上限 (例: $5) を設定しておくと、暴走時の安心料になります。

### 2-5. GitHub Secretsを登録

リポジトリの **Settings → Secrets and variables → Actions → New repository secret** で以下を登録します。

| 名前 | 中身 |
|------|------|
| `ANTHROPIC_API_KEY` | Anthropicから発行したAPIキー |
| `THREADS_USER_ID` | 上で取得した数字のID |
| `THREADS_ACCESS_TOKEN` | Long-livedアクセストークン |

⚠️ 値の前後に空白が入ると認証失敗します。コピペ時に注意。

### 2-6. プロンプトを自分の業種に差し替え

書き換えるのは2ファイルです。

| ファイル | 役割 | 使うエージェント |
|------|------|------|
| `prompts/system.md` | 文体・キャラクター・ルール (NGワード等) | writer / proofreader |
| `prompts/research.md` | 分野・キーワード・競合・時間帯ごとの役割 | research |

`prompts/learnings.md` は計測エージェントが自動更新するので、手で書く必要はありません。

`prompts/examples/` 配下に8業種の `system.md` サンプルがあるので、自分に近いものをコピーして上書きしてください。

```bash
# 例: グラフィックデザイナー版の文体に差し替え
cp prompts/examples/designer/system.md prompts/system.md
# research.md は自分の分野・キーワード・競合に合わせて直接編集する
```

同梱しているサンプル業種:

- `cafe/` カフェオーナー
- `salon/` 美容室オーナー
- `seitai/` 整体院
- `shigyo/` 士業 (税理士・社労士・行政書士)
- `ec/` EC運営者
- `coach/` コーチ・コンサル
- `school/` 個人教室 (ピアノ・英会話など)
- `designer/` グラフィックデザイナー

---

## 3. 最小構成での動作確認 (5分で1投稿)

本格運用の前に、まず1投稿だけテストすることを強く推奨します。
費用は **$0.05〜$0.10程度** で、設定の不備をここで全部洗い出せます。

### 手順

1. **PDCA Generate を実行**

   - **Actions** タブ → **PDCA Generate** → **Run workflow** (`days` は `1` のまま)
   - ジョブが緑になったら、`drafts/<今日の日付>.json` がコミットされていることを確認
   - ローカルで試す場合: `ANTHROPIC_API_KEY=... DAYS=1 python scripts/pdca_manager.py`

2. **生成された原稿を確認**

   - `drafts/YYYY-MM-DD.json` を開く。`posts` に 4枠 (07:00/12:00/19:00/21:00) があり、
     各枠に `main` と `replies`(4件) が入っているか確認
   - 違和感があれば、ブラウザ上で直接編集して **Commit changes** で保存

3. **手動で投稿テスト**

   - **Actions** → **Post Scheduled** → **Run workflow**
   - `force_date` に **今日の日付 (YYYY-MM-DD)** を入力 → **Run workflow**
     (`force_date` 指定時は予約時刻を無視して、その日の全枠を投稿します)
   - ジョブが緑になったら、Threadsアプリで4投稿(各ツリー)が反映されているか確認

4. **計測テスト (任意)**

   - **Actions** → **Measure** → **Run workflow**
   - `insights/<日付>.json` と `prompts/learnings.md` が更新されるか確認

5. **テスト投稿の後始末**

   - 投稿の出来が確認できたら、Threadsアプリ側で投稿を削除
   - リポジトリの `drafts/<今日の日付>.json` も削除しておく (二重投稿防止)

ここまで通ったら、実運用に進めます。

---

## 4. 本番運用への切り替え

最小構成テストが通ったら、後は放置でOKです。
- 毎日 05:00 JST に当日分の4枠ドラフトが自動生成される (リサーチ→作成→校正)
- 毎時0分に予約投稿チェックが走り、`scheduled_at` を過ぎた枠から順に投稿される
- 毎日 22:00 JST に計測が走り、伸びた投稿の傾向が `prompts/learnings.md` に反映される
- 翌日の生成は更新された `learnings.md` を読み込むので、PDCAが自動で回り続ける

### 投稿時刻の変更

`scripts/agents/common.py` の `POST_SLOTS`(既定 `["07:00","12:00","19:00","21:00"]`)を変更してください。
個別に時刻を変えたい場合は、ドラフトJSONの各枠の `scheduled_at` を直接編集すればOKです。
投稿本数を増減したい場合も `POST_SLOTS` を編集します(リスト要素数=1日の投稿数)。

### ドラフトの上書き編集

生成されたJSONはGitHubのWeb UIから直接編集できます。
気に入らない原稿は手で書き換えてからcommitすれば、その内容で投稿されます。

### トークンの更新 (60日に1度)

Long-livedトークンは60日で失効します。`THREADS_ACCESS_TOKEN` の値を、再取得した新しいトークンで上書き更新してください。
失効が近づくと投稿が `OAuthException` で失敗するので、その前に更新するのが安全です。

### Forkリポジトリのcron停止について (重要)

GitHub Actionsの仕様で、**Forkしたリポジトリで60日間コミットがないと、cronワークフローが自動的に無効化** されます。
本テンプレートは `PDCA Generate` と `Measure` が毎日コミットを行うため、通常運用では問題になりません。
ただし、長期間放置した場合は無効化される可能性があります。

万一停止していたら、Actionsタブから手動で再有効化してください。

---

## 5. ファイル構成

```
.
├── .github/
│   └── workflows/
│       ├── pdca-generate.yml     # P→D: リサーチ→作成→校正 (毎日05:00 + 手動)
│       ├── post-scheduled.yml    # D: 予約投稿 (毎時0分)
│       ├── measure.yml           # C→A: 計測→learnings更新 (毎日22:00 + 手動)
│       └── threads-post.yml      # 手動投稿 (任意テキスト)
├── scripts/
│   ├── agents/
│   │   ├── common.py             # 共通基盤 (POST_SLOTS, draft IO, Claudeクライアント)
│   │   ├── research.py           # リサーチ (Web検索)
│   │   ├── writer.py             # 投稿文作成 (5ツリー×4枠)
│   │   ├── proofreader.py        # 校正
│   │   └── analytics.py          # 計測 (インサイト集計 + learnings生成)
│   ├── pdca_manager.py           # 管理エージェント (P→D 統括)
│   ├── measure.py                # 計測エントリ (C→A 統括)
│   ├── post_threads.py           # 自動投稿エージェント (4枠×5ツリー)
│   ├── post_manual.py            # 手動投稿
│   └── generate_drafts.py        # [後方互換] pdca_manager へ委譲
├── prompts/
│   ├── system.md                 # ★文体・キャラクター (writer/proofreader)
│   ├── research.md               # ★分野・キーワード・競合 (research)
│   ├── learnings.md              # 計測フィードバック (自動更新)
│   └── examples/                 # 8業種のサンプル
│       ├── cafe/ salon/ seitai/ shigyo/
│       └── ec/ coach/ school/ designer/
├── drafts/                       # 生成される投稿JSON (4枠スキーマ)
├── research/                     # リサーチ出力 (監査用)
├── insights/                     # 取得したインサイト生データ
├── requirements.txt              # Python依存パッケージ
├── LICENSE
└── README.md
```

---

## 6. トラブルシューティング

### Actionsタブを開いても何も動かない

→ 2-2のActions有効化手順を実施。Forkしただけでは動きません。

### PDCA Generate が失敗する

- `ANTHROPIC_API_KEY` がSecretsに登録されていない / 失効している
- API残高不足 (Console.anthropic.com の Billing で確認)
- レート制限 — 数分待って再実行
- Web検索が地域/権限で使えない場合でも、検索なしフォールバックでテーマ生成は続行します

### Post Scheduled で投稿されない

- `drafts/YYYY-MM-DD.json` が存在するか
- 各枠の `scheduled_at` が現在時刻より未来になっていないか
- その枠が `posted: true` になっていないか (二重投稿防止)
- `main` が空の枠は投稿されません (生成に失敗した枠)
- `THREADS_ACCESS_TOKEN` が失効していないか

### Measure でインサイトが取れない

- アクセストークンに `threads_manage_insights` 権限が付いているか (2-3 を参照)
- まだ投稿が `posted` になっていない (投稿後に計測される)

### 401 OAuthException

- トークン失効 → 2-3の手順で再取得し、Secretsを更新

### Permission denied to actions/checkout / git push に失敗

- 2-2のWorkflow permissionsを **Read and write** に設定し直す

### 投稿の文体が業種と合わない

- `prompts/system.md` のキャラクター設定を見直す
- 「禁止する語」「使ってほしい語」をルールに追記
- 模範例 (Few-shot) を `system.md` に追加すると安定する

---

## 7. ライセンス

[MIT License](LICENSE)

著作権表示: `Copyright (c) 2026 6960`
