import random

class Room:

    # --- model bounds ---
    TEMP_MIN = 18
    TEMP_MAX = 34

    OCCUPANCY_MIN = 0
    OCCUPANCY_MAX = 35

    HUMIDITY_MIN = 30
    HUMIDITY_MAX = 65

    CO2_MIN = 400
    CO2_MAX = 2000

    WINDOW_OPEN_PROB_LOW = 0.1
    WINDOW_OPEN_PROB_MEDIUM = 0.4
    WINDOW_OPEN_PROB_HIGH = 0.8

    WINDOW_OPEN_VALUE = 20

    VENTILATION_MIN = 1
    VENTILATION_MAX = 3

    VENTILATION_VALUE_1 = 10
    VENTILATION_VALUE_2 = 30
    VENTILATION_VALUE_3 = 50

    CLASS_TARGET_MIN = 25
    CLASS_TARGET_MAX = 33

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


    def update(self, current_phase, current_minute_of_day):

        #current_phase = self._get_phase(current_minute_of_day)

        # Transition logic

        if current_phase != self.previous_phase:
            if current_phase == "lesson":
                self.class_target_occupancy = random.randint(Room.CLASS_TARGET_MIN, Room.CLASS_TARGET_MAX)
                self.occupancy = self.class_target_occupancy
            elif current_phase == "break":
                self.class_target_occupancy = None
                occupancy_factor = random.uniform(0.5, 0.6)
                self.occupancy = int(self.occupancy * occupancy_factor)
            elif current_phase == "outside":
                pass

        # Phase logic

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
                if current_minute_of_day % 5 == 0:
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

        # Ventilation Level

        if self.co2_level < 800:
            self.ventilation_level = 1
        elif self.co2_level <= 1200:
            self.ventilation_level = 2
        else:
            self.ventilation_level = 3

        # Window State

        if self.co2_level < 900:
            if random.random() < Room.WINDOW_OPEN_PROB_LOW:
                self.window_open = True
            else:
                self.window_open = False
        elif self.co2_level <= 1400:
            if random.random() < Room.WINDOW_OPEN_PROB_MEDIUM:
                self.window_open = True
            else:
                self.window_open = False
        else:
            if random.random() < Room.WINDOW_OPEN_PROB_HIGH:
                self.window_open = True
            else:
                self.window_open = False

        # CO2 Update

        co2_value_change = self.co2_level + (self.occupancy * random.uniform(1, 2))

        if self.ventilation_level == 1:
            co2_value_change -= Room.VENTILATION_VALUE_1
        elif self.ventilation_level == 2:
            co2_value_change -= Room.VENTILATION_VALUE_2
        else:
            co2_value_change -= Room.VENTILATION_VALUE_3

        if self.window_open:
            co2_value_change -= Room.WINDOW_OPEN_VALUE

        self.co2_level = int(co2_value_change)

        if self.co2_level < Room.CO2_MIN:
            self.co2_level = Room.CO2_MIN
        elif self.co2_level > Room.CO2_MAX:
            self.co2_level = Room.CO2_MAX

        # Temperature update

        temp_occupancy = self.occupancy * random.uniform(0.002, 0.008)

        temp_drift = random.uniform(-0.3, 0.3)

        temp_change = temp_drift + temp_occupancy

        if self.window_open:
            temp_change -= random.uniform(0.3, 0.5)

        self.temperature += temp_change

        if self.temperature < Room.TEMP_MIN:
            self.temperature = Room.TEMP_MIN
        elif self.temperature > Room.TEMP_MAX:
            self.temperature = Room.TEMP_MAX
        
        # Humidity Update

        humidity_drift = random.randint(-1, 1)

        self.humidity += humidity_drift

        if self.humidity < Room.HUMIDITY_MIN:
            self.humidity = Room.HUMIDITY_MIN
        elif self.humidity > Room.HUMIDITY_MAX:
            self.humidity = Room.HUMIDITY_MAX

        self.previous_phase = current_phase