import pstats
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

profiles_dir = Path(__file__).parent / 'profiles'

baseline = pstats.Stats(f'{profiles_dir}/rmq_producer_baseline.prof')
bottleneck = pstats.Stats(f'{profiles_dir}/rmq_producer_bottleneck.prof')

baseline_time = baseline.total_tt
bottleneck_time = bottleneck.total_tt

fig = plt.figure(figsize=(14, 5))

ax1 = plt.subplot(1, 3, 1)
labels = ['Baseline', 'Bottleneck']
runtimes = [baseline_time, bottleneck_time]
colors = ['#2ecc71', '#e74c3c']
bars = ax1.bar(labels, runtimes, color=colors, edgecolor='black', linewidth=1.5, width=0.6)
ax1.set_ylabel('Runtime (seconds)', fontsize=12)
ax1.set_title('Producer Runtime Comparison', fontsize=13, fontweight='bold')
ax1.set_ylim(0, max(runtimes) * 1.2)

for bar, runtime in zip(bars, runtimes):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
             f'{runtime:.2f}s', ha='center', va='bottom', fontsize=12, fontweight='bold')

overhead = ((bottleneck_time - baseline_time) / baseline_time) * 100
ax1.annotate(f'+{overhead:.1f}% overhead\n(+{bottleneck_time - baseline_time:.2f}s)',
             xy=(1, bottleneck_time), xytext=(1.3, bottleneck_time - 2),
             fontsize=9, color='#e74c3c', fontweight='bold',
             arrowprops=dict(arrowstyle='->', color='#e74c3c', lw=1.5))

def get_func_cumulative(stats_dict, search_strings):
    """Search for function names containing any of the search strings (substring match)."""
    if isinstance(search_strings, str):
        search_strings = [search_strings]
    total = 0
    for func, func_stats in stats_dict.items():
        fname = func[2]
        for search_str in search_strings:
            if search_str in fname:
                total += func_stats[3]
                break
    return total

baseline_sleep = get_func_cumulative(baseline.stats, ['sleep', '_sleep'])
baseline_json = get_func_cumulative(baseline.stats, ['json_dumps', 'dumps', 'json.dumps'])
baseline_publish = get_func_cumulative(baseline.stats, ['basic_publish'])
baseline_other = baseline_time - baseline_sleep - baseline_json - baseline_publish

bottleneck_sleep = get_func_cumulative(bottleneck.stats, ['sleep', '_sleep'])
bottleneck_json = get_func_cumulative(bottleneck.stats, ['json_dumps', 'dumps', 'json.dumps'])
bottleneck_publish = get_func_cumulative(bottleneck.stats, ['basic_publish'])
bottleneck_other = bottleneck_time - bottleneck_sleep - bottleneck_json - bottleneck_publish

ax2 = plt.subplot(1, 3, 2)
categories = ['time.sleep', 'json.dumps', 'basic_publish', 'Other']
baseline_vals = [baseline_sleep, baseline_json, baseline_publish, baseline_other]
bottleneck_vals = [bottleneck_sleep, bottleneck_json, bottleneck_publish, bottleneck_other]

x = np.arange(len(categories))
width = 0.35

bars1 = ax2.bar(x - width/2, baseline_vals, width, label='Baseline', color='#2ecc71', edgecolor='black')
bars2 = ax2.bar(x + width/2, bottleneck_vals, width, label='Bottleneck', color='#e74c3c', edgecolor='black')
ax2.set_ylabel('Time (seconds)', fontsize=12)
ax2.set_title('Time Breakdown', fontsize=13, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(categories, rotation=15, ha='right', fontsize=9)
ax2.legend(loc='upper right')
ax2.set_yscale('log')
ax2.set_ylim(0.001, 100)

ax3 = plt.subplot(1, 3, 3)
key_funcs = {
    'time.sleep': lambda f: 'time.sleep' in f or ('sleep' in f.lower() and 'method' in f),
    'basic_publish': lambda f: f == 'basic_publish',
    'poll': lambda f: f == 'poll',
    'send': lambda f: '.send' in f and 'socket' in f,
}
baseline_dict = {}
bottleneck_dict = {}

for func, stats in baseline.stats.items():
    fname = func[2]
    for key, matcher in key_funcs.items():
        if matcher(fname) and stats[3] > 0.001:
            baseline_dict[key] = baseline_dict.get(key, 0) + stats[3]

for func, stats in bottleneck.stats.items():
    fname = func[2]
    for key, matcher in key_funcs.items():
        if matcher(fname) and stats[3] > 0.001:
            bottleneck_dict[key] = bottleneck_dict.get(key, 0) + stats[3]

all_funcs = list(key_funcs.keys())
baseline_times = [baseline_dict.get(f, 0) for f in all_funcs]
bottleneck_times = [bottleneck_dict.get(f, 0) for f in all_funcs]

x = np.arange(len(all_funcs))
width = 0.35

bars1 = ax3.bar(x - width/2, baseline_times, width, label='Baseline', color='#2ecc71', edgecolor='black')
bars2 = ax3.bar(x + width/2, bottleneck_times, width, label='Bottleneck', color='#e74c3c', edgecolor='black')
ax3.set_ylabel('Cumulative Time (seconds)', fontsize=12)
ax3.set_title('Key Functions Comparison', fontsize=13, fontweight='bold')
ax3.set_xticks(x)
ax3.set_xticklabels(all_funcs, rotation=15, ha='right', fontsize=10)
ax3.legend(loc='upper right')
ax3.set_yscale('log')
ax3.set_ylim(0.001, 100)

plt.tight_layout()
plt.savefig(profiles_dir / 'profile_comparison.png', dpi=150, bbox_inches='tight')
plt.close()

print(f"Saved: {profiles_dir}/profile_comparison.png")

print("\n=== PROFILING SUMMARY ===")
print(f"Baseline producer runtime: {baseline_time:.3f}s")
print(f"Bottleneck producer runtime: {bottleneck_time:.3f}s")
print(f"Overhead: +{overhead:.2f}%")
print("\nVisualization complete!")