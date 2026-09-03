# pam-sales-log

Google Drive に溜まった商談・会議の録音を、**Whisper API で書き起こしてスプレッドシートに転記する**までを自動化するツールです。

営業チームが訪問先で録音した音声をDriveに放り込んでおくだけで、書き起こしまで一括で回せます。実運用（クラシック音楽事務所の営業ログ、約150件の商談）で使っているものを汎用化して公開しています。

```
Google Drive（音声）→ 自動ダウンロード → ffmpegで圧縮 → Whisper API
    → transcripts/*.txt → （任意）Google Sheets へ転記 → 処理済みフォルダへ移動
```

## 特徴

- **25MB超の音声を自動圧縮**（Whisper APIの上限対策）。1〜2時間の商談録音でもそのまま投げられる
- **処理済みファイルはスキップ**するので、何度実行しても安全
- **ハルシネーション検出**：録音レベルが低いと Whisper は同じ文を延々繰り返すことがある。これを自動で検知して警告する
- **NFD/NFC 正規化**：macOSで作られた日本語ファイル名（濁点が分解される）でも取りこぼさない
- シークレットは**すべて環境変数**。コードに直書きしない

## セットアップ

### 1. インストール

```bash
git clone https://github.com/jbgmusic/pam-sales-log.git
cd pam-sales-log
pip install -r requirements.txt
```

**ffmpeg** が必要です（音声圧縮に使用）。

```bash
# Windows
winget install Gyan.FFmpeg
# macOS
brew install ffmpeg
# Ubuntu
sudo apt install ffmpeg
```

### 2. Google API の準備

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. **Google Drive API** と **Google Sheets API** を有効化
3. 「認証情報」→「OAuth クライアント ID」→ 種類は **デスクトップアプリ**
4. JSONをダウンロードし、`credentials.json` としてこのフォルダに置く

### 3. 設定

```bash
cp .env.example .env
```

`.env` を編集します。最低限必要なのは次の2つです。

| 変数 | 内容 |
|---|---|
| `OPENAI_API_KEY` | [OpenAIのAPIキー](https://platform.openai.com/api-keys) |
| `DRIVE_LOG_FOLDER_ID` | 音声を置くDriveフォルダのID |

フォルダIDは、Driveでそのフォルダを開いたときのURL末尾です。

```
https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz
                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^ ここ
```

### 4. 初回認証

```bash
python auth_google.py
```

ブラウザが開くのでGoogleアカウントで許可します。`token.json` が作られれば完了です。

## 使い方

```bash
# 1. 未処理の音声を確認
python list_new_files.py

# 2. 書き起こし（transcripts/ に .txt が出力される）
python transcribe.py

# 3. 転記が済んだファイルを処理済みフォルダへ移動
python move_processed.py "商談_2026-08-06.m4a"
python move_processed.py --all
```

## 書き起こし精度を上げる

`.env` の `WHISPER_PROMPT` に**固有名詞を並べる**と、人名・団体名・商品名の誤変換が大きく減ります。

```
WHISPER_PROMPT=山田太郎,鈴木花子,株式会社サンプル,定期演奏会,共催,買取
```

## つまずきやすい点

### 書き起こしが同じ文の繰り返しになる

```
本日はご覧いただきありがとうございます。本日はご覧いただきありがとうございます。（延々続く）
```

Whisperのハルシネーションです。**録音の音量が極端に小さい／無音区間が長い**ときに起きます。`transcribe.py` は自動で検知して `⚠` を出します。

対策として音量正規化を試せますが、そもそも声が入っていない場合は回復しません。**録音時にマイクが塞がれていないか確認するのが最も確実**です。

```bash
ffmpeg -i input.m4a -af loudnorm -b:a 64k -ac 1 -ar 16000 output.mp3
```

### 音声ファイルが見つからない（macOSで録音した場合）

macOSは日本語ファイル名を **NFD**（「ぴ」を「ひ」+「゜」に分解）で保存します。Windows/Linuxの **NFC** と一致しないため、単純な文字列比較では引っかかりません。

本ツールは `drive_utils.nfc()` で正規化してから比較しているので、通常は意識不要です。自分でスクリプトを書く場合は必ず正規化してください。

```python
import unicodedata
unicodedata.normalize("NFC", filename)
```

### Whisper API が 413 を返す

圧縮後も25MBを超えています。`transcribe.py` は自動で16kbpsまで落としますが、それでも大きい場合は元ファイルを分割してください。

## スプレッドシートへの転記

書き起こしたテキストを構造化してSheetsに書き込む例は [`examples/write_to_sheet.py`](examples/write_to_sheet.py) にあります。

**数式が入った列を壊さないこと。** `A:Z` のように広い範囲を一括更新すると、集計用の数式が値で上書きされます。書き込む列を明示的に分けてください。

```python
# NG: 数式列ごと潰れる
{"range": "Sheet1!A2:H2", "values": [[...]]}

# OK: 数式列(F,G)を避けて分割
{"range": "Sheet1!A2:E2", "values": [[...]]}
{"range": "Sheet1!H2",    "values": [[...]]}
```

## ライセンス

MIT
