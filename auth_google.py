"""Google OAuth2 認証。初回実行時にブラウザが開き、token.json が作られる。"""
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

import config

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_credentials():
    creds = None
    if os.path.exists(config.TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(config.TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(config.CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"{config.CREDENTIALS_FILE} が見つかりません。\n"
                    "Google Cloud Console で OAuth クライアント（デスクトップアプリ）を作成し、\n"
                    "JSON をダウンロードして credentials.json として置いてください。"
                )
            flow = InstalledAppFlow.from_client_secrets_file(config.CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(config.TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return creds


if __name__ == "__main__":
    get_credentials()
    print("認証に成功しました。トークンを保存:", config.TOKEN_FILE)
