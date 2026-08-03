# ※ adk web / adk run は `root_agent` をエントリポイントとして探す。変数名を変えないこと。
import base64
import logging
import os
from datetime import datetime, timezone, timedelta

import requests
from dotenv import load_dotenv
from fastapi.openapi.models import OAuth2, OAuthFlowAuthorizationCode, OAuthFlows
from google.adk.agents import Agent
from google.adk.auth import AuthConfig, AuthCredential, AuthCredentialTypes, OAuth2Auth
from google.adk.tools import AgentTool, ToolContext

load_dotenv()

# ── 設定 ──────────────────────────────────────────────────────────────────────
MODEL = os.environ.get("AGENT_MODEL")
CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")

# ── OAuth 認証設定 ─────────────────────────────────────────────────────────────
# request_credential と get_auth_response に同一インスタンスを渡すことで
# credential_key（設定内容のハッシュ）が一致し、保存済みトークンを正しく取り出せる。
_auth_config = AuthConfig(
    auth_scheme=OAuth2(
        flows=OAuthFlows(
            authorizationCode=OAuthFlowAuthorizationCode(
                authorizationUrl="https://accounts.google.com/o/oauth2/v2/auth",
                tokenUrl="https://oauth2.googleapis.com/token",
                scopes={
                    # キー: スコープURL（どのAPI操作を許可させるか）、値: 説明文（UI表示用）
                    "https://www.googleapis.com/auth/gmail.readonly": "Gmail メールの読み取り",
                    # 
                },
            )
        )
    ),
    raw_auth_credential=AuthCredential(
        auth_type=AuthCredentialTypes.OAUTH2,
        oauth2=OAuth2Auth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
        ),
    ),
)


# ── ツール定義 ─────────────────────────────────────────────────────────

# 
def authenticate(tool_context: ToolContext) -> dict:
    """Google アカウントの OAuth 認証を行う。

    認証済みの場合はそのまま成功を返す。未認証の場合は認可 URL をフロントに送信して
    ターンを一時停止し、ユーザーが認可を完了した後に ADK がこのツールを再実行する。
    認証に成功すると、以降のツールが使用できるよう state["access_token"] にトークンを保存する。

    Returns:
        dict: 以下のいずれかを返す。
            - {"status": "ok", "message": "..."} : 認証済み、または認証完了
            - {"status": "auth_required", "message": "..."} : 認可 URL を送信してターン停止
    """
    # tool_context.stateはセッション内でエージェント、ツールが互いに値を共有できるキーバリューストア
    # tool_context.state["key"]=valueで値を格納し、tool_context.state.get["key"]で値を取り出す
    
    # 既に認証済みかどうかのチェック
    if tool_context.state.get("access_token"):
        return {"status": "ok", "message": "認証済みです。"}

    # get_auth_response は OAuth コールバック完了後にトークンを返す。初回は None。
    auth_response = tool_context.get_auth_response(_auth_config)
    if (
        auth_response is None
        or not getattr(auth_response, "oauth2", None)
        or not auth_response.oauth2.access_token
    ):
        # 認可 URL をフロントに送信してターンを一時停止する。
        # ユーザーが認可完了後、ADK がこのツールを再実行する。
        tool_context.request_credential(_auth_config)
        return {
            "status": "auth_required",
            "message": "Google アカウントの認証が必要です。表示された認可 URL にアクセスしてください。",
        }

    tool_context.state["access_token"] = auth_response.oauth2.access_token
    return {"status": "ok", "message": "認証が完了しました。"}



