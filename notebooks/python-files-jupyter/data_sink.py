import json
import time
import os
import csv
import threading
from kafka import KafkaConsumer

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# Ensure the data directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def sink_loop(topic, file_name, group_id, fieldnames):
    file_path = os.path.join(DATA_DIR, file_name)
    
    # Initialize Kafka Consumer
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=['kafka1:9092', 'kafka2:9092', 'kafka3:9092'],
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest',
        group_id=group_id
    )

    print(f"Started sink for topic '{topic}' -> writing to {file_name}")

    file_exists = os.path.isfile(file_path)
    
    # Open file in append mode. We use newline='' to prevent blank lines between rows
    with open(file_path, mode='a', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        
        # Write header if file is newly created
        if not file_exists:
            writer.writeheader()
            
        try:
            for message in consumer:
                data = message.value
                
                # Make sure we only write fields that are in fieldnames
                # In case data has extra fields we filter them out. If missing, they default to empty string.
                row = {field: data.get(field, "") for field in fieldnames}
                
                writer.writerow(row)
                csv_file.flush() # Ensure it writes to disk immediately to prevent data loss
                
        except Exception as e:
            # We exit loop gracefully on KeyboardInterrupt or exception
            pass
        finally:
            consumer.close()

def run_sinks():
    # Define topics, file names, group IDs, and expected CSV headers
    temp_fields = ["timestamp", "room_id", "temperature"]
    alerts_fields = ["timestamp", "processed_timestamp", "room_id", "temperature", "occupancy", 
                     "humidity", "co2_level", "window_open", "ventilation_level", 
                     "air_quality_warning", "alert_msg"]

    # Thread 1: Sink for room_temperature
    t1 = threading.Thread(
        target=sink_loop, 
        args=("room_temperature", "temperature_log.csv", "sink_temp_group", temp_fields)
    )
    
    # Thread 2: Sink for room_alerts
    t2 = threading.Thread(
        target=sink_loop, 
        args=("room_alerts", "alerts_log.csv", "sink_alerts_group", alerts_fields)
    )

    # Allow threads to be killed when main thread exits
    t1.daemon = True
    t2.daemon = True

    print("Starting data sinks. CSVs will be saved in the 'data' folder. Press Ctrl+C to stop.")
    t1.start()
    t2.start()

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down sinks gracefully.")

if __name__ == "__main__":
    run_sinks()
