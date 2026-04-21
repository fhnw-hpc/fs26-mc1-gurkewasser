import json
import time
from kafka import KafkaConsumer

def run_simple_consumer():
    # Initialize the Kafka Consumer
    consumer = KafkaConsumer(
        'room_temperature_mp',
        bootstrap_servers=['kafka1:9092', 'kafka2:9092', 'kafka3:9092'],
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest', 
        group_id='simple_temperature_group'
    )

    print("Listening to 'room_temperature_mp' topic. Press Ctrl+C to stop.")

    message_count = 0
    start_time = time.time()

    try:
        for message in consumer:
            data = message.value
            message_count += 1
            
            # Print the payload cleanly
            room_id = data.get('room_id', 'Unknown')
            temp = data.get('temperature', 'N/A')
            timestamp = data.get('timestamp', 'N/A')
            
            print(f"[Simple] Room: {room_id} | Temp: {temp} | Time: {timestamp}")
            
            # Print performance counter every 50 messages
            if message_count % 50 == 0:
                elapsed = time.time() - start_time
                rate = message_count / elapsed
                print(f"*** Performance: {rate:.2f} msgs/sec ***")
                
    except KeyboardInterrupt:
        print("\nShutting down simple consumer gracefully.")
    finally:
        consumer.close()

if __name__ == "__main__":
    run_simple_consumer()