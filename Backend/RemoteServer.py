# === Jarvis Unified Remote Server ===
# Serves the web dashboard and provides API endpoints for remote control.

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from functools import wraps
from threading import Thread
from datetime import datetime
from dotenv import dotenv_values
import asyncio
import os
import sys
import json
import io
import logging
import base64
import tempfile
import edge_tts

# Fix import path for backend modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Backend.Automation import Automation
from Backend.Chatbot import ChatBot
from Backend.TextToSpeech import TextToSpeech
from Backend.RealtimeSearchEngine import RealtimesearchEngine
from Backend.Model import FirstLayerDMM
from Backend.SpaceAPI import space_client
from Backend.Scheduler import scheduler
from Backend.NavigationService import (
    update_phone_location, get_phone_location, set_home_location,
    get_home_location, geocode, reverse_geocode, get_route,
    get_traffic_summary, navigate_from_phone, navigate_home, where_am_i
)
from Frontend.GUI import (
    SetAssistantStatus,
    ShowTextToScreen,
    GetAssistantStatus,
    GetMicrophoneStatus,
    QueryModifier,
    AnswerModifier,
)

# ========== CONFIG ==========
env_vars = dotenv_values(".env")
REMOTE_TOKEN = env_vars.get("REMOTE_TOKEN", "jarvis2026")
Username = env_vars.get("Username", "User")
Assistantname = env_vars.get("Assistantname", "Jarvis")

# ========== APP INIT ==========
remote_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Frontend", "remote"))
app = Flask(__name__, static_folder=remote_dir, static_url_path="/static")
CORS(app)

# Suppress Flask request logging to keep console clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

# ========== IN-MEMORY STATE ==========
command_history = []
MAX_HISTORY = 50
latest_phone_frame = {"data": None, "timestamp": None}  # Phone camera frame


