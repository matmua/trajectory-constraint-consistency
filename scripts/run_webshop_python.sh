#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH=/root/miniconda3/envs/webshop/bin:$PATH JAVA_HOME=/root/miniconda3/envs/webshop/lib/jvm
export JVM_PATH=/root/miniconda3/envs/webshop/lib/jvm/lib/server/libjvm.so
export CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$ROOT/third_party/WebShop"
cd "$ROOT"
exec python "$@"
