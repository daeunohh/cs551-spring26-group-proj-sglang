#!/usr/bin/env python3
"""
Parse one SGLang benchmark JSONL output file and write a two-column CSV summary.

Usage:
    python repo_root/scripts/parse_metrics.py <bench_metrics.jsonl> [output_csv]
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


FIELDS = [
    "duration",
    "completed",
    "request_throughput",
    "input_throughput",
    "output_throughput",
    "total_throughput",
    "mean_e2e_latency_ms",
    "median_e2e_latency_ms",
    "p99_e2e_latency_ms",
    "mean_ttft_ms",
    "median_ttft_ms",
    "p99_ttft_ms",
    "mean_tpot_ms",
    "median_tpot_ms",
    "p99_tpot_ms",
    "mean_itl_ms",
    "median_itl_ms",
    "p95_itl_ms",
    "p99_itl_ms",
    "concurrency",
    "total_input_tokens",
    "total_output_tokens",
    "total_input_tokens_retokenized",
    "total_output_tokens_retokenized",
]

ALIASES = {
    "total_input_tokens": ["total_input_tokens", "total_input"],
    "total_output_tokens": ["total_output_tokens", "total_output"],
    "total_input_tokens_retokenized": [
        "total_input_tokens_retokenized",
        "total_input_retokenized",
    ],
    "total_output_tokens_retokenized": [
        "total_output_tokens_retokenized",
        "total_output_retokenized",
    ],
}


def load_last_json_record(path: Path) -> Dict[str, Any]:
    last_obj: Optional[Dict[str, Any]] = None
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            last_obj = json.loads(line)
    if last_obj is None:
        raise ValueError(f"No JSON records found in {path}")
    return last_obj


def first_present(data: Dict[str, Any], key: str) -> Any:
    for candidate in ALIASES.get(key, [key]):
        if candidate in data:
            return data[candidate]
    return None


def safe_float(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return value
    return value


def write_csv(rows: Iterable[tuple[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for key, value in rows:
            writer.writerow([key, safe_float(value)])


def main() -> None:
    if len(sys.argv) not in (2, 3):
        print("Usage: python parse_metrics.py <bench_metrics.jsonl> [output_csv]")
        sys.exit(1)

    input_path = Path(sys.argv[1]).expanduser().resolve()
    if not input_path.exists():
        print(f"Error: file not found: {input_path}")
        sys.exit(1)

    if len(sys.argv) == 3:
        output_path = Path(sys.argv[2]).expanduser().resolve()
    else:
        output_path = input_path.with_name("bench_metrics.csv")

    data = load_last_json_record(input_path)
    rows = [(field, first_present(data, field)) for field in FIELDS]
    write_csv(rows, output_path)

    print(f"Benchmark summary saved to: {output_path}")


if __name__ == "__main__":
    main()
