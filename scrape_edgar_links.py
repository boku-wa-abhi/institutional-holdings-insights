#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

from src.data_extraction.scrape_edgar_links import EdgarLinksProcessor


def main() -> int:
    parser = argparse.ArgumentParser(description="Process a single EDGAR links Excel file and download 13F-HR submission text files")
    parser.add_argument("filename", help="Excel filename to process (e.g., blackrock.xlsx)")
    parser.add_argument(
        "--dir",
        default=str(Path("data") / "edgar_links"),
        help="Directory containing the Excel file (default: data/edgar_links)",
    )
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    edgar_dir = Path(args.dir)
    xlsx_path = edgar_dir / args.filename

    if not xlsx_path.exists():
        print(f"Input not found: {xlsx_path}")
        return 1
    if xlsx_path.suffix.lower() != ".xlsx":
        print(f"Input must be an .xlsx file: {xlsx_path}")
        return 1

    try:
        processor = EdgarLinksProcessor(base)
        res = processor.process_file(xlsx_path)
        print(f"Processed: {xlsx_path.name} -> {res.get('status')}\n  Details: "
              f"{', '.join([f'{k}:{v}' for k,v in res.items() if k.startswith('error_') or k.startswith('saved_')])}")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())