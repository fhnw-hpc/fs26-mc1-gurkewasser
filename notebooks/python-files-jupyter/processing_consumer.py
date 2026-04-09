import json
import time
import msgpack
from kafka import KafkaConsumer, KafkaProducer

def run_processing_consumer():
    # Consumer reads from 'room_environment', which has complex messages with CO2 levels, etc.
    consumer = KafkaConsumer(
        'room_environment_mp',
        bootstrap_servers=['kafka1:9092', 'kafka2:9092', 'kafka3:9092'],

        # --- BASE SERIALIZATION (JSON) ---
        #value_serializer=lambda v: json.dumps(v).encode('utf-8')
        
        # --- BONUS SERIALIZATION (MessagePack) ---
        value_deserializer=lambda m: msgpack.unpackb(m, raw=False),

        auto_offset_reset='latest',
        group_id='processing_group'
    )

    # Producer writes to 'room_alerts'
    producer = KafkaProducer(
        bootstrap_servers=['kafka1:9092', 'kafka2:9092', 'kafka3:9092'],

        # --- BASE SERIALIZATION (JSON) ---
        # value_serializer=lambda v: json.dumps(v).encode('utf-8')
        
        # --- BONUS SERIALIZATION (MessagePack) ---
        value_serializer=lambda v: msgpack.packb(v)
    )

    print("Running processing consumer.")
    print("Listening to 'room_environment_mp' and writing enriched data to 'room_alerts'.")
    print("Press Ctrl+C to stop.")

    message_count = 0

    try:
        for message in consumer:
            data = message.value
            message_count += 1
            
            # Processing: Check if CO2 level is too high
            co2 = data.get('co2_level', 0)
            if co2 > 1000:
                data['air_quality_warning'] = True
                data['alert_msg'] = "High CO2 Levels detected. Please ventilate."
            else:
                data['air_quality_warning'] = False
                data['alert_msg'] = "CO2 Levels normal."

            # Enrichment: adding processing timestamp
            data['processed_timestamp'] = time.time()
            
            # Re-insert processed data into Kafka under a new topic
            producer.send('room_alerts_mp', value=data)
            
            # Log selectively to avoid spamming the terminal too much
            if message_count % 10 == 0:
                print(f"[Processor] Processed 10 messages... Last Room: {data.get('room_id')} | CO2: {co2:.0f} | Warning: {data['air_quality_warning']}")
            
    except KeyboardInterrupt:
        print("\nShutting down processing consumer gracefully.")
    finally:
        consumer.close()
        producer.flush()
        producer.close()

if __name__ == "__main__":
    run_processing_consumer()
