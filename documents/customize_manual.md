# エージェントのカスタマイズ

現状のエージェントに機能を追加する場合のカスタマイズ例を記載します。

---

## カレンダー連携機能を追加する

Gmail で取得した候補日時をもとに、カレンダーの空き状況を確認する機能を追加します。

---

### **事前準備**

以下コマンドをCloud Shellで実行してCalendar API を有効化します。
```bash
gcloud services enable \
  calendar.googleapis.com \
  --project=$(gcloud config get-value project)
```

---

### **実装手順**

1. `agent.py` の `_auth_config` に Calendar のスコープを追加します

   ```python
   scopes={
       "https://www.googleapis.com/auth/gmail.readonly": "Gmail メールの読み取り",
       "https://www.googleapis.com/auth/calendar.readonly": "Google カレンダーの読み取り",  # 追加
   },
   ```

2. Calendar API を呼び出すツールを実装します

   ```python
   def check_calendar_availability(date: str, tool_context: ToolContext) -> dict:
       """指定日の予定一覧を Google Calendar API から取得する。"""
       token = tool_context.state.get("access_token")
       # ...Calendar API 呼び出し処理...
   ```

3. `calendar_agent` を定義して `root_agent` の tools に追加します

   ```python
   calendar_agent = Agent(
       name="calendar_agent",
       model=MODEL,
       description="Google カレンダーを確認し、指定日の空き状況を返す。",
       instruction="summarizer_agent が抽出した候補日時について、カレンダーの予定を確認して空き状況を返してください。",
       tools=[check_calendar_availability],
   )

   root_agent = Agent(
       ...
       instruction=(
           "1. authenticate ツールで認証する\n"
           "2. mail_reader_agent で日程調整メールを取得する\n"
           "3. summarizer_agent で候補日時を整理する\n"
           "4. calendar_agent で候補日時の空き状況を確認する"  # 追加
       ),
       tools=[
           authenticate,
           AgentTool(agent=_mail_reader_agent),
           AgentTool(agent=_summarizer_agent),
           AgentTool(agent=_calendar_agent),  # 追加
       ],
   )
   ```
