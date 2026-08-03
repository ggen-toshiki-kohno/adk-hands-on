# ADK エージェント 利用手順書

ADK エージェントをローカルで動作確認するための手順を説明します。

<walkthrough-tutorial-duration duration="30"></walkthrough-tutorial-duration>

---

## Step 1: 作業環境確認
### **プロジェクトとアカウントの確認**

1. ターミナルで以下のコマンドを実行します

```bash
gcloud config list
```

2. 作業を行うアカウント、GCPプロジェクトが正しいことを確認します
```
account = 作業を行うアカウント
project = 作業を行うGCPプロジェクト
```

---

## Step 2: 必要な API を有効化する

エージェントの動作に必要な Google Cloud API を有効化します。

### **有効化する API 一覧**

| API | 用途 |
|-----|------|
| Agent Platform API | ADK エージェントの実行・Agent Runtime へのデプロイ |
| Gmail API | メールの検索・本文取得 |

### **コマンドで一括有効化する**

ターミナルで以下のコマンドを実行します

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  gmail.googleapis.com \
  --project=$(gcloud config get-value project)
```

`Operation ... finished successfully.` と表示されれば完了です。

---

## Step 3: IAM 権限を確認する

エージェントの実行・デプロイには、実行アカウントに以下のロールが必要です。

### **必要なロール一覧**

| ロール | 用途 |
|--------|------|
| `roles/aiplatform.user` | Agent Runtime のデプロイ・管理 |

### **現在のアカウントに付与されているロールを確認する**

```bash
gcloud projects get-iam-policy $(gcloud config get-value project) \
  --flatten="bindings[].members" \
  --filter="bindings.members=$(gcloud config get-value account)" \
  --format="table(bindings.role)"
```

上記ロールが表示されない場合は、プロジェクトオーナーに付与を依頼してください。

---

## Step 4: OAuth 同意画面を設定する

エージェントが Gmail API にアクセスするために、OAuth 同意画面を設定します。

### **同意画面を開く**

1. [Google Cloud コンソール](https://console.cloud.google.com/) を開きます

2. 検索窓に **`OAuth 同意画面`** と入力して開きます  
   または: **[APIとサービス]** > **[OAuth 同意画面]**

### **同意画面を設定する**

1. ユーザーの種類で **[内部]** を選択し、**[作成]** をクリックします  
   ※ 社内利用のため「内部」を選択します（「内部」の場合、Google Cloud組織で利用しているドメインのユーザーのみがOAuth認証を行えます）

2. 以下の項目を入力します

   | 項目 | 入力値 |
   |------|--------|
   | アプリ名 | `ADK Hackathon Agent`（任意） |
   | ユーザーサポートメール | 貸与されたアカウントのメールアドレス |
   | デベロッパーの連絡先情報 | 同上 |

3. **[保存して次へ]** をクリックします

4. 確認画面で内容を確認し、**[ダッシュボードに戻る]** をクリックします

---

## Step 5: OAuth 2.0 クライアント ID を作成する

### **認証情報の画面を開く**

1. [Google Cloud コンソール](https://console.cloud.google.com/) の **[APIとサービス]** > **[認証情報]** を開きます

2. 画面上部の **[+ 認証情報を作成]** > **[OAuth クライアント ID]** をクリックします

### **クライアント ID を作成する**

1. アプリケーションの種類で **[ウェブ アプリケーション]** を選択します

2. 名前に任意の名前を入力します（例: `ADK Hackathon Local`）

3. **[承認済みのリダイレクト URI]** の **[+ URIを追加]** をクリックし、以下の URI を追加します

   ```
   http://127.0.0.1:8000/dev-ui/
   ```

   > **このリダイレクト URI について**  
   > `adk web` のフロントエンドは `http://127.0.0.1:8000/dev-ui/` をコールバック先として使います。  
   > `localhost` と `127.0.0.1` は Google OAuth では別ホスト扱いになるため、**`127.0.0.1`** を使用してください。  
   > この URI が登録されていないと、認証後に「このアプリは OAuth 2.0 ポリシーを遵守していない」エラーになるため必ず追加してください。

