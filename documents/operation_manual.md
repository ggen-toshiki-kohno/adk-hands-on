# ADK エージェント 利用手順書

## はじめに
ADK エージェントをローカルで動作確認するための手順を説明します。

<walkthrough-footnote>
  <walkthrough-next-step-button></walkthrough-next-step-button>
</walkthrough-footnote>


## Step 1: 必要な API を有効化する

エージェントの動作に必要な Google Cloud API を有効化します。

### **有効化する API 一覧**

| API | 用途 |
|-----|------|
| Agent Platform API | ADK エージェントの実行 |
| Gmail API | メールの検索・本文取得 |

### **コマンドで一括有効化する**

ターミナルで以下のコマンドを実行します。

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  gmail.googleapis.com \
  --project=$(gcloud config get-value project)
```

`Operation ... finished successfully.` と表示されれば完了です。

---

## Step 2: OAuth 同意画面を設定する

エージェントが Gmail API にアクセスするために、OAuth 同意画面を設定します。  

### **同意画面を開く**

1. [Google Cloud コンソール](https://console.cloud.google.com/) を開きます

2. 検索窓に **`OAuth 同意画面`** と入力して開きます  
> （※）画面を開いた際に「GCPプロジェクト」が別のプロジェクトに切り替わる可能性があります。その場合は作業用のプロジェクトに戻してください。

### **同意画面を設定する**
1. サイドメニューの **[概要]** をクリックします

2. 「Google Auth Platform はまだ構成されていません」と表示されている場合は[開始]をクリックします

3. 以下の項目を入力します
| 項目 | 入力値 |
|------|--------|
| アプリ名 | `ADK Hackathon Agent`（任意） |
| ユーザーサポートメール | 自身のメールアドレス |
| 対象 | 内部（※） |
| 連絡先情報 | 自身のメールアドレス |
| ポリシーに同意 | ☑ |
> (※)「内部」の場合、Google Cloud組織で利用しているドメインのユーザーのみがOAuth認証を行えます

3. **[作成]** をクリックします

---

## Step 3: OAuth 2.0 クライアント ID を作成する

### **クライアントを開く**

1. OAuth 同意画面のサイドメニューにて **[クライアント]** をクリックします

2. 画面上部の **[+ クライアントを作成]** をクリックします

### **クライアント ID を作成する**

1. アプリケーションの種類で **[ウェブ アプリケーション]** を選択します

2. 名前に任意の名前を入力します（例: `ADK Hackathon Local`）

3. **[承認済みのリダイレクト URI]** の **[+ URIを追加]** を選択します（後ほど設定）
> ⚠️ **注意：ここでは設定しません。**  
>ローカル環境で作業する場合、以下の`adk web`の画面URLを設定すれば良いです。
   >```
   >http://127.0.0.1:8000/dev-ui/ 
   >```
>ただ今回は、Cloud Shell（別サーバー）上で`adk web`を実施します。  
>この際、`127.0.0.1`のままだと、Cloud Shellではなく自身のPC側を指してしまうため、Cloud Shellはlocalhostの通信を、Googleが用意する一時的なアドレスに転送します。  
>上記より、実際に`adk web`をCloud Shellで起動して、転送先のURLが分かったタイミングで設定が必要になります。


> **このリダイレクト URI について**  
> `adk web` の画面の URL から OAuth 認証を行うことを許可するための設定です。
> 
> 正確には、Google での認証完了後にアクセストークン等を受け取る「安全なリダイレクト先（戻り先）」として、この URL を許可しています。

4. **[作成]** をクリックします

5. 作成完了後にダイアログが表示され、以下の情報をメモしておきます。

- **クライアント ID**（`xxxxxxxx.apps.googleusercontent.com` の形式）
- **クライアントシークレット**


---

## Step 4: エージェントフォルダへ移動する

次のコマンドを実行して、エージェントのフォルダへ移動します。

```bash
cd schedule_mail_reader
```

> **以降のすべてのコマンドは、このディレクトリ（`schedule_mail_reader/`）で実行します。**

---

## Step 5: 仮想環境を作成・有効化する

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

## Step 6: 環境設定ファイルを更新

以下をクリックして`.env` ファイルを開きます


<walkthrough-editor-open-file filePath="adk-hands-on/schedule_mail_reader/.env">
.env ファイルを開く
</walkthrough-editor-open-file>

### **.env ファイルを編集する**

以下の項目を書き換えます。

| 項目 | 設定値 |
|------|--------|
| `GOOGLE_CLOUD_PROJECT` | 使用する GCP プロジェクト ID |
| `GOOGLE_OAUTH_CLIENT_ID` | Step 3 で控えたクライアント ID |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Step 3 で控えたクライアントシークレット |

書き換え例:

```
GOOGLE_CLOUD_PROJECT=my-project-id
GOOGLE_OAUTH_CLIENT_ID=123456789-abcdefgh.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxxxxxx
```

ファイルを保存します（`Ctrl + S`）。

---

## Step 7: 依存パッケージをインストールする

次のコマンドを実行して、仮想環境内に必要なパッケージをインストールします。

```bash
pip install -r requirements.txt
```

---

## Step 8: エージェントの動作をローカルで確認する（起動）

次のコマンドを実行して、ローカル上で動作確認用 Web アプリを起動します。

```bash
adk web . --allow_origins "regex:https://.*\.cloudshell\.dev"
```

> **`--allow_origins` オプションについて**  
> Cloud Shell 開発ではブラウザ（`cloudshell.dev`）とサーバー（`localhost`）のオリジンが異なるため、ブラウザのセキュリティ制限（CORS）により通信がブロックされます。  
> `--allow_origins` でこの制限を解除しています。

---

## Step 9: エージェントのURLを[承認済みのリダイレクト URI]に追加

1. ターミナル上に`adk web`へのアクセスURL（http://127.0.0.1:8000/）が表示されるので、`Ctrl + クリック`で開きます

2. ブラウザのURL欄から`https://~dev-ui/`までの文字列をコピーします  
例）`https://8000-cs-924648547011-default.cs-asia-east1-cats.cloudshell.dev/dev-ui/`

3. Step 3:で作成した **OAuth 2.0 クライアント ID** にて **[承認済みのリダイレクト URI]** にコピーした文字列を追加して保存します。

---

## Step 10: ブラウザでエージェントの動作を確認する

1. `adk web`の画面下部の入力欄 **[Type a message...]** にメッセージを入力します

   ```
   直近3日間の日程調整メールを確認して
   ```

2. 初回実行時は Google アカウントの認証を求めるメッセージが表示されます。表示された認可 URL にアクセスし、Google アカウントでログインして権限を許可してください

3. エージェントの応答を確認します（候補日時・参加者・議題が要約されて返ってきます）

---

## Step 11: adk web を停止する

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

