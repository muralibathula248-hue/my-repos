# backend/app.py
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import uuid
import sqlite3

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import openai

# load config
load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_KEY:
    print("WARNING: OPENAI_API_KEY not set in .env")

openai.api_key = OPENAI_KEY

# DB file (in backend folder)
DB_PATH = os.path.join(os.path.dirname(__file__), "conversations.db")

# logging
LOG_FILE = os.path.join(os.path.dirname(__file__), "bot.log")
logger = logging.getLogger("ai-bot")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=3)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)

# flask app
app = Flask(__name__)
CORS(app)

# DB helpers
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
      CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        role TEXT,
        content TEXT,
        created_at TEXT
      )
    """)
    conn.commit()
    conn.close()

def save_message(session_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
              (session_id, role, content, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_history(session_id, limit=20):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?", (session_id, limit))
    rows = c.fetchall()
    conn.close()
    # return chronological
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def clear_history(session_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

# initialize DB
init_db()

# endpoints
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "AI Support Bot (improved) is running 🚀"})

@app.route("/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True)
    user_message = body.get("message", "").strip()
    session_id = body.get("session_id") or str(uuid.uuid4())

    logger.info("chat request session=%s message=%s", session_id, user_message[:200])

    if not user_message:
        return jsonify({"error": "empty message"}), 400
    if len(user_message) > 8000:
        return jsonify({"error": "message too long"}), 400

    # save user message
    save_message(session_id, "user", user_message)

    # build messages list: system message + recent history
    system_msg = {"role": "system", "content": "You are a helpful AI support assistant."}
    history = get_history(session_id, limit=10)  # last 10 pairs
    messages = [system_msg] + history + [{"role": "user", "content": user_message}]

    try:
        # call OpenAI
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        bot_reply = response.choices[0].message.content
    except Exception as e:
        logger.exception("OpenAI call failed")
        return jsonify({"error": "OpenAI request failed: " + str(e)}), 502

    # save assistant message
    save_message(session_id, "assistant", bot_reply)

    logger.info("reply session=%s len=%d", session_id, len(bot_reply))
    return jsonify({"reply": bot_reply, "session_id": session_id})

@app.route("/history", methods=["GET"])
def history():
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error":"session_id required"}), 400
    return jsonify({"history": get_history(session_id, limit=100)})

@app.route("/clear_session", methods=["POST"])
def clear_session():
    body = request.get_json(force=True)
    session_id = body.get("session_id")
    if not session_id:
        return jsonify({"error":"session_id required"}), 400
    clear_history(session_id)
    logger.info("cleared session %s", session_id)
    return jsonify({"ok": True})

if __name__ == "__main__":
    # dev server (use gunicorn for production)
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
