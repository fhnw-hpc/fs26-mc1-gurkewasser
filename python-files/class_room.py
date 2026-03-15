from random import random
import random

class Room:

    # --- model bounds ---
    TEMP_MIN = 18
    TEMP_MAX = 32

    OCCUPANCY_MIN = 0
    OCCUPANCY_MAX = 35

    HUMIDITY_MIN = 30
    HUMIDITY_MAX = 65

    CO2_MIN = 400
    CO2_MAX = 2000

    VENTILATION_MIN = 1
    VENTILATION_MAX = 3

    # --- init ranges ---

    TEMP_INIT_MIN = 20
    TEMP_INIT_MAX = 25

    HUMIDITY_INIT_MIN = 45
    HUMIDITY_INIT_MAX = 50

    CO2_INIT_MIN = 500
    CO2_INIT_MAX = 700

    def __init__(self, room_id):

        self.room_id = room_id
        self.temperature = random.uniform(Room.TEMP_INIT_MIN, Room.TEMP_INIT_MAX)
        self.occupancy = random.randint(Room.OCCUPANCY_MIN, Room.OCCUPANCY_MAX)
        self.humidity = random.randint(Room.HUMIDITY_INIT_MIN, Room.HUMIDITY_INIT_MAX)
        self.co2_level = random.randint(Room.CO2_INIT_MIN, Room.CO2_INIT_MAX)
        self.window_open = False
        self.ventilation_level = random.randint(Room.VENTILATION_MIN, Room.VENTILATION_MAX)

        self.class_target_occupancy = None
        self.previous_phase = "outside"
        self.outside_study_minutes_remaining = 0

    def _get_phase(self, current_minute):

        cycle_position = current_minute % 60

        if current_minute >= 405:
            return "outside"

        if cycle_position < 45:
            return "lesson"
        else:
            return "break"


    def update(self, current_minute):

        current_phase = self._get_phase(current_minute)

        if current_phase != self.previous_phase:
            if current_phase == "lesson":
                self.class_target_occupancy = random.randint(25, 33)
                self.occupancy = self.class_target_occupancy
            elif current_phase == "break":
                self.class_target_occupancy = None
                occupancy_factor = random.uniform(0.5, 0.6)
                self.occupancy = int(self.occupancy * occupancy_factor)
            elif current_phase == "outside":
                pass


        if current_phase == "lesson":
            lesson_fluctuation = random.randint(-2, 2)
            self.occupancy = self.class_target_occupancy + lesson_fluctuation

        elif current_phase == "break":
            break_fluctuation = random.randint(-1, 1)
            self.occupancy +=  break_fluctuation

        elif current_phase == "outside":
            if self.outside_study_minutes_remaining > 0:
                self.outside_study_minutes_remaining -= 1
                if self.outside_study_minutes_remaining == 0:
                    self.occupancy = 0

            elif self.occupancy > 0:
                if current_minute % 5 == 0:
                    outside_decreaser = random.randint(2, 3)
                    self.occupancy -= outside_decreaser
                    
            elif self.occupancy == 0:
                chance_to_start_new_study_session = 0.9
                study_time = random.randint(30, 45)
                groups = [1, 2, random.randint(3, 5), random.randint(6, 8)]
                if random.random() < chance_to_start_new_study_session:
                    self.occupancy = random.choice(groups)
                    self.outside_study_minutes_remaining = study_time

        if self.occupancy < Room.OCCUPANCY_MIN:
            self.occupancy = Room.OCCUPANCY_MIN
        elif self.occupancy > Room.OCCUPANCY_MAX:
            self.occupancy = Room.OCCUPANCY_MAX
            
        self.previous_phase = current_phase


