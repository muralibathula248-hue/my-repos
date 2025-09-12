from flask import Flask, request, jsonify, send_from_directory, render_template

import os
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # 🔑 Load variables from .env

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@app.route("/html")
def html_page():
    return render_template("index.html")  # or send_from_directory(".", "index.html")


@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json.get("message")
    if not user_msg:
        return jsonify({"error": "No message provided"}), 400

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": user_msg}
        ]
    )

    bot_reply = response.choices[0].message.content
    return jsonify({"reply": bot_reply})

if __name__ == "__main__":
    app.run(debug=True)
