#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH=/root/miniconda3/envs/webshop/bin:$PATH
export JAVA_HOME=/root/miniconda3/envs/webshop/lib/jvm
export JVM_PATH=/root/miniconda3/envs/webshop/lib/jvm/lib/server/libjvm.so
export CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$ROOT/third_party/WebShop${PYTHONPATH:+:$PYTHONPATH}"
cd "$ROOT/third_party/WebShop"
[ -e data ] || ln -s ../../data data
cd search_engine
mkdir -p resources resources_100 resources_1k resources_100k
python convert_product_file_format.py
python -m pyserini.index.lucene --collection JsonCollection --input resources_1k --index indexes_1k --generator DefaultLuceneDocumentGenerator --threads 1 --storePositions --storeDocvectors --storeRaw
cd "$ROOT"
python scripts/check_webshop.py
