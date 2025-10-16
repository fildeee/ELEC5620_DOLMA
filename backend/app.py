from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message")
    conversation = data.get("conversation", [])

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # System role
    messages = [
        {
            "role": "system",
            "content": (
                "You are DOLMA, a friendly and intelligent personal assistant. "
                "Always respond helpfully and conversationally, even for repeated questions."
            ),
        }
    ]

    # Add trimmed context (only recent 6 messages)
    trimmed_history = [
        m for m in conversation if m["role"] in ["user", "assistant"]
    ][-6:]

    messages.extend(
        {"role": m["role"], "content": m["text"]} for m in trimmed_history
    )

    # Add the new message
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_completion_tokens=250
        )

        reply = response.choices[0].message.content.strip()

        # If reply is empty or too minimal, re-ask once
        if not reply or reply in ["...", "…", "Ok", "Okay"]:
            regen = client.chat.completions.create(
                model="gpt-5",
                messages=messages + [{"role": "user", "content": "Please elaborate."}],
                max_completion_tokens=250
            )
            reply = regen.choices[0].message.content.strip()

        return jsonify({"reply": reply})

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
