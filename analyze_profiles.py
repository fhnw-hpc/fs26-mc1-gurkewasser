import subprocess
import statistics
import re
import os
import sys

def extract_runtime(prof_path):
    result = subprocess.run(
        ['python3', '-c', f'''
import pstats
stats = pstats.Stats("{prof_path}")
stats.sort_stats("cumulative")
stats.print_stats(1)
'''],
        capture_output=True,
        text=True
    )
    match = re.search(r'in\s+(\d+\.\d+)\s+seconds', result.stdout)
    if match:
        return float(match.group(1))
    return None


def analyze_file(prof_path, label):
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
    mq_funcs = []

    for line in lines:
        if '/app/' in line:
            parts = line.split()
            if len(parts) >= 4:
                try:
                    ncalls = parts[0].strip()
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

        elif 'kafka/' in line or 'pika/' in line:
            parts = line.split()
            if len(parts) >= 4:
                try:
                    ncalls = parts[0].strip()
                    cumtime = float(parts[3].strip())
                    func_name = line.split('(')[-1].replace(')', '').strip()
                    pct = (cumtime / total_time * 100) if total_time > 0 else 0
                    mq_funcs.append({
                        'name': func_name,
                        'ncalls': ncalls,
                        'cumtime': cumtime,
                        'pct': pct
                    })
                except:
                    pass

    app_funcs.sort(key=lambda x: x['cumtime'], reverse=True)
    mq_funcs.sort(key=lambda x: x['cumtime'], reverse=True)

    return {
        'label': label,
        'total_time': total_time,
        'app_funcs': app_funcs[:3],
        'mq_funcs': mq_funcs[:3]
    }


