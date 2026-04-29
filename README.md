# threads-auto-post-template

Threadsへの毎日の投稿を、Claude APIに任せて自動化するためのテンプレートです。
GitHub Actionsだけで動くので、サーバー不要・無料枠で運用できます。

| 機能 | 内容 |
|------|------|
| ドラフト生成 | 週1回、1週間分の投稿原稿をClaude APIで生成 |
| 自動投稿 | 毎時0分にチェック、予約時刻になったらThreadsに投稿 |
| ツリー対応 | メイン投稿に続けて返信形式でツリーを連投 |
| 業種別プロンプト | 8業種のサンプルプロンプト同梱、自分の業種に差し替え可能 |
| 手動投稿 | GitHubのActions画面から任意のテキストを投稿 |

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
| Anthropic API (1日1投稿・ツリー2件) | $0.30〜$1.00 (約45〜150円) |
| Threads API | 0円 |
| **合計** | **45〜150円程度/月** |

※ モデルやプロンプト長によって変動します。Anthropic Consoleで利用上限 (例: $5/月) を設定しておくのを推奨します。

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
3. 左メニュー **Use cases → Threads → Customize** でPermissionsに `threads_basic`、`threads_content_publish` を追加
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

`prompts/system.md` と `prompts/user.md` がそのまま使われます。
`prompts/examples/` 配下に8業種のサンプルがあるので、自分に近いものをコピーして上書きしてください。

```bash
# 例: グラフィックデザイナー版に差し替え
cp prompts/examples/designer/system.md prompts/system.md
cp prompts/examples/designer/user.md prompts/user.md
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

1. **Generate Drafts を1日分だけ実行**

   - **Actions** タブ → **Generate Drafts** → **Run workflow**
   - `days` フィールドに **`1`** を入力 → **Run workflow**
   - ジョブが緑になったら、`drafts/<今日の日付>.json` がコミットされていることを確認

2. **生成された原稿を確認**

   - リポジトリのルートから `drafts/YYYY-MM-DD.json` を開く
   - `main` と `replies` の中身が、自分の業種・キャラクターに合っているかチェック
   - 違和感があれば、ブラウザ上で直接編集して **Commit changes** で保存

3. **手動で投稿テスト**

   - **Actions** → **Post Scheduled** → **Run workflow**
   - `force_date` に **今日の日付 (YYYY-MM-DD)** を入力 → **Run workflow**
   - ジョブが緑になったら、Threadsアプリで投稿が反映されているか確認

4. **テスト投稿の後始末**

   - 投稿の出来が確認できたら、Threadsアプリ側で投稿を削除
   - リポジトリの `drafts/<今日の日付>.json` も削除しておく (二重投稿防止)

ここまで通ったら、実運用に進めます。

---

## 4. 本番運用への切り替え

最小構成テストが通ったら、後は放置でOKです。
- 毎週日曜 18:00 JST に1週間分のドラフトが自動生成される
- 毎時0分に予約投稿チェックが走り、`scheduled_at` を過ぎたものから順に投稿される

### 投稿時刻の変更

`scripts/generate_drafts.py` の `DEFAULT_POST_HOUR / DEFAULT_POST_MINUTE` を変更してください (デフォルトは8:00 JST)。
個別に時刻を変えたい場合は、ドラフトJSONの `scheduled_at` を直接編集すればOKです。

### ドラフトの上書き編集

生成されたJSONはGitHubのWeb UIから直接編集できます。
気に入らない原稿は手で書き換えてからcommitすれば、その内容で投稿されます。

### トークンの更新 (60日に1度)

Long-livedトークンは60日で失効します。`THREADS_ACCESS_TOKEN` の値を、再取得した新しいトークンで上書き更新してください。
失効が近づくと投稿が `OAuthException` で失敗するので、その前に更新するのが安全です。

### Forkリポジトリのcron停止について (重要)

GitHub Actionsの仕様で、**Forkしたリポジトリで60日間コミットがないと、cronワークフローが自動的に無効化** されます。
本テンプレートは `Generate Drafts` が週1回コミットを行うため、通常運用では問題になりません。
ただし、ドラフト生成を手動運用に切り替えた場合や、長期間放置した場合は無効化される可能性があります。

万一停止していたら、Actionsタブから手動で再有効化してください。

---

## 5. ファイル構成

```
.
├── .github/
│   └── workflows/
│       ├── generate-drafts.yml   # ドラフト生成 (週1回 + 手動)
│       ├── post-scheduled.yml    # 予約投稿 (毎時0分)
│       └── threads-post.yml      # 手動投稿 (任意テキスト)
├── scripts/
│   ├── generate_drafts.py
│   ├── post_threads.py
│   └── post_manual.py
├── prompts/
│   ├── system.md                 # ★自分の業種用に書き換える
│   ├── user.md                   # ★同上
│   └── examples/                 # 8業種のサンプル
│       ├── cafe/
│       ├── salon/
│       ├── seitai/
│       ├── shigyo/
│       ├── ec/
│       ├── coach/
│       ├── school/
│       └── designer/
├── drafts/                       # 自動生成されるJSON置き場
├── requirements.txt              # Python依存パッケージ (バージョン固定)
├── LICENSE
└── README.md
```

---

## 6. トラブルシューティング

### Actionsタブを開いても何も動かない

→ 2-2のActions有効化手順を実施。Forkしただけでは動きません。

### Generate Drafts が失敗する

- `ANTHROPIC_API_KEY` がSecretsに登録されていない / 失効している
- API残高不足 (Console.anthropic.com の Billing で確認)
- レート制限 — 数分待って再実行

### Post Scheduled で投稿されない

- `drafts/YYYY-MM-DD.json` が存在するか
- `scheduled_at` が現在時刻より未来になっていないか
- `posted: true` になっていないか (二重投稿防止)
- `THREADS_ACCESS_TOKEN` が失効していないか

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
