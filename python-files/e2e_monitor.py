import csv
import os
import sys
import signal
import time
import msgpack
from kafka import KafkaConsumer

E2E_DIR = os.environ.get("E2E_DATA_DIR", "/app/e2e_data")
PUBLISH_INTERVAL = int(os.environ.get("E2E_PUBLISH_INTERVAL", "5"))

_shutdown_requested = False


def signal_handler(signum, frame):
    global _shutdown_requested
    print(f"\n[E2E Monitor] Received signal {signum}, shutting down...")
    _shutdown_requested = True


def monitor_simple_topic():
    consumer = KafkaConsumer(
        'room_temperature_mp',
        bootstrap_servers=['kafka1:9092', 'kafka2:9092', 'kafka3:9092'],
        value_deserializer=lambda m: msgpack.unpackb(m, raw=False),
        auto_offset_reset='latest',
        group_id='e2e_monitor_simple_group'
    )

    os.makedirs(E2E_DIR, exist_ok=True)
    csv_path = os.path.join(E2E_DIR, "e2e_simple_latency.csv")

    fieldnames = [
        "wall_time", "room_id", "e2e_send_ts", "e2e_sink_arrival_ts",
        "e2e_latency_ms", "topic"
    ]

    file_exists = os.path.isfile(csv_path)
    fh = open(csv_path, "a", newline="")
    writer = csv.DictWriter(fh, fieldnames=fieldnames)
    if not file_exists:
        writer.writeheader()
        fh.flush()

    count = 0
    latencies = []

    print("[E2E Simple Monitor] Listening on room_temperature_mp...")

    try:
        for message in consumer:
            if _shutdown_requested:
                break

            data = message.value
            now = time.time()
            send_ts = data.get('e2e_send_ts')

            if send_ts:
                latency_ms = round((now - send_ts) * 1000, 3)
                latencies.append(latency_ms)

                writer.writerow({
                    "wall_time": round(now, 3),
                    "room_id": data.get('room_id', ''),
                    "e2e_send_ts": round(send_ts, 3),
                    "e2e_sink_arrival_ts": round(now, 3),
                    "e2e_latency_ms": latency_ms,
                    "topic": "room_temperature_mp"
                })
                fh.flush()

            count += 1

            if count % PUBLISH_INTERVAL == 0 and latencies:
                recent = latencies[-PUBLISH_INTERVAL:]
                avg = sum(recent) / len(recent)
                p50 = sorted(recent)[len(recent) // 2]
                p99 = sorted(recent)[int(len(recent) * 0.99)] if len(recent) > 1 else recent[0]
                print(f"[E2E Simple] {count} msgs | Avg: {avg:.1f}ms | P50: {p50:.1f}ms | P99: {p99:.1f}ms")

    except Exception as e:
        print(f"[E2E Simple Monitor] Stopped: {e}")
    finally:
        fh.close()
        consumer.close()

    return count, latencies


def monitor_alerts_topic():
    consumer = KafkaConsumer(
        'room_alerts_mp',
        bootstrap_servers=['kafka1:9092', 'kafka2:9092', 'kafka3:9092'],
        value_deserializer=lambda m: msgpack.unpackb(m, raw=False),
        auto_offset_reset='latest',
        group_id='e2e_monitor_alerts_group'
    )

    os.makedirs(E2E_DIR, exist_ok=True)
    csv_path = os.path.join(E2E_DIR, "e2e_alerts_latency.csv")

    fieldnames = [
        "wall_time", "room_id", "e2e_send_ts", "e2e_consumer_done_ts",
        "e2e_sink_arrival_ts", "e2e_total_latency_ms",
        "e2e_producer_to_consumer_ms", "e2e_consumer_to_sink_ms",
        "topic"
    ]

    file_exists = os.path.isfile(csv_path)
    fh = open(csv_path, "a", newline="")
    writer = csv.DictWriter(fh, fieldnames=fieldnames)
    if not file_exists:
        writer.writeheader()
        fh.flush()

    count = 0
    latencies = []

    print("[E2E Alerts Monitor] Listening on room_alerts_mp...")

    try:
        for message in consumer:
            if _shutdown_requested:
                break

            data = message.value
            now = time.time()
            send_ts = data.get('e2e_send_ts')
            consumer_done_ts = data.get('e2e_consumer_done_ts')
            p2c = data.get('e2e_producer_to_consumer_ms')

            if send_ts:
                total_latency_ms = round((now - send_ts) * 1000, 3)
                latencies.append(total_latency_ms)

                c2s_ms = round((now - consumer_done_ts) * 1000, 3) if consumer_done_ts else -1

                writer.writerow({
                    "wall_time": round(now, 3),
                    "room_id": data.get('room_id', ''),
                    "e2e_send_ts": round(send_ts, 3),
                    "e2e_consumer_done_ts": round(consumer_done_ts, 3) if consumer_done_ts else '',
                    "e2e_sink_arrival_ts": round(now, 3),
                    "e2e_total_latency_ms": total_latency_ms,
                    "e2e_producer_to_consumer_ms": p2c if p2c else '',
                    "e2e_consumer_to_sink_ms": c2s_ms,
                    "topic": "room_alerts_mp"
                })
                fh.flush()

            count += 1

            if count % PUBLISH_INTERVAL == 0 and latencies:
                recent = latencies[-PUBLISH_INTERVAL:]
                avg = sum(recent) / len(recent)
                p50 = sorted(recent)[len(recent) // 2]
                p99 = sorted(recent)[int(len(recent) * 0.99)] if len(recent) > 1 else recent[0]
                c2s_vals = []
                print(f"[E2E Alerts] {count} msgs | E2E Avg: {avg:.1f}ms | P50: {p50:.1f}ms | P99: {p99:.1f}ms")

    except Exception as e:
        print(f"[E2E Alerts Monitor] Stopped: {e}")
    finally:
        fh.close()
        consumer.close()

    return count, latencies


def monitor_throughput(topic, group_id, label):
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=['kafka1:9092', 'kafka2:9092', 'kafka3:9092'],
        value_deserializer=lambda m: msgpack.unpackb(m, raw=False),
        auto_offset_reset='latest',
        group_id=group_id
    )

    os.makedirs(E2E_DIR, exist_ok=True)
    csv_path = os.path.join(E2E_DIR, f"e2e_throughput_{label}.csv")

    fieldnames = ["window_start", "window_end", "message_count", "msgs_per_sec", "topic"]
    file_exists = os.path.isfile(csv_path)
    fh = open(csv_path, "a", newline="")
    writer = csv.DictWriter(fh, fieldnames=fieldnames)
    if not file_exists:
        writer.writeheader()
        fh.flush()

    window_size = int(os.environ.get("E2E_THROUGHPUT_WINDOW", "10"))
    window_start = time.time()
    window_count = 0
    total_count = 0

    print(f"[E2E Throughput {label}] Listening on {topic} (window={window_size}s)...")

    try:
        for message in consumer:
            if _shutdown_requested:
                break

            window_count += 1
            total_count += 1
            now = time.time()

            if now - window_start >= window_size:
                elapsed = now - window_start
                rate = window_count / elapsed
                writer.writerow({
                    "window_start": round(window_start, 3),
                    "window_end": round(now, 3),
                    "message_count": window_count,
                    "msgs_per_sec": round(rate, 2),
                    "topic": topic
                })
                fh.flush()
                print(f"[E2E Throughput {label}] {rate:.1f} msg/s | Total: {total_count}")
                window_start = now
                window_count = 0

    except Exception as e:
        print(f"[E2E Throughput {label}] Stopped: {e}")
    finally:
        fh.close()
        consumer.close()

    return total_count


METRICS_FIELDNAMES = [
    "timestamp", "metric", "topic", "value", "unit", "count"
]


def write_stability_metrics(latencies_simple, latencies_alerts):
    os.makedirs(E2E_DIR, exist_ok=True)
    csv_path = os.path.join(E2E_DIR, "e2e_stability_metrics.csv")

    file_exists = os.path.isfile(csv_path)
    fh = open(csv_path, "a", newline="")
    writer = csv.DictWriter(fh, fieldnames=METRICS_FIELDNAMES)
    if not file_exists:
        writer.writeheader()

    now = time.time()

    def write_latency_metrics(latencies, label):
        if not latencies:
            return
        sorted_l = sorted(latencies)
        n = len(sorted_l)
        metrics = {
            "avg_ms": sum(latencies) / n,
            "min_ms": sorted_l[0],
            "max_ms": sorted_l[-1],
            "p50_ms": sorted_l[n // 2],
            "p95_ms": sorted_l[int(n * 0.95)],
            "p99_ms": sorted_l[int(n * 0.99)] if n > 1 else sorted_l[0],
            "stddev_ms": (sum((x - sum(latencies)/n)**2 for x in latencies) / n) ** 0.5
        }
        for metric_name, value in metrics.items():
            writer.writerow({
                "timestamp": round(now, 3),
                "metric": metric_name,
                "topic": label,
                "value": round(value, 3),
                "unit": "ms",
                "count": n
            })

    write_latency_metrics(latencies_simple, "room_temperature_mp")
    write_latency_metrics(latencies_alerts, "room_alerts_mp")

    fh.flush()
    fh.close()
    print(f"[E2E] Stability metrics written to {csv_path}")


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 60)
    print("E2E Performance Monitor")
    print(f"Data directory: {E2E_DIR}")
    print("=" * 60)

    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode == "all":
        import threading

        t_simple = threading.Thread(target=monitor_simple_topic, daemon=True)
        t_alerts = threading.Thread(target=monitor_alerts_topic, daemon=True)
        t_tp_simple = threading.Thread(
            target=monitor_throughput,
            args=("room_temperature_mp", "e2e_tp_simple_group", "simple"),
            daemon=True
        )
        t_tp_alerts = threading.Thread(
            target=monitor_throughput,
            args=("room_alerts_mp", "e2e_tp_alerts_group", "alerts"),
            daemon=True
        )

        t_simple.start()
        t_alerts.start()
        t_tp_simple.start()
        t_tp_alerts.start()

        print("[E2E Monitor] All monitors running. Press Ctrl+C to stop.")
        try:
            while not _shutdown_requested:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[E2E Monitor] Keyboard interrupt, shutting down...")
            _shutdown_requested = True

        time.sleep(2)

    elif mode == "latency-simple":
        monitor_simple_topic()
    elif mode == "latency-alerts":
        monitor_alerts_topic()
    elif mode == "throughput-simple":
        monitor_throughput("room_temperature_mp", "e2e_tp_simple_group", "simple")
    elif mode == "throughput-alerts":
        monitor_throughput("room_alerts_mp", "e2e_tp_alerts_group", "alerts")
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python e2e_monitor.py [all|latency-simple|latency-alerts|throughput-simple|throughput-alerts]")
        sys.exit(1)