def search_schedule_emails(days: int, tool_context: ToolContext) -> dict:
    """Gmail を検索して、日程調整に関連するメールの ID 一覧を返す。

    日程・曜日・時間・打ち合わせ関連のキーワードで OR 検索を行い、
    直近 days 日以内に受信したメッセージを対象とする。
    検索はメッセージ単位のため、スレッド内の他のメッセージはヒットしない点に注意。

    Args:
        days: 検索対象とする日数。1 を指定すると直近1日分を検索する。

    Returns:
        dict: 以下のいずれかを返す。
            - {"status": "ok", "count": N, "messages": [{"id": "..."}, ...]} : 検索成功
            - {"status": "not_found", "message": "..."} : 該当メールなし
            - {"status": "error", "message": "..."} : トークン未取得または API エラー
    """
    
    # 関数「authenticate」でstateにセットしたアクセストークンを取得
    # アクセストークンを使ってGamil APIを実行する
    token = tool_context.state.get("access_token")
    if not token:
        return {"status": "error", "message": "アクセストークンが state に見つかりません。"}

    # フィルタ条件をの定義
    # 取得範囲：直近 {days} 日
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y/%m/%d")
    # 検索ワード：日程調整に関わるワード
    # ※直近○日のメールを全て取得して、LLMによって日程調整メールかどうかを判別させる方法もあるが、
    # 　その場合、対象メールが膨大になり推論コスト・時間がかかるため、事前に間引く
    keywords = (
        # 調整・確認・候補
        "日程 OR スケジュール OR 候補 OR 都合 OR 時間 OR 日時"
        # 曜日
        " OR 月 OR 火 OR 水 OR 木 OR 金 OR 土 OR 日"
        # 時間
        " OR 午前 OR 午後 OR 時 OR : OR ： OR ~ OR 〜"
        # 週・期間
        " OR 来週 OR 今週 OR 週明け OR 平日"
        # 打ち合わせ・会議
        " OR 打ち合わせ OR ミーティング OR 定例 OR 会議"
    )
    
    # 上記の上限に基づいて、Gmailメッセージ取得API実行
    resp = requests.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        headers={"Authorization": f"Bearer {token}"},
        params={"q": f"({keywords}) after:{since}"},
        timeout=10,
    )
    if resp.status_code != 200:
        return {"status": "error", "message": f"Gmail API エラー ({resp.status_code}): {resp.text[:300]}"}

    messages = resp.json().get("messages", [])
    logging.info("search_schedule_emails: %d 件ヒット (days=%d)", len(messages), days)
    if not messages:
        return {"status": "not_found", "message": f"直近{days}日以内に日程調整関連のメールが見つかりませんでした。"}

    return {"status": "ok", "count": len(messages), "messages": [{"id": m["id"]} for m in messages]}


def get_email_content(message_id: str, tool_context: ToolContext) -> dict:
    """指定したメッセージ ID のメールを Gmail API から取得し、件名・送信者・受信日・本文を返す。

    本文は text/plain パートを MIME 構造から再帰的に探して返す。
    本文が 3000 文字を超える場合は切り詰める。

    Args:
        message_id: 取得対象のメッセージ ID。search_schedule_emails の返す messages[].id を渡す。

    Returns:
        dict: 以下のいずれかを返す。
            - {"status": "ok", "subject": "...", "from": "...", "date": "...", "body": "..."} : 取得成功
            - {"status": "error", "message": "..."} : トークン未取得または API エラー
    """
    token = tool_context.state.get("access_token")
    if not token:
        return {"status": "error", "message": "アクセストークンが state に見つかりません。"}

    resp = requests.get(
        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
        headers={"Authorization": f"Bearer {token}"},
        params={"format": "full"},  # full: ヘッダー・本文・添付情報すべてを返す
        timeout=10,
    )
    if resp.status_code != 200:
        return {"status": "error", "message": f"Gmail API エラー ({resp.status_code}): {resp.text[:300]}"}

    msg = resp.json()
    headers_list = msg.get("payload", {}).get("headers", [])
    subject = next((h["value"] for h in headers_list if h["name"].lower() == "subject"), "(件名なし)")
    sender = next((h["value"] for h in headers_list if h["name"].lower() == "from"), "(送信者不明)")
    date = next((h["value"] for h in headers_list if h["name"].lower() == "date"), "")

    # Gmail の本文は MIME のネスト構造で返る。
    # text/plain パートを再帰的に探して Base64 デコードする。
    def extract(payload: dict) -> str:
        if payload.get("mimeType") == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                # Gmail API は Base64 の末尾パディングを省略するため "==" を補完する
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        return next((t for part in payload.get("parts", []) if (t := extract(part))), "")

    body = extract(msg.get("payload", {}))
    return {
        "status": "ok",
        "subject": subject,
        "from": sender,
        "date": date,
        "body": body[:3000] if len(body) > 3000 else body,  # LLM のコンテキスト長を考慮して切り詰め
    }


# ── エージェント定義 ───────────────────────────────────────────────────────────

