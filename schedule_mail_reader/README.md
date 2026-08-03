# 日程調整メール読み取りエージェント

## このエージェントができること

Gmail から日程調整に関するメールを検索・読み取り、候補日時・参加者・議題を整理して返します。

```
[あなた] 「日程調整メールを確認して」と入力
    ↓
[root_agent] authenticate ツールを呼び出す
    ↓  OAuth 認証（初回のみ）→ アクセストークンを state["access_token"] に保存
    ↓
[mail_reader_agent] search_schedule_emails ツールでキーワード検索 → メッセージ ID 一覧を取得
    ↓
[mail_reader_agent] get_email_contents ツールで全件の本文を一括取得
    ↓  日程調整メールかどうかを推論で判別・絞り込み
    ↓
[summarizer_agent] 絞り込んだメールを指定フォーマットで整形・出力
    ↓
[あなた] 候補日時・参加者・議題を見やすくまとめた回答を受け取る
```

**入力例 :**

```
・日程調整メールを確認して
・直近3日の日程調整メールをまとめて
```
---

## ファイル構成

```
schedule_mail_reader/
├── agent.py          メインファイル（設定・ツール・エージェント定義）
├── __init__.py       root_agent を公開するパッケージ初期化
├── .env              環境変数（各自の値に書き換えて使用）
├── requirements.txt  依存パッケージ
└── README.md         本資料
```
