#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export UV_CACHE_DIR="$PWD/.cache/uv" TMPDIR="$PWD/.cache/tmp" PIP_CACHE_DIR="$PWD/.cache/pip"
export UV_HTTP_TIMEOUT=60 UV_CONCURRENT_DOWNLOADS=16
mkdir -p "$UV_CACHE_DIR" "$TMPDIR" "$PIP_CACHE_DIR"
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy
test -x .venv-inference/bin/python || /root/miniconda3/bin/uv venv --python /root/miniconda3/bin/python .venv-inference
shopt -s nullglob
wheels=(.cache/wheels/*.whl)
if ((${#wheels[@]})); then /root/miniconda3/bin/python scripts/verify_wheels.py; fi
/root/miniconda3/bin/uv pip install --index-url https://mirrors.aliyun.com/pypi/simple --python .venv-inference/bin/python "${wheels[@]}" 'vllm==0.18.0' modelscope
.venv-inference/bin/python scripts/check_inference.py
