import hashlib
import os
import threading
import time
import msgpack
import json
import sys
import signal
import cProfile

from kafka import KafkaProducer

import message_builder
from schoolsim import SchoolSimulation

PROFILE_DIR = "/app/profiles"

_profiler = None
_profiler_output = None
_shutdown_requested = False


def signal_handler(signum):
    global _shutdown_requested
    print(f"\nReceived signal {signum}, will shutdown gracefully...")
    _shutdown_requested = True


def simulation_loop(sim):
    debug_room = sim.rooms[0]

    while not _shutdown_requested:
        sim.step()

        time_str = sim.get_current_time_string()
        phase = sim.get_current_phase()

        print(
            f"[Sim] {time_str} | {phase} | {debug_room.room_id} | "
            f"Occ: {debug_room.occupancy} | CO2: {debug_room.co2_level:.0f} | "
            f"Vent: {debug_room.ventilation_level} | Win: {debug_room.window_open} | "
            f"Temp: {debug_room.temperature:.1f}"
        )

        time.sleep(1)


def simple_producer_work(sim, topic, num_messages):
    producer = KafkaProducer(
        bootstrap_servers=['kafka1:9092', 'kafka2:9092', 'kafka3:9092'],
        value_serializer=lambda v: msgpack.packb(v),
    )

    room_index = 0
    num_rooms = len(sim.rooms)

    for i in range(num_messages):
        room = sim.rooms[room_index]
        message = message_builder.build_simple_message(room, sim)

        # Old Message and Key Partition DEEPDIVE 1
        #producer.send(topic, value=message)

        # New Message and Key Partition

        if i % 100 == 0:
            print(f"[Simple Producer] {i}/{num_messages} messages sent")
            sys.stdout.flush()

        producer.send(topic, key=room.room_id.encode('utf-8'), value=message)

        room_index = (room_index + 1) % num_rooms
        time.sleep(0.1)

    producer.flush()
    producer.close()


def complex_producer_work(sim, topic, num_messages):
    producer = KafkaProducer(
        bootstrap_servers=['kafka1:9092', 'kafka2:9092', 'kafka3:9092'],
        value_serializer=lambda v: msgpack.packb(v),
    )

    room_index = 0
    num_rooms = len(sim.rooms)

    for i in range(num_messages):
        target_room = sim.rooms[room_index]
        message = message_builder.build_complex_message(target_room, sim)
        # Old Message and Key Partition DEEPDIVE 1
        #producer.send(topic, value=message)
        
        # New Message and Key Partition

        if i % 10 == 0:
            print(f"[Complex Producer] {i}/{num_messages} messages sent")
            sys.stdout.flush()

        if "--bottleneck" in sys.argv:
            time.sleep(0.2)
            json_temp = json.dumps(message)
            json_temp = json.loads(json_temp)
            _ = hashlib.sha256(str(time.time()).encode()).hexdigest()

        producer.send(topic, key=target_room.room_id.encode('utf-8'), value=message)

        room_index = (room_index + 1) % num_rooms
        time.sleep(1)

    producer.flush()
    producer.close()


def run_profiled():
    global _profiler, _profiler_output
    sim = SchoolSimulation()
    SIMPLE_COUNT = int(os.environ.get('PROFILE_SIMPLE_MSGS', '50'))
    COMPLEX_COUNT = int(os.environ.get('PROFILE_COMPLEX_MSGS', '15'))

    print("=" * 60)
    print("Profiling producer work directly...")
    print(f"Simple messages: {SIMPLE_COUNT}, Complex messages: {COMPLEX_COUNT}")
    print("=" * 60)
    sys.stdout.flush()

    if "--bottleneck" in sys.argv:
        print("Bottleneck mode: artificial delay + JSON + SHA256 enabled")
        simple_producer_work(sim, "room_temperature_mp", SIMPLE_COUNT)
        complex_producer_work(sim, "room_environment_mp", COMPLEX_COUNT)
    else:
        print("Baseline mode: no artificial delay")
        simple_producer_work(sim, "room_temperature_mp", SIMPLE_COUNT)
        complex_producer_work(sim, "room_environment_mp", COMPLEX_COUNT)

    sys.stdout.flush()
    print("Profiling complete.")


def run_background():
    sim = SchoolSimulation()

    producer = KafkaProducer(
        bootstrap_servers=['kafka1:9092', 'kafka2:9092', 'kafka3:9092'],
        # --- BASE SERIALIZATION (JSON) ---
        #value_serializer=lambda v: json.dumps(v).encode('utf-8')
        
        # --- BONUS SERIALIZATION (MessagePack) ---
        value_serializer=lambda v: msgpack.packb(v),
    )

        # JSON: room_temperature, room_environment | MessagePack: room_temperature_mp, room_environment_mp

    sim_thread = threading.Thread(target=simulation_loop, args=(sim,))
    simple_thread = threading.Thread(
        target=simple_producer_work, args=(sim, "room_temperature_mp", producer)
    )
    complex_thread = threading.Thread(
        target=complex_producer_work, args=(sim, "room_environment_mp", producer)
    )

    sim_thread.daemon = True
    simple_thread.daemon = True
    complex_thread.daemon = True

    print("Starting simulation and producer threads. Press Ctrl+C to stop.")
    sim_thread.start()
    simple_thread.start()
    complex_thread.start()

    try:
        while not _shutdown_requested:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down gracefully.")
    finally:
        producer.flush()
        producer.close()


if __name__ == "__main__":
    os.makedirs(PROFILE_DIR, exist_ok=True)

    print("=" * 60)
    print("Starting simulation and producer threads. Press Ctrl+C to stop.")
    print("Profiling enabled - check /app/profiles for .prof files")
    print("=" * 60)

    if "--profile" in sys.argv:
        print("Running with cProfile profiling...")

        if "--bottleneck" in sys.argv:
            _profiler_output = os.path.join(PROFILE_DIR, os.environ.get('PROFILE_OUTPUT', 'kafka_producer_bottleneck.prof'))
        else:
            _profiler_output = os.path.join(PROFILE_DIR, os.environ.get('PROFILE_OUTPUT', 'kafka_producer_baseline.prof'))

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        _profiler = cProfile.Profile()
        _profiler.runctx("run_profiled()", globals(), locals())
        _profiler.dump_stats(_profiler_output)

        print(f"\nProfile saved to {_profiler_output}")
        print(f"View with: snakeviz {_profiler_output}")
    else:
        run_background()