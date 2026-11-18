#!/usr/bin/env bash
set -euo pipefail
model_dir=${MODEL_DIR:-/root/autodl-tmp/icml_test/models/Qwen3.5-9B}
vllm_bin=${VLLM_BIN:-/root/autodl-tmp/icml_test/.venv-inference/bin/vllm}
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 NO_PROXY=localhost,127.0.0.1
exec "$vllm_bin" serve "$model_dir" --served-model-name Qwen3.5-9B --host 127.0.0.1 --port 8000 --dtype bfloat16 --max-model-len 32768 --max-num-seqs 6 --gpu-memory-utilization .88 --language-model-only --enforce-eager --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3
