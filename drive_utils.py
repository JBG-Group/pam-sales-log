"""Google Drive / Sheets の共通ユーティリティ。"""
import os
import sys
import unicodedata

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from auth_google import get_credentials

AUDIO_EXTS = (".m4a", ".mp3", ".wav", ".aac", ".mp4", ".caf", ".ogg", ".webm")

# 共有ドライブ上のフォルダを扱うときに必須。付けないと中身が0件に見える
_ALL_DRIVES = {"supportsAllDrives": True, "includeItemsFromAllDrives": True}


def get_drive_service():
    return build("drive", "v3", credentials=get_credentials())


def get_sheets_service():
    return build("sheets", "v4", credentials=get_credentials())


def nfc(name: str) -> str:
    """macOS で作られたファイル名は NFD（濁点が分解）のことがある。
    比較の前に必ず NFC へ正規化する。"""
    return unicodedata.normalize("NFC", name or "")


def is_audio(f: dict) -> bool:
    if f.get("mimeType") == "application/vnd.google-apps.folder":
        return False
    return (f.get("mimeType", "").startswith("audio/")
            or f.get("name", "").lower().endswith(AUDIO_EXTS))


def list_folder_contents(service, folder_id, page_size=200):
    files, token = [], None
    while True:
        res = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType, size)",
            pageSize=page_size,
            pageToken=token,
            **_ALL_DRIVES,
        ).execute()
        files.extend(res.get("files", []))
        token = res.get("nextPageToken")
        if not token:
            break
    return files


def list_audio_in_folders(service, folder_ids):
    """複数フォルダから音声ファイルを集める。各要素に folder_id を付ける。
    アクセスできないフォルダは警告してスキップする（他のフォルダは処理を続ける）。"""
    result = []
    for folder_id in folder_ids:
        try:
            files = list_folder_contents(service, folder_id)
        except HttpError as e:
            print(f"⚠ フォルダにアクセスできません（{e.resp.status}）。スキップ: {folder_id}")
            continue
        for f in files:
            if is_audio(f):
                f["folder_id"] = folder_id
                result.append(f)
    result.sort(key=lambda x: nfc(x["name"]))
    return result


def find_subfolder(service, parent_id, folder_name):
    safe = folder_name.replace("'", "\\'")
    res = service.files().list(
        q=(f"'{parent_id}' in parents and name='{safe}' "
           "and mimeType='application/vnd.google-apps.folder' and trashed=false"),
        fields="files(id, name)",
        **_ALL_DRIVES,
    ).execute()
    files = res.get("files", [])
    return files[0] if files else None


def ensure_subfolder(service, parent_id, folder_name):
    """サブフォルダを取得。なければ作成して返す。"""
    found = find_subfolder(service, parent_id, folder_name)
    if found:
        return found["id"]
    created = service.files().create(
        body={
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        },
        fields="id",
        supportsAllDrives=True,
    ).execute()
    return created["id"]


def find_spreadsheet(service, parent_id, name):
    res = service.files().list(
        q=(f"'{parent_id}' in parents and name contains '{name}' "
           "and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"),
        fields="files(id, name)",
        **_ALL_DRIVES,
    ).execute()
    files = res.get("files", [])
    return files[0] if files else None


def download_file(service, file_id, file_name, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, file_name)
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        print(f"  既にダウンロード済み: {file_name}")
        return dest_path
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    with open(dest_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"  ダウンロード中 {file_name}: {int(status.progress() * 100)}%")
    print(f"  ダウンロード完了: {file_name}")
    return dest_path


def move_file(service, file_id, from_folder_id, to_folder_id):
    service.files().update(
        fileId=file_id,
        addParents=to_folder_id,
        removeParents=from_folder_id,
        fields="id, parents",
        supportsAllDrives=True,
    ).execute()
