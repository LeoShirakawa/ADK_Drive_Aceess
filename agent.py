import os
import requests
import json

from google.adk.tools import ToolContext
from google.adk.agents import LlmAgent

# The AUTH_ID must match the one registered in Agentspace
AUTH_ID = "google-drive-reader-auth"

def list_drive_files(query: str, tool_context: ToolContext) -> str:
    """
    Lists files and folders from the user's Google Drive.
    The query is ignored, and items from the root directory are returned.
    """
    print(f"DEBUG: Attempting to retrieve access token with AUTH_ID: {AUTH_ID}")
    access_token = tool_context.state.get(f"temp:{AUTH_ID}")

    # --- LOCAL TESTING WORKAROUND ---
    if not access_token:
        print("DEBUG: Token not in tool_context, trying environment variable 'DRIVE_ACCESS_TOKEN'...")
        access_token = os.getenv("DRIVE_ACCESS_TOKEN")
    # --------------------------------

    if not access_token:
        print(f"DEBUG: Authentication token NOT found.")
        return "エラー: 認証トークンが見つかりません。UIで認証するか、ローカルテストの場合は環境変数を設定してください。"
    
    print(f"DEBUG: Authentication token found.")

    try:
        url = "https://www.googleapis.com/drive/v3/files"
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {
            'pageSize': 15,
            'fields': "nextPageToken, files(id, name)"
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        files = response.json().get('files', [])
        if not files:
            return "Google Driveにファイルが見つかりませんでした。"
        
        file_names = [f"- {file.get('name')} (ID: {file.get('id')})" for file in files]
        return "Google Driveのファイル一覧:\n" + "\n".join(file_names)

    except requests.exceptions.RequestException as e:
        error_message_for_llm = f"APIリクエストエラー: {e}"
        if e.response is not None:
            try:
                error_json = e.response.json()
                print(f"DEBUG: Full JSON error from API: {json.dumps(error_json)}")
                error_message_for_llm = f"API Error: {error_json.get('error', {}).get('message', 'Unknown error')}"
            except json.JSONDecodeError:
                print(f"DEBUG: Non-JSON error response from API: {e.response.text}")
                error_message_for_llm = f"API Error: {e.response.status_code} {e.response.reason}"
        else:
            print(f"DEBUG: RequestException with no response: {e}")

        return error_message_for_llm
    except Exception as e:
        return f"予期せぬエラーが発生しました: {e}"

# Define the agent programmatically.
root_agent = LlmAgent(
    name="GoogleDriveAgent",
    model="gemini-2.5-flash",
    instruction="""
    Your goal is to help the user check files in their Google Drive.
    Use the `list_drive_files` tool to get a list of files.
    Present the list of files returned by the tool as your final answer.
    """,
    description="An agent that lists files from a user's Google Drive.",
    tools=[list_drive_files]
)