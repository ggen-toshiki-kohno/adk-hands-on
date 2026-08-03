# ADK Tips

## Session について

1会話分のデータ（会話履歴・state）を保持するオブジェクト。`adk web` では自動的に `.adk/session.db`（SQLite）に永続化される。

**session.db の特徴:**

- `adk web` が自動生成する。ユーザーが作成するものではない
- OAuth アクセストークンなどの state が平文で保存されるため `.gitignore` に追加すること
- ADKエージェントをAgent Runtime(※) にデプロイする場合、セッションは自動的に保管管理される（参考: https://docs.cloud.google.com/gemini-enterprise-agent-platform/scale?hl=ja#supported-regions）
    > (※) **Agent Runtime とは**: Google Cloud の Agent Platform(旧Vertex AI) が提供するマネージドなエージェント実行基盤。インフラ管理不要でエージェントをデプロイするだけで、スケーリング、セッションの自動管理が行える。

---

## Agent（LlmAgent）と Workflow について

複数のエージェントを直列に実行するマルチエージェントを構成する場合、**Agent(今回のソースコードで利用)** や **Workflow** を使う方式がある。

### Agent（LlmAgent）

LLM が instruction を読んで自律的にツールの呼び出し順を判断する。

```python
root_agent = Agent(
    instruction="1. authenticate で認証する\n2. mail_reader_agent でメールを取得する\n...",
    tools=[authenticate, AgentTool(agent=mail_reader_agent), ...],
)
```

### Workflow

コードで処理フローを明示的に定義する。

```python
from google.adk.workflow import Workflow, START

root_agent = Workflow(
    name="pipeline",
    edges=[
        (START, mail_reader_agent, summarizer_agent),
    ],
)
```

### Workflow + OAuth は動作しない（ADK 2.5.0 の不具合）

OAuth認証をADKエージェント側で行う際、`Workflow` 内で OAuth 認証を試みると、認証が完了しない事象が発生する。
※Gemini Enterprise 側で OAuth 認証を行う場合は、仕様上は本事象は発生せずWokflowは利用可能想定（未検証）。

**原因:** ユーザーが認可を完了すると、ADK は「**ユーザ**ーからの返答が届いた」ことを検知してトークンを取得する。しかし `Workflow` はその直後に自分(**エージェント**)のメッセージを割り込ませてしまうため、ADK が「ユーザーからの返答」を見失い、認証が完了しない。

**回避策:** Workflowを使いつつOAuth認証処理を実装したい場合は、`Agent`でOAuth 認証を行い、`Workflow`を外部で定義して呼び出すことで本事象を回避可能。

```python
_workflow = Workflow(
    name="workflow",
    edges=[
        (START, mail_reader_agent, summarizer_agent),
    ],
)

root_agent = Agent(  # root は LlmAgent にする
    instruction=(
        "1. authenticate ツールで OAuth 認証を行う\n"
        "2. 認証完了後、workflow ツールで日程調整メールを取得・要約する"
    ),
    tools=[
        authenticate,
        AgentTool(agent=_workflow),
    ],
)
```

---
## ADK公式ドキュメント

- [ADK Get Started](https://adk.dev/get-started/) - ADK公式リファレンス