4. **[作成]** をクリックします

### **クライアント ID とシークレットを控える**

作成完了後にダイアログが表示されます。

- **クライアント ID**（`xxxxxxxx.apps.googleusercontent.com` の形式）
- **クライアントシークレット**

この 2 つの値を必ずメモしておきます（次の手順で `.env` に設定します）。

> ダイアログを閉じた後は、認証情報の一覧から該当のクライアントをクリックすれば再確認できます。

---

## Step 6: エージェントフォルダへ移動する

次のコマンドを実行して、エージェントのフォルダへ移動します。

```bash
cd adk-hackathon/schedule_mail_reader && ls
```

> **以降のすべてのコマンドは、このディレクトリ（`schedule_mail_reader/`）で実行します。**

---

## Step 7: 仮想環境を作成・有効化する

Python の仮想環境を作成し、有効化します。

```bash
python3 -m venv .venv
source .venv/bin/activate
```

プロンプトの先頭に `(.venv)` が表示されれば、仮想環境が有効化されています。

```
(.venv) [アカウント名]@cloudshell:~/adk-hackathon/schedule_mail_reader ([プロジェクトID])$
```

---

## Step 8: 環境設定ファイルを更新

以下をクリックして`.env` ファイルを開きます


<walkthrough-editor-open-file filePath="adk-hackathon/schedule_mail_reader/.env">
.env ファイルを開く
</walkthrough-editor-open-file>

### **.env ファイルを編集する**

以下の項目を書き換えます。

| 項目 | 設定値 |
|------|--------|
| `GOOGLE_CLOUD_PROJECT` | 使用する GCP プロジェクト ID |
| `GOOGLE_OAUTH_CLIENT_ID` | Step 4 で控えたクライアント ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Step 4 で控えたクライアントシークレット |

書き換え例:

```
GOOGLE_CLOUD_PROJECT=my-project-id
GOOGLE_OAUTH_CLIENT_ID=123456789-abcdefgh.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxxxxxx
```

ファイルを保存します（`Ctrl + S`）。

---

## Step 9: 依存パッケージをインストールする

次のコマンドを実行して、仮想環境内に必要なパッケージをインストールします。

```bash
pip install -r requirements.txt
```

---

## Step 10: エージェントの動作をローカルで確認する（起動）

次のコマンドを実行して、ローカル上で動作確認用 Web アプリを起動します。

```bash
adk web . --allow_origins "regex:https://.*\.cloudshell\.dev"
```

> **`--allow_origins` オプションについて**  
> Cloud Shell 開発ではブラウザ（`cloudshell.dev`）とサーバー（`localhost`）のオリジンが異なるため、ブラウザのセキュリティ制限（CORS）により通信がブロックされます。  
> `--allow_origins` でこの制限を解除しています。

---

## Step 11: ブラウザでエージェントの動作を確認する

1. ブラウザで以下の URL を開きます

   ```
   http://127.0.0.1:8000
   ```

2. 画面下部の入力欄 **[Type a message...]** にメッセージを入力します

   ```
   日程調整メールを確認して
   ```

3. 初回実行時は Google アカウントの認証を求めるメッセージが表示されます。表示された認可 URL にアクセスし、Google アカウントでログインして権限を許可してください

4. エージェントの応答を確認します（候補日時・参加者・議題が要約されて返ってきます）

---

## Step 12: adk web を停止する

動作確認が完了したら、ターミナルで以下のキー操作を行い `adk web` を停止します。

```
Ctrl + C
```

---

## （参考）Agent Runtime へのデプロイと Gemini Enterprise 連携

ローカルでの動作確認後、ADKエージェントを Agent Runtime にデプロイし、
Gemini Enterprise に接続することで、Gemini Enterprise 経由でエージェントを利用することができます。

