# Part 1

I will simulate a school monitoring system where a fast simple stream publishes temperature readings for 15 classrooms at 10Hz per room (150 Messages per second or 6.7ms per message), while a slower complex stream publishes fuller environmental state per class room.

## Simple Stream:
- 15 Rooms
- 10 Hz per room
- one message reading per room
- round-robin (it cycles through the rooms in fixed order)
- complex stream will have 1 Hz per room

### Simple schema
- timestamp : String
- room_id : String
- temperature : float (min 18 to max 32)

### Complex schema
- timestamp : String
- room_id : String
- temperature : float (min 18 to max 32)
- people_in_room : integer (0 - 35)
- humidity : integer (30 - 65)
- co2_level : integer (400 - 2000)
- window_open : boolean
- ventilation_level : integer (1/2/3 - Low Medium High)

### Relationships
- people_in_room changes in steps, not continuously
- co2_level reacts strongly to occupancy and air exchange
- temperature reacts weakly to occupancy
- humidity changes slowly
- window_open and ventilation_level can influence co2_level reduction

### State
- one internal room rate model
    - simple generator publishes a reduced view
        - timestamp, room_id, temperature
    - complex generator publishes the fuller view
        - all fields



Update behaviour will drift slowly, since there will be no Human input to change the event directly.


