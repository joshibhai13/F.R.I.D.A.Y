# === Jarvis Unified Remote Server (server.py) ===
from flask import Flask, request, jsonify, send_from_directory
from threading import Thread
import os, time, sys
import pygame
import asyncio
import edge_tts
from dotenv import dotenv_values

# Fix path for backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from TextToSpeech import TextToSpeech
from SpeechToText import SpeechRecognition

frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'Frontend'))
app = Flask(__name__, static_folder=frontend_path, static_url_path='')


# ========== CONFIG ==========
env_vars = dotenv_values(".env")
AssistantVoice = env_vars.get("AssistantVoice", "en-US-GuyNeural")
AUDIO_FILE = "Data/speech.mp3"

# ========== INIT ==========
last_audio_play_time = 0

# ========== HELPERS ==========
def stop_audio():
    try:
        pygame.mixer.music.stop()
        pygame.mixer.quit()
    except:
        pass

async def text_to_speech(text):
    global last_audio_play_time
    if os.path.exists(AUDIO_FILE):
        os.remove(AUDIO_FILE)
    communicate = edge_tts.Communicate(text, voice=AssistantVoice)
    await communicate.save(AUDIO_FILE)
    pygame.mixer.init()
    pygame.mixer.music.load(AUDIO_FILE)
    pygame.mixer.music.play()
    last_audio_play_time = time.time()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

def speak(text):
    print(f"Jarvis: {text}")
    asyncio.run(text_to_speech(text))

def run_in_thread(func, *args):
    thread = Thread(target=func, args=args)
    thread.start()

# ========== ROUTES ==========
@app.route("/")
def index():
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Frontend"))
    return send_from_directory(os.path.abspath("Frontend"), "index.html")


# @app.route("/control")
# def control_ui():
#     frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Frontend"))
#     return send_from_directory(os.path.abspath("Frontend"), "index.html")




@app.route("/speak", methods=["POST"])
def api_speak():
    data = request.json
    text = data.get("text")
    if not text:
        return jsonify({"error": "Missing 'text' field"}), 400
    run_in_thread(speak, text)
    return jsonify({"status": "Speaking", "text": text})

@app.route("/listen", methods=["GET"])
def api_listen():
    text = SpeechRecognition()
    return jsonify({"transcription": text})

@app.route("/status")
def status():
    return jsonify({"Jarvis": "Running"})

@app.route("/command", methods=["POST"])
def api_command():
    data = request.json
    command = data.get("text", "").lower()
    if not command:
        return jsonify({"error": "Missing 'text' field"}), 400

    def handle_command():
        speak(f"Executing command: {command}")
        if "camera" in command:
            os.system("start python Backend/Camera/camera.py")
        elif "gesture" in command:
            os.system("start python Backend/Camera/gesture_detector.py")
        elif "shutdown" in command:
            speak("Shutting down system.")
            os.system("shutdown /s /t 1")
        else:
            speak("Command not recognized.")

    run_in_thread(handle_command)
    return jsonify({"status": "Command received", "text": command})

@app.route("/shutdown", methods=["POST"])
def api_shutdown():
    def shutdown_now():
        speak("System will shut down now.")
        os.system("shutdown /s /t 1")
    run_in_thread(shutdown_now)
    return jsonify({"status": "Shutting down"})

@app.route("/camera", methods=["POST"])
def api_camera():
    run_in_thread(os.system, "start python Backend/Camera/camera.py")
    return jsonify({"status": "Camera activated"})

@app.route("/gesture", methods=["POST"])
def api_gesture():
    run_in_thread(os.system, "start python Backend/Camera/gesture_detector.py")
    return jsonify({"status": "Gesture detection activated"})

# ========== SERVER ==========
if __name__ == "__main__":
    print("[INFO] Starting Jarvis server...")
    app.run(host="0.0.0.0", port=5000)
