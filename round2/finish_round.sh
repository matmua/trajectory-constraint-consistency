#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
py=../round1/env/bin/python
until "$py" - <<'PY'
from pathlib import Path as P
sets={'full_web':20,'app/echo20':10,'app/echo50':10,'app/native50':10,'app/assisted20':10,'app/wire20':10,'app/live20':10,'cctu_shared':60,'order_shared':20}
raise SystemExit(0 if all(len(list((P('out')/k).glob('*.json')))==n for k,n in sets.items()) else 1)
PY
do sleep 20; done
"$py" src/analyze.py
"$py" src/public_export.py
"$py" src/make_report.py
