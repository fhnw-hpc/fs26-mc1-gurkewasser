#!/usr/bin/env python3
"""
Part 4 Profiling Analysis Script
Extracts Top-3 functions with ncalls, cumtime and percentage
"""

import subprocess
import os
import re

PROFILES_DIR = "profiles"
PROFILES_20SEC = f"{PROFILES_DIR}/20sec"
PROFILES_SHORT = f"{PROFILES_DIR}/short_test"
PROFILES_10MIN = PROFILES_DIR


def analyze_file(prof_path, label):
    """Analyze a single .prof file"""
    result = subprocess.run(
        ['python3', '-c', f'''
import pstats
stats = pstats.Stats("{prof_path}")
stats.sort_stats("cumulative")
stats.print_stats(25)
'''],
        capture_output=True,
        text=True
    )

    text = result.stdout
    lines = text.split('\n')

    total_time = 0
    for line in lines[:5]:
        match = re.search(r'in\s+(\d+\.\d+)\s+seconds', line)
        if match:
            total_time = float(match.group(1))
            break

    app_funcs = []
    pika_funcs = []

    for line in lines:
        if '/app/' in line:
            parts = line.split()
            if len(parts) >= 4:
                try:
                    ncalls = parts[0].strip()
                    tottime = float(parts[1].strip())
                    cumtime = float(parts[3].strip())
                    func_name = line.split('(')[-1].replace(')', '').strip()
                    pct = (cumtime / total_time * 100) if total_time > 0 else 0
                    app_funcs.append({
                        'name': func_name,
                        'ncalls': ncalls,
                        'cumtime': cumtime,
                        'pct': pct
                    })
                except:
                    pass

        elif 'pika/' in line:
            parts = line.split()
            if len(parts) >= 4:
                try:
                    ncalls = parts[0].strip()
                    cumtime = float(parts[3].strip())
                    func_name = line.split('(')[-1].replace(')', '').strip()
                    pct = (cumtime / total_time * 100) if total_time > 0 else 0
                    pika_funcs.append({
                        'name': func_name,
                        'ncalls': ncalls,
                        'cumtime': cumtime,
                        'pct': pct
                    })
                except:
                    pass

    app_funcs.sort(key=lambda x: x['cumtime'], reverse=True)
    pika_funcs.sort(key=lambda x: x['cumtime'], reverse=True)

    return {
        'label': label,
        'total_time': total_time,
        'app_funcs': app_funcs[:3],
        'pika_funcs': pika_funcs[:3]
    }


