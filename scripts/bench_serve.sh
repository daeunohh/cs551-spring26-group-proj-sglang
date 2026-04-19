#!/usr/bin/env bash
set -euo pipefail

# Benchmark an SGLang endpoint and write raw results under:
#   repo_root/logs/<dataset_name>/<timestamp>/bench_metrics.jsonl
#
# Usage:
#   bash repo_root/scripts/bench_serve.sh <dataset_name> <num_prompts> <host> <port> [request_rate] [max_concurrency]
#
# Example:
#   bash repo_root/scripts/bench_serve.sh sharegpt 500 34.80.233.120 30000 8 32
#
# Notes:
# - DATASET_NAME is restricted to the dataset names SGLang supports by default:
#   autobench, sharegpt, custom, openai, random, random-ids,
#   generated-shared-prefix, mmmu, image, mooncake, longbench_v2
# - This script targets the visible serving endpoint directly.
# - To force output into an existing directory (used by the wrapper script),
#   set OUTDIR before invoking this script.

if [[ $# -lt 4 || $# -gt 6 ]]; then
    echo "Usage: bash repo_root/scripts/bench_serve.sh <dataset_name> <num_prompts> <host> <port> [request_rate] [max_concurrency]"
    exit 1
fi

DATASET_NAME="$1"
NUM_PROMPTS="$2"
HOST="$3"
PORT="$4"
REQUEST_RATE="${5:-8}"
MAX_CONCURRENCY="${6:-32}"

SUPPORTED_DATASETS=(
  autobench
  sharegpt
  custom
  openai
  random
  random-ids
  generated-shared-prefix
  mmmu
  image
  mooncake
  longbench_v2
)

is_supported=false
for ds in "${SUPPORTED_DATASETS[@]}"; do
    if [[ "$DATASET_NAME" == "$ds" ]]; then
        is_supported=true
        break
    fi
done

if [[ "$is_supported" != "true" ]]; then
    echo "Error: unsupported DATASET_NAME '$DATASET_NAME'"
    echo "Supported datasets: ${SUPPORTED_DATASETS[*]}"
    exit 1
fi

REPO_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"

if [[ -n "${CONDA_PREFIX:-}" && -x "${CONDA_PREFIX}/bin/python" ]]; then
    PYTHON="${CONDA_PREFIX}/bin/python"
else
    PYTHON="${PYTHON:-python3}"
fi

MODEL="${MODEL:-meta-llama/Meta-Llama-3-8B}"

DATASET_PATH="${SCRIPT_DATASET_PATH:-$REPO_ROOT/sharegpt.json}"

if [ ! -f "$DATASET_PATH" ]; then
    echo "Error: Dataset file not found at $DATASET_PATH"
    echo "Please run: wget -O sharegpt.json https://huggingface.co/datasets/anon8231489123/ShareGPT_Vicuna_unfiltered/resolve/main/ShareGPT_V3_unfiltered_cleaned_split.json"
    exit 1
fi


TIMESTAMP="${TIMESTAMP:-$(date +"%Y%m%d-%H%M%S")}"
OUTDIR="${OUTDIR:-$REPO_ROOT/logs/$DATASET_NAME/$TIMESTAMP}"
mkdir -p "$OUTDIR"

OUTFILE="$OUTDIR/bench_metrics.jsonl"
META_FILE="$OUTDIR/run_info.txt"

BENCH_START_EPOCH="$(python3 - <<'PY'
import time
print(f"{time.time():.6f}")
PY
)"

{
    echo "dataset_name=$DATASET_NAME"
    echo "num_prompts=$NUM_PROMPTS"
    echo "host=$HOST"
    echo "port=$PORT"
    echo "request_rate=$REQUEST_RATE"
    echo "max_concurrency=$MAX_CONCURRENCY"
    echo "model=$MODEL"
    echo "timestamp=$TIMESTAMP"
    echo "outdir=$OUTDIR"
    echo "bench_start_epoch=$BENCH_START_EPOCH"
} > "$META_FILE"

echo "=== Running SGLang benchmark ==="
echo "Dataset:        $DATASET_NAME"
echo "Prompts:        $NUM_PROMPTS"
echo "Endpoint:       $HOST:$PORT"
echo "Model:          $MODEL"
echo "Request rate:   $REQUEST_RATE"
echo "Concurrency:    $MAX_CONCURRENCY"
echo "Output JSONL:   $OUTFILE"
echo

"$PYTHON" -m sglang.bench_serving     --backend sglang     --host "$HOST"     --port "$PORT"     --model "$MODEL"     --dataset-name "$DATASET_NAME"  --dataset-path "$DATASET_PATH"    --num-prompts "$NUM_PROMPTS"     --max-concurrency "$MAX_CONCURRENCY"     --request-rate "$REQUEST_RATE"     --flush-cache     --output-details     --disable-stream     --output-file "$OUTFILE" --gsp-num-groups=256

BENCH_END_EPOCH="$(python3 - <<'PY'
import time
print(f"{time.time():.6f}")
PY
)"

echo "bench_end_epoch=$BENCH_END_EPOCH" >> "$META_FILE"

echo
echo "=== Benchmark completed ==="
echo "Raw benchmark output: $OUTFILE"
echo "Run info:            $META_FILE"
