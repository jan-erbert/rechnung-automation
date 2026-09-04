#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"

echo "Starte Rechnungsgenerierung..."

if [ ! -x "$PYTHON_BIN" ]; then
    echo "Virtuelle Umgebung nicht gefunden oder Python nicht ausfuehrbar unter: $PYTHON_BIN"
    exit 1
fi

cd "$SCRIPT_DIR"
"$PYTHON_BIN" "$SCRIPT_DIR/src/main.py" "$@"