# 第1エージェント: Gmail を検索してメール本文を取得し、日程調整メールのみ出力する
mail_reader_agent = Agent(
    name="mail_reader_agent",
    model=MODEL,
    description="Gmail からメールを検索・取得し、日程調整メールの内容のみを出力する。",
    instruction=(
        "Gmail からメールを検索・取得し、日程調整メールのみを出力してください。\n"
        "\n"
        "【手順】\n"
        "1. search_schedule_emails ツールでメールを検索する\n"
        "   - ユーザーが「直近N日」と指定した場合はその日数を days に渡す\n"
        "   - 指定がない場合は days=1（デフォルト）を渡す\n"
        "2. 見つかったメール全件について get_email_content ツールで本文を取得する\n"
        "3. 各メールが日程調整メールかどうかを推論で判別する\n"
        "   日程調整メールの条件：\n"
        "   - 候補日時・空き時間・都合の確認などが含まれる\n"
        "   - ミーティング・打ち合わせ・面談などの設定を目的としている\n"
        "4. 日程調整メールと判断したものの内容（件名・送信者・受信日・本文）のみを出力する\n"
        "   日程調整メールでないと判断したものは除外する\n"
        "   要約・フォーマット整形は行わない。次のエージェントが行う。\n"
        "5. 日程調整メールが1件も見つからなかった場合はその旨を出力して終了する"
    ),
    tools=[search_schedule_emails, get_email_content],
)

# 第2エージェント: mail_reader_agent が絞り込んだ日程調整メールを指定フォーマットで出力する
summarizer_agent = Agent(
    name="summarizer_agent",
    model=MODEL,
    description="mail_reader_agent が絞り込んだ日程調整メールを指定フォーマットで出力する。",
    instruction=(
        "mail_reader_agent が出力した日程調整メールを、以下のフォーマットで出力してください。\n"
        "（複数ある場合はメールごとに繰り返す）\n"
        "\n"
        "【出力フォーマット】\n"
        "\n"
        "---\n"
        "\n"
        "**【件名】** （件名）\n"
        "\n"
        "**【送信者】** （送信者名 <メールアドレス>）\n"
        "\n"
        "**【受信日】** （YYYY-MM-DD）\n"
        "\n"
        "**【ミーティング概要】**\n"
        "\n"
        "- 目的: （目的・議題）\n"
        "- 参加者: （参加者）\n"
        "- 形式: （オンライン / オフライン / 不明）\n"
        "- 場所: （場所。オンラインの場合は URL など。不明の場合は「不明」）\n"
        "\n"
        "**【候補日時】**\n"
        "\n"
        "（候補日時が提示されている場合）\n"
        "\n"
        "- YYYY-MM-DD（曜日） HH:MM〜HH:MM\n"
        "\n"
        "（候補日時が提示されていない場合）\n"
        "\n"
        "提案なし\n"
        "\n"
        "---\n"
        "\n"
        "mail_reader_agent から日程調整メールが渡されなかった場合は「指定期間内に日程調整メールは見つかりませんでした。」と伝えてください。"
    ),
)

# 「OAuth認証」 → 「日程調整メール取得・判別」 → 「フォーマット整形・出力」 の順に処理するオーケストレーター
# 以下のエージェントからなるマルチエージェント構成
# root_agent：全体のオーケストレーター
# mail_reader_agent：Gmail からメールを検索・取得し、日程調整メールかどうかを判別して絞り込む
# summarizer_agent：mail_reader_agent が絞り込んだメールを指定フォーマットで整形・出力する
root_agent = Agent(
    name="root_agent",
    model=MODEL,
    # エージェントの説明
    description="Gmail から日程調整メールを読み取り、要約するマルチエージェント。",
    
    # エージェントへの指示（システムプロンプト）
    instruction=(
        "以下の手順で日程調整メールを処理してください。\n"
        "\n"
        "1. authenticate ツールで OAuth認証を行う\n"
        "2. 認証完了後、取得したアクセストークンを用いて、mail_reader_agent ツールで Gmail を検索する\n"
        "3. 検索結果を summarizer_agent ツールで分析し、指定フォーマットで出力する"
    ),
    # Q.mail_reader_agent で取得した結果が、どのようにsummarizer_agent に渡されているのか？
    # A.LLMがinstructionの指示文をもとに、summarizer_agent に取得結果を渡している


    # エージェントが使えるツール（関数）の一覧
    # 各ツールはinstructionから自然言語で呼び出し可能
    tools=[
        # AgentToolはエージェントをツール化し、ツールとして呼び出せるようにする
        authenticate,
        AgentTool(agent=mail_reader_agent),
        AgentTool(agent=summarizer_agent),
        # Q.authenticate だけ関数で、他は Agent化している理由は？ 
        # A.authenticate は「OAuth認証を行いアクセストークンを取得」するという確定したの単一処理のため関数で十分
        #   他はLLMを使い、複数ツールを使った自律的な処理が必要なため Agent にしている
    ],
)