def main():
    print("="*90)
    print(" " * 35 + "PART 4 PROFILING ANALYSIS")
    print("="*90)

    files = [
        (f"{PROFILES_SHORT}/rmq_producer_baseline_run1.prof", "Producer Short Baseline Run1", "producer"),
        (f"{PROFILES_SHORT}/rmq_producer_baseline_run2.prof", "Producer Short Baseline Run2", "producer"),
        (f"{PROFILES_SHORT}/rmq_producer_baseline_run3.prof", "Producer Short Baseline Run3", "producer"),
        (f"{PROFILES_SHORT}/rmq_producer_baseline_run4.prof", "Producer Short Baseline Run4", "producer"),
        (f"{PROFILES_SHORT}/rmq_producer_bottleneck_run1.prof", "Producer Short Bottleneck Run1", "producer"),
        (f"{PROFILES_SHORT}/rmq_producer_bottleneck_run2.prof", "Producer Short Bottleneck Run2", "producer"),
        (f"{PROFILES_SHORT}/rmq_producer_bottleneck_run3.prof", "Producer Short Bottleneck Run3", "producer"),
        (f"{PROFILES_SHORT}/rmq_producer_bottleneck_run4.prof", "Producer Short Bottleneck Run4", "producer"),
        (f"{PROFILES_SHORT}/rmq_consumer.prof", "Consumer Short", "consumer"),
        (f"{PROFILES_SHORT}/rmq_sink.prof", "Sink Short", "sink"),
        (f"{PROFILES_10MIN}/rmq_producer_baseline.prof", "Producer 10min Baseline", "producer"),
        (f"{PROFILES_10MIN}/rmq_producer_bottleneck.prof", "Producer 10min Bottleneck", "producer"),
        (f"{PROFILES_10MIN}/rmq_consumer.prof", "Consumer 10min", "consumer"),
    ]

    results = {}
    for path, label, ptype in files:
        if os.path.exists(path):
            r = analyze_file(path, label)
            results[label] = r
            print(f"  [OK] {label}: {r['total_time']:.3f}s")
        else:
            print(f"  [SKIP] {path} not found")

    print("\n" + "="*90)
    print(" " * 35 + "PRODUCER ANALYSIS")
    print("="*90)

    producer_labels = [k for k in results if k.startswith("Producer")]
    for label in producer_labels:
        r = results[label]
        print(f"\n### {label} (Total: {r['total_time']:.3f}s) ###")

        print("\n  Application Code (Top-3):")
        for i, f in enumerate(r['app_funcs'], 1):
            print(f"    {i}. {f['name']}")
            print(f"       ncalls: {f['ncalls']}, cumtime: {f['cumtime']:.3f}s ({f['pct']:.1f}%)")

        print("\n  Pika/MQ Functions (Top-3):")
        for i, f in enumerate(r['pika_funcs'], 1):
            print(f"    {i}. {f['name']}")
            print(f"       ncalls: {f['ncalls']}, cumtime: {f['cumtime']:.3f}s ({f['pct']:.1f}%)")

    print("\n" + "="*90)
    print(" " * 35 + "CONSUMER/SINK ANALYSIS")
    print("="*90)

    non_producer = [k for k in results if not k.startswith("Producer")]
    for label in non_producer:
        r = results[label]
        print(f"\n### {label} (Total: {r['total_time']:.3f}s) ###")

        print("\n  Application Code (Top-3):")
        for i, f in enumerate(r['app_funcs'], 1):
            print(f"    {i}. {f['name']}")
            print(f"       ncalls: {f['ncalls']}, cumtime: {f['cumtime']:.3f}s ({f['pct']:.1f}%)")

        print("\n  Pika/MQ Functions (Top-3):")
        for i, f in enumerate(r['pika_funcs'], 1):
            print(f"    {i}. {f['name']}")
            print(f"       ncalls: {f['ncalls']}, cumtime: {f['cumtime']:.3f}s ({f['pct']:.1f}%)")

    print("\n" + "="*90)
    print(" " * 35 + "OVERHEAD COMPARISON")
    print("="*90)

    baseline_runs = [results[k]['total_time'] for k in results
                     if "Baseline" in k and "Short" in k]
    bottleneck_runs = [results[k]['total_time'] for k in results
                       if "Bottleneck" in k and "Short" in k]

    if baseline_runs and bottleneck_runs:
        import statistics
        b_mean = statistics.mean(baseline_runs)
        bn_mean = statistics.mean(bottleneck_runs)
        overhead = ((bn_mean - b_mean) / b_mean) * 100
        print(f"\n  Short test Baseline mean:    {b_mean:.3f}s")
        print(f"  Short test Bottleneck mean:  {bn_mean:.3f}s")
        print(f"  Overhead: +{overhead:.1f}%")

    bottleneck_10m = results.get("Producer 10min Bottleneck", {}).get('total_time', 0)
    if bottleneck_10m:
        print(f"\n  10min Bottleneck: {bottleneck_10m:.3f}s")

    print("\n" + "="*90)
    print(" " * 30 + "MARKDOWN TABLES FOR DOCUMENTATION")
    print("="*90)

    print("\n### Producer Top-3 Functions\n")
    print("| Experiment | Runtime | Function 1 (ncalls, cumtime, %) | Function 2 | Function 3 |")
    print("|------------|---------|-------|-------|-------|")

    for label in producer_labels:
        r = results[label]
        funcs = r['app_funcs'][:3]
        while len(funcs) < 3:
            funcs.append({'name': '-', 'ncalls': '-', 'cumtime': 0, 'pct': 0})

        row = [
            label.replace("Producer ", ""),
            f"{r['total_time']:.1f}s",
        ]
        for f in funcs:
            row.append(f"{f['name']} ({f['ncalls']}, {f['cumtime']:.1f}s, {f['pct']:.0f}%)")

        print("| " + " | ".join(row) + " |")

    print("\n### Consumer/Sink Top-3 Functions\n")
    print("| Component | Runtime | Function 1 (ncalls, cumtime, %) | Function 2 |")
    print("|-----------|---------|-------|-------|")

    for label in non_producer:
        r = results[label]
        funcs = r['app_funcs'][:2]
        while len(funcs) < 2:
            funcs.append({'name': '-', 'ncalls': '-', 'cumtime': 0, 'pct': 0})

        row = [
            label,
            f"{r['total_time']:.1f}s",
        ]
        for f in funcs:
            row.append(f"{f['name']} ({f['ncalls']}, {f['cumtime']:.2f}s, {f['pct']:.0f}%)")

        print("| " + " | ".join(row) + " |")


if __name__ == "__main__":
    main()