def add_to_history(command, result="success", detail=""):
    """Add a command to the history log."""
    entry = {
        "id": len(command_history) + 1,
        "command": command,
        "result": result,
        "detail": detail,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    command_history.insert(0, entry)
    if len(command_history) > MAX_HISTORY:
        command_history.pop()
    return entry


# ========== AUTH MIDDLEWARE ==========
def require_token(f):
    """Decorator to require Bearer token authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            token = request.args.get("token", "")

        if token != REMOTE_TOKEN:
            return jsonify({"error": "Unauthorized", "message": "Invalid or missing token"}), 401
        return f(*args, **kwargs)
    return decorated


# ========== HELPERS ==========
def run_async(coro):
    """Run an async coroutine in a new event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def run_in_thread(func, *args):
    """Run a function in a background thread."""
    thread = Thread(target=func, args=args, daemon=True)
    thread.start()
    return thread


async def _generate_base64_audio(text: str):
    """Generate TTS audio and return as base64 string."""
    if not text or not text.strip():
        return None
        
    voice = env_vars.get("AssistantVoice", "en-US-JennyNeural")
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            temp_path = temp_audio.name
            
        communicate = edge_tts.Communicate(text=text, voice=voice)
        await communicate.save(temp_path)
        
        with open(temp_path, "rb") as f:
            audio_data = f.read()
            
        os.remove(temp_path)
        return base64.b64encode(audio_data).decode("utf-8")
    except Exception as e:
        print(f"[Remote TTS Error] {e}")
        return None


# ========== ROUTES: Dashboard ==========
@app.route("/")
def serve_dashboard():
    """Serve the main dashboard HTML page."""
    return send_from_directory(remote_dir, "index.html")


@app.route("/style.css")
def serve_css():
    return send_from_directory(remote_dir, "style.css")


@app.route("/app.js")
def serve_js():
    return send_from_directory(remote_dir, "app.js")


# ========== ROUTES: API ==========

@app.route("/api/status", methods=["GET"])
@require_token
def api_status():
    """Get current Jarvis status."""
    try:
        assistant_status = GetAssistantStatus()
        mic_status = GetMicrophoneStatus()
    except Exception:
        assistant_status = "Available..."
        mic_status = "False"

    return jsonify({
        "status": "running",
        "assistant_status": assistant_status.strip(),
        "mic_active": mic_status.strip() == "True",
        "assistant_name": Assistantname,
        "username": Username,
    })


@app.route("/api/command", methods=["POST"])
@require_token
def api_command():
    """
    Process a natural language command through the full Jarvis pipeline.
    This goes through: DMM decision → appropriate handler (chat/search/automation/etc.)
    """
    data = request.get_json(force=True)
    cmd = str(data.get("command", "")).strip()

    if not cmd:
        return jsonify({"status": "error", "message": "No command provided"}), 400

    try:
        print(f"[Remote] Processing command: {cmd}")
        SetAssistantStatus("Thinking...")
        ShowTextToScreen(f"{Username} : {cmd}")

        # Run through the decision model
        decision = FirstLayerDMM(cmd)
        print(f"[Remote] Decision: {decision}")

        response_text = ""

        # Process each decision
        for item in decision:
            if item.startswith("general"):
                query_final = item.replace("general", "", 1).strip()
                response_text = ChatBot(QueryModifier(query_final))

            elif item.startswith("realtime"):
                query_final = item.replace("realtime", "", 1).strip()
                response_text = RealtimesearchEngine(QueryModifier(query_final))

            elif item.startswith("open") or item.startswith("close") or \
                 item.startswith("play") or item.startswith("system") or \
                 item.startswith("google search") or item.startswith("youtube search"):
                run_async(Automation([item]))
                response_text = f"Executed: {item}"

            elif item.startswith("content"):
                from Backend.Automation import Content
                topic = item.replace("content", "", 1).strip()
                response_text = Content(topic)

            elif item.startswith("exit"):
                response_text = "Goodbye!"

            else:
                response_text = f"Processed: {item}"

        if response_text:
            ShowTextToScreen(f"{Assistantname} : {response_text}")

        SetAssistantStatus("Available...")
        entry = add_to_history(cmd, "success", response_text)
        
        # Generate audio for the frontend to play
        audio_b64 = run_async(_generate_base64_audio(response_text)) if response_text else None

        return jsonify({
            "status": "success",
            "command": cmd,
            "decision": decision,
            "response": response_text,
            "audio_data": audio_b64,
            "history_entry": entry,
        })

    except Exception as e:
        SetAssistantStatus("Available...")
        print(f"[Remote Command Error] {e}")
        entry = add_to_history(cmd, "error", str(e))
        return jsonify({"status": "error", "message": str(e), "history_entry": entry}), 500


@app.route("/api/system", methods=["POST"])
@require_token
def api_system():
    """Execute a system command (mute, volume, brightness, screenshot, etc.)."""
    data = request.get_json(force=True)
    cmd = str(data.get("command", "")).strip()

    if not cmd:
        return jsonify({"status": "error", "message": "No command provided"}), 400

    # Map frontend button names to Automation.py System() command names
    CMD_MAP = {
        "mute": "mute",
        "unmute": "unmute",
        "volume_up": "volume up",
        "volume_down": "volume down",
        "brightness_up": "brightness up",
        "brightness_down": "brightness down",
        "screenshot": "take screenshot",
        "lock": "lock screen",
        "sleep": "sleep",
        "shutdown": "shutdown",
        "file_explorer": "open file explorer",
        "toggle_wifi": "toggle wifi",
        "toggle_bluetooth": "toggle bluetooth",
    }

    mapped_cmd = CMD_MAP.get(cmd, cmd.replace("_", " "))

    try:
        print(f"[Remote] System command: {cmd} -> {mapped_cmd}")
        system_cmd = f"system {mapped_cmd}"
        run_async(Automation([system_cmd]))
        entry = add_to_history(f"System: {mapped_cmd}", "success")
        return jsonify({"status": "success", "command": mapped_cmd, "history_entry": entry})
    except Exception as e:
        print(f"[Remote System Error] {e}")
        entry = add_to_history(f"System: {mapped_cmd}", "error", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/speak", methods=["POST"])
@require_token
def api_speak():
    """Make Jarvis speak text via TTS."""
    data = request.get_json(force=True)
    text = str(data.get("text", "")).strip()

    if not text:
        return jsonify({"status": "error", "message": "No text provided"}), 400

    try:
        print(f"[Remote] Speaking: {text}")
        SetAssistantStatus("Answering...")
        ShowTextToScreen(f"{Assistantname} : {text}")
        
        # Generate audio for the frontend instead of playing locally
        audio_b64 = run_async(_generate_base64_audio(text))
        
        add_to_history(f"Speak: {text}", "success")
        return jsonify({"status": "success", "text": text, "audio_data": audio_b64})
    except Exception as e:
        print(f"[Remote Speak Error] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
@require_token
def api_chat():
    """Chat with the Jarvis AI chatbot."""
    data = request.get_json(force=True)
    message = str(data.get("message", "")).strip()

    if not message:
        return jsonify({"status": "error", "message": "No message provided"}), 400

    try:
        print(f"[Remote] Chat: {message}")
        SetAssistantStatus("Thinking...")
        ShowTextToScreen(f"{Username} : {message}")

        response = ChatBot(QueryModifier(message))
        ShowTextToScreen(f"{Assistantname} : {response}")
        SetAssistantStatus("Available...")
        
        # Generate audio for the frontend
        audio_b64 = run_async(_generate_base64_audio(response))

        add_to_history(f"Chat: {message}", "success", response)
        return jsonify({"status": "success", "response": response, "audio_data": audio_b64})
    except Exception as e:
        SetAssistantStatus("Available...")
        print(f"[Remote Chat Error] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/open", methods=["POST"])
@require_token
def api_open():
    """Open an application."""
    data = request.get_json(force=True)
    app_name = str(data.get("app", "")).strip()

    if not app_name:
        return jsonify({"status": "error", "message": "No app name provided"}), 400

    try:
        print(f"[Remote] Opening: {app_name}")
        run_async(Automation([f"open {app_name}"]))
        add_to_history(f"Open: {app_name}", "success")
        return jsonify({"status": "success", "app": app_name})
    except Exception as e:
        print(f"[Remote Open Error] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/close", methods=["POST"])
@require_token
def api_close():
    """Close an application."""
    data = request.get_json(force=True)
    app_name = str(data.get("app", "")).strip()

    if not app_name:
        return jsonify({"status": "error", "message": "No app name provided"}), 400

    try:
        print(f"[Remote] Closing: {app_name}")
        run_async(Automation([f"close {app_name}"]))
        add_to_history(f"Close: {app_name}", "success")
        return jsonify({"status": "success", "app": app_name})
    except Exception as e:
        print(f"[Remote Close Error] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/screenshot", methods=["GET"])
@require_token
def api_screenshot():
    """Take a screenshot and return it as an image."""
    try:
        import pyautogui
        screenshot = pyautogui.screenshot()
        img_buffer = io.BytesIO()
        screenshot.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        add_to_history("Screenshot", "success")
        return send_file(img_buffer, mimetype="image/png", download_name="screenshot.png")
    except Exception as e:
        print(f"[Remote Screenshot Error] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/history", methods=["GET"])
@require_token
def api_history():
    """Get recent command history."""
    return jsonify({"history": command_history})


@app.route("/api/search", methods=["POST"])
@require_token
def api_search():
    """Perform a realtime search."""
    data = request.get_json(force=True)
    query = str(data.get("query", "")).strip()

    if not query:
        return jsonify({"status": "error", "message": "No query provided"}), 400

    try:
        print(f"[Remote] Search: {query}")
        SetAssistantStatus("Searching...")
        result = RealtimesearchEngine(QueryModifier(query))
        SetAssistantStatus("Available...")
        add_to_history(f"Search: {query}", "success", result)
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        SetAssistantStatus("Available...")
        print(f"[Remote Search Error] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ========== SPACE APIs ==========

@app.route("/api/space/apod", methods=["GET"])
@require_token
def api_space_apod():
    data = space_client.get_apod()
    return jsonify({"status": "success", "data": data})

@app.route("/api/space/asteroids", methods=["GET"])
@require_token
def api_space_asteroids():
    data = space_client.get_asteroid_threats()
    return jsonify({"status": "success", "data": data})

@app.route("/api/space/telescope", methods=["GET"])
@require_token
def api_space_telescope():
    telescope = request.args.get("telescope", "jwst")
    data = space_client.get_telescope_image(telescope)
    return jsonify({"status": "success", "data": data})

@app.route("/api/space/launches", methods=["GET"])
@require_token
def api_space_launches():
    data = space_client.get_upcoming_launches()
    return jsonify({"status": "success", "data": data})


# ========== LOCATION & NAVIGATION APIs ==========

@app.route("/api/location", methods=["POST"])
@require_token
def api_update_location():
    """Phone sends its GPS coordinates."""
    data = request.get_json(force=True)
    lat = data.get("lat")
    lon = data.get("lon")
    accuracy = data.get("accuracy")
    if lat is None or lon is None:
        return jsonify({"status": "error", "message": "lat and lon required"}), 400
    update_phone_location(float(lat), float(lon), accuracy)
    return jsonify({"status": "success", "message": "Location updated"})

@app.route("/api/location", methods=["GET"])
@require_token
def api_get_location():
    """Get latest phone location."""
    return jsonify({"status": "success", "data": get_phone_location()})

@app.route("/api/whereami", methods=["GET"])
@require_token
def api_where_am_i():
    """Get human-readable description of phone location."""
    result = where_am_i()
    if "error" in result:
        return jsonify({"status": "error", "message": result["error"]}), 400
    return jsonify({"status": "success", "data": result})

@app.route("/api/navigate", methods=["POST"])
@require_token
def api_navigate():
    """Navigate from phone to a destination."""
    data = request.get_json(force=True)
    destination = data.get("destination", "").strip()
    if not destination:
        return jsonify({"status": "error", "message": "Destination required"}), 400
    result = navigate_from_phone(destination)
    if "error" in result:
        return jsonify({"status": "error", "message": result["error"]}), 400
    add_to_history(f"Navigate to: {destination}", "success", f"{result['distance_km']}km, {result['duration_min']}min")
    return jsonify({"status": "success", "data": result})

@app.route("/api/navigate/home", methods=["POST"])
@require_token
def api_navigate_home():
    """Navigate from phone back to home (laptop location)."""
    result = navigate_home()
    if "error" in result:
        return jsonify({"status": "error", "message": result["error"]}), 400
    add_to_history("Navigate home", "success", f"{result['distance_km']}km, {result['duration_min']}min")
    return jsonify({"status": "success", "data": result})

@app.route("/api/traffic", methods=["POST"])
@require_token
def api_traffic():
    """Get traffic + ETA + weather for a route."""
    data = request.get_json(force=True)
    destination = data.get("destination", "").strip()
    if not destination:
        return jsonify({"status": "error", "message": "Destination required"}), 400
    phone = get_phone_location()
    if phone["lat"] is None:
        return jsonify({"status": "error", "message": "Phone GPS not available"}), 400
    result = get_traffic_summary({"lat": phone["lat"], "lon": phone["lon"]}, destination)
    if "error" in result:
        return jsonify({"status": "error", "message": result["error"]}), 400
    return jsonify({"status": "success", "data": result})


# ========== PHONE CAMERA APIs ==========

@app.route("/api/camera/frame", methods=["POST"])
@require_token
def api_camera_frame():
    """Phone sends a camera frame (base64 JPEG)."""
    data = request.get_json(force=True)
    frame_data = data.get("frame")
    if not frame_data:
        return jsonify({"status": "error", "message": "No frame data"}), 400
    latest_phone_frame["data"] = frame_data
    latest_phone_frame["timestamp"] = datetime.now().isoformat()
    return jsonify({"status": "success"})

@app.route("/api/camera/analyze", methods=["POST"])
@require_token
def api_camera_analyze():
    """Analyze a phone camera frame with YOLO + optional LLM question."""
    data = request.get_json(force=True)
    frame_b64 = data.get("frame", "")
    question = data.get("question", "What objects do you see?")
    
    if not frame_b64:
        return jsonify({"status": "error", "message": "No frame data"}), 400
    
    try:
        import cv2
        import numpy as np
        from ultralytics import YOLO
        
        # Decode base64 to image
        img_bytes = base64.b64decode(frame_b64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({"status": "error", "message": "Invalid image"}), 400
        
        # Run YOLO detection
        model = YOLO("yolov8x.pt")
        results = model(frame, verbose=False)
        
        detected = []
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                name = model.names[cls_id]
                if conf > 0.5:
                    detected.append({"name": name, "confidence": round(conf, 2)})
        
        # Build response
        obj_names = [d["name"] for d in detected]
        summary = f"I can see: {', '.join(set(obj_names))}" if obj_names else "No objects detected."
        
        # Generate audio response
        audio_data = None
        try:
            voice = env_vars.get("AssistantVoice", "en-US-JennyNeural")
            communicate = edge_tts.Communicate(summary, voice)
            audio_bytes = b""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            async def get_audio():
                nonlocal audio_bytes
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_bytes += chunk["data"]
            loop.run_until_complete(get_audio())
            loop.close()
            audio_data = base64.b64encode(audio_bytes).decode("utf-8")
        except Exception as e:
            print(f"[Camera Analyze TTS Error] {e}")
        
        return jsonify({
            "status": "success",
            "objects": detected,
            "summary": summary,
            "audio_data": audio_data
        })
    except Exception as e:
        print(f"[Camera Analyze Error] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/camera/stream", methods=["GET"])
@require_token
def api_camera_stream():
    """Get the latest phone camera frame."""
    if latest_phone_frame["data"]:
        return jsonify({"status": "success", "data": latest_phone_frame})
    return jsonify({"status": "error", "message": "No phone camera frame available"}), 404


# ========== SERVER RUNNER ==========
def _start_ngrok(port):
    import subprocess, time, requests
    try:
        ngrok_path = os.path.join(os.path.dirname(__file__), "ngrok.exe")
        # Use https://localhost:port since the local server uses ssl_context='adhoc'
        subprocess.Popen([ngrok_path, "http", f"https://localhost:{port}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(4)
        res = requests.get('http://localhost:4040/api/tunnels')
        url = res.json()['tunnels'][0]['public_url']
        print(f"  Global:  {url}")
        print(f"{'='*55}\n")
    except Exception as e:
        pass # ngrok might already be running or blocked, fail silently

def start_remote_server(port=5000):
    """Start the remote server in the current thread."""
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    # Set home location from laptop's IP-based coordinates
    try:
        loc = space_client.get_location()
        set_home_location(loc["lat"], loc["lon"])
        print(f"  [+] Home location set to: {loc['city']} ({loc['lat']}, {loc['lon']})")
    except Exception as e:
        print(f"  [!] Could not set home location: {e}")

    print(f"\n{'='*55}")
    print(f"  [+] F.R.I.D.A.Y. REMOTE DASHBOARD")
    print(f"{'='*55}")
    print(f"  Local:   https://localhost:{port}")
    print(f"  Network: https://{local_ip}:{port}")
    print(f"  Token:   {REMOTE_TOKEN}")
    print(f"  Generating global link... Please wait.")

    # Start the background tasks
    scheduler.start()
    
    import threading
    threading.Thread(target=_start_ngrok, args=(port,), daemon=True).start()

    # Use ssl_context='adhoc' to generate a self-signed certificate for HTTPS
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, ssl_context='adhoc')


if __name__ == "__main__":
    start_remote_server()
