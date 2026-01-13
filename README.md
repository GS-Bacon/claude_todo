# Claude Todo

Notion、Slack、Discordと連携するタスク管理システム。Claude Codeとの統合を想定した設計。

## 機能

- **Notionデータベース連携**: チーム用・個人用の2つのNotionデータベースからタスクを同期
- **Slack/Discord Webhook**: メンションを受信してタスクとして自動登録
- **通知機能**: 期限タスクや期限切れタスクをDiscordに通知
- **スケジューラ**: 定期的な同期と通知の自動実行
- **CLI**: コマンドラインからタスク管理操作
- **REST API**: プログラマブルなタスク操作

## クイックスタート

### 1. インストール

```bash
# リポジトリをクローン
git clone https://github.com/your-username/claude-todo.git
cd claude-todo

# 仮想環境を作成（推奨）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または
venv\Scripts\activate     # Windows

# 依存関係をインストール
pip install -e ".[dev]"
```

### 2. 環境変数の設定

`.env`ファイルをプロジェクトルートに作成:

```env
# Notion設定（必須）
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_TEAM_DATABASE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
NOTION_PERSONAL_DATABASE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Discord通知（任意）
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxxxx/xxxxx

# Slack連携（任意）
SLACK_SIGNING_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxx-xxxxx-xxxxx

# アプリ設定
DEBUG=true
HOST=0.0.0.0
PORT=8000

# スケジューラ設定
SCHEDULER_ENABLED=true
SCHEDULER_TIMEZONE=Asia/Tokyo
```

### 3. Notionデータベースの準備

**既存のデータベースを使う場合:**

環境変数でプロパティ名とステータス値をマッピングできます。

```env
# プロパティ名のマッピング（既存DBに合わせて変更）
NOTION_PROP_TITLE=タスク名
NOTION_PROP_STATUS=ステータス
NOTION_PROP_PRIORITY=優先度
NOTION_PROP_DUE_DATE=期限
NOTION_PROP_TAGS=タグ
NOTION_PROP_DESCRIPTION=説明

# ステータス値のマッピング
NOTION_STATUS_TODO=未着手
NOTION_STATUS_IN_PROGRESS=進行中
NOTION_STATUS_DONE=完了
NOTION_STATUS_BLOCKED=ブロック中

# 優先度値のマッピング
NOTION_PRIORITY_LOW=低
NOTION_PRIORITY_MEDIUM=中
NOTION_PRIORITY_HIGH=高
NOTION_PRIORITY_URGENT=緊急
```

**新規でデータベースを作成する場合:**

デフォルト設定を使う場合は、以下のプロパティを持つデータベースを作成:

| プロパティ名 | タイプ | 設定値 |
| ------------ | ------ | ------ |
| Name | タイトル | - |
| Status | ステータス | Not started, In progress, Done, Blocked |
| Priority | セレクト | Low, Medium, High, Urgent |
| Due | 日付 | - |
| Tags | マルチセレクト | - |
| Description | テキスト | - |
| Assignee | ユーザー | - |
| Created | 作成日時 | - |

Notion APIキーは [Notion Developers](https://developers.notion.com/) から取得できます。

## 使い方

### CLI コマンド

```bash
# タスク一覧
claude-todo list
claude-todo list --status todo
claude-todo list --priority high
claude-todo list --tags "work,urgent"
claude-todo list --json  # JSON出力

# タスク詳細
claude-todo show <task_id>

# タスク完了
claude-todo complete <task_id>

# 今日が期限のタスク
claude-todo due-today

# 期限切れタスク
claude-todo overdue

# サマリー
claude-todo summary

# Notionから同期
claude-todo sync

# スケジュールジョブ一覧
claude-todo jobs

# ジョブを手動実行
claude-todo run-job sync_team_tasks
claude-todo run-job send_daily_summary

# APIサーバー起動
claude-todo serve
claude-todo serve --port 3000 --reload
```

### API エンドポイント

サーバー起動後、`http://localhost:8000/docs` でSwagger UIを確認できます。

```bash
# ヘルスチェック
curl http://localhost:8000/health

# タスク一覧
curl http://localhost:8000/tasks

# タスク取得
curl http://localhost:8000/tasks/{task_id}

# タスク作成
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "新しいタスク", "priority": "high"}'

# タスク更新
curl -X PATCH http://localhost:8000/tasks/{task_id} \
  -H "Content-Type: application/json" \
  -d '{"status": "done"}'
```

### Webhook設定

#### Slack

1. [Slack API](https://api.slack.com/apps) でアプリを作成
2. Event Subscriptions を有効化
3. Request URL に `https://your-domain.com/webhooks/slack` を設定
4. `app_mention` イベントを購読

#### Discord

1. Discordサーバー設定 > 連携サービス > Webhook で作成
2. Webhook URLを環境変数に設定

## 開発

### テスト実行

```bash
# 全テスト
pytest

# カバレッジ付き
pytest --cov=src --cov-report=html

# 特定のテスト
pytest tests/unit/test_task_service.py
pytest tests/api/test_webhooks.py
```

### プロジェクト構成

```
src/
├── domain/          # ドメインモデル・プロトコル
├── repositories/    # データ永続化層
├── services/        # ビジネスロジック層
├── api/             # REST API (FastAPI)
├── cli/             # CLIコマンド (Click)
├── scheduler/       # 定期実行ジョブ (APScheduler)
├── notifications/   # 通知送信
├── parsers/         # Webhookパーサー
├── config/          # 設定管理
└── container.py     # DIコンテナ
```

### 新機能の追加

詳細は [CLAUDE.md](CLAUDE.md) を参照してください。

## スケジュールジョブ

| ジョブ名 | スケジュール | 説明 |
|---------|-------------|------|
| sync_team_tasks | */15 * * * * | チームタスクの同期（15分毎） |
| sync_personal_tasks | */15 * * * * | 個人タスクの同期（15分毎） |
| send_due_notifications | 0 9 * * * | 本日期限タスクの通知（毎日9時） |
| send_overdue_notifications | 0 9,18 * * * | 期限切れタスクの通知（9時と18時） |
| send_daily_summary | 0 8 * * 1-5 | デイリーサマリー（平日8時） |

## ライセンス

MIT License
