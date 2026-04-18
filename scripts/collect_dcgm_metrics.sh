#!/usr/bin/env bash
set -euo pipefail

# Collect raw DCGM exporter metrics repeatedly and save a timestamped CSV trace.
#
# Usage:
#   bash repo_root/scripts/collect_dcgm_metrics.sh <dcgm_metrics_url> <output_csv> [interval_seconds]

if [[ $# -lt 2 || $# -gt 3 ]]; then
    echo "Usage: bash repo_root/scripts/collect_dcgm_metrics.sh <dcgm_metrics_url> <output_csv> [interval_seconds]"
    exit 1
fi

DCGM_URL="$1"
OUTCSV="$2"
INTERVAL="${3:-1}"

mkdir -p "$(dirname "$OUTCSV")"

TMP_METRICS="$(mktemp /tmp/dcgm_metrics.XXXXXX)"
trap 'rm -f "$TMP_METRICS"' EXIT

echo "timestamp_epoch,power_w,gpu_util,mem_copy_util" > "$OUTCSV"

echo "=== Starting DCGM collection ==="
echo "URL:      $DCGM_URL"
echo "Output:   $OUTCSV"
echo "Interval: ${INTERVAL}s"
echo

while true; do
    TS="$(python3 - <<'PY'
import time
print(f"{time.time():.6f}")
PY
)"
    if curl -fsSL "$DCGM_URL" > "$TMP_METRICS"; then
        POWER="$(grep '^DCGM_FI_DEV_POWER_USAGE{' "$TMP_METRICS" | awk 'NR==1{print $NF}')"
        GPU_UTIL="$(grep '^DCGM_FI_DEV_GPU_UTIL{' "$TMP_METRICS" | awk 'NR==1{print $NF}')"
        MEM_COPY_UTIL="$(grep '^DCGM_FI_DEV_MEM_COPY_UTIL{' "$TMP_METRICS" | awk 'NR==1{print $NF}')"
        echo "${TS},${POWER:-},${GPU_UTIL:-},${MEM_COPY_UTIL:-}" >> "$OUTCSV"
    else
        echo "${TS},,," >> "$OUTCSV"
    fi
    sleep "$INTERVAL"
done
