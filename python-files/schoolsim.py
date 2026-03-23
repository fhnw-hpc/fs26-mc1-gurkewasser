import random
from class_room import Room

class SchoolSimulation:

    def __init__(self):

        self.rooms = [Room(room_id=f"room_{i:02d}") for i in range(1, 16)]
        self.weekdays = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
        self.current_weekday_index = 0
        self.current_minute_of_day = 0
        self.today_schedule = []
        self.today_double_lesson_period = None
        self.build_day_schedule()


    def build_day_schedule(self):
        self.today_double_lesson_period = random.choice(["morning", "afternoon"])

        self.today_schedule = [
            {"start": 0, "end": 540, "phase": "outside"},
            {"start": 540, "end": 585, "phase": "lesson"},
            {"start": 585, "end": 600, "phase": "break"},
            {"start": 600, "end": 645, "phase": "lesson"},
            {"start": 645, "end": 660, "phase": "break"},
            {"start": 660, "end": 705, "phase": "lesson"},
            {"start": 705, "end": 720, "phase": "break"},
            {"start": 720, "end": 780, "phase": "outside"},
            {"start": 780, "end": 825, "phase": "lesson"},
            {"start": 825, "end": 840, "phase": "break"},
            {"start": 840, "end": 885, "phase": "lesson"},
            {"start": 885, "end": 900, "phase": "break"},
            {"start": 900, "end": 945, "phase": "lesson"},
            {"start": 945, "end": 960, "phase": "break"},
            {"start": 960, "end": 1005, "phase": "lesson"},
            {"start": 1005, "end": 1020, "phase": "break"},
            {"start": 1020, "end": 1440, "phase": "outside"}
        ]
        

    def get_current_phase(self):
        for block in self.today_schedule:
            if block["start"] <= self.current_minute_of_day < block["end"]:
                return block["phase"]
                
        # Safety fallback in case current_minute_of_day is out of bounds (e.g., >= 1440)
        return "outside"
    
    def step(self):
        current_phase = self.get_current_phase()

        for room in self.rooms:
            room.update(current_phase, self.current_minute_of_day)

        # Advance the minute by 1
        self.current_minute_of_day += 1

        # Check for day rollover
        if self.current_minute_of_day >= 1440:
            # Reset minute to 0
            self.current_minute_of_day = 0
            
            self.current_weekday_index = (self.current_weekday_index + 1) % len(self.weekdays)
            
            self.build_day_schedule()

    def get_current_weekday(self):
        return self.weekdays[self.current_weekday_index]

    def get_current_time_string(self):
        hours = self.current_minute_of_day // 60
        minutes = self.current_minute_of_day % 60
        return f"{hours:02d}:{minutes:02d}"
