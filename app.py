import os
import smtplib
import logging
from email.message import EmailMessage

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# --- Load environment variables ---
load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")
TO_EMAIL = os.getenv("TO_EMAIL") or GMAIL_USER

# --- Flask app ---
app = Flask(__name__)

# Allow requests FROM the frontend
CORS(
    app,
    resources={
        r"/proxy-message": {
            "origins": "https://ethanpervere.com"
        }
    }
)

# --- Rate limiting ---
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["5 per hour"]
)

limiter.init_app(app)

# --- Logging ---
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/error.log",
    level=logging.ERROR,
    format="%(asctime)s %(levelname)s %(message)s"
)

# --- Email sender ---
def send_email(name, email, message):
    msg = EmailMessage()
    msg["Subject"] = f"Portfolio Contact: {name}"
    msg["From"] = GMAIL_USER
    msg["To"] = TO_EMAIL
    msg["Reply-To"] = email
    msg.set_content(message)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        logging.error(f"SMTP error: {e}")
        return False

# --- API endpoint ---
@app.route("/proxy-message", methods=["POST"])
@limiter.limit("5 per hour")
def proxy_message():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    message = data.get("message", "").strip()

    if not name or not email or not message:
        return jsonify({"error": "Missing required fields"}), 400

    if len(message) < 10 or len(message) > 5000:
        return jsonify({"error": "Invalid message length"}), 400

    if not send_email(name, email, message):
        return jsonify({"error": "Failed to send email"}), 500

    return jsonify({"status": "Message sent"}), 200

# --- Run locally (Cloudflare Tunnel connects here) ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

@app.route("/ping")
def ping():
    return "pong", 200