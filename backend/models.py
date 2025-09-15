from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Room(db.Model):
    __tablename__ = "rooms"
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String, nullable=True)

class Faculty(db.Model):
    __tablename__ = "faculties"
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    subjects = db.Column(db.ARRAY(db.String), nullable=False)
    available_times = db.Column(db.ARRAY(db.Integer), nullable=False)

class Batch(db.Model):
    __tablename__ = "batches"
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    size = db.Column(db.Integer, nullable=False)

class Subject(db.Model):
    __tablename__ = "subjects"
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    hours_per_week = db.Column(db.Integer, nullable=False)
    allowed_rooms = db.Column(db.ARRAY(db.String), nullable=True)
    eligible_faculties = db.Column(db.ARRAY(db.String), nullable=True)
