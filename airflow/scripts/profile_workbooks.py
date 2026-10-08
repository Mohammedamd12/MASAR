from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def build_inventory(input_dir: Path) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for workbook in sorted(input_dir.glob("*.xlsx")):
        excel = pd.ExcelFile(workbook)
        for sheet_name in excel.sheet_names:
            frame = pd.read_excel(workbook, sheet_name=sheet_name)
            records.append(
                {
                    "file_name": workbook.name,
                    "sheet_name": sheet_name,
                    "row_count": len(frame),
                    "column_count": len(frame.columns),
                }
            )
    return pd.DataFrame(
        records,
        columns=["file_name", "sheet_name", "row_count", "column_count"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile Masar Excel workbooks.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    inventory = build_inventory(args.input_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    inventory.to_csv(args.output, index=False)
    print(f"Wrote {len(inventory)} sheet records to {args.output}")


if __name__ == "__main__":
    main()

