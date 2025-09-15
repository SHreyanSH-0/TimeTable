from flask import Flask, jsonify, request
import json
import os
from optimization_engine import generate_timetable

app = Flask(__name__)

from flask_cors import CORS
CORS(app)

DATA_FILE = os.path.join(os.path.dirname(__file__), "sample_data.json")
data_store = {}

@app.route("/api/sample-data/load", methods=["POST"])
def load_sample_data():
    global data_store
    with open(DATA_FILE, "r") as f:
        data_store = json.load(f)
    return jsonify({"status": "ok", "message": "Sample data loaded", "counts": {k: v for k,v in data_store.items()}})

@app.route("/api/generate", methods=["POST"])
def generate():
    global data_store
    if not data_store:
        return jsonify({"error": "No data loaded"}), 400
    
    payload = request.get_json(force=True)
    days = payload.get("days", 5)
    periods_per_day = payload.get("periods_per_day", 6)
    num_variants = payload.get("num_variants", 1)

    solutions, session_map = generate_timetable(data_store, days, periods_per_day, num_variants)
    return jsonify({"solutions": solutions, "sessions": session_map})

if __name__ == "__main__":
    app.run(debug=True)
