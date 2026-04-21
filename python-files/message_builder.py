import time


def get_simulation_timestamp(sim):
    weekday = sim.get_current_weekday()
    time_str = sim.get_current_time_string()
    return f"{weekday} {time_str}"


def build_simple_message(room, sim):
    return {
        "timestamp": get_simulation_timestamp(sim),
        "room_id": room.room_id,
        "temperature": round(room.temperature, 2),
        "e2e_send_ts": time.time()
    }


def build_complex_message(room, sim):
    return {
        "timestamp": get_simulation_timestamp(sim),
        "room_id": room.room_id,
        "temperature": round(room.temperature, 2),
        "occupancy": room.occupancy,
        "humidity": room.humidity,
        "co2_level": room.co2_level,
        "window_open": room.window_open,
        "ventilation_level": room.ventilation_level,
        "e2e_send_ts": time.time()
    }