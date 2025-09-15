from optimization_engine import generate_timetable
data = {
  "rooms": [
    {"id": "R1", "name": "Room 69", "capacity": 40, "type": "classroom"},
    {"id": "R1", "name": "Room 69", "capacity": 40, "type": "classroom"},
    {"id": "R2", "name": "Lab 201", "capacity": 30, "type": "lab"}
  ],
  "faculties": [
    {"id": "F1", "name": "Dr. Smith", "subjects": ["S1"], "available_times": [0,1,2,3,4,5,6,7,8,9]},
    {"id": "F2", "name": "Dr. Alice", "subjects": ["S2"], "available_times": [0,1,2,3,4,5,6,7,8,9]}
  ],
  "batches": [
    {"id": "B1", "name": "CSE 1st Year", "size": 40}
  ],
  "subjects": [
    {"id": "S1", "name": "Maths", "hours_per_week": 3, "allowed_rooms": ["R1"], "eligible_faculties": ["F1"]},
    {"id": "S2", "name": "Programming", "hours_per_week": 2, "allowed_rooms": ["R2"], "eligible_faculties": ["F2"]}
  ],
  "fixed_slots": [
    {"session_idx": 0, "timeslot": 0, "room": "R1", "faculty": "F1"}
  ]
}

generate_timetable(data, 5, 6, 1)