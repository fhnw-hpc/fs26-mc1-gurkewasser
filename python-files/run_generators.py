import threading
import time

import msgpack
from kafka import KafkaProducer

import message_builder
from schoolsim import SchoolSimulation


def simulation_loop(sim):
    debug_room = sim.rooms[0]

    while True:
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


def simple_producer_loop(sim, topic, producer):
    room_index = 0
    num_rooms = len(sim.rooms)

    while True:
        room = sim.rooms[room_index]
        message = message_builder.build_simple_message(room, sim)

        producer.send(topic, value=message)

        room_index = (room_index + 1) % num_rooms
        time.sleep(0.1)


def complex_producer_loop(sim, topic, producer):
    target_room = sim.rooms[0]

    while True:
        message = message_builder.build_complex_message(target_room, sim)
        producer.send(topic, value=message)
        # Optional: Print to confirm Kafka is getting the same data
        # print(f"[Complex] Sent to {topic} | Room: {target_room.room_id} | Msg: {message}")
        
        time.sleep(1)


if __name__ == "__main__":
    producer = KafkaProducer(
        bootstrap_servers=['kafka1:9092', 'kafka2:9092', 'kafka3:9092'],
        # --- BASE SERIALIZATION (JSON) ---
        #value_serializer=lambda v: json.dumps(v).encode('utf-8')
        
        # --- BONUS SERIALIZATION (MessagePack) ---
        value_serializer=lambda v: msgpack.packb(v)
    )

    sim = SchoolSimulation()
    
    # JSON: room_temperature, room_environment | MessagePack: room_temperature_mp, room_environment_mp
    sim_thread = threading.Thread(target=simulation_loop, args=(sim,))
    simple_thread = threading.Thread(
        target=simple_producer_loop, args=(sim, "room_temperature_mp", producer)
    )
    complex_thread = threading.Thread(
        target=complex_producer_loop, args=(sim, "room_environment_mp", producer)
    )

    sim_thread.daemon = True
    simple_thread.daemon = True
    complex_thread.daemon = True

    print("Starting simulation and producer threads. Press Ctrl+C to stop.")
    sim_thread.start()
    simple_thread.start()
    complex_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down gracefully.")
        producer.flush()
        producer.close()