import json
import time
import os
import sys
import signal
import cProfile
import msgpack
from kafka import KafkaConsumer, KafkaProducer

PROFILE_DIR = "/app/profiles"

_profiler = None
_profiler_output = None
_consumer = None
_producer = None
_shutdown_requested = False


def signal_handler(signum, frame):
    global _shutdown_requested
    print(f"\nReceived signal {signum}, closing Kafka connections...")
    _shutdown_requested = True
    if _consumer:
        try:
            _consumer.close()
        except:
            pass
    if _producer:
        try:
            _producer.flush()
            _producer.close()
        except:
            pass


def start_processing_consumer():
    global _consumer, _producer

    _consumer = KafkaConsumer(
        'room_environment_mp',
        bootstrap_servers=['kafka1:9092', 'kafka2:9092', 'kafka3:9092'],
        value_deserializer=lambda m: msgpack.unpackb(m, raw=False),
        auto_offset_reset='latest',
        group_id='processing_group'
    )

    _producer = KafkaProducer(
        bootstrap_servers=['kafka1:9092', 'kafka2:9092', 'kafka3:9092'],

        # --- BASE SERIALIZATION (JSON) ---
        # value_serializer=lambda v: json.dumps(v).encode('utf-8')
        
        # --- BONUS SERIALIZATION (MessagePack) ---
        value_serializer=lambda v: msgpack.packb(v)
    )

    print("Running processing consumer.")
    print("Listening to 'room_environment_mp' and writing enriched data to 'room_alerts_mp'.")
    print("Press Ctrl+C to stop.")

    message_count = 0

    try:
        for message in _consumer:
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

            now = time.time()
            data['processed_timestamp'] = now

            send_ts = data.get('e2e_send_ts')
            if send_ts:
                data['e2e_producer_to_consumer_ms'] = round((now - send_ts) * 1000, 2)

            data['e2e_consumer_done_ts'] = now

            _producer.send('room_alerts_mp', value=data)

            if message_count % 10 == 0:
                lat_str = f" | Latency: {data.get('e2e_producer_to_consumer_ms', 'N/A')}ms" if send_ts else ""
                print(f"[Processor] {message_count} msgs | Room: {data.get('room_id')} | CO2: {co2:.0f}{lat_str}")

    except Exception as e:
        print(f"\nConsumer stopped: {e}")
    finally:
        if _consumer:
            _consumer.close()
        if _producer:
            _producer.flush()
            _producer.close()


if __name__ == "__main__":
    os.makedirs(PROFILE_DIR, exist_ok=True)

    print("Starting processing consumer with profiling...")
    print("Profiling enabled - check /app/profiles for .prof files")

    if "--profile" in sys.argv:
        print("Running with cProfile profiling...")
        _profiler_output = os.path.join(PROFILE_DIR, 'kafka_consumer.prof')
        _profiler = cProfile.Profile()
        _profiler.enable()

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        try:
            start_processing_consumer()
        finally:
            _profiler.disable()
            _profiler.create_stats()
            _profiler.dump_stats(_profiler_output)
            print(f"\nProfile saved to {_profiler_output}")
    else:
        start_processing_consumer()