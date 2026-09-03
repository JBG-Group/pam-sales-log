"""
転記が済んだ音声ファイルを、処理済みフォルダへ移動する。

使い方:
    python move_processed.py file1.mp3 file2.m4a
    python move_processed.py --all          # フォルダ内の全音声を移動
    python move_processed.py --from-list done.txt
"""
import argparse
import sys

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import config
from drive_utils import (get_drive_service, list_folder_contents,
                         ensure_subfolder, move_file, nfc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help="移動するファイル名")
    ap.add_argument("--all", action="store_true", help="全音声ファイルを移動")
    ap.add_argument("--from-list", help="1行1ファイル名のテキストから読む")
    args = ap.parse_args()

    targets = set(nfc(f) for f in args.files)
    if args.from_list:
        with open(args.from_list, encoding="utf-8") as fh:
            targets |= {nfc(line.strip()) for line in fh if line.strip()}

    if not targets and not args.all:
        ap.error("ファイル名か --all を指定してください")

    folder_id = config.require_log_folder()
    service = get_drive_service()
    done_id = ensure_subfolder(service, folder_id, config.DONE_FOLDER_NAME)
    print(f"移動先: {config.DONE_FOLDER_NAME} (id={done_id})")

    moved = 0
    for f in list_folder_contents(service, folder_id):
        if f["mimeType"] == "application/vnd.google-apps.folder":
            continue
        # macOS 由来の NFD 名に備えて正規化して比較する
        if args.all or nfc(f["name"]) in targets:
            print(f"  移動: {f['name']}")
            move_file(service, f["id"], folder_id, done_id)
            moved += 1

    print(f"\n{moved} 件を移動しました。")


if __name__ == "__main__":
    main()
