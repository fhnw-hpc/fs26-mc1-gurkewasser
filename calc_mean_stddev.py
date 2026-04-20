import subprocess
import statistics
import re
import os

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


BASE_DIR = "profiles/small-test"
N_RUNS = 4
FRAMEWORK = "kafka"

baseline_runtimes = []
bottleneck_runtimes = []

for i in range(1, N_RUNS + 1):
    rt = extract_runtime(f"{BASE_DIR}/{FRAMEWORK}_producer_baseline_run{i}.prof")
    if rt:
        baseline_runtimes.append(rt)

    rt = extract_runtime(f"{BASE_DIR}/{FRAMEWORK}_producer_bottleneck_run{i}.prof")
    if rt:
        bottleneck_runtimes.append(rt)

print("=" * 60)
print(f"PART 4 — Mean + StdDev ({FRAMEWORK.upper()} Producer)")
print("=" * 60)

if baseline_runtimes:
    print(f"\nBaseline (N={len(baseline_runtimes)}): {baseline_runtimes}")
    print(f"  Mean:   {statistics.mean(baseline_runtimes):.3f}s")
    if len(baseline_runtimes) > 1:
        print(f"  StdDev: {statistics.stdev(baseline_runtimes):.3f}s")

if bottleneck_runtimes:
    print(f"\nBottleneck (N={len(bottleneck_runtimes)}): {bottleneck_runtimes}")
    print(f"  Mean:   {statistics.mean(bottleneck_runtimes):.3f}s")
    if len(bottleneck_runtimes) > 1:
        print(f"  StdDev: {statistics.stdev(bottleneck_runtimes):.3f}s")

if baseline_runtimes and bottleneck_runtimes:
    overhead = ((statistics.mean(bottleneck_runtimes) - statistics.mean(baseline_runtimes))
                / statistics.mean(baseline_runtimes)) * 100
    print(f"\nOverhead: +{overhead:.1f}%")

rmq_baseline = [20.378, 20.400, 20.370, 20.375]
rmq_bottleneck = [23.461, 23.425, 23.443, 23.462]

if baseline_runtimes and rmq_baseline:
    print("\n" + "=" * 60)
    print(" " * 15 + "KAFKA vs RABBITMQ COMPARISON")
    print("=" * 60)
    k_mean = statistics.mean(baseline_runtimes)
    r_mean = statistics.mean(rmq_baseline)
    diff = ((k_mean - r_mean) / r_mean) * 100
    print(f"\n  RabbitMQ Baseline mean: {r_mean:.3f}s")
    print(f"  Kafka Baseline mean:     {k_mean:.3f}s")
    print(f"  Difference:              {diff:+.1f}%")
    if diff > 0:
        print(f"  -> Kafka is {abs(diff):.1f}% slower than RabbitMQ")
    else:
        print(f"  -> Kafka is {abs(diff):.1f}% faster than RabbitMQ")