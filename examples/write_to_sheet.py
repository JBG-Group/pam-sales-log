"""
書き起こしテキストを Google Sheets に転記するサンプル。

このリポジトリは「音声→テキスト」までを担当し、
テキストから何を抽出してどう並べるかは案件ごとに異なるため、
ここでは最小構成の書き込み例のみを示す。

実運用では、書き起こしをLLMに読ませて
「面会者・提案内容・次アクション」等を構造化してから転記するとよい。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from drive_utils import get_sheets_service


def append_row(values: list, row: int):
    """指定行に1件書き込む。

    重要: 数式が入っている列は絶対に含めないこと。
    A:Z のような広い範囲で一括更新すると数式が値で上書きされる。
    """
    if not config.SPREADSHEET_ID:
        raise RuntimeError(".env の SPREADSHEET_ID を設定してください")

    svc = get_sheets_service()
    sheet = config.SHEET_NAME

    # 例: A〜E に基本情報、G にメモ（F列は数式なので触らない）
    data = [
        {"range": f"{sheet}!A{row}:E{row}", "values": [values[:5]]},
        {"range": f"{sheet}!G{row}", "values": [[values[5]]]},
    ]

    res = svc.spreadsheets().values().batchUpdate(
        spreadsheetId=config.SPREADSHEET_ID,
        body={"valueInputOption": "USER_ENTERED", "data": data},
    ).execute()
    print(f"更新セル数: {res.get('totalUpdatedCells')}")


def verify_formulas(row: int, col_range: str = "F:F"):
    """書き込み後、数式が生きているか確認する。"""
    svc = get_sheets_service()
    res = svc.spreadsheets().values().get(
        spreadsheetId=config.SPREADSHEET_ID,
        range=f"{config.SHEET_NAME}!{col_range.split(':')[0]}{row}",
        valueRenderOption="FORMULA",
    ).execute()
    print("数式:", res.get("values"))


if __name__ == "__main__":
    append_row(
        ["2026/08/06", "株式会社サンプル", "東京都", "山田太郎", "初回訪問",
         "先方は前向き。次回は見積を持参する。"],
        row=2,
    )
    verify_formulas(row=2)
