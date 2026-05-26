"""
export_to_sheets.py

Inputs:  credentials.json (OAuth client secret), CSV path as argv[1] or default
Outputs: New Google Sheet with formatted data, prints URL

First run opens a browser for Google sign-in. token.json is cached afterwards.
"""

import os
import csv
import sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
TOKEN_PATH = "token.json"
CREDS_PATH = "credentials.json"

CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else ".tmp/channel_research.csv"
SHEET_TITLE = "Space Lofi — Channel Research"


def get_creds():
    creds = None
    if Path(TOKEN_PATH).exists():
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return creds


def read_csv(path: str) -> tuple[list[str], list[list]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    return rows[0], rows[1:]


def col_letter(n: int) -> str:
    """Convert 0-based column index to A1 notation letter."""
    result = ""
    while True:
        result = chr(65 + n % 26) + result
        n = n // 26 - 1
        if n < 0:
            break
    return result


def main():
    if not Path(CREDS_PATH).exists():
        print(f"ERROR: {CREDS_PATH} not found.")
        print("Follow setup instructions to download OAuth credentials from Google Cloud Console.")
        sys.exit(1)

    if not Path(CSV_PATH).exists():
        print(f"ERROR: {CSV_PATH} not found. Run youtube_channel_research.py first.")
        sys.exit(1)

    headers, rows = read_csv(CSV_PATH)
    print(f"Loaded {len(rows)} rows from {CSV_PATH}")

    creds = get_creds()
    service = build("sheets", "v4", credentials=creds)
    sheets = service.spreadsheets()

    # --- Create spreadsheet ---
    spreadsheet = sheets.create(body={
        "properties": {"title": SHEET_TITLE},
        "sheets": [{"properties": {"title": "Channels"}}],
    }).execute()

    sheet_id = spreadsheet["spreadsheetId"]
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
    grid_id = spreadsheet["sheets"][0]["properties"]["sheetId"]
    print(f"Created sheet: {url}")

    # --- Write data ---
    all_rows = [headers] + rows
    sheets.values().update(
        spreadsheetId=sheet_id,
        range="Channels!A1",
        valueInputOption="RAW",
        body={"values": all_rows},
    ).execute()
    print(f"Written {len(all_rows)} rows")

    last_col = col_letter(len(headers) - 1)
    num_rows = len(all_rows)

    # --- Format: freeze header, bold, background, auto-resize ---
    requests = [
        # freeze header row
        {"updateSheetProperties": {
            "properties": {"sheetId": grid_id, "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount",
        }},
        # bold + background on header row
        {"repeatCell": {
            "range": {"sheetId": grid_id, "startRowIndex": 0, "endRowIndex": 1},
            "cell": {"userEnteredFormat": {
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                "backgroundColor": {"red": 0.13, "green": 0.09, "blue": 0.27},
            }},
            "fields": "userEnteredFormat(textFormat,backgroundColor)",
        }},
        # auto-resize all columns
        {"autoResizeDimensions": {
            "dimensions": {"sheetId": grid_id, "dimension": "COLUMNS",
                           "startIndex": 0, "endIndex": len(headers)},
        }},
        # alternate row shading
        {"addConditionalFormatRule": {
            "rule": {
                "ranges": [{"sheetId": grid_id, "startRowIndex": 1, "endRowIndex": num_rows}],
                "booleanRule": {
                    "condition": {"type": "CUSTOM_FORMULA",
                                  "values": [{"userEnteredValue": "=ISEVEN(ROW())"}]},
                    "format": {"backgroundColor": {"red": 0.95, "green": 0.93, "blue": 1.0}},
                },
            },
            "index": 0,
        }},
        # number format: commas for numeric columns (cols C-L, 0-based indices 2-11)
        {"repeatCell": {
            "range": {"sheetId": grid_id, "startRowIndex": 1, "endRowIndex": num_rows,
                      "startColumnIndex": 2, "endColumnIndex": 12},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}}},
            "fields": "userEnteredFormat.numberFormat",
        }},
    ]

    sheets.batchUpdate(spreadsheetId=sheet_id, body={"requests": requests}).execute()
    print("Formatting applied")
    print(f"\nDone! Open your sheet:\n{url}")


if __name__ == "__main__":
    main()
