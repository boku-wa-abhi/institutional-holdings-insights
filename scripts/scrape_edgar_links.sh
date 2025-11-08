#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_DIR="$ROOT_DIR/data/edgar_links"

usage() {
  echo "Usage: $(basename "$0") <filename.xlsx> [--dir <folder>]" >&2
  exit 1
}

FILENAME="${1:-}"
if [[ -z "$FILENAME" ]]; then
  usage
fi

DIR="$DEFAULT_DIR"
if [[ "${2:-}" == "--dir" ]]; then
  DIR="${3:-$DEFAULT_DIR}"
fi

XLSX_PATH="$DIR/$FILENAME"
if [[ ! -f "$XLSX_PATH" ]]; then
  echo "Input file not found: $XLSX_PATH" >&2
  exit 1
fi

cd "$ROOT_DIR"

python3 - <<PY
from pathlib import Path
import sys
try:
    from src.data_extraction.scrape_edgar_links import EdgarLinksProcessor
    base = Path("$ROOT_DIR")
    xlsx_path = Path("$XLSX_PATH")
    processor = EdgarLinksProcessor(base)
    res = processor.process_file(xlsx_path)
    details = ", ".join([f"{k}:{v}" for k,v in res.items() if k.startswith("error_") or k.startswith("saved_")])
    print(f"Processed: {xlsx_path.name} -> {res.get('status')}\n  Details: {details}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(2)
PY