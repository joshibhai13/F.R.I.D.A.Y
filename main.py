import sys
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from Frontend.GUI import (
    GraphicalUserInterface,
    SetAssistantStatus,
    ShowTextToScreen,
    TempDirectoryPath,
    SetMicrophoneStatus,
    AnswerModifier,
    QueryModifier,
    GetMicrophoneStatus,
    GetAssistantStatus
)

from Backend.Model import FirstLayerDMM
from Backend.RealtimeSearchEngine import RealtimesearchEngine
from Backend.Automation import (
    Automation, Content, get_ip_address, open_support, WikipediaSearch,
    WriteNote, ShowNotes, ReadPdf, HowToMode, FlipCoin,
    SendWhatsAppMessage, SendEmail, ChangeWindow, SleepAssistant
)
from Backend.SpeechToText import SpeechRecognition
from Backend.Chatbot import ChatBot
from Backend.TextToSpeech import TextToSpeech, StopSpeaking

from Backend.RemoteServer import start_remote_server
from Backend.NavigationService import where_am_i, navigate_home, navigate_from_phone, get_traffic_summary, get_phone_location

from dotenv import dotenv_values
from asyncio import run
from time import sleep

import subprocess
import threading
import warnings
import json
import os
import sys

# Suppress Pydantic deprecation warnings from Cohere
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*__fields__.*")


# -------------------- Config -------------------- #
env_vars = dotenv_values(".env")
Username = env_vars.get("Username", "User")
Assistantname = env_vars.get("Assistantname", "Jarvis")

DefaultMessage = f"""{Username} : Hello {Assistantname}, How are You?
{Assistantname} : Welcome {Username}. I am doing well. How may I help you?
"""

subprocesses = []
image_gen_process = None
camera_process = None

Functions = [
    "open",
    "close",
    "play",
    "system",
    "content",
    "google search",
    "youtube search",
    "generate image"
]


# -------------------- Intro -------------------- #
def advanced_startup_greeting():
    import datetime
    from Backend.SpaceAPI import space_client
    from Backend.Automation import GroqAPIKey
    
    hour = datetime.datetime.now().hour
    if hour < 12: greeting = "Good morning"
    elif hour < 18: greeting = "Good afternoon"
    else: greeting = "Good evening"
    
    weather = space_client.get_weather_data()
    city = weather.get("city", "your current location") if weather else "Unknown"
    temp = weather.get("temp", "unknown") if weather else "unknown"
    condition = weather.get("condition", "unknown") if weather else "unknown"
    precip = weather.get("precipitation", 0) if weather else 0
    
    clothes = "casual indoor clothing"
    if weather and type(temp) in (int, float):
        if temp < 15: clothes = "a warm jacket or sweater"
        elif temp > 30: clothes = "light, breathable summer clothing"
        else: clothes = "comfortable casual wear"
        if precip > 0.5: clothes += " and an umbrella or raincoat"
        
    last_topic = ""
    try:
        log_data = ReadChatLogJson()
        if len(log_data) >= 2:
            last_topic = log_data[-2].get("content", "")
    except:
        pass

    prompt = (f"Write a short, engaging, 3-sentence voice assistant startup greeting. "
              f"The assistant's name is {Assistantname}. "
              f"Say '{greeting}'. Mention the user is in {city}, it's {temp} degrees and {condition}. "
              f"Suggest wearing {clothes}. "
              f"End by asking 'What's on your mind today, or should we continue our previous conversation about \"{last_topic}\"?'")
              
    try:
        from groq import Groq
        groq_client = Groq(api_key=GroqAPIKey)
        completion = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "system", "content": f"You are {Assistantname}, a highly intelligent AI assistant."}, {"role": "user", "content": prompt}],
            temperature=0.7, max_tokens=150
        )
        msg = completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Greeting Generation Error: {e}")
        msg = f"{greeting}! I am {Assistantname}. You are in {city}, where it is currently {temp} degrees and {condition}. I recommend wearing {clothes}. What's on your mind today, or should we continue our previous conversation about '{last_topic}'?"
        
    print(f"\n[STARTUP] {msg}\n")
    # Show on GUI and speak
    ShowTextToScreen(f"{Assistantname} : {msg}")
    TextToSpeech(msg)