def main():
    print("=" * 90)
    print(" " * 30 + "KAFKA PROFILING ANALYSIS")
    print("=" * 90)

    PROFILES_DIR = "profiles"
    SHORT_DIR = f"{PROFILES_DIR}/small-test"

    files = [
        (f"{SHORT_DIR}/kafka_producer_baseline_run1.prof", "Kafka Producer Short Baseline Run1", "producer"),
        (f"{SHORT_DIR}/kafka_producer_baseline_run2.prof", "Kafka Producer Short Baseline Run2", "producer"),
        (f"{SHORT_DIR}/kafka_producer_baseline_run3.prof", "Kafka Producer Short Baseline Run3", "producer"),
        (f"{SHORT_DIR}/kafka_producer_baseline_run4.prof", "Kafka Producer Short Baseline Run4", "producer"),
        (f"{SHORT_DIR}/kafka_producer_bottleneck_run1.prof", "Kafka Producer Short Bottleneck Run1", "producer"),
        (f"{SHORT_DIR}/kafka_producer_bottleneck_run2.prof", "Kafka Producer Short Bottleneck Run2", "producer"),
        (f"{SHORT_DIR}/kafka_producer_bottleneck_run3.prof", "Kafka Producer Short Bottleneck Run3", "producer"),
        (f"{SHORT_DIR}/kafka_producer_bottleneck_run4.prof", "Kafka Producer Short Bottleneck Run4", "producer"),
        (f"{SHORT_DIR}/kafka_consumer.prof", "Kafka Consumer Short", "consumer"),
        (f"{SHORT_DIR}/kafka_sink.prof", "Kafka Sink Short", "sink"),
        (f"{PROFILES_DIR}/kafka_producer_baseline.prof", "Kafka Producer 10min Baseline", "producer"),
        (f"{PROFILES_DIR}/kafka_producer_bottleneck.prof", "Kafka Producer 10min Bottleneck", "producer"),
        (f"{PROFILES_DIR}/kafka_consumer.prof", "Kafka Consumer 10min", "consumer"),
    ]

    results = {}
    for path, label, ptype in files:
        if os.path.exists(path):
            r = analyze_file(path, label)
            results[label] = r
            print(f"  [OK] {label}: {r['total_time']:.3f}s")
        else:
            print(f"  [SKIP] {path} not found")

    print("\n" + "=" * 90)
    print(" " * 35 + "PRODUCER ANALYSIS")
    print("=" * 90)

    producer_labels = [k for k in results if k.startswith("Kafka Producer")]
    for label in producer_labels:
        r = results[label]
        print(f"\n### {label} (Total: {r['total_time']:.3f}s) ###")

        print("\n  Application Code (Top-3):")
        for i, f in enumerate(r['app_funcs'], 1):
            print(f"    {i}. {f['name']}")
            print(f"       ncalls: {f['ncalls']}, cumtime: {f['cumtime']:.3f}s ({f['pct']:.1f}%)")

        print("\n  Kafka/Pika Functions (Top-3):")
        for i, f in enumerate(r['mq_funcs'], 1):
            print(f"    {i}. {f['name']}")
            print(f"       ncalls: {f['ncalls']}, cumtime: {f['cumtime']:.3f}s ({f['pct']:.1f}%)")

    print("\n" + "=" * 90)
    print(" " * 35 + "CONSUMER/SINK ANALYSIS")
    print("=" * 90)

    non_producer = [k for k in results if not k.startswith("Kafka Producer")]
    for label in non_producer:
        r = results[label]
        print(f"\n### {label} (Total: {r['total_time']:.3f}s) ###")

        print("\n  Application Code (Top-3):")
        for i, f in enumerate(r['app_funcs'], 1):
            print(f"    {i}. {f['name']}")
            print(f"       ncalls: {f['ncalls']}, cumtime: {f['cumtime']:.3f}s ({f['pct']:.1f}%)")

        print("\n  Kafka/Pika Functions (Top-3):")
        for i, f in enumerate(r['mq_funcs'], 1):
            print(f"    {i}. {f['name']}")
            print(f"       ncalls: {f['ncalls']}, cumtime: {f['cumtime']:.3f}s ({f['pct']:.1f}%)")

    print("\n" + "=" * 90)
    print(" " * 35 + "OVERHEAD COMPARISON")
    print("=" * 90)

    baseline_runs = [results[k]['total_time'] for k in results
                     if "Baseline" in k and "Short" in k]
    bottleneck_runs = [results[k]['total_time'] for k in results
                       if "Bottleneck" in k and "Short" in k]

    if baseline_runs:
        print(f"\n  Kafka Short Baseline runs: {baseline_runs}")
        print(f"  Mean: {statistics.mean(baseline_runs):.3f}s")
        if len(baseline_runs) > 1:
            print(f"  StdDev: {statistics.stdev(baseline_runs):.3f}s")

    if bottleneck_runs:
        print(f"\n  Kafka Short Bottleneck runs: {bottleneck_runs}")
        print(f"  Mean: {statistics.mean(bottleneck_runs):.3f}s")
        if len(bottleneck_runs) > 1:
            print(f"  StdDev: {statistics.stdev(bottleneck_runs):.3f}s")

    if baseline_runs and bottleneck_runs:
        b_mean = statistics.mean(baseline_runs)
        bn_mean = statistics.mean(bottleneck_runs)
        overhead = ((bn_mean - b_mean) / b_mean) * 100
        print(f"\n  Kafka Overhead: +{overhead:.1f}%")

    print("\n" + "=" * 90)
    print(" " * 30 + "MARKDOWN TABLES FOR DOCUMENTATION")
    print("=" * 90)

    print("\n### Kafka Producer Top-3 Functions\n")
    print("| Experiment | Runtime | Function 1 (ncalls, cumtime, %) | Function 2 | Function 3 |")
    print("|------------|---------|-------|-------|-------|")

    for label in producer_labels:
        r = results[label]
        funcs = r['app_funcs'][:3]
        while len(funcs) < 3:
            funcs.append({'name': '-', 'ncalls': '-', 'cumtime': 0, 'pct': 0})

        row = [
            label.replace("Kafka Producer ", ""),
            f"{r['total_time']:.1f}s",
        ]
        for f in funcs:
            row.append(f"{f['name']} ({f['ncalls']}, {f['cumtime']:.1f}s, {f['pct']:.0f}%)")

        print("| " + " | ".join(row) + " |")

    print("\n### Kafka Consumer/Sink Top-3 Functions\n")
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