デプロイ手順は以下の記事を参照してください。
- [Gemini Enterprise × ADKでスプレッドシートを操作するAIエージェントを開発してみた（g-gen ブログ）](https://blog.g-gen.co.jp/entry/work-with-spreadsheets-on-adk-agents)

※ 記事に書かれているエージェントの内容は今回作成したものとは異なりますが、デプロイの流れは同様です。

### ⚠️ Gemini Enterprise 利用時のソースコード修正点

現在の実装では、OAuth認証をエージェント側が処理しています（`authenticate` ツール）。Gemini Enterprise をフロントエンドとして利用する場合、OAuth認証は Gemini Enterprise 側が全て担うため、エージェント側の OAuth認証を行う処理は不要になります。

**① `agent.py` から以下をまるごと削除する**

- `_auth_config` の定義（23〜44行目）
- `authenticate` 関数の定義（50〜83行目）

**② `agent.py` の import と変数定義から不要になった行を削除する**

```python
# 削除する行
from fastapi.openapi.models import OAuth2, OAuthFlowAuthorizationCode, OAuthFlows  # 削除
from google.adk.auth import AuthConfig, AuthCredential, AuthCredentialTypes, OAuth2Auth  # 削除
...
CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")        # 削除
CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET") # 削除
```

**③ `root_agent` の `tools` から `authenticate` を削除する**

```python
# 修正前
tools=[
    authenticate,                      # 削除
    AgentTool(agent=mail_reader_agent),
    AgentTool(agent=summarizer_agent),
]

# 修正後
tools=[
    AgentTool(agent=mail_reader_agent),
    AgentTool(agent=summarizer_agent),
]
```

**④ `root_agent` の `instruction` から authenticate の手順を削除する**

```python
# 修正前
instruction=(
    "以下の手順で日程調整メールを処理してください。\n"
    "\n"
    "1. authenticate ツールで OAuth認証を行う\n" # 削除
    "2. 認証完了後、取得したアクセストークンを用いて、mail_reader_agent ツールで Gmail を検索する\n"
    "3. 検索結果を summarizer_agent ツールで分析し、指定フォーマットで出力する"
),

# 修正後
instruction=(
    "以下の手順で日程調整メールを処理してください。\n"
    "\n"
    "1. mail_reader_agent ツールで Gmail を検索する\n"
    "2. 検索結果を summarizer_agent ツールで分析し、指定フォーマットで出力する"
),
```

**⑤ トークン取得のキー名を Gemini Enterprise の認証 ID に合わせる**

現在の実装では `authenticate` 関数が `state["access_token"]` にトークンの取得・格納を行っていますが、Gemini Enterprise 側がその処理を担います。

Gemini Enterprise 側でOAuth認証の設定を行い、Gemini Enterprise 経由による認証で得たトークンは `state`に格納されます。`state`のキー名は Gemini Enterprise 側の設定で指定する「認証 ID」となります。※詳細は手順書を参照

`search_schedule_emails`と `get_email_contents`のキー名を、任意の値（Gemini Enterprise で設定する認証ID） に変更してください。

```python
# 例：Gemini Enterprise 側の認証 ID を "gmail_token" に設定した場合

# 修正前
token = tool_context.state.get("access_token")

# 修正後
token = tool_context.state.get("gmail_token")  # Gemini Enterprise の認証 ID と一致させる
```

**⑥ `.env` から不要になった項目を削除する**

```
GOOGLE_OAUTH_CLIENT_ID=...       # 削除
GOOGLE_OAUTH_CLIENT_SECRET=...   # 削除
```

**⑦ Google Cloud Console の OAuth クライアント設定でリダイレクト URI を変更する**

[APIとサービス] > [認証情報] で Step 5 で作成した OAuth クライアントを開き、承認済みのリダイレクト URI を以下に変更します。

| 変更前 | 変更後 |
|--------|--------|
| `http://127.0.0.1:8000/dev-ui/` | `https://vertexaisearch.cloud.google.com/oauth-redirect` |

