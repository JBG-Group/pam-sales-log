"""
設定の一元管理。すべて環境変数（.env）から読み込む。
シークレットやフォルダIDをコードに直書きしないこと。
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# .env を読む（python-dotenv が入っていれば）
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(
            f"環境変数 {name} が未設定です。.env.example をコピーして .env を作成してください。"
        )
    return val


# --- OpenAI ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# --- Google Drive ---
# 音声ファイルを置くフォルダのID（DriveのURL末尾）
DRIVE_LOG_FOLDER_ID = os.getenv("DRIVE_LOG_FOLDER_ID", "")
# 処理済みの移動先サブフォルダ名（存在しなければ自動作成）
DONE_FOLDER_NAME = os.getenv("DONE_FOLDER_NAME", "processed")

# --- Google Sheets（転記先。使わないなら空でよい） ---
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")

# --- 認証ファイル ---
CREDENTIALS_FILE = os.getenv("CREDENTIALS_FILE", str(BASE_DIR / "credentials.json"))
TOKEN_FILE = os.getenv("TOKEN_FILE", str(BASE_DIR / "token.json"))

# --- 音声処理 ---
AUDIO_DIR = Path(os.getenv("AUDIO_DIR", BASE_DIR / "audio_downloads"))
TRANSCRIPT_DIR = Path(os.getenv("TRANSCRIPT_DIR", BASE_DIR / "transcripts"))
# Whisper APIの上限は25MB。余裕をみて24MBを圧縮の目標にする
MAX_SIZE_MB = int(os.getenv("MAX_SIZE_MB", "24"))
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "")

# --- Whisper ---
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-1")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "ja")
# 固有名詞のヒント。認識させたい人名・商品名を並べると精度が上がる
WHISPER_PROMPT = os.getenv("WHISPER_PROMPT", "")
WHISPER_TEMPERATURE = float(os.getenv("WHISPER_TEMPERATURE", "0"))


def require_openai_key() -> str:
    return _require("OPENAI_API_KEY")


def require_log_folder() -> str:
    return _require("DRIVE_LOG_FOLDER_ID")
