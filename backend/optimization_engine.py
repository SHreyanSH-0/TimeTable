import random

from models import Batch, Faculty

# def generate_timetable(data, days=5, periods_per_day=6, num_variants=1):
#     rooms = data["rooms"]
#     faculties = data["faculties"]
#     batches = data["batches"]
#     subjects = data["subjects"]
#     fixed_slots = data["fixed_slots"]

#     total_slots = days * periods_per_day
#     sessions = []

#     # Expand subjects into required sessions
#     for subj in subjects:
#         for b in batches:
#             for _ in range(subj["hours_per_week"]):
#                 sessions.append({
#                     "batch_id": b["id"],
#                     "subject_id": subj["id"],
#                     "faculty_id": random.choice(subj["eligible_faculties"]),
#                     "room_id": random.choice(subj["allowed_rooms"])
#                 })

#     # Map session_id -> session details for frontend
#     session_map = {i: sessions[i] for i in range(len(sessions))}

#     solutions = []
#     for _ in range(num_variants):
#         used_slots = set()
#         timetable = []
#         for sid, sess in session_map.items():
#             timeslot = random.randint(0, total_slots - 1)
#             while timeslot in used_slots:
#                 timeslot = random.randint(0, total_slots - 1)
#             used_slots.add(timeslot)
#             timetable.append([sid, timeslot, sess["room_id"], sess["faculty_id"]])
#         solutions.append(timetable)

#     return solutions, session_map


def generate_timetable(data, days=5, periods_per_day=6, num_variants=1):
    """
Smart Timetable Optimization Engine (prototype)

Usage:
1) Install ortools: pip install ortools
2) Run this script directly: python optimization_engine.py

This is a prototype intended to show a constraint programming approach using
OR-Tools CP-SAT. It creates session-level boolean assignment variables and
searches for multiple diverse, high-quality timetable variants.

Notes / limitations:
- Designed for clarity and extendability, not for extremely large instances.
- You should adapt data ingestion and output formatting to your web/backend.

"""
    from ortools.sat.python import cp_model
    from collections import defaultdict, namedtuple
    import random
    import itertools
    import math

    # ------------------------ Data models ------------------------

    # Times: represent as integers 0..T-1. Provide helper to map to day/period.
    class TimeTableUtils:
        def __init__(self, days=5, periods_per_day=8):
            self.days = days
            self.periods_per_day = periods_per_day
            self.T = days * periods_per_day

        def timeslot_to_day_period(self, t):
            day = t // self.periods_per_day
            period = t % self.periods_per_day
            return day, period

        def day_period_to_timeslot(self, day, period):
            return day * self.periods_per_day + period

    # ------------------------ Helper functions ------------------------

    def expand_sessions(batches, subjects):
        """
        For each (batch, subject) combination, create `hours_per_week` session entries.
        Each session represents one class instance that must be scheduled into a timeslot.
        Returns list of sessions where each is a dict with keys: id, batch_id, subject_id, size, allowed_rooms, eligible_faculties
        """
        sessions = []
        sid = 0
        for batch in batches:
            for subj in subjects:
                # assume every subject applies to all batches for which it is intended. In real system, subjects will be assigned per batch.
                # For prototype, schedule subject for every batch.
                for _ in range(subj.hours_per_week):
                    sessions.append({
                        'id': sid,
                        'batch_id': batch.id,
                        'subject_id': subj.id,
                        'size': batch.size,
                        'allowed_rooms': subj.allowed_rooms,
                        'eligible_faculties': subj.eligible_faculties,
                    })
                    sid += 1
        return sessions

    # ------------------------ Optimization Engine ------------------------

    def solve_timetables(rooms, faculties, batches, subjects, utils: TimeTableUtils, fixed_slots=None, max_classes_per_day=4, num_variants=2):
        """
        rooms: list of Room
        faculties: list of Faculty
        batches: list of Batch
        subjects: list of Subject
        utils: TimeTableUtils instance
        fixed_slots: list of FixedSlot (optional) to force specific session -> timeslot/room/faculty
        max_classes_per_day: soft/hard constraint for batch/faculty
        num_variants: how many different timetable variants to return (tries to diversify between variants)

        Returns list of solutions. Each solution is a list of assignments: (session_id, timeslot, room_id, faculty_id)
        """
        if fixed_slots is None:
            fixed_slots = []

        # Expand sessions
        sessions = expand_sessions(batches, subjects)
        S = len(sessions)
        T = utils.T
        R = len(rooms)

        # Map id->index for easier loops
        room_id_to_idx = {r.id: i for i, r in enumerate(rooms)}
        faculty_id_to_idx = {f.id: i for i, f in enumerate(faculties)}
        batch_id_to_obj = {b.id: b for b in batches}
        subj_id_to_obj = {s.id: s for s in subjects}

        # Precompute eligibility: for each session, which (room, faculty) are allowed
        eligible_room_idxs = {}
        eligible_faculty_idxs = {}
        for sess in sessions:
            rlist = [room_id_to_idx[rid] for rid in sess['allowed_rooms'] if rid in room_id_to_idx and rooms[room_id_to_idx[rid]].capacity >= sess['size']]
            flist = [faculty_id_to_idx[fid] for fid in sess['eligible_faculties'] if fid in faculty_id_to_idx]
            # If empty, allow any room with capacity and any faculty qualified for the subject (fallback)
            if not rlist:
                rlist = [i for i,r in enumerate(rooms) if r.capacity >= sess['size']]
            eligible_room_idxs[sess['id']] = rlist
            eligible_faculty_idxs[sess['id']] = flist

        # Convert fixed_slots into dict by session id
        fixed_map = {fs.session_idx: fs for fs in fixed_slots}

        solutions = []
        forbidden_solutions = []  # list of sets of true var tuples to forbid previously found solutions

        # We'll run iterative solves to obtain multiple variants
        for variant in range(num_variants):
            model = cp_model.CpModel()

            # Boolean assignment var: assign[(s,t,r,f)] = 1 if session s is assigned to timeslot t, room r, faculty f
            assign = {}
            for s in sessions:
                sid = s['id']
                for t in range(T):
                    for r_idx in eligible_room_idxs[sid]:
                        # For faculties, if eligible list is empty allow any faculty who can teach this subject
                        fac_idxs = eligible_faculty_idxs[sid] if eligible_faculty_idxs[sid] else list(faculty_id_to_idx.values())
                        for f_idx in fac_idxs:
                            # check faculty availability for timeslot t
                            fac = faculties[f_idx]
                            if t not in fac.available_times:
                                continue
                            var = model.NewBoolVar(f"a_s{sid}_t{t}_r{r_idx}_f{f_idx}")
                            assign[(sid, t, r_idx, f_idx)] = var

            # Constraint: each session assigned exactly once
            for s in sessions:
                sid = s['id']
                vars_for_session = [v for (ss,_,_,_), v in assign.items() if ss == sid]
                if not vars_for_session:
                    raise ValueError(f"No feasible assignment variables for session {sid}; check room/faculty availability and capacities")
                model.Add(sum(vars_for_session) == 1)

            # Constraint: no room double booking at same timeslot
            for t in range(T):
                for r_idx in range(R):
                    vars_room_time = [v for (ss, tt, rr, ff), v in assign.items() if tt == t and rr == r_idx]
                    if vars_room_time:
                        model.Add(sum(vars_room_time) <= 1)

            # Constraint: faculty can't teach >1 at same timeslot
            F = len(faculties)
            for t in range(T):
                for f_idx in range(F):
                    vars_fac_time = [v for (ss, tt, rr, ff), v in assign.items() if tt == t and ff == f_idx]
                    if vars_fac_time:
                        model.Add(sum(vars_fac_time) <= 1)

            # Constraint: batch can't attend >1 class at same timeslot
            for t in range(T):
                for b in batches:
                    vars_batch_time = [v for (ss, tt, rr, ff), v in assign.items() if tt == t and sessions[ss]['batch_id'] == b.id]
                    if vars_batch_time:
                        model.Add(sum(vars_batch_time) <= 1)

            # Constraint: max classes per day for faculty and batch (hard constraint)
            for day in range(utils.days):
                timeslots_that_day = [utils.day_period_to_timeslot(day, p) for p in range(utils.periods_per_day)]
                for f_idx in range(F):
                    vars_fac_day = [v for (ss, tt, rr, ff), v in assign.items() if ff == f_idx and tt in timeslots_that_day]
                    if vars_fac_day:
                        model.Add(sum(vars_fac_day) <= max_classes_per_day)
                for b in batches:
                    vars_batch_day = [v for (ss, tt, rr, ff), v in assign.items() if sessions[ss]['batch_id'] == b.id and tt in timeslots_that_day]
                    if vars_batch_day:
                        model.Add(sum(vars_batch_day) <= max_classes_per_day)

            # Fixed slots: force assignment
            for fs in fixed_slots:
                # session must be assigned to the exact timeslot/room/faculty
                sid = fs.session_idx
                t = fs.timeslot
                r_idx = room_id_to_idx.get(fs.room, None) if fs.room is not None else None
                f_idx = faculty_id_to_idx.get(fs.faculty, None) if fs.faculty is not None else None
                # Build list of variables for that exact combination
                matching_vars = []
                for (ss, tt, rr, ff), v in assign.items():
                    if ss == sid and tt == t and (r_idx is None or rr == r_idx) and (f_idx is None or ff == f_idx):
                        matching_vars.append(v)
                if not matching_vars:
                    raise ValueError(f"No variable matches fixed slot for session {sid}")
                model.Add(sum(matching_vars) == 1)

            # Soft objectives: try to
            # 1) minimize total "undesirable assignments" (e.g., assigning faculty in their less preferred periods)
            # For prototype, we randomly mark late periods as undesirable for faculty to demonstrate soft penalty concept.
            penalty_terms = []
            for (ss, tt, rr, ff), v in assign.items():
                fac = faculties[ff]
                day, period = utils.timeslot_to_day_period(tt)
                # example: discourage evening periods (period >= periods_per_day-2)
                if period >= utils.periods_per_day - 2:
                    w = 1
                    penalty_terms.append((w, v))
                # example: prefer assigning subject to labs or special room types; penalize if room type doesn't match
                subj_id = sessions[ss]['subject_id']
                subj = subj_id_to_obj[subj_id]
                room = rooms[rr]
                if subj.allowed_rooms and rr not in [room_id_to_idx[rid] for rid in subj.allowed_rooms]:
                    # if this room is not in allowed list, add mild penalty
                    penalty_terms.append((1, v))

            # Compose objective: minimize sum of penalties (weighted) and also try to balance faculty loads
            penalty_vars = []
            for w, var in penalty_terms:
                # model doesn't allow weighted bool in linear objective directly, so we create int var to represent penalty contribution
                p = model.NewIntVar(0, w, f"pen_{var.Name()}")
                model.Add(p == var * w)
                penalty_vars.append(p)

            # Faculty load balancing: minimize the variance of assigned classes across faculties (soft)
            load_vars = []
            for f_idx in range(F):
                load = model.NewIntVar(0, S, f"load_f{f_idx}")
                vars_fac = [v for (ss, tt, rr, ff), v in assign.items() if ff == f_idx]
                if vars_fac:
                    model.Add(load == sum(vars_fac))
                else:
                    model.Add(load == 0)
                load_vars.append(load)
            # compute average load as int
            avg_load_num = model.NewIntVar(0, S * F, "avg_load_num")
            model.Add(avg_load_num * 1 == sum(load_vars))  # avg_load_num will be sum(loads)
            # minimize sum of absolute deviations from mean is tricky; approximate by minimizing max_load - min_load
            max_load = model.NewIntVar(0, S, "max_load")
            min_load = model.NewIntVar(0, S, "min_load")
            model.AddMaxEquality(max_load, load_vars)
            model.AddMinEquality(min_load, load_vars)

            # Objective: weighted sum of penalties + spread (max-min)
            model.Minimize(sum(penalty_vars) * 10 + (max_load - min_load) * 5)

            # Forbid previously found solutions (to obtain diverse variants)
            for forb in forbidden_solutions:
                # forb is a list of tuples (sid,t,r,f) that were True in previous solution
                # Add constraint: sum(those vars) <= len(forb)-1  => at least one assignment must differ
                vars_to_forbid = []
                for tup in forb:
                    if tup in assign:
                        vars_to_forbid.append(assign[tup])
                if vars_to_forbid:
                    model.Add(sum(vars_to_forbid) <= len(vars_to_forbid) - 1)

            # Solve
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 30.0
            solver.parameters.num_search_workers = 8
            solver.parameters.maximize = False

            result = solver.Solve(model)
            if result not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                print(f"Variant {variant}: No feasible solution found")
                break

            # Collect solution assignments
            sol_assignment = []
            true_vars = []
            for (ss, tt, rr, ff), v in assign.items():
                if solver.Value(v) == 1:
                    sol_assignment.append((ss, tt, rooms[rr].id, faculties[ff].id))
                    true_vars.append((ss, tt, rr, ff))

            solutions.append(sol_assignment)
            forbidden_solutions.append(true_vars)

        return solutions

    # ------------------------ Pretty printing / sample data ------------------------

    def print_solution(sol, sessions, rooms, faculties, utils):
        """
        sol: list of tuples (session_id, timeslot, room_id, faculty_id)
        sessions: expanded sessions list
        """
        # map session->details
        by_batch = defaultdict(list)
        for sid, t, rid, fid in sol:
            sess = sessions[sid]
            day, period = utils.timeslot_to_day_period(t)
            by_batch[sess['batch_id']].append((sid, day, period, rid, fid))

        for batch_id, items in by_batch.items():
            print(f"Batch {batch_id} timetable:")
            for sid, day, period, rid, fid in sorted(items, key=lambda x:(x[1], x[2])):
                subj_id = sessions[sid]['subject_id']
                print(f"  Day {day} Period {period} -> Subject {subj_id}, Room {rid}, Faculty {fid}")
            print()


    if __name__ == '__main__':
        # Create sample data for demonstration
        utils = TimeTableUtils(days=5, periods_per_day=6)  # 30 timeslots

        #     rooms = data["rooms"]
    #     faculties = data["faculties"]
    #     batches = data["batches"]
    #     subjects = data["subjects"]
    #     fixed_slots = data["fixed_slots"]

        rooms = data["rooms"]
        # faculties with availability (all timeslots for simplicity but we can remove some)
        all_times = list(range(utils.T))
        faculties = data["faculties"]
        batches = data["batches"]
        # subjects: S0,S1,S2 with different hours/week and allowed rooms
        subjects = data["subjects"]

        # fixed_slots: empty for demo
        fixed_slots = data["fixed_slots"]

        # Solve for 2 variants
        solutions = solve_timetables(rooms, faculties, batches, subjects, utils, fixed_slots=fixed_slots, max_classes_per_day=3, num_variants=2)

        # Expand sessions used in solver to print nicely
        sessions = expand_sessions(batches, subjects)

        for i, sol in enumerate(solutions):
            print("\n=== Solution variant", i, "===")
            print_solution(sol, sessions, rooms, faculties, utils)

        print("Done")
