#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path
from statistics import fmean
from typing import Dict, List, Optional

def read_run_info(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            data[k] = v
    return data

def read_metrics_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def to_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    value = value.strip()
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None

def integrate_energy_j(samples: List[Dict[str, str]], baseline_w: float = 0.0) -> float:
    points = []
    for row in samples:
        ts = to_float(row.get("timestamp_epoch"))
        power = to_float(row.get("power_w"))
        if ts is None or power is None:
            continue
        points.append((ts, max(power - baseline_w, 0.0)))
    if len(points) < 2:
        return 0.0
    energy = 0.0
    for i in range(1, len(points)):
        t0, p0 = points[i - 1]
        t1, p1 = points[i]
        dt = t1 - t0
        if dt > 0:
            energy += (p0 + p1) * 0.5 * dt
    return energy

def filter_window(samples: List[Dict[str, str]], start: float, end: float) -> List[Dict[str, str]]:
    out = []
    for row in samples:
        ts = to_float(row.get("timestamp_epoch"))
        if ts is not None and start <= ts <= end:
            out.append(row)
    return out

def avg_field(samples: List[Dict[str, str]], key: str) -> Optional[float]:
    vals = [to_float(r.get(key)) for r in samples]
    vals = [v for v in vals if v is not None]
    return None if not vals else fmean(vals)

def read_bench_summary(path: Path) -> Dict[str, float]:
    out: Dict[str, float] = {}
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            metric = row.get("metric")
            value = to_float(row.get("value"))
            if metric is not None and value is not None:
                out[metric] = value
    return out

def main() -> None:
    if len(sys.argv) not in (3, 4, 5):
        print("Usage: python parse_dcgm_metrics.py <dcgm_metrics.csv> <run_info.txt> [bench_metrics.csv] [output_csv]")
        sys.exit(1)

    dcgm_path = Path(sys.argv[1]).expanduser().resolve()
    run_info_path = Path(sys.argv[2]).expanduser().resolve()

    bench_summary_path: Optional[Path] = None
    output_path: Optional[Path] = None

    if len(sys.argv) >= 4:
        p = Path(sys.argv[3]).expanduser().resolve()
        if p.exists():
            bench_summary_path = p
        else:
            output_path = p
    if len(sys.argv) == 5:
        output_path = Path(sys.argv[4]).expanduser().resolve()
    if output_path is None:
        output_path = dcgm_path.with_name("dcgm_summary.csv")

    run_info = read_run_info(run_info_path)
    bench_start = to_float(run_info.get("bench_start_epoch"))
    bench_end = to_float(run_info.get("bench_end_epoch"))
    if bench_start is None or bench_end is None or bench_end <= bench_start:
        raise SystemExit("Error: invalid benchmark start/end timestamps in run_info.txt")

    all_samples = read_metrics_csv(dcgm_path)
    bench_samples = filter_window(all_samples, bench_start, bench_end)
    idle_samples = [r for r in all_samples if (to_float(r.get("timestamp_epoch")) or -1) < bench_start]

    avg_power = avg_field(bench_samples, "power_w")
    avg_idle_power = avg_field(idle_samples, "power_w") or 0.0
    avg_gpu_util = avg_field(bench_samples, "gpu_util")
    avg_mem_copy_util = avg_field(bench_samples, "mem_copy_util")

    total_energy_j = integrate_energy_j(bench_samples, baseline_w=0.0)
    net_serving_energy_j = integrate_energy_j(bench_samples, baseline_w=avg_idle_power)

    bench_duration_s = bench_end - bench_start
    idle_duration_s = 0.0
    if idle_samples:
        ts_vals = [to_float(r.get("timestamp_epoch")) for r in idle_samples]
        ts_vals = [v for v in ts_vals if v is not None]
        if len(ts_vals) >= 2:
            idle_duration_s = max(ts_vals) - min(ts_vals)

    energy_per_request = None
    energy_per_output_token = None
    if bench_summary_path is not None:
        bench_summary = read_bench_summary(bench_summary_path)
        completed = bench_summary.get("completed")
        total_output_tokens = bench_summary.get("total_output_tokens") or bench_summary.get("total_output")
        if completed and completed > 0:
            energy_per_request = net_serving_energy_j / completed
        if total_output_tokens and total_output_tokens > 0:
            energy_per_output_token = net_serving_energy_j / total_output_tokens

    rows = [
        ("benchmark_duration_s", bench_duration_s),
        ("idle_duration_s", idle_duration_s),
        ("avg_power_w", avg_power),
        ("avg_idle_power_w", avg_idle_power),
        ("total_energy_j", total_energy_j),
        ("net_serving_energy_j", net_serving_energy_j),
        ("energy_per_request_j", energy_per_request),
        ("energy_per_output_token_j", energy_per_output_token),
        ("avg_gpu_util", avg_gpu_util),
        ("avg_mem_copy_util", avg_mem_copy_util),
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        for k, v in rows:
            writer.writerow([k, v])

    print(f"DCGM summary saved to: {output_path}")

if __name__ == "__main__":
    main()
