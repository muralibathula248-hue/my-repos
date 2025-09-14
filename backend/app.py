from flask import Flask, request, jsonify, render_template
import os
from flask_cors import CORS
from dotenv import load_dotenv

# Load API keys from .env
load_dotenv()

# OpenAI
from openai import OpenAI
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Gemini
import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Flask setup
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# Serve HTML UI
@app.route("/")
def home():
    return render_template("index.html")

# Chat route
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        user_msg = data.get("message")
        provider = data.get("provider", "openai")  # default OpenAI

        if not user_msg:
            return jsonify({"error": "No message provided"}), 400

        reply = None

        # 🔹 OpenAI
        if provider == "openai":
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant."},
                    {"role": "user", "content": user_msg}
                ]
            )
            reply = response.choices[0].message.content

        # 🔹 Gemini
        elif provider == "gemini":
            model = genai.GenerativeModel("gemini-pro")
            response = model.generate_content(user_msg)
            reply = response.text

        else:
            return jsonify({"error": "Unknown provider"}), 400

        return jsonify({"reply": reply, "provider": provider})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
