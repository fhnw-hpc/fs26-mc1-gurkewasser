import time
import threading
import json
from kafka import KafkaProducer
from schoolsim import SchoolSimulation
import message_builder

"""def simulation_loop(sim):
    while True:
        sim.step()
        
        weekday = sim.get_current_weekday()
        time_str = sim.get_current_time_string()
        phase = sim.get_current_phase()
        
        print(f"[Simulation] {weekday} {time_str} | {phase}")
        time.sleep(1)
"""

def simulation_loop(sim):
    # Select a single room for debugging (assuming rooms[0] is room_01)
    debug_room = sim.rooms[0]
    
    while True:
        sim.step()
        
        weekday = sim.get_current_weekday()
        time_str = sim.get_current_time_string()
        phase = sim.get_current_phase()
        
        # Focused print to observe the control loop
        print(f"[Sim] {time_str} | {phase} | {debug_room.room_id} | "
              f"Occ: {debug_room.occupancy} | CO2: {debug_room.co2_level:.0f} | "
              f"Vent: {debug_room.ventilation_level} | Win: {debug_room.window_open} | "
              f"Temp: {debug_room.temperature:.1f}")
              
        time.sleep(1)

# Added 'producer' to parameters
def simple_producer_loop(sim, topic, producer):
    room_index = 0
    num_rooms = len(sim.rooms)
    message_count = 0 
    
    while True:
        room = sim.rooms[room_index]
        message = message_builder.build_simple_message(room, sim)
        
        # Actually send the message to Kafka
        producer.send(topic, value=message)
        
        # Increment counter and print every third time
        message_count += 1
        if message_count % 3 == 0:
            #print(f"[Simple] Sent to {topic} | Room Index: {room_index} | Msg: {message}")
            pass
        
        # Move to the next room
        room_index = (room_index + 1) % num_rooms
        time.sleep(0.1)

# Added 'producer' to parameters
"""def complex_producer_loop(sim, topic, producer):
    room_index = 0
    num_rooms = len(sim.rooms)
    
    while True:
        room = sim.rooms[room_index]
        message = message_builder.build_complex_message(room, sim)
        
        # Actually send the message to Kafka
        producer.send(topic, value=message)
        print(f"[Complex] Sent to {topic} | Room Index: {room_index} | Msg: {message}")
        
        room_index = (room_index + 1) % num_rooms
        time.sleep(1)"""
def complex_producer_loop(sim, topic, producer):
    # Lock to the same single room
    target_room = sim.rooms[0]
    
    while True:
        message = message_builder.build_complex_message(target_room, sim)
        
        # Send the message to Kafka
        producer.send(topic, value=message)
        # Optional: Print to confirm Kafka is getting the same data
        # print(f"[Complex] Sent to {topic} | Room: {target_room.room_id} | Msg: {message}")
        
        time.sleep(1)

if __name__ == "__main__":

    producer = KafkaProducer(
        bootstrap_servers=['kafka1:9092', 'kafka2:9092', 'kafka3:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    sim = SchoolSimulation()

    sim_thread = threading.Thread(target=simulation_loop, args=(sim,))
    
    # Passed 'producer' into the args tuple for both threads
    simple_thread = threading.Thread(target=simple_producer_loop, args=(sim, "room_temperature", producer))
    complex_thread = threading.Thread(target=complex_producer_loop, args=(sim, "room_environment", producer))

    sim_thread.daemon = True
    simple_thread.daemon = True
    complex_thread.daemon = True

    print("Starting simulation and producer threads. Press Ctrl+C to stop.")
    sim_thread.start()
    simple_thread.start()
    complex_thread.start()

    # Keep the main thread alive to watch the output
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down gracefully.")
        # Added graceful shutdown for the Kafka producer
        producer.flush()
        producer.close()