# -------------------- Chat/UI Helpers -------------------- #
def ShowDefaultChatIfNoChats():
    os.makedirs("Data", exist_ok=True)

    chatlog_path = r"Data\ChatLog.json"
    if not os.path.exists(chatlog_path):
        with open(chatlog_path, "w", encoding="utf-8") as f:
            json.dump([], f, indent=4)

    with open(chatlog_path, "r", encoding="utf-8") as file:
        content = file.read().strip()

    if len(content) < 5:
        with open(TempDirectoryPath("Database.data"), "w", encoding="utf-8") as file:
            file.write("")

        with open(TempDirectoryPath("Responses.data"), "w", encoding="utf-8") as file:
            file.write(DefaultMessage)


def ReadChatLogJson():
    chatlog_path = r"Data\ChatLog.json"
    if not os.path.exists(chatlog_path):
        with open(chatlog_path, "w", encoding="utf-8") as file:
            json.dump([], file, indent=4)

    with open(chatlog_path, "r", encoding="utf-8") as file:
        return json.load(file)


def ChatLogIntegeration():
    json_data = ReadChatLogJson()
    formatted_chatlog = ""

    for entry in json_data:
        if entry["role"] == "user":
            formatted_chatlog += f"{Username}: {entry['content']}\n"
        elif entry["role"] == "assistant":
            formatted_chatlog += f"{Assistantname}: {entry['content']}\n"

    with open(TempDirectoryPath("Database.data"), "w", encoding="utf-8") as file:
        file.write(AnswerModifier(formatted_chatlog))


def ShowChatsOnGui():
    with open(TempDirectoryPath("Database.data"), "r", encoding="utf-8") as file:
        data = file.read()

    if len(str(data)) > 0:
        lines = data.split("\n")
        result = "\n".join(lines)

        with open(TempDirectoryPath("Responses.data"), "w", encoding="utf-8") as file:
            file.write(result)


def InitialExecution():
    SetMicrophoneStatus("True")
    with open(TempDirectoryPath('Camera.data'), 'w') as f:
        f.write("False")
    ShowTextToScreen("")
    ShowDefaultChatIfNoChats()
    ChatLogIntegeration()


InitialExecution()


def CloseAndExit(answer: str = "Goodbye sir, have a great day!"):
    """Signals the GUI window to close, plays farewell speech with strict safety timeout, and terminates the process."""
    ShowTextToScreen(f"{Assistantname} : {answer}")
    SetAssistantStatus("Goodbye...")

    # 1. Signal GUI window via Exit.data
    try:
        with open(TempDirectoryPath('Exit.data'), 'w', encoding='utf-8') as f:
            f.write("True")
    except Exception:
        pass

    # 2. Speak farewell with strict timeout (never hangs exit)
    try:
        def speak_farewell():
            try:
                TextToSpeech(answer)
            except Exception:
                pass

        t = threading.Thread(target=speak_farewell, daemon=True)
        t.start()
        t.join(timeout=1.8)
    except Exception:
        pass

    # 3. Terminate all background subprocesses
    for p in subprocesses:
        try:
            p.terminate()
        except Exception:
            pass

    # 4. Force terminate on Windows
    try:
        import ctypes
        ctypes.windll.kernel32.TerminateProcess(ctypes.windll.kernel32.GetCurrentProcess(), 0)
    except Exception:
        pass
    os._exit(0)


# -------------------- Main Execution -------------------- #
def MainExecution(override_query: str = None):
    from_voice = False

    if override_query:
        query = override_query.strip()
    else:
        StopSpeaking()
        SetAssistantStatus("Listening...")
        query = SpeechRecognition()
        from_voice = True

    if not query or not str(query).strip() or str(query).strip(".!? ") == "" or str(query).lower().strip(".!? ") in ["the", "you", "a", "an"]:
        SetAssistantStatus("Available...")
        return False

    # Check if a typed command arrived while listening: if so, prioritize the typed command and discard noise
    cmd_file = TempDirectoryPath('UserCommand.data')
    if from_voice and os.path.exists(cmd_file):
        try:
            with open(cmd_file, "r", encoding="utf-8") as f:
                typed = f.read().strip()
            if typed:
                os.remove(cmd_file)
                query = typed
                from_voice = False
        except Exception:
            pass

    # Immediately mute microphone during processing and TTS to prevent self-hearing / double commands
    SetMicrophoneStatus("False")

    try:
        return _dispatch_execution(query, from_voice=from_voice)
    finally:
        SetAssistantStatus("Available...")
        sleep(0.3)
        SetMicrophoneStatus("True")


def _dispatch_execution(query: str, from_voice: bool = True):
    global image_gen_process
    global camera_process

    task_execution = False
    image_execution = False
    image_generation_query = ""

    if from_voice:
        ShowTextToScreen(f"{Username} : {query}")

    # -------- Immediate Exit / Goodbye Detection -------- #
    clean_q = query.lower().strip().rstrip(".!? ")
    exit_words = {
        "bye", "goodbye", "good bye", "exit", "quit", "tata", "alvida",
        "close assistant", "stop assistant", "bye friday", "goodbye friday",
        "bye jarvis", "goodbye jarvis", "band ho jao", "shut down", "shutdown",
        "close yourself", "terminate", "tata bye bye", "bye bye", "see you later"
    }
    if (clean_q in exit_words or 
        any(w in clean_q for w in ["goodbye", "good bye", "bye bye", "alvida", "tata bye"]) or
        any(clean_q.startswith(p) for p in ["bye ", "goodbye ", "good bye ", "exit ", "quit "]) or 
        any(clean_q.endswith(p) for p in [" bye", " goodbye", " good bye"])):
        CloseAndExit("Goodbye sir, have a great day!")

    SetAssistantStatus("Thinking...")

    decision = FirstLayerDMM(query)

    print("")
    print(f"Decision: {decision}")
    print("")

    # Check if decision contains exit
    if any(i == "exit" or i.startswith("exit") for i in decision):
        CloseAndExit("Goodbye sir, have a great day!")

    has_general = any(i.startswith("general") for i in decision)
    has_realtime = any(i.startswith("realtime") for i in decision)

    merged_query = " and ".join(
        [" ".join(i.split()[1:]) for i in decision if i.startswith("general") or i.startswith("realtime")]
    ).strip()

    # -------- Image generation detection -------- #
    for item in decision:
        if item.startswith("generate image"):
            image_generation_query = item.replace("generate image", "").strip()
            if image_generation_query:
                image_execution = True

    # -------- Automation commands -------- #
    automation_commands = [
        q for q in decision
        if not q.startswith("content")
        and not q.startswith("generate image")
        and not q.startswith("general")
        and not q.startswith("realtime")
        and not q.startswith("camera")
        and not q.startswith("switch camera")
        and not q.startswith("learn face")
        and not q.startswith("close camera")
        and not q.startswith("exit")
        and not q.startswith("where am i")
        and not q.startswith("navigate")
        and not q.startswith("traffic to")
        and not q.startswith("ip address")
        and not q.startswith("support")
        and not q.startswith("wikipedia search")
        and not q.startswith("write note")
        and not q.startswith("show notes")
        and not q.startswith("read pdf")
        and not q.startswith("how to")
        and not q.startswith("toss coin")
        and not q.startswith("send whatsapp message")
        and not q.startswith("send email")
        and not q.startswith("change window")
        and not q.startswith("sleep now")
    ]

    if automation_commands:
        try:
            # Immediate responsive visual & verbal feedback
            for cmd in automation_commands:
                if cmd.startswith("open "):
                    target = cmd.replace("open ", "", 1).strip()
                    ack = f"Opening {target}."
                    ShowTextToScreen(f"{Assistantname} : {ack}")
                    SetAssistantStatus("Answering...")
                    threading.Thread(target=TextToSpeech, args=(ack,), daemon=True).start()
                elif cmd.startswith("play "):
                    target = cmd.replace("play ", "", 1).strip()
                    ack = f"Playing {target} on YouTube."
                    ShowTextToScreen(f"{Assistantname} : {ack}")
                    SetAssistantStatus("Answering...")
                    threading.Thread(target=TextToSpeech, args=(ack,), daemon=True).start()
                elif cmd.startswith("close "):
                    target = cmd.replace("close ", "", 1).strip()
                    ack = f"Closing {target}."
                    ShowTextToScreen(f"{Assistantname} : {ack}")

            run(Automation(automation_commands))
            task_execution = True
        except Exception as e:
            print(f"[AUTOMATION ERROR] {e}")

    # -------- Image generation -------- #
    if image_execution:
        try:
            with open(r"Frontend\Files\ImageGeneration.data", "w", encoding="utf-8") as file:
                file.write(f"{image_generation_query},True")

            response_text = f"Okay, generating an image of {image_generation_query}."
            ShowTextToScreen(f"{Assistantname} : {response_text}")
            SetAssistantStatus("Answering...")
            TextToSpeech(response_text)

            if image_gen_process is None or image_gen_process.poll() is not None:
                image_gen_process = subprocess.Popen([sys.executable, r"Backend\ImageGeneration.py"])
                subprocesses.append(image_gen_process)
            else:
                print("[INFO] ImageGeneration.py is already running.")

            return True

        except Exception as e:
            print(f"[IMAGE GENERATION ERROR] {e}")
            SetAssistantStatus("Available...")
            return False

    # -------- Combined general/realtime -------- #
    if has_realtime or (has_general and has_realtime):
        try:
            SetAssistantStatus("Searching...")
            answer = RealtimesearchEngine(QueryModifier(merged_query or query))
            ShowTextToScreen(f"{Assistantname} : {answer}")
            SetAssistantStatus("Answering...")
            TextToSpeech(answer)
            return True
        except Exception as e:
            print(f"[REALTIME SEARCH ERROR] {e}")
            SetAssistantStatus("Available...")
            return False

    # -------- Individual decisions -------- #
    for item in decision:
        try:
            if item.startswith("general"):
                SetAssistantStatus("Thinking...")
                query_final = item.replace("general", "", 1).strip()
                answer = ChatBot(QueryModifier(query_final))
                ShowTextToScreen(f"{Assistantname} : {answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(answer)
                return True

            elif item.startswith("realtime"):
                SetAssistantStatus("Searching...")
                query_final = item.replace("realtime", "", 1).strip()
                answer = RealtimesearchEngine(QueryModifier(query_final))
                ShowTextToScreen(f"{Assistantname} : {answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(answer)
                return True

            elif item.startswith("content"):
                SetAssistantStatus("Writing Content...")
                topic = item.replace("content", "", 1).strip()
                response = Content(topic)
                ShowTextToScreen(f"{Assistantname} : {response}")
                SetAssistantStatus("Answering...")
                TextToSpeech(response)
                return True

            elif item.startswith("learn face"):
                person_name = item.replace("learn face", "", 1).strip()
                SetAssistantStatus("Learning Face...")
                import cv2
                import os
                try:
                    cam_index = 0
                    try:
                        with open(TempDirectoryPath('CameraIndex.data'), "r") as f:
                            cam_index = int(f.read().strip())
                    except:
                        pass
                    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
                    ret, frame = cap.read()
                    cap.release()
                    if ret:
                        faces_dir = os.path.join("Data", "faces", person_name)
                        os.makedirs(faces_dir, exist_ok=True)
                        img_path = os.path.join(faces_dir, f"{person_name}.jpg")
                        cv2.imwrite(img_path, frame)
                        response = f"I have successfully learned and saved the face for {person_name}."
                    else:
                        response = "I couldn't access the camera. Make sure Vision Mode is closed before asking me to learn a face."
                except Exception as e:
                    response = "An error occurred while trying to save the face."
                
                ShowTextToScreen(f"{Assistantname} : {response}")
                SetAssistantStatus("Answering...")
                TextToSpeech(response)
                return True

            elif item.startswith("switch camera"):
                import os
                cam_index = 0
                cam_file = TempDirectoryPath('CameraIndex.data')
                try:
                    with open(cam_file, "r") as f:
                        cam_index = int(f.read().strip())
                except:
                    pass
                
                # Cycle between 0, 1, 2
                cam_index = (cam_index + 1) % 3
                
                with open(cam_file, "w") as f:
                    f.write(str(cam_index))
                    
                response = f"Switched to camera {cam_index}."
                if camera_process is not None and camera_process.poll() is None:
                    camera_process.terminate()
                    camera_process = subprocess.Popen([sys.executable, "Backend/camera.py"])
                    response += " Restarting Vision Mode with the new camera."
                    
                ShowTextToScreen(f"{Assistantname} : {response}")
                SetAssistantStatus("Answering...")
                TextToSpeech(response)
                return True

            elif item.startswith("camera"):
                with open(TempDirectoryPath('Camera.data'), 'w') as f:
                    f.write("True")
                if camera_process is None or camera_process.poll() is not None:
                    camera_process = subprocess.Popen([sys.executable, "Backend/camera.py"])
                ShowTextToScreen(f"{Assistantname} : Activating Vision Mode on your dashboard.")
                SetAssistantStatus("Answering...")
                TextToSpeech("Activating Vision Mode.")
                return True

            elif item.startswith("close camera"):
                with open(TempDirectoryPath('Camera.data'), 'w') as f:
                    f.write("False")
                if camera_process is not None and camera_process.poll() is None:
                    camera_process.terminate()
                    camera_process = None
                ShowTextToScreen(f"{Assistantname} : Deactivating Vision Mode.")
                SetAssistantStatus("Answering...")
                TextToSpeech("Deactivating Vision Mode.")
                return True

            elif item == "where am i":
                SetAssistantStatus("Locating...")
                result = where_am_i()
                if "error" in result:
                    answer = result["error"]
                else:
                    loc = result.get("location", "unknown")
                    w = result.get("weather", {})
                    temp = w.get("temp", "unknown") if w else "unknown"
                    cond = w.get("condition", "") if w else ""
                    answer = f"You are currently at {loc}. The weather there is {temp} degrees and {cond}."
                ShowTextToScreen(f"{Assistantname} : {answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(answer)
                return True

            elif item == "navigate home":
                SetAssistantStatus("Navigating...")
                result = navigate_home()
                if "error" in result:
                    answer = result["error"]
                else:
                    answer = (f"Navigating you home. Distance is {result['distance_km']} kilometers, "
                              f"estimated time {result['duration_min']} minutes. "
                              f"Head {result['compass']} to start.")
                ShowTextToScreen(f"{Assistantname} : {answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(answer)
                return True

            elif item.startswith("navigate to"):
                destination = item.replace("navigate to", "", 1).strip()
                SetAssistantStatus("Navigating...")
                result = navigate_from_phone(destination)
                if "error" in result:
                    answer = result["error"]
                else:
                    answer = (f"Navigation to {destination} started. Distance is {result['distance_km']} kilometers, "
                              f"estimated time {result['duration_min']} minutes. Head {result['compass']}.")
                ShowTextToScreen(f"{Assistantname} : {answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(answer)
                return True

            elif item.startswith("traffic to"):
                destination = item.replace("traffic to", "", 1).strip()
                SetAssistantStatus("Checking traffic...")
                phone = get_phone_location()
                if phone["lat"] is None:
                    answer = "Phone GPS is not available. Please enable location on your phone."
                else:
                    result = get_traffic_summary({"lat": phone["lat"], "lon": phone["lon"]}, destination)
                    if "error" in result:
                        answer = result["error"]
                    else:
                        w = result.get("dest_weather", {})
                        weather_info = ""
                        if w:
                            weather_info = f" Weather there is {w.get('temp', '?')} degrees and {w.get('condition', 'unknown')}."
                        answer = (f"To reach {destination}, the distance is {result['distance_km']} kilometers. "
                                  f"Estimated travel time is {result['duration_min']} minutes.{weather_info}")
                ShowTextToScreen(f"{Assistantname} : {answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(answer)
                return True

            elif item == "ip address":
                SetAssistantStatus("Checking IP...")
                answer = get_ip_address()
                ShowTextToScreen(f"{Assistantname} : {answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(answer)
                return True

            elif item == "support":
                answer = open_support()
                ShowTextToScreen(f"{Assistantname} : {answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(answer)
                return True

            elif item.startswith("wikipedia search"):
                topic = item.replace("wikipedia search", "", 1).strip()
                SetAssistantStatus("Searching Wikipedia...")
                answer = WikipediaSearch(topic)
                ShowTextToScreen(f"{Assistantname} : {answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(answer)
                return True

            elif item.startswith("write note"):
                note_text = item.replace("write note", "", 1).strip()
                SetAssistantStatus("Recording Note...")
                answer = WriteNote(note_text)
                ShowTextToScreen(f"{Assistantname} : {answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(answer)
                return True

            elif item == "show notes":
                SetAssistantStatus("Reading Notes...")
                answer = ShowNotes()
                ShowTextToScreen(f"{Assistantname} : {answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(answer)
                return True

            elif item == "read pdf":
                SetAssistantStatus("Reading PDF...")
                answer = ReadPdf()
                ShowTextToScreen(f"{Assistantname} : {answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(answer)
                return True

            elif item.startswith("how to"):
                topic = item.replace("how to", "", 1).strip()
                SetAssistantStatus("Generating Guide...")
                answer = HowToMode(topic)
                ShowTextToScreen(f"{Assistantname} : {answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(answer)
                return True

            elif item == "toss coin":
                answer = FlipCoin()
                ShowTextToScreen(f"{Assistantname} : {answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(answer)
                return True

            elif item.startswith("send whatsapp message") or item.startswith("whatsapp"):
                params = item.replace("send whatsapp message", "").replace("whatsapp", "").strip()
                SetAssistantStatus("Sending WhatsApp...")
                answer = SendWhatsAppMessage(params)
                ShowTextToScreen(f"{Assistantname} : {answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(answer)
                return True

            elif item.startswith("send email"):
                params = item.replace("send email", "").strip()
                SetAssistantStatus("Sending Email...")
                answer = SendEmail(params)
                ShowTextToScreen(f"{Assistantname} : {answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(answer)
                return True

            elif item == "change window":
                answer = ChangeWindow()
                ShowTextToScreen(f"{Assistantname} : {answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(answer)
                return True

            elif item == "sleep now":
                answer = SleepAssistant()
                ShowTextToScreen(f"{Assistantname} : {answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(answer)
                return True

            elif item.startswith("exit"):
                CloseAndExit("Okay, bye!")

        except Exception as e:
            print(f"[DECISION HANDLER ERROR] {item} -> {e}")

    if task_execution:
        SetAssistantStatus("Available...")
        return True

    SetAssistantStatus("Available...")
    return False


# -------------------- Threads -------------------- #
def FirstThread():
    while True:
        try:
            # 1. High-priority check: Process any typed commands from the GUI terminal first
            cmd_file = TempDirectoryPath('UserCommand.data')
            typed_cmd = ""
            if os.path.exists(cmd_file):
                try:
                    with open(cmd_file, "r", encoding="utf-8") as f:
                        typed_cmd = f.read().strip()
                    if typed_cmd:
                        os.remove(cmd_file)
                except Exception:
                    typed_cmd = ""

            if typed_cmd:
                try:
                    MainExecution(override_query=typed_cmd)
                except Exception as e:
                    print(f"[TYPED EXECUTION ERROR] {e}")
                sleep(0.1)
                continue

            # 2. Voice listening (only when mic is explicitly active)
            current_status = GetMicrophoneStatus()

            if current_status == "True":
                try:
                    MainExecution()
                except Exception as e:
                    print(f"[VOICE EXECUTION ERROR] {e}")
                    sleep(0.3)
            else:
                ai_status = GetAssistantStatus()
                if "Available..." not in ai_status:
                    SetAssistantStatus("Available...")
                sleep(0.1)

        except Exception as e:
            print(f"[FIRST THREAD LOOP ERROR] {e}")
            sleep(0.5)


def SecondThread():
    GraphicalUserInterface()


def run_server():
    try:
        start_remote_server(port=5000)
    except Exception as e:
        print(f"[REMOTE SERVER ERROR] {e}")


# -------------------- App Start -------------------- #
if __name__ == "__main__":
    for f in ['Exit.data', 'UserCommand.data']:
        try:
            p = TempDirectoryPath(f)
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    worker_thread = threading.Thread(target=FirstThread, daemon=True)
    worker_thread.start()
    
    # Start the startup greeting in the background
    greeting_thread = threading.Thread(target=advanced_startup_greeting, daemon=True)
    greeting_thread.start()

    SecondThread()