import time
import threading
from schoolsim import SchoolSimulation
import message_builder

def simulation_loop(sim):
    while True:
        sim.step()
        
        weekday = sim.get_current_weekday()
        time_str = sim.get_current_time_string()
        phase = sim.get_current_phase()
        
        print(f"[Simulation] {weekday} {time_str} | {phase}")
        time.sleep(1)

def simple_producer_loop(sim, topic):
    room_index = 0
    num_rooms = len(sim.rooms)
    
    while True:
        room = sim.rooms[room_index]
        message = message_builder.build_simple_message(room, sim)
        print(f"[Simple] Topic: {topic} | Room Index: {room_index} \n Msg: {message}")
        
        # Move to the next room
        room_index = (room_index + 1) % num_rooms
        time.sleep(0.1)

def complex_producer_loop(sim, topic):
    room_index = 0
    num_rooms = len(sim.rooms)
    
    while True:
        room = sim.rooms[room_index]
        message = message_builder.build_complex_message(room, sim)
        print(f"[Complex] Topic: {topic} | Room Index: {room_index} | Msg: {message}")
        
        room_index = (room_index + 1) % num_rooms
        time.sleep(1)

if __name__ == "__main__":
    sim = SchoolSimulation()

    sim_thread = threading.Thread(target=simulation_loop, args=(sim,))
    simple_thread = threading.Thread(target=simple_producer_loop, args=(sim, "room_temperature"))
    complex_thread = threading.Thread(target=complex_producer_loop, args=(sim, "room_environment"))

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