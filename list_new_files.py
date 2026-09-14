"""Drive の対象フォルダ（複数可）にある未処理の音声ファイルを一覧表示する。"""
import sys
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import config
from drive_utils import get_drive_service, is_audio, list_folder_contents, nfc
from googleapiclient.errors import HttpError


def main():
    service = get_drive_service()
    total = 0
    for folder_id in config.require_log_folders():
        try:
            audio = [f for f in list_folder_contents(service, folder_id) if is_audio(f)]
        except HttpError as e:
            print(f"⚠ フォルダにアクセスできません（{e.resp.status}）: {folder_id}\n")
            continue
        total += len(audio)
        print(f"[{folder_id}] {len(audio)} 件")
        for f in sorted(audio, key=lambda x: nfc(x["name"])):
            size_mb = int(f.get("size", 0)) / 1024 / 1024
            print(f"  {f['name']}  ({size_mb:.1f}MB)")
        print()
    print(f"合計: {total} 件")


if __name__ == "__main__":
    main()
