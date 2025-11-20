#!/usr/bin/env python3
# app.py — FINAL VERSION (Clean, stable, no flooding)

from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO
import sqlite3
import time
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

DB_FILE = "access_store.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER,
            uid INTEGER,
            filename TEXT,
            action TEXT,
            decision TEXT,
            probability REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

def save_event(data):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO events (timestamp, uid, filename, action, decision, probability)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data["timestamp"],
        data["uid"],
        data["filename"],
        data["action"],
        data["decision"],
        data["probability"],
    ))
    conn.commit()
    conn.close()

# -------------------------------------------------------------------
# ROUTES
# -------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

# ------------- MAIN INGEST EVENT ROUTE -------------------

@app.route('/ingest_event', methods=['POST'])
def ingest_event():
    data = request.json

    # Prevent dashboard spam:
    current_key = f"{data['uid']}-{data['filename']}-{data['action']}"
    last_key = getattr(app, "last_event", None)

    if last_key == current_key:
        return "ok", 200  # Ignore exact duplicates

    app.last_event = current_key

    save_event(data)

    # NEW: SocketIO emit FIX (no broadcast=True)
    socketio.emit('new_event', data)

    return "ok", 200

# ------------- STATS API -------------------

@app.route("/api/stats")
def stats_api():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Count decision types
    cur.execute("SELECT decision, COUNT(*) FROM events GROUP BY decision")
    decision_counts = {row[0]: row[1] for row in cur.fetchall()}

    # Count actions
    cur.execute("SELECT action, COUNT(*) FROM events GROUP BY action")
    action_counts = {row[0]: row[1] for row in cur.fetchall()}

    # Last 50 events
    cur.execute("""
        SELECT timestamp, uid, filename, action, decision, probability
        FROM events ORDER BY id DESC LIMIT 50
    """)
    rows = cur.fetchall()
    conn.close()

    recent = []
    for r in rows:
        recent.append({
            "timestamp": r[0],
            "uid": r[1],
            "filename": r[2],
            "action": r[3],
            "decision": r[4],
            "probability": r[5],
        })

    return jsonify({
        "decision_counts": decision_counts,
        "action_counts": action_counts,
        "recent": recent,
    })

# ------------- TOP FILES API -------------------

@app.route("/api/top_files")
def top_files_api():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT filename, COUNT(*) AS c
        FROM events
        GROUP BY filename
        ORDER BY c DESC
        LIMIT 10
    """)
    rows = cur.fetchall()
    conn.close()

    return jsonify([{"filename": r[0], "count": r[1]} for r in rows])

# -------------------------------------------------------------------
# START SERVER
# -------------------------------------------------------------------

if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5000)