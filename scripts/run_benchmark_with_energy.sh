#!/usr/bin/env bash
set -euo pipefail

# Run one benchmark with direct DCGM power sampling and summarize both serving
# and energy metrics into the same timestamped directory.
#
# Usage:
#   bash repo_root/scripts/run_benchmark_with_energy.sh \
#       <dataset_name> <num_prompts> <host> <port> <dcgm_metrics_url> \
#       [request_rate] [max_concurrency] [dcgm_interval_seconds] [idle_seconds]

if [[ $# -lt 5 || $# -gt 9 ]]; then
    echo "Usage: bash repo_root/scripts/run_benchmark_with_energy.sh <dataset_name> <num_prompts> <host> <port> <dcgm_metrics_url> [request_rate] [max_concurrency] [dcgm_interval_seconds] [idle_seconds]"
    exit 1
fi

DATASET_NAME="$1"
NUM_PROMPTS="$2"
HOST="$3"
PORT="$4"
DCGM_URL="$5"
REQUEST_RATE="${6:-8}"
MAX_CONCURRENCY="${7:-32}"
DCGM_INTERVAL="${8:-1}"
IDLE_SECONDS="${9:-10}"

REPO_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
TIMESTAMP="$(date +"%Y%m%d-%H%M%S")"
OUTDIR="$REPO_ROOT/logs/$DATASET_NAME/$TIMESTAMP"
mkdir -p "$OUTDIR"

DCGM_RAW="$OUTDIR/dcgm_metrics.csv"
RUN_INFO="$OUTDIR/run_info.txt"
BENCH_RAW="$OUTDIR/bench_metrics.jsonl"
BENCH_SUMMARY="$OUTDIR/bench_metrics.csv"
DCGM_SUMMARY="$OUTDIR/dcgm_summary.csv"

cleanup() {
    if [[ -n "${DCGM_PID:-}" ]]; then
        if kill -0 "$DCGM_PID" 2>/dev/null; then
            kill "$DCGM_PID" 2>/dev/null || true
            wait "$DCGM_PID" 2>/dev/null || true
        fi
    fi
}
trap cleanup EXIT INT TERM

echo "=== Benchmark with energy collection ==="
echo "Dataset:           $DATASET_NAME"
echo "Prompts:           $NUM_PROMPTS"
echo "Serving endpoint:  $HOST:$PORT"
echo "DCGM endpoint:     $DCGM_URL"
echo "Request rate:      $REQUEST_RATE"
echo "Concurrency:       $MAX_CONCURRENCY"
echo "DCGM interval:     ${DCGM_INTERVAL}s"
echo "Idle baseline:     ${IDLE_SECONDS}s"
echo "Output directory:  $OUTDIR"
echo

echo "Starting DCGM sampler..."
bash "$REPO_ROOT/scripts/collect_dcgm_metrics.sh" "$DCGM_URL" "$DCGM_RAW" "$DCGM_INTERVAL" &
DCGM_PID=$!

echo "Collecting idle baseline for ${IDLE_SECONDS}s..."
sleep "$IDLE_SECONDS"

echo "Running serving benchmark..."
OUTDIR="$OUTDIR" TIMESTAMP="$TIMESTAMP" bash "$REPO_ROOT/scripts/bench_serve.sh"     "$DATASET_NAME" "$NUM_PROMPTS" "$HOST" "$PORT" "$REQUEST_RATE" "$MAX_CONCURRENCY"

echo "Stopping DCGM sampler..."
cleanup
unset DCGM_PID

echo "Summarizing serving metrics..."
bash "$REPO_ROOT/scripts/analyze_metrics.sh" "$BENCH_RAW"

echo "Summarizing DCGM metrics..."
python3 "$REPO_ROOT/scripts/parse_dcgm_metrics.py" "$DCGM_RAW" "$RUN_INFO" "$BENCH_SUMMARY" "$DCGM_SUMMARY"

echo
echo "=== All done ==="
echo "Serving raw:       $BENCH_RAW"
echo "Serving summary:   $BENCH_SUMMARY"
echo "DCGM raw:          $DCGM_RAW"
echo "DCGM summary:      $DCGM_SUMMARY"
