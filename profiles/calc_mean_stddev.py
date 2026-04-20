import subprocess
import statistics
import re


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


BASE_DIR = "profiles/short_test"
N_RUNS = 4

baseline_runtimes = []
bottleneck_runtimes = []

for i in range(1, N_RUNS + 1):
    rt = extract_runtime(f"{BASE_DIR}/rmq_producer_baseline_run{i}.prof")
    if rt:
        baseline_runtimes.append(rt)

    rt = extract_runtime(f"{BASE_DIR}/rmq_producer_bottleneck_run{i}.prof")
    if rt:
        bottleneck_runtimes.append(rt)

print("=" * 60)
print("PART 4 — Mean + StdDev (Producer)")
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