"""
Drive の音声ファイルを OpenAI Whisper API で書き起こす。

- 25MB を超えるファイルは ffmpeg で自動圧縮（モノラル16kHz）
- 書き起こし済みのファイルはスキップ
- 結果は transcripts/ に .txt で保存
"""
import os
import sys
import shutil
import subprocess
import tempfile

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from openai import OpenAI

import config
from drive_utils import get_drive_service, list_audio_in_folders, download_file


def resolve_ffmpeg() -> str:
    path = config.FFMPEG_PATH or shutil.which("ffmpeg")
    if not path:
        raise RuntimeError(
            "ffmpeg が見つかりません。インストールして PATH を通すか、\n"
            ".env の FFMPEG_PATH に実行ファイルのフルパスを設定してください。"
        )
    return path


def compress_audio(input_path: str, bitrate: str = "32k") -> str:
    """Whisper の 25MB 制限に収まるよう圧縮する。"""
    ffmpeg = resolve_ffmpeg()
    out = os.path.join(tempfile.gettempdir(), "whisper_compressed.mp3")
    orig_mb = os.path.getsize(input_path) / 1024 / 1024
    print(f"  圧縮中 ({orig_mb:.1f}MB → 目標 <{config.MAX_SIZE_MB}MB)...")

    for br in (bitrate, "16k"):
        subprocess.run(
            [ffmpeg, "-y", "-i", input_path,
             "-ac", "1", "-ar", "16000", "-b:a", br, "-map", "0:a", out],
            capture_output=True,
        )
        new_mb = os.path.getsize(out) / 1024 / 1024
        print(f"  圧縮後: {new_mb:.1f}MB (bitrate={br})")
        if new_mb <= config.MAX_SIZE_MB:
            break
    return out


def transcribe_file(audio_path: str) -> str:
    client = OpenAI(api_key=config.require_openai_key())
    file_mb = os.path.getsize(audio_path) / 1024 / 1024
    upload_path = compress_audio(audio_path) if file_mb > config.MAX_SIZE_MB else audio_path

    # 日本語ファイル名のままだと API が弾くことがあるので ASCII 名にコピーして送る
    ext = os.path.splitext(upload_path)[1] or ".mp3"
    ascii_path = os.path.join(tempfile.gettempdir(), f"whisper_upload{ext}")
    if upload_path != ascii_path:
        shutil.copy2(upload_path, ascii_path)

    print("  Whisper API に送信中...")
    kwargs = dict(
        model=config.WHISPER_MODEL,
        language=config.WHISPER_LANGUAGE,
        temperature=config.WHISPER_TEMPERATURE,
    )
    if config.WHISPER_PROMPT:
        kwargs["prompt"] = config.WHISPER_PROMPT

    with open(ascii_path, "rb") as f:
        result = client.audio.transcriptions.create(file=f, **kwargs)
    return result.text


def looks_like_hallucination(text: str) -> bool:
    """無音・極小音量の録音で Whisper が同一フレーズを繰り返す現象を検出する。"""
    if len(text) < 200:
        return False
    head = text[:400]
    for size in (12, 20):
        frag = head[:size].strip()
        if frag and text.count(frag) > 15:
            return True
    return False


def main():
    folder_ids = config.require_log_folders()
    config.TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    config.AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    drive = get_drive_service()
    audio_files = list_audio_in_folders(drive, folder_ids)

    print(f"=== 対象フォルダ {len(folder_ids)} 件: {len(audio_files)} 音声ファイル ===\n")
    results = []

    for i, f in enumerate(audio_files, 1):
        name = f["name"]
        size_mb = int(f.get("size", 0)) / 1024 / 1024
        txt_path = config.TRANSCRIPT_DIR / (os.path.splitext(name)[0] + ".txt")
        print(f"[{i}/{len(audio_files)}] {name} ({size_mb:.1f}MB)")

        if txt_path.exists() and txt_path.stat().st_size > 100:
            print("  スキップ（書き起こし済み）")
            results.append((name, "already_done"))
            continue

        audio_path = str(config.AUDIO_DIR / name)
        if not os.path.exists(audio_path):
            download_file(drive, f["id"], name, str(config.AUDIO_DIR))

        try:
            text = transcribe_file(audio_path)
            txt_path.write_text(text, encoding="utf-8")
            if looks_like_hallucination(text):
                print(f"  ⚠ 完了 ({len(text)}字) — 同一フレーズの反復を検出。"
                      "録音レベルが低い可能性があります。要確認")
                results.append((name, "done_suspect"))
            else:
                print(f"  完了 ({len(text)}字)")
                results.append((name, "done"))
        except Exception as e:
            print(f"  エラー: {e}")
            results.append((name, "error"))

    print("\n=== 結果 ===")
    for name, status in results:
        print(f"  {status:>13}: {name}")


if __name__ == "__main__":
    main()
