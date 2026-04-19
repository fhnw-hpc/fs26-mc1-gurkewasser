import csv
import os
import threading
import time
import json
import pika
import msgpack
import sys
import signal
import cProfile

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

RABBITMQ_URL = os.environ.get('BROKER_URL', 'amqp://admin:admin@localhost:5672/')
PROFILE_DIR = "/app/profiles"

_profiler = None
_profiler_output = None
_connections = []


def signal_handler(signum):
    print(f"\nReceived signal {signum}, closing connections to trigger shutdown...")
    for conn in _connections:
        if conn.is_open:
            conn.close()
    print("Connections closed, will save profile on exit.")


def sink_loop(queue_name, file_name, fieldnames):
    file_path = os.path.join(DATA_DIR, file_name)

    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    _connections.append(connection)
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)

    print(f"Started sink for queue '{queue_name}' -> writing to {file_name}")

    file_exists = os.path.isfile(file_path)

    with open(file_path, mode="a", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        def callback(ch, method, properties, body):
            try:
                data = msgpack.unpackb(body, raw=False)
                row = {field: data.get(field, "") for field in fieldnames}
                writer.writerow(row)
                csv_file.flush()
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                print(f"[ERROR in {queue_name} sink] {e}")
                # Im Fehlerfall Nachricht nicht bestätigen (wird erneut eingereiht)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=queue_name, on_message_callback=callback)

        try:
            channel.start_consuming()
        except Exception as e:
            print(f"\nSink {queue_name} stopped: {e}")
        finally:
            if connection.is_open:
                connection.close()


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
        args=("room_temperature_mp", "temperature_log.csv", temp_fields))

    t2 = threading.Thread(
        target=sink_loop,
        args=("room_alerts_mp", "alerts_log.csv", alerts_fields))

    t1.daemon = True
    t2.daemon = True

    print("Starting data sinks. CSVs will be saved in the 'data' folder. Press Ctrl+C to stop.")
    t1.start()
    t2.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down sinks gracefully.")


if __name__ == "__main__":
    os.makedirs(PROFILE_DIR, exist_ok=True)

    print("Starting data sinks with profiling...")
    print("Profiling enabled - check /app/profiles for .prof files")

    if "--profile" in sys.argv:
        print("Running with cProfile profiling...")
        _profiler_output = os.path.join(PROFILE_DIR, 'rmq_sink.prof')
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