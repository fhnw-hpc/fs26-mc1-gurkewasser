import csv
import os
import threading
import time
import json

import msgpack
from kafka import KafkaConsumer


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


def sink_loop(topic, file_name, group_id, fieldnames):
    file_path = os.path.join(DATA_DIR, file_name)

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=["kafka1:9092", "kafka2:9092", "kafka3:9092"],
        value_deserializer=lambda m: msgpack.unpackb(m, raw=False),
        auto_offset_reset="latest",
        group_id=group_id,
    )

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
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down sinks gracefully.")


if __name__ == "__main__":
    run_sinks()
