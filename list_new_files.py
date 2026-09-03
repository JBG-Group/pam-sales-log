"""Drive の対象フォルダにある未処理の音声ファイルを一覧表示する。"""
import sys
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import config
from drive_utils import get_drive_service, list_folder_contents


def main():
    folder_id = config.require_log_folder()
    service = get_drive_service()
    files = list_folder_contents(service, folder_id)
    audio = [f for f in files if f["mimeType"].startswith("audio/")]

    print(f"音声ファイル: {len(audio)} 件\n")
    for f in sorted(audio, key=lambda x: x["name"]):
        size_mb = int(f.get("size", 0)) / 1024 / 1024
        print(f"  {f['name']}  ({size_mb:.1f}MB)")
    if not audio:
        print("  （なし）")


if __name__ == "__main__":
    main()
