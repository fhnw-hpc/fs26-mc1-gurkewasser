import csv
import os
import sys
import statistics
import argparse

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

E2E_DIR = os.environ.get("E2E_DATA_DIR", "e2e_data")


def load_csv(filename, data_dir=None):
    if data_dir is None:
        data_dir = E2E_DIR
    filepath = os.path.join(data_dir, filename)
    if not os.path.isfile(filepath):
        print(f"[WARN] File not found: {filepath}")
        return []

    rows = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def parse_float(val, default=-1.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def analyze_latency(rows, label, latency_field='e2e_latency_ms'):
    if not rows:
        print(f"\n[!] No latency data for {label}")
        return {}

    latencies = [parse_float(r.get(latency_field, -1)) for r in rows if parse_float(r.get(latency_field, -1)) >= 0]
    if not latencies:
        print(f"\n[!] No valid latency values for {label} (field: {latency_field})")
        return {}

    sorted_l = sorted(latencies)
    n = len(sorted_l)
    stats = {
        "label": label,
        "count": n,
        "avg_ms": statistics.mean(latencies),
        "stddev_ms": statistics.stdev(latencies) if n > 1 else 0,
        "min_ms": sorted_l[0],
        "max_ms": sorted_l[-1],
        "p50_ms": sorted_l[n // 2],
        "p90_ms": sorted_l[int(n * 0.90)],
        "p95_ms": sorted_l[int(n * 0.95)],
        "p99_ms": sorted_l[int(n * 0.99)] if n > 1 else sorted_l[0],
    }

    print(f"\n{'='*60}")
    print(f"  E2E LATENCY ANALYSIS: {label}")
    print(f"{'='*60}")
    print(f"  Messages analyzed: {stats['count']}")
    print(f"  Average latency:   {stats['avg_ms']:.2f} ms")
    print(f"  Std deviation:     {stats['stddev_ms']:.2f} ms")
    print(f"  Min latency:       {stats['min_ms']:.2f} ms")
    print(f"  Max latency:       {stats['max_ms']:.2f} ms")
    print(f"  P50 (median):      {stats['p50_ms']:.2f} ms")
    print(f"  P90:               {stats['p90_ms']:.2f} ms")
    print(f"  P95:               {stats['p95_ms']:.2f} ms")
    print(f"  P99:               {stats['p99_ms']:.2f} ms")
    print(f"{'='*60}")

    return stats


def analyze_throughput(rows, label):
    if not rows:
        print(f"\n[!] No throughput data for {label}")
        return {}

    rates = [parse_float(r.get('msgs_per_sec', -1)) for r in rows if parse_float(r.get('msgs_per_sec', -1)) >= 0]
    if not rates:
        print(f"\n[!] No valid throughput values for {label}")
        return {}

    stats = {
        "label": label,
        "count": len(rates),
        "avg_msgs_per_sec": statistics.mean(rates),
        "stddev_msgs_per_sec": statistics.stdev(rates) if len(rates) > 1 else 0,
        "min_msgs_per_sec": min(rates),
        "max_msgs_per_sec": max(rates),
    }

    print(f"\n{'='*60}")
    print(f"  E2E THROUGHPUT ANALYSIS: {label}")
    print(f"{'='*60}")
    print(f"  Windows analyzed:  {stats['count']}")
    print(f"  Avg throughput:    {stats['avg_msgs_per_sec']:.2f} msg/s")
    print(f"  Std deviation:     {stats['stddev_msgs_per_sec']:.2f} msg/s")
    print(f"  Min throughput:    {stats['min_msgs_per_sec']:.2f} msg/s")
    print(f"  Max throughput:    {stats['max_msgs_per_sec']:.2f} msg/s")
    print(f"{'='*60}")

    return stats


def analyze_pipeline_latency(alerts_rows):
    if not alerts_rows:
        print("\n[!] No alerts data for pipeline breakdown")
        return

    p2c = [parse_float(r.get('e2e_producer_to_consumer_ms', -1)) for r in alerts_rows if parse_float(r.get('e2e_producer_to_consumer_ms', -1)) >= 0]
    c2s = [parse_float(r.get('e2e_consumer_to_sink_ms', -1)) for r in alerts_rows if parse_float(r.get('e2e_consumer_to_sink_ms', -1)) >= 0]

    print(f"\n{'='*60}")
    print(f"  E2E PIPELINE BREAKDOWN: room_alerts_mp")
    print(f"{'='*60}")
    if p2c:
        print(f"  Producer → Consumer:  avg={statistics.mean(p2c):.2f}ms  p50={sorted(p2c)[len(p2c)//2]:.2f}ms  p99={sorted(p2c)[int(len(p2c)*0.99)] if len(p2c)>1 else p2c[0]:.2f}ms")
    if c2s:
        print(f"  Consumer → Sink:      avg={statistics.mean(c2s):.2f}ms  p50={sorted(c2s)[len(c2s)//2]:.2f}ms  p99={sorted(c2s)[int(len(c2s)*0.99)] if len(c2s)>1 else c2s[0]:.2f}ms")
    total = [parse_float(r.get('e2e_total_latency_ms', -1)) for r in alerts_rows if parse_float(r.get('e2e_total_latency_ms', -1)) >= 0]
    if total:
        print(f"  Total E2E (prod→sink):  avg={statistics.mean(total):.2f}ms  p50={sorted(total)[len(total)//2]:.2f}ms  p99={sorted(total)[int(len(total)*0.99)] if len(total)>1 else total[0]:.2f}ms")
    print(f"{'='*60}")


def analyze_stability(simple_rows, alerts_rows):
    if not simple_rows and not alerts_rows:
        print("\n[!] No data for stability analysis")
        return

    print(f"\n{'='*60}")
    print(f"  E2E STABILITY ANALYSIS")
    print(f"{'='*60}")

    for label, rows, field in [("room_temperature_mp (simple)", simple_rows, 'e2e_latency_ms'), ("room_alerts_mp (alerts)", alerts_rows, 'e2e_total_latency_ms')]:
        if not rows:
            continue

        latencies = [parse_float(r.get(field, -1)) for r in rows if parse_float(r.get(field, -1)) >= 0]
        if len(latencies) < 10:
            print(f"  {label}: Not enough data points ({len(latencies)})")
            continue

        n_buckets = min(10, len(latencies) // 10)
        bucket_size = len(latencies) // n_buckets
        bucket_avgs = []
        for i in range(n_buckets):
            bucket = latencies[i * bucket_size:(i + 1) * bucket_size]
            bucket_avgs.append(statistics.mean(bucket))

        first_avg = bucket_avgs[0]
        last_avg = bucket_avgs[-1]
        max_avg = max(bucket_avgs)
        min_avg = min(bucket_avgs)
        drift_pct = ((last_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0

        print(f"\n  {label}:")
        print(f"    First 10% avg: {first_avg:.2f}ms | Last 10% avg: {last_avg:.2f}ms")
        print(f"    Min bucket avg: {min_avg:.2f}ms | Max bucket avg: {max_avg:.2f}ms")
        print(f"    Latency drift: {drift_pct:+.1f}%")
        if abs(drift_pct) > 20:
            print(f"    ❌ REGRESSION DETECTED ({drift_pct:+.1f}%)")
        elif abs(drift_pct) > 10:
            print(f"    ⚠ Moderate drift ({drift_pct:+.1f}%)")
        else:
            print(f"    ✅ Stable (< 10% drift)")
    print(f"{'='*60}")


def plot_latency_over_time(rows, label, output_path, latency_field='e2e_latency_ms'):
    if not HAS_MPL:
        print("[WARN] matplotlib not available, skipping plot")
        return
    if not rows:
        return

    times = [parse_float(r.get('wall_time', 0)) for r in rows]
    latencies = [parse_float(r.get(latency_field, -1)) for r in rows]

    valid = [(t, l) for t, l in zip(times, latencies) if l >= 0]
    if len(valid) < 2:
        return

    times, latencies = zip(*valid)
    t0 = times[0]
    times_rel = [(t - t0) for t in times]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.scatter(times_rel, latencies, s=2, alpha=0.4, color='steelblue', label='Individual msgs')

    window = max(1, len(latencies) // 50)
    rolling_avg = [statistics.mean(latencies[max(0, i - window):i + 1]) for i in range(len(latencies))]
    ax.plot(times_rel, rolling_avg, color='red', linewidth=1.5, label=f'Rolling avg (w={window})')

    ax.set_xlabel('Time (s)')
    ax.set_ylabel('E2E Latency (ms)')
    ax.set_title(f'End-to-End Latency Over Time: {label}')
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"[PLOT] Saved: {output_path}")


def plot_throughput_over_time(rows, label, output_path):
    if not HAS_MPL:
        return
    if not rows:
        return

    times_start = [parse_float(r.get('window_start', 0)) for r in rows]
    rates = [parse_float(r.get('msgs_per_sec', 0)) for r in rows]

    valid = [(t, r) for t, r in zip(times_start, rates) if r > 0]
    if len(valid) < 2:
        return

    times_start, rates = zip(*valid)
    t0 = times_start[0]
    times_rel = [(t - t0) for t in times_start]

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(times_rel, rates, marker='o', markersize=3, linewidth=1.5, color='seagreen')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Throughput (msg/s)')
    ax.set_title(f'Throughput Over Time: {label}')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"[PLOT] Saved: {output_path}")


def plot_latency_breakdown(alerts_rows, output_path):
    if not HAS_MPL:
        return
    if not alerts_rows:
        return

    p2c = [parse_float(r.get('e2e_producer_to_consumer_ms', -1)) for r in alerts_rows if parse_float(r.get('e2e_producer_to_consumer_ms', -1)) >= 0]
    c2s = [parse_float(r.get('e2e_consumer_to_sink_ms', -1)) for r in alerts_rows if parse_float(r.get('e2e_consumer_to_sink_ms', -1)) >= 0]

    if not p2c or not c2s:
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    labels = ['Producer → Consumer', 'Consumer → Sink']
    avgs = [statistics.mean(p2c), statistics.mean(c2s)]
    p50s = [sorted(p2c)[len(p2c) // 2], sorted(c2s)[len(c2s) // 2]]
    p99s = [sorted(p2c)[int(len(p2c) * 0.99)] if len(p2c) > 1 else p2c[0],
            sorted(c2s)[int(len(c2s) * 0.99)] if len(c2s) > 1 else c2s[0]]

    x = range(len(labels))
    width = 0.25
    ax.bar([i - width for i in x], avgs, width, label='Average', color='steelblue')
    ax.bar(x, p50s, width, label='P50', color='seagreen')
    ax.bar([i + width for i in x], p99s, width, label='P99', color='coral')

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel('Latency (ms)')
    ax.set_title('E2E Pipeline Latency Breakdown')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"[PLOT] Saved: {output_path}")


def analyze_directory(data_dir, label=""):
    if label:
        print(f"\n{'#'*60}")
        print(f"  ANALYZING: {label}")
        print(f"  Directory: {data_dir}")
        print(f"{'#'*60}")

    simple_rows = load_csv("e2e_simple_latency.csv", data_dir)
    alerts_rows = load_csv("e2e_alerts_latency.csv", data_dir)
    tp_simple_rows = load_csv("e2e_throughput_simple.csv", data_dir)
    tp_alerts_rows = load_csv("e2e_throughput_alerts.csv", data_dir)

    simple_stats = analyze_latency(simple_rows, "room_temperature_mp (simple)", latency_field='e2e_latency_ms')
    alerts_stats = analyze_latency(alerts_rows, "room_alerts_mp (alerts)", latency_field='e2e_total_latency_ms')

    analyze_pipeline_latency(alerts_rows)

    tp_simple_stats = analyze_throughput(tp_simple_rows, "room_temperature_mp (simple)")
    tp_alerts_stats = analyze_throughput(tp_alerts_rows, "room_alerts_mp (alerts)")

    analyze_stability(simple_rows, alerts_rows)

    out_dir = os.path.join(data_dir, "plots")
    os.makedirs(out_dir, exist_ok=True)

    plot_latency_over_time(simple_rows, "room_temperature_mp", os.path.join(out_dir, "e2e_latency_simple.png"))
    plot_latency_over_time(alerts_rows, "room_alerts_mp", os.path.join(out_dir, "e2e_latency_alerts.png"), latency_field='e2e_total_latency_ms')
    plot_throughput_over_time(tp_simple_rows, "room_temperature_mp", os.path.join(out_dir, "e2e_throughput_simple.png"))
    plot_throughput_over_time(tp_alerts_rows, "room_alerts_mp", os.path.join(out_dir, "e2e_throughput_alerts.png"))
    plot_latency_breakdown(alerts_rows, os.path.join(out_dir, "e2e_pipeline_breakdown.png"))

    print(f"\n[Done] Analysis complete. Plots saved to: {out_dir}")

    return {
        "simple": simple_stats,
        "alerts": alerts_stats,
        "tp_simple": tp_simple_stats,
        "tp_alerts": tp_alerts_stats,
    }


def main():
    parser = argparse.ArgumentParser(description="E2E Performance Analysis")
    parser.add_argument("--dir", "-d", default=None,
                        help="Data directory to analyze (default: E2E_DATA_DIR env var or 'e2e_data')")
    parser.add_argument("--multi", "-m", default=None,
                        help="Parent directory containing exp1_*/exp2_*/exp3_*/ subdirectories for multi-experiment analysis")
    args = parser.parse_args()

    data_dir = args.dir or E2E_DIR

    if args.multi:
        parent_dir = args.multi
        subdirs = sorted([d for d in os.listdir(parent_dir)
                          if os.path.isdir(os.path.join(parent_dir, d)) and d.startswith('exp')])
        if not subdirs:
            print(f"[ERROR] No exp* subdirectories found in {parent_dir}")
            sys.exit(1)

        print(f"\nFound {len(subdirs)} experiments in {parent_dir}:")
        for sd in subdirs:
            print(f"  - {sd}")

        all_stats = {}
        for subdir in subdirs:
            exp_dir = os.path.join(parent_dir, subdir)
            stats = analyze_directory(exp_dir, label=subdir)
            all_stats[subdir] = stats

        print(f"\n{'='*60}")
        print(f"  SUMMARY: ALL {len(subdirs)} EXPERIMENTS")
        print(f"{'='*60}")
        for subdir in subdirs:
            stats = all_stats.get(subdir, {})
            simple = stats.get('simple', {})
            alerts = stats.get('alerts', {})
            if simple or alerts:
                print(f"\n  {subdir}:")
                if simple and simple.get('count'):
                    print(f"    Simple: {simple['count']} msgs, P50={simple['p50_ms']:.2f}ms, P99={simple['p99_ms']:.2f}ms, Avg={simple['avg_msgs_per_sec'] if 'avg_msgs_per_sec' in simple.get('label', '') else simple['avg_ms']:.2f}ms")
                if alerts and alerts.get('count'):
                    print(f"    Alerts: {alerts['count']} msgs, P50={alerts['p50_ms']:.2f}ms, P99={alerts['p99_ms']:.2f}ms")
        print(f"{'='*60}")
    else:
        analyze_directory(data_dir)


if __name__ == "__main__":
    main()