"""Helpers for reading the messy Excel files (title rows, different column orders, Arabic text)."""
from pathlib import Path

import pandas as pd


def norm_ar(value):
    """Clean a text value so two spellings of the same word look the same.

    It removes accents, replaces letter variants, and fixes extra spaces.
    The codes below are Arabic letters written as escape codes, so this repo has no Arabic script.
    """
    text = str(value)
    for accent in "\u064b\u064c\u064d\u064e\u064f\u0650\u0651\u0652\u0640":
        text = text.replace(accent, "")
    for letter in "\u0623\u0625\u0622":  # three kinds of alef
        text = text.replace(letter, "\u0627")  # -> plain alef
    text = text.replace("\u0629", "\u0647")  # teh marbuta -> heh
    text = text.replace("\u0649", "\u064a")  # alef maksura -> yeh
    text = " ".join(text.split())  # one space between words
    return text.lower()


def read_sheet(path, sheet, headers, min_found):
    """Read one sheet. The header row can be anywhere in the first 30 rows.

    headers is {"english_name": {"cleaned source header", ...}}.
    Returns (table, layout_version, header_row), or None if no header row is found.
    Only the columns we know are kept, and they get English names, so the column
    order and extra columns (notes, empty columns) do not matter.
    """
    raw = pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)

    # source header text -> English name
    lookup = {}
    for english_name, source_names in headers.items():
        for source_name in source_names:
            lookup[source_name] = english_name

    # the header row is the first row that has enough known column names
    header_row = None
    for row_number in range(min(30, len(raw))):
        found = set()
        for cell in raw.iloc[row_number]:
            if pd.notna(cell) and norm_ar(cell) in lookup:
                found.add(lookup[norm_ar(cell)])
        if len(found) >= min_found:
            header_row = row_number
            break
    if header_row is None:
        return None

    # keep only the known columns and rename them
    columns = {}  # column position -> English name
    for position, cell in enumerate(raw.iloc[header_row]):
        if pd.notna(cell) and norm_ar(cell) in lookup:
            english_name = lookup[norm_ar(cell)]
            if english_name not in columns.values():
                columns[position] = english_name

    table = raw.iloc[header_row + 1:, list(columns.keys())].copy()
    table.columns = list(columns.values())
    table = table.dropna(how="all")  # remove empty rows
    table["source_row"] = table.index + 1  # the row number you see in Excel

    layout_version = f"{raw.shape[1]} columns, header on row {header_row + 1}"
    return table, layout_version, header_row + 1


def read_workbook(path, headers, min_found):
    """Read every sheet of one Excel file. Returns (rows, log).

    Sheets without a header row (for example metadata sheets) are skipped and written to the log.
    """
    path = Path(path)
    tables = []
    log = []
    sheet_names = pd.ExcelFile(path).sheet_names
    for number, sheet in enumerate(sheet_names, start=1):  # sheet names can be Arabic, so we log the number
        result = read_sheet(path, sheet, headers, min_found)
        if result is None:
            log.append({"source_file": path.name, "sheet_number": number, "status": "skipped: no header row found"})
            continue
        table, layout_version, header_row = result
        table["source_file"] = path.name
        table["layout_version"] = layout_version
        tables.append(table)
        log.append({"source_file": path.name, "sheet_number": number, "status": "ok",
                    "layout_version": layout_version, "header_row": header_row, "data_rows": len(table)})
    rows = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()
    return rows, log
