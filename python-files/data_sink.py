import csv
import os
import threading
import time
import sys
import signal
import cProfile

import msgpack
from kafka import KafkaConsumer

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

PROFILE_DIR = "/app/profiles"

_profiler = None
_profiler_output = None
_consumers = []
_shutdown_requested = False


def signal_handler(signum, frame):
    global _shutdown_requested
    print(f"\nReceived signal {signum}, closing Kafka consumers...")
    _shutdown_requested = True
    for c in _consumers:
        try:
            c.close()
        except:
            pass


def sink_loop(topic, file_name, group_id, fieldnames):
    file_path = os.path.join(DATA_DIR, file_name)

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=["kafka1:9092", "kafka2:9092", "kafka3:9092"],
        value_deserializer=lambda m: msgpack.unpackb(m, raw=False),
        auto_offset_reset="latest",
        group_id=group_id,
    )
    _consumers.append(consumer)

    print(f"Started sink for topic '{topic}' -> writing to {file_name}")

    file_exists = os.path.isfile(file_path)

    with open(file_path, mode="a", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        try:
            for message in consumer:
                data = message.value
                row = {field: data.get(field, "") for field in fieldnames}
                writer.writerow(row)
                csv_file.flush()

        except Exception as e:
            print(f"[ERROR in {topic} sink] {e}")
        finally:
            if consumer in _consumers:
                _consumers.remove(consumer)
            consumer.close()


def run_sinks():
    temp_fields = ["timestamp", "room_id", "temperature"]
    alerts_fields = [
        "timestamp",
        "processed_timestamp",
        "room_id",
        "temperature",
        "occupancy",
        "humidity",
        "co2_level",
        "window_open",
        "ventilation_level",
        "air_quality_warning",
        "alert_msg",
    ]

    t1 = threading.Thread(
        target=sink_loop,
        args=("room_temperature_mp", "temperature_log.csv", "sink_temp_group_mp", temp_fields),
    )

    t2 = threading.Thread(
        target=sink_loop,
        args=("room_alerts_mp", "alerts_log.csv", "sink_alerts_group_mp", alerts_fields),
    )

    t1.daemon = True
    t2.daemon = True

    print("Starting data sinks. CSVs will be saved in the 'data' folder. Press Ctrl+C to stop.")
    t1.start()
    t2.start()

    try:
        while not _shutdown_requested:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down sinks gracefully.")


if __name__ == "__main__":
    os.makedirs(PROFILE_DIR, exist_ok=True)

    print("Starting data sinks with profiling...")
    print("Profiling enabled - check /app/profiles for .prof files")

    if "--profile" in sys.argv:
        print("Running with cProfile profiling...")
        _profiler_output = os.path.join(PROFILE_DIR, 'kafka_sink.prof')
        _profiler = cProfile.Profile()
        _profiler.enable()

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        try:
            run_sinks()
        finally:
            _profiler.disable()
            _profiler.create_stats()
            _profiler.dump_stats(_profiler_output)
            print(f"\nProfile saved to {_profiler_output}")
    else:
        run_sinks()