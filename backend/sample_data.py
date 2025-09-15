def seed_sample_data(db):
    from models import Room, Faculty, Batch, Subject
    db.session.query(Room).delete()
    db.session.query(Faculty).delete()
    db.session.query(Batch).delete()
    db.session.query(Subject).delete()
    db.session.commit()

    rooms = [
        Room(id="R1", name="Room 1", capacity=50, type="lec"),
        Room(id="R2", name="Room 2", capacity=40, type="lec"),
        Room(id="L1", name="Lab 1", capacity=24, type="lab"),
    ]

    faculties = [
        Faculty(id="F1", name="Dr A", subjects=["S0","S1"], available_times=list(range(30))),
        Faculty(id="F2", name="Dr B", subjects=["S1","S2"], available_times=list(range(30))),
        Faculty(id="F3", name="Dr C", subjects=["S0","S2"], available_times=list(range(30))),
    ]

    batches = [
        Batch(id="B0", name="CSE-1", size=45),
        Batch(id="B1", name="ECE-1", size=28),
    ]

    subjects = [
        Subject(id="S0", name="Maths", hours_per_week=3, allowed_rooms=["R1","R2"], eligible_faculties=["F1","F3"]),
        Subject(id="S1", name="Physics", hours_per_week=2, allowed_rooms=["R1"], eligible_faculties=["F1","F2"]),
        Subject(id="S2", name="LabWork", hours_per_week=2, allowed_rooms=["L1"], eligible_faculties=["F2","F3"]),
    ]

    db.session.add_all(rooms + faculties + batches + subjects)
    db.session.commit()
