import json
import time
import msgpack
import pika
import os
import sys
import signal
import cProfile

#from kafka import KafkaConsumer, KafkaProducer
RABBITMQ_URL = os.environ.get('BROKER_URL', 'amqp://admin:admin@localhost:5672/')
PROFILE_DIR = "/app/profiles"

_profiler = None
_profiler_output = None
_connection = None


def signal_handler(signum):
    print(f"\nReceived signal {signum}, closing connection to trigger shutdown...")
    if _connection and _connection.is_open:
        _connection.close()
    print("Connection closed, will save profile on exit.")


def start_processing_consumer():
    global _connection
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    _connection = connection
    channel = connection.channel()

    # Queues deklarieren, um sicherzustellen, dass sie existieren
    channel.queue_declare(queue='room_environment_mp', durable=True)
    channel.queue_declare(queue='room_alerts_mp', durable=True)

    message_count = 0

    def callback(ch, method, properties, body):
        nonlocal message_count
        data = msgpack.unpackb(body, raw=False)
        message_count += 1
        
        # Geschäftslogik aus Kafka-Version
        co2 = data.get('co2_level', 0)
        if co2 > 1000:
            data['air_quality_warning'] = True
            data['alert_msg'] = "High CO2 Levels detected. Please ventilate."
        else:
            data['air_quality_warning'] = False
            data['alert_msg'] = "CO2 Levels normal."

        data['processed_timestamp'] = time.time()
        
        # Angereicherte Daten direkt in die Alerts-Queue publizieren
        ch.basic_publish(
            exchange='',
            routing_key='room_alerts_mp',
            body=msgpack.packb(data),
            properties=pika.BasicProperties(delivery_mode=2)
        )

        ch.basic_ack(delivery_tag=method.delivery_tag)

        if message_count % 10 == 0:
            print(f"[Processor] Processed 10 messages... Last Room: {data.get('room_id')} | CO2: {co2:.0f} | Warning: {data['air_quality_warning']}")

    # Verhindert, dass ein Worker mehr als 1 ungelesene Nachricht auf einmal bekommt
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='room_environment_mp', on_message_callback=callback)

    try:
        channel.start_consuming()
    except Exception as e:
        print(f"\nConsumer stopped: {e}")
    finally:
        if connection.is_open:
            connection.close()


if __name__ == "__main__":
    os.makedirs(PROFILE_DIR, exist_ok=True)

    print("Starting processing consumer with profiling...")
    print("Profiling enabled - check /app/profiles for .prof files")

    if "--profile" in sys.argv:
        print("Running with cProfile profiling...")
        _profiler_output = os.path.join(PROFILE_DIR, 'rmq_consumer.prof')
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