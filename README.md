# ADKエージェントとGoogle Drive認証 - デプロイガイド

このガイドは、Agentspace内でOAuth 2.0認証を利用してユーザーのGoogle DriveファイルにアクセスできるADKエージェントを構築、デプロイ、登録するためのステップバイステップの手順を説明します。

## 前提条件

- Google Cloud SDK (`gcloud`) がインストールされ、認証済みであること。
- Python 3.10+ および `pip` がインストール済みであること。
- 課金が有効なGoogle Cloudプロジェクト。
- Python環境にGoogle ADK CLIがインストール済みであること。

---

## ステップ1: Google Cloud OAuthの設定

まず、アプリケーション用のOAuth認証情報を作成します。

1.  **Google Drive APIの有効化:**
    以下のリンクを使い、あなたのプロジェクトでGoogle Drive APIが有効になっていることを確認します。
    ```
    https://console.cloud.google.com/apis/library/drive.googleapis.com?project=<YOUR_PROJECT_ID>
    ```

2.  **OAuthクライアントIDの作成:**
    - Cloudコンソールの[認証情報ページ](https://console.cloud.google.com/apis/credentials)に移動します。
    - **+ 認証情報を作成** > **OAuthクライアントID** をクリックします。
    - アプリケーションの種類として **ウェブアプリケーション** を選択します。
    - **承認済みのリダイレクトURI** の下にある **+ URIを追加** をクリックし、以下の値を正確に入力します。
      ```
      https://vertexaisearch.cloud.google.com/oauth-redirect
      ```
    - **作成** をクリックします。
    - 生成された **クライアントID** と **クライアントシークレット** をコピーしておきます。後で必要になります。

---

## ステップ2: エージェントプロジェクトのファイル設定

エージェント用のディレクトリを作成し、必要なファイルを準備します。

1.  **プロジェクトディレクトリの作成:**
    ```bash
    mkdir adk_drive_acl
    cd adk_drive_acl
    ```

2.  **`requirements.txt` の作成:** このファイルはPythonの依存関係をリストします。
    ```text
    google-cloud-aiplatform[adk,agent_engines]
    requests
    ```

3.  **`.env` ファイルの作成:** このファイルはエージェントがVertex AIを使用するよう設定します。**これは非常に重要なステップです。**
    ```text
    GOOGLE_GENAI_USE_VERTEXAI="True"
    GOOGLE_CLOUD_PROJECT="<YOUR_PROJECT_ID>"
    GOOGLE_CLOUD_LOCATION="us-central1"
    ```
    `<YOUR_PROJECT_ID>` を実際のGoogle CloudプロジェクトIDに置き換えてください。

4.  **`agent.py` の作成:** エージェントのコアロジックです。
    ```python
    import os
    import requests
    from google.adk.tools import ToolContext
    from google.adk.agents import LlmAgent

    AUTH_ID = "google-drive-reader-auth" # ステップ4で使うIDと一致させる必要があります

    def list_drive_files(query: str, tool_context: ToolContext) -> str:
        # ... (このファイルのコードは前の手順で作成したものと同じです)

    root_agent = LlmAgent(
        name="GoogleDriveAgent",
        model="gemini-2.5-flash",
        instruction="Use the list_drive_files tool to get a list of files from the user's Google Drive.",
        description="An agent that lists files from a user's Google Drive.",
        tools=[list_drive_files]
    )
    ```

5.  **`deploy.py` の作成:** このスクリプトはエージェントをVertex AIにデプロイします。
    ```python
    import vertexai
    from vertexai import agent_engines
    from vertexai.preview import reasoning_engines
    import os
    from dotenv import load_dotenv

    load_dotenv()

    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "<YOUR_PROJECT_ID>")
    LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    STAGING_BUCKET = "gs://<YOUR_STAGING_BUCKET_NAME>"
    DEPLOY_DISPLAY_NAME = "Google Drive ACL Agent"

    DEPLOY_ENVIRONMENT = {
        "GOOGLE_GENAI_USE_VERTEXAI": os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "True"),
    }

    from agent import root_agent
    with open("requirements.txt", "r") as f:
        requirements = [line.strip() for line in f if line.strip()]

    vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

    app = reasoning_engines.AdkApp(agent=root_agent, enable_tracing=True)

    remote_app = agent_engines.create(
        display_name=DEPLOY_DISPLAY_NAME,
        agent_engine=app,
        requirements=requirements,
        extra_packages=["agent.py"],
        description="An agent that can list files in Google Drive.",
        env_vars=DEPLOY_ENVIRONMENT
    )

    print(f"\nDeployment submitted successfully!")
    print(f"The Reasoning Engine resource name is: {remote_app.resource_name}")
    deployment_id = remote_app.resource_name.split('/')[-1]
    print(f"Extracted ADK_DEPLOYMENT_ID: {deployment_id}")
    ```
    このスクリプト内の `<YOUR_PROJECT_ID>` と `<YOUR_STAGING_BUCKET_NAME>` を置き換えてください。

---

## ステップ3: ローカル認証情報の設定

デプロイとローカルテストのために、ローカル環境に正しい権限を設定します。

1.  **スコープ付きでログイン:** このコマンドを実行し、ユーザー認証情報に必要なAPIスコープを付与します。ブラウザウィンドウが開き、承認を求められます。
    ```bash
    gcloud auth application-default login --scopes='openid,https://www.googleapis.com/auth/drive.readonly,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/cloud-platform'
    ```

2.  **Quotaプロジェクトの設定:** このコマンドは、APIの課金と割り当てに使用するプロジェクトを指定します。ユーザー認証情報を使用する際に必要です。
    ```bash
    gcloud auth application-default set-quota-project <YOUR_PROJECT_ID>
    ```

---

## ステップ4: Agentspace認可リソースの作成

OAuth認証情報をAgentspaceに登録します。エージェント登録ごとに、一意の認可リソースが必要です。

-   プレースホルダーを置き換えて、この`curl`コマンドを実行します。
-   `AUTH_ID` には、任意のユニークな文字列（例: `google-drive-auth-prod`）を指定します。

```bash
export ACCESS_TOKEN=$(gcloud auth print-access-token)
export PROJECT_ID="<YOUR_PROJECT_ID>"
export AUTH_ID="<CHOOSE_A_UNIQUE_AUTH_ID>"
export OAUTH_CLIENT_ID="<YOUR_CLIENT_ID_FROM_STEP_1>"
export OAUTH_CLIENT_SECRET="<YOUR_CLIENT_SECRET_FROM_STEP_1>"

curl -X POST \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: $PROJECT_ID" \
  "https://discoveryengine.googleapis.com/v1alpha/projects/$PROJECT_ID/locations/global/authorizations?authorizationId=$AUTH_ID" \
  -d '{
    "name": "projects/'$PROJECT_ID'/locations/global/authorizations/'$AUTH_ID'",
    "serverSideOauth2": {
      "clientId": "$OAUTH_CLIENT_ID",
      "clientSecret": "$OAUTH_CLIENT_SECRET",
      "authorizationUri": "https://accounts.google.com/o/oauth2/v2/auth?scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive.readonly&include_granted_scopes=true&response_type=code&access_type=offline&prompt=consent",
      "tokenUri": "https://oauth2.googleapis.com/token"
    }
  }'
```

---

## ステップ5: エージェントのデプロイ

作成したデプロイスクリプトを実行します。

1.  **依存関係のインストール:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **デプロイの実行:**
    ```bash
    python deploy.py
    ```

3.  **出力のコピー:** スクリプトの最後に `ADK_DEPLOYMENT_ID` が表示されます。最終ステップのためにこのIDをコピーしておきます。

---

## ステップ6: Agentspaceへのエージェント登録

最後に、デプロイしたエージェントをAgentspaceアプリに登録します。

-   プレースホルダー、特に `<YOUR_AGENTSPACE_APP_ID>`, `<YOUR_ADK_DEPLOYMENT_ID>`、そしてステップ4の出力から得られる `AUTH_ID` と `AUTH_PROJECT_ID` を置き換えます。

```bash
export ACCESS_TOKEN=$(gcloud auth print-access-token)
export PROJECT_ID="<YOUR_PROJECT_ID>"
export APP_ID="<YOUR_AGENTSPACE_APP_ID>"
export ADK_DEPLOYMENT_ID="<ID_FROM_STEP_5>"
export AUTH_ID="<ID_FROM_STEP_4>"
# これはOAuthクライアントを所有するプロジェクト番号です（ステップ4の出力から）
export AUTH_PROJECT_ID="<AUTH_PROJECT_NUMBER>" 

curl -X POST \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: $PROJECT_ID" \
  "https://discoveryengine.googleapis.com/v1alpha/projects/$PROJECT_ID/locations/global/collections/default_collection/engines/$APP_ID/assistants/default_assistant/agents" \
  -d '{
    "displayName": "Google Drive ACL Agent",
    "description": "Google Drive内のファイル一覧を表示します。",
    "adk_agent_definition": {
      "tool_settings": {
        "tool_description": "ユーザーのGoogle Driveにあるファイルやフォルダを一覧表示する必要がある場合に使用します。"
      },
      "provisioned_reasoning_engine": {
        "reasoning_engine": "projects/'$PROJECT_ID'/locations/us-central1/reasoningEngines/'$ADK_DEPLOYMENT_ID'"
      }
    },
    "authorization_config": {
      "tool_authorizations": [
        "projects/$AUTH_PROJECT_ID/locations/global/authorizations/$AUTH_ID"
      ]
    }
  }'
```

---

## ステップ7: Agentspaceでのテスト

これでエージェントが登録されました。AgentspaceアプリケーションのUIに移動し、エージェントを選択してテストしてください。最初の利用時に、Google Driveへのアクセスを許可するために **Authorize** ボタンを押すよう求められます。

```