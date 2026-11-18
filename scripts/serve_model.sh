#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy
export NO_PROXY=localhost,127.0.0.1,::1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export HF_HOME="$ROOT/.cache/huggingface" XDG_CACHE_HOME="$ROOT/.cache"
export TMPDIR="$ROOT/.cache/tmp" CUDA_VISIBLE_DEVICES=0
exec .venv-inference/bin/vllm serve "$ROOT/models/Qwen3.5-9B" --served-model-name Qwen3.5-9B --host 127.0.0.1 --port 8000 --dtype bfloat16 --max-model-len 16384 --max-num-seqs 2 --gpu-memory-utilization 0.85 --language-model-only --enforce-eager --reasoning-parser qwen3
