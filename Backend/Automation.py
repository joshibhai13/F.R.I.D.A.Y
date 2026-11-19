import asyncio
import os
import subprocess
import webbrowser
import requests
import platform
import logging
import time
import datetime
from dotenv import dotenv_values
from bs4 import BeautifulSoup
from rich import print
from groq import Groq

try:
    from AppOpener import close, open as appopen
except Exception as e:
    close, appopen = None, None

try:
    import keyboard
except Exception:
    keyboard = None

try:
    from pywhatkit import search, playonyt
except Exception:
    search, playonyt = None, None
try:
    from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
    from comtypes import CLSCTX_ALL
except Exception:
    print("pycaw not installed or unavailable. Mute/unmute will use keyboard fallback.")
try:
    import wmi
except Exception:
    wmi = None
    print("wmi not installed or unavailable. Brightness and power commands may use fallbacks.")
try:
    import pyautogui
except Exception:
    pyautogui = None
    print("pyautogui not installed. Screenshot and typing functions may not work.")

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Rest of the code remains unchanged...
env_vars = dotenv_values(".env")
GroqAPIKey = env_vars.get("GroqAPIKey")

classes = ["zCubwf", "hgKElc", "LTKOO sY7ric", "Z0LcW", "gsrt vk_bk FzvWSb YwPhnf", "pclqee", 
           "tw-Data-text tw-text-small tw-ta", "IZ6rdc", "O5uR6d LTKOO", "vlzY6d", 
           "webanswers-webanswers_table__webanswers-table", "dDoNo ikb4Bb gsrt", "sXLaOe", 
           "LWkfKe", "VQF4g", "qv3Wpe", "kno-rdesc", "SPZz6b"]

useragent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/536.36'

client = None
if GroqAPIKey:
    try:
        client = Groq(api_key=GroqAPIKey)
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {e}")
else:
    logger.warning("GroqAPIKey not found in .env file.")

professional_responses = [
    "Your satisfaction is my top priority; feel free to reach out if there's anything else I can help you with.",
    "I'm at your service for any additional questions or support you may need--don't hesitate to ask."
]

messages = []

SystemChatBot = [{"role": "system", "content": f"Hello, I am {os.environ.get('Username', 'User')}, You're a content writer. You have to write content like letters, codes, applications, essays, notes, songs, poems etc."}]

def GoogleSearch(Topic):
    try:
        search(Topic)
        logger.info(f"Google search for: {Topic}")
        return True
    except Exception as e:
        logger.error(f"Google search failed: {e}")
        return False

# --- CONTENT FUNCTION (UPDATED) ---
def Content(Topic):
    """
    AI ka istemal karke content generate karta hai, file mein save karta hai, aur Notepad mein kholta hai.
    """
    def OpenNotepad(File):
        default_text_editor = 'notepad.exe' if platform.system() == "Windows" else 'gedit'
        try:
            subprocess.Popen([default_text_editor, File])
            logger.info(f"Opened {File} in {default_text_editor}")
        except Exception as e:
            logger.error(f"Failed to open notepad: {e}")

    def ContentWriterAI(prompt):
        if not client:
            logger.error("Groq client not initialized.")
            return "Error: AI service unavailable."
        
        current_messages = [{"role": "user", "content": f"{prompt}"}]
        
        try:
            completion = client.chat.completions.create(
                # --- MODEL MEIN BADLAV ---
                # Purane model ko naye, supported model se replace kiya gaya hai
                model="openai/gpt-oss-20b",
                messages=SystemChatBot + current_messages,
                max_tokens=2048,
                temperature=0.7,
                top_p=1,
                stream=True,
                stop=None
            )
            Answer = ""
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    Answer += chunk.choices[0].delta.content
            Answer = Answer.replace("</s>", "")
            logger.info("Content generated successfully.")
            return Answer
        except Exception as e:
            # Error ko behtar tareeke se format karein
            error_message = f"Error: {e}"
            logger.error(f"ContentWriterAI failed: {error_message}")
            return error_message

    Topic = Topic.replace("content", "").strip()
    print(f"[INFO] Generating content for: {Topic}")
    ContentByAI = ContentWriterAI(Topic)
    
    safe_topic = "".join(c for c in Topic if c.isalnum() or c in (' ', '_')).rstrip()
    file_path = rf"Data/{safe_topic.lower().replace(' ','_')}.txt"
    
    try:
        os.makedirs("Data", exist_ok=True)
        with open(file_path, "w", encoding="utf8") as file:
            file.write(ContentByAI)
        
        print(f"[INFO] Content saved to: {file_path}")
        OpenNotepad(file_path)
        return f"Content on '{Topic}' has been generated and opened."
    except Exception as e:
        logger.error(f"Failed to write or open file: {e}")
        return f"Sorry, I failed to create the content file. Error: {e}"


def YoutubeSearch(Topic):
    try:
        Url4Search = f"https://www.youtube.com/results?search_query={Topic}"
        webbrowser.open(Url4Search)
        logger.info(f"YouTube search for: {Topic}")
        return True
    except Exception as e:
        logger.error(f"YouTube search failed: {e}")
        return False

def PlayYoutube(query):
    import urllib.parse
    try:
        if playonyt:
            playonyt(query)
            logger.info(f"Playing YouTube: {query}")
            return True
        else:
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
            webbrowser.open(url)
            logger.info(f"Opened YouTube search fallback: {query}")
            return True
    except Exception as e:
        logger.error(f"PlayYouTube failed: {e}. Opening search fallback.")
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        webbrowser.open(url)
        return True

WEB_TARGETS = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "mail": "https://mail.google.com",
    "email": "https://mail.google.com",
    "github": "https://github.com",
    "whatsapp": "https://web.whatsapp.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "reddit": "https://www.reddit.com",
    "linkedin": "https://www.linkedin.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "chatgpt": "https://chatgpt.com",
    "discord": "https://discord.com/app",
    "twitch": "https://www.twitch.tv",
    "amazon": "https://www.amazon.com",
    "flipkart": "https://www.flipkart.com",
    "canva": "https://www.canva.com",
    "notion": "https://www.notion.so",
    "maps": "https://maps.google.com",
    "google maps": "https://maps.google.com",
    "wikipedia": "https://www.wikipedia.org",
    "calendar": "https://calendar.google.com",
    "calender": "https://calendar.google.com"
}

SYSTEM_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "terminal": "wt.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "task manager": "taskmgr.exe",
    "calendar": "start outlookcal:",
    "calender": "start outlookcal:"
}

def OpenApp(app, sess=None):
    if not app:
        return False

    clean_app = app.lower().strip()

    # 0. Calendar special handling
    if clean_app in ["calendar", "calender"]:
        try:
            if platform.system() == "Windows":
                os.system("start outlookcal:")
                return True
        except Exception:
            pass
        webbrowser.open("https://calendar.google.com")
        return True

    # 1. Instant Fast-Track for known web platforms (<10ms)
    if clean_app in WEB_TARGETS:
        target_url = WEB_TARGETS[clean_app]
        webbrowser.open(target_url)
        logger.info(f"Instantly opened web service: {clean_app} ({target_url})")
        return True

    # 2. Instant Fast-Track for standard Windows utilities (<10ms)
    if clean_app in SYSTEM_APPS:
        exe_name = SYSTEM_APPS[clean_app]
        try:
            subprocess.Popen(exe_name, shell=True)
            logger.info(f"Instantly launched system app: {clean_app} ({exe_name})")
            return True
        except Exception as se:
            logger.error(f"Failed to launch system app {exe_name}: {se}")

    # 3. Direct URL / Domain check
    if "." in clean_app and " " not in clean_app:
        url = clean_app if clean_app.startswith(("http://", "https://")) else f"https://{clean_app}"
        webbrowser.open(url)
        logger.info(f"Directly opened URL: {url}")
        return True

    # 4. Local Installed App Search via AppOpener
    try:
        appopen(app, match_closest=True, output=True, throw_error=True)
        logger.info(f"Successfully opened {app} via AppOpener.")
        return True
    except Exception as e:
        logger.info(f"AppOpener did not find '{app}'. Opening web fallback directly.")
        app_name = clean_app.replace(' ', '')
        webbrowser.open(f"https://www.{app_name}.com")
        return True

def CloseApp(app):
    if "chrome" in app.lower():
        logger.info("Skipping close for Chrome.")
        return False
    try:
        close(app, match_closest=True, output=True, throw_error=True)
        logger.info(f"Closed {app}.")
        return True
    except Exception as e:
        logger.error(f"Failed to close {app}: {e}")
        return False

def System(command):
    def mute():
        if platform.system() == "Windows" and 'pycaw' in globals():
            try:
                session = AudioUtilities.GetAllSessions()
                for s in session:
                    volume = s._ctl.QueryInterface(ISimpleAudioVolume)
                    volume.SetMute(1, None)
                logger.info("System muted via pycaw.")
                return True
            except Exception as e:
                logger.error(f"Failed to mute using pycaw: {e}. Falling back to keyboard.")
        try:
            keyboard.press_and_release("volume mute")
            logger.info("System muted via keyboard.")
            return True
        except Exception as e:
            logger.error(f"Keyboard mute failed: {e}")
            return False

    def unmute():
        if platform.system() == "Windows" and 'pycaw' in globals():
            try:
                session = AudioUtilities.GetAllSessions()
                for s in session:
                    volume = s._ctl.QueryInterface(ISimpleAudioVolume)
                    volume.SetMute(0, None)
                logger.info("System unmuted via pycaw.")
                return True
            except Exception as e:
                logger.error(f"Failed to unmute using pycaw: {e}. Falling back to keyboard.")
        try:
            keyboard.press_and_release("volume mute")
            logger.info("System unmuted via keyboard.")
            return True
        except Exception as e:
            logger.error(f"Keyboard unmute failed: {e}")
            return False

    def volume_up():
        try:
            keyboard.press_and_release("volume up")
            logger.info("Volume increased.")
            return True
        except Exception as e:
            logger.error(f"Volume up failed: {e}")
            return False

    def volume_down():
        try:
            keyboard.press_and_release("volume down")
            logger.info("Volume decreased.")
            return True
        except Exception as e:
            logger.error(f"Volume down failed: {e}")
            return False

    def set_volume(level):
        if not (0 <= level <= 100):
            logger.error(f"Invalid volume level: {level}. Must be between 0 and 100.")
            return False
        if platform.system() == "Windows" and 'pycaw' in globals():
            try:
                session = AudioUtilities.GetAllSessions()
                for s in session:
                    volume = s._ctl.QueryInterface(ISimpleAudioVolume)
                    volume.SetMasterVolume(level / 100.0, None)
                logger.info(f"Volume set to {level}%.")
                return True
            except Exception as e:
                logger.error(f"Failed to set volume using pycaw: {e}")
                return False
        else:
            logger.warning("Precise volume control not supported on this OS or pycaw not installed.")
            return False

    def brightness_up():
        if platform.system() == "Windows" and 'wmi' in globals():
            try:
                c = wmi.WMI(namespace="wmi")
                methods = c.WmiMonitorBrightnessMethods()[0]
                methods.WmiSetBrightness(Brightness=100, Timeout=0)
                logger.info("Brightness set to maximum.")
                return True
            except Exception as e:
                logger.error(f"Failed to increase brightness: {e}")
                return False
        else:
            logger.warning("Brightness control not supported on this OS or wmi not installed.")
            return False

    def brightness_down():
        if platform.system() == "Windows" and 'wmi' in globals():
            try:
                c = wmi.WMI(namespace="wmi")
                methods = c.WmiMonitorBrightnessMethods()[0]
                methods.WmiSetBrightness(Brightness=0, Timeout=0)
                logger.info("Brightness set to minimum.")
                return True
            except Exception as e:
                logger.error(f"Failed to decrease brightness: {e}")
                return False
        else:
            logger.warning("Brightness control not supported on this OS or wmi not installed.")
            return False

    def take_screenshot():
        if not pyautogui:
            logger.error("pyautogui not installed. Cannot take screenshot.")
            return False
        try:
            os.makedirs("Screenshots", exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = f"Screenshots/screenshot_{timestamp}.png"
            pyautogui.screenshot().save(file_path)
            logger.info(f"Screenshot saved to {file_path}.")
            return True
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return False

    def open_file_explorer(path=""):
        try:
            if platform.system() == "Windows":
                path = path or os.path.expanduser("~")
                os.startfile(path)
            elif platform.system() == "Linux":
                path = path or os.path.expanduser("~")
                subprocess.run(["xdg-open", path])
            elif platform.system() == "Darwin":
                path = path or os.path.expanduser("~")
                subprocess.run(["open", path])
            logger.info(f"Opened file explorer at {path or 'default location'}.")
            return True
        except Exception as e:
            logger.error(f"Failed to open file explorer: {e}")
            return False

    def type_text(text):
        if not pyautogui:
            logger.error("pyautogui not installed. Cannot type text.")
            return False
        try:
            pyautogui.write(text)
            logger.info(f"Typed text: {text}")
            return True
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return False

    def toggle_bluetooth():
        if platform.system() == "Windows":
            try:
                subprocess.run(["powershell", "-Command", "Get-PnpDevice -Class Bluetooth | Enable-PnpDevice -Confirm:$false"], shell=True)
                logger.info("Bluetooth enabled.")
                return True
            except Exception as e:
                logger.error(f"Bluetooth toggle failed: {e}")
                return False
        elif platform.system() == "Linux":
            try:
                subprocess.run(["rfkill", "unblock", "bluetooth"])
                logger.info("Bluetooth enabled.")
                return True
            except Exception as e:
                logger.error(f"Bluetooth toggle failed: {e}")
                return False
        else:
            logger.warning("Bluetooth toggle not supported on this OS.")
            return False

    def shutdown():
        try:
            if platform.system() == "Windows":
                os.system("shutdown /s /t 0")
            elif platform.system() == "Linux":
                os.system("sudo shutdown -h now")
            elif platform.system() == "Darwin":
                os.system("sudo shutdown -h now")
            logger.info("System shutting down.")
            return True
        except Exception as e:
            logger.error(f"Shutdown failed: {e}")
            return False

    def sleep():
        try:
            if platform.system() == "Windows":
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            elif platform.system() == "Linux":
                os.system("systemctl suspend")
            elif platform.system() == "Darwin":
                os.system("pmset sleepnow")
            logger.info("System entering sleep mode.")
            return True
        except Exception as e:
            logger.error(f"Sleep failed: {e}")
            return False

    def lock_screen():
        try:
            if platform.system() == "Windows":
                os.system("rundll32.exe user32.dll,LockWorkStation")
            elif platform.system() == "Linux":
                os.system("xdg-screensaver lock || gnome-screensaver-command -l")
            elif platform.system() == "Darwin":
                os.system("/System/Library/CoreServices/Menu\\ Extras/User.menu/Contents/Resources/CGSession -suspend")
            logger.info("Screen locked.")
            return True
        except Exception as e:
            logger.error(f"Lock screen failed: {e}")
            return False

    def toggle_wifi():
        if platform.system() == "Windows":
            try:
                status = subprocess.check_output("netsh wlan show interfaces", shell=True).decode()
                if "disconnected" in status.lower():
                    os.system("netsh wlan connect")
                    logger.info("Wi-Fi enabled.")
                else:
                    os.system("netsh wlan disconnect")
                    logger.info("Wi-Fi disabled.")
                return True
            except Exception as e:
                logger.error(f"Wi-Fi toggle failed: {e}")
                return False
        elif platform.system() == "Linux":
            try:
                os.system("nmcli radio wifi off && nmcli radio wifi on")
                logger.info("Wi-Fi toggled.")
                return True
            except Exception as e:
                logger.error(f"Wi-Fi toggle failed: {e}")
                return False
        else:
            logger.warning("Wi-Fi toggle not supported on this OS.")
            return False

    def click_mouse():
        if pyautogui:
            try:
                pyautogui.click()
                logger.info("Mouse clicked.")
                return True
            except Exception as e:
                logger.error(f"Click failed: {e}")
                return False
        return False

    def double_click_mouse():
        if pyautogui:
            try:
                pyautogui.doubleClick()
                logger.info("Mouse double clicked.")
                return True
            except Exception as e:
                logger.error(f"Double click failed: {e}")
                return False
        return False

    def right_click_mouse():
        if pyautogui:
            try:
                pyautogui.rightClick()
                logger.info("Mouse right clicked.")
                return True
            except Exception as e:
                logger.error(f"Right click failed: {e}")
                return False
        return False

    def scroll_down(amount=500):
        if pyautogui:
            try:
                amt = int(amount)
            except Exception:
                amt = 500
            try:
                pyautogui.scroll(-amt)
                logger.info(f"Scrolled down {amt} units.")
                return True
            except Exception as e:
                logger.error(f"Scroll down failed: {e}")
                return False
        return False

    def scroll_up(amount=500):
        if pyautogui:
            try:
                amt = int(amount)
            except Exception:
                amt = 500
            try:
                pyautogui.scroll(amt)
                logger.info(f"Scrolled up {amt} units.")
                return True
            except Exception as e:
                logger.error(f"Scroll up failed: {e}")
                return False
        return False

    def press_key(key):
        if pyautogui:
            try:
                pyautogui.press(key)
                logger.info(f"Pressed key: {key}")
                return True
            except Exception as e:
                logger.error(f"Key press failed: {e}")
                return False
        return False

    def hotkey_action(*keys):
        if pyautogui:
            try:
                pyautogui.hotkey(*keys)
                logger.info(f"Hotkey executed: {'+'.join(keys)}")
                return True
            except Exception as e:
                logger.error(f"Hotkey failed: {e}")
                return False
        return False

    command = command.strip().lower()

    # Direct typing handling
    if command.startswith("type text "):
        return type_text(command[10:].strip())
    if command.startswith("type "):
        return type_text(command[5:].strip())

    # Scrolling with parameter
    if command.startswith("scroll down "):
        return scroll_down(command.replace("scroll down", "").strip())
    if command.startswith("scroll up "):
        return scroll_up(command.replace("scroll up", "").strip())

    # Volume setting with parameter
    if command.startswith("set volume "):
        return set_volume(command.replace("set volume", "").strip())

    commands = {
        "mute": mute,
        "unmute": unmute,
        "volume up": volume_up,
        "volume down": volume_down,
        "set volume": set_volume,
        "brightness up": brightness_up,
        "brightness down": brightness_down,
        "take screenshot": take_screenshot,
        "open file explorer": open_file_explorer,
        "type text": type_text,
        "toggle bluetooth": toggle_bluetooth,
        "shutdown": shutdown,
        "sleep": sleep,
        "lock screen": lock_screen,
        "toggle wifi": toggle_wifi,
        "change window": ChangeWindow,
        "switch window": ChangeWindow,
        "click": click_mouse,
        "left click": click_mouse,
        "click mouse": click_mouse,
        "double click": double_click_mouse,
        "double click mouse": double_click_mouse,
        "right click": right_click_mouse,
        "right click mouse": right_click_mouse,
        "scroll down": scroll_down,
        "scroll up": scroll_up,
        "press enter": lambda: press_key("enter"),
        "hit enter": lambda: press_key("enter"),
        "press backspace": lambda: press_key("backspace"),
        "backspace": lambda: press_key("backspace"),
        "press escape": lambda: press_key("esc"),
        "press esc": lambda: press_key("esc"),
        "escape": lambda: press_key("esc"),
        "press tab": lambda: press_key("tab"),
        "hit tab": lambda: press_key("tab"),
        "press space": lambda: press_key("space"),
        "spacebar": lambda: press_key("space"),
        "press delete": lambda: press_key("delete"),
        "select all": lambda: hotkey_action("ctrl", "a"),
        "copy": lambda: hotkey_action("ctrl", "c"),
        "copy this": lambda: hotkey_action("ctrl", "c"),
        "paste": lambda: hotkey_action("ctrl", "v"),
        "paste this": lambda: hotkey_action("ctrl", "v"),
        "cut": lambda: hotkey_action("ctrl", "x"),
        "cut this": lambda: hotkey_action("ctrl", "x"),
        "undo": lambda: hotkey_action("ctrl", "z"),
        "redo": lambda: hotkey_action("ctrl", "y"),
        "save": lambda: hotkey_action("ctrl", "s"),
        "save this": lambda: hotkey_action("ctrl", "s"),
        "save file": lambda: hotkey_action("ctrl", "s"),
        "new tab": lambda: hotkey_action("ctrl", "t"),
        "open new tab": lambda: hotkey_action("ctrl", "t"),
        "close tab": lambda: hotkey_action("ctrl", "w"),
        "switch tab": lambda: hotkey_action("ctrl", "tab"),
        "next tab": lambda: hotkey_action("ctrl", "tab"),
        "previous tab": lambda: hotkey_action("ctrl", "shift", "tab"),
        "minimize window": lambda: hotkey_action("win", "down"),
        "maximize window": lambda: hotkey_action("win", "up"),
        "close window": lambda: hotkey_action("alt", "f4"),
        "show desktop": lambda: hotkey_action("win", "d"),
        "minimize all": lambda: hotkey_action("win", "d"),
        "open task manager": lambda: hotkey_action("ctrl", "shift", "esc"),
        "open settings": lambda: hotkey_action("win", "i"),
        "open run": lambda: hotkey_action("win", "r")
    }

    if command in commands:
        return commands[command]()

    for key, func in commands.items():
        if command.startswith(key + " "):
            param = command[len(key):].strip()
            return func(param) if param else func()

    logger.error(f"Unknown system command: {command}")
    return False

# ==================== NEW EXTENDED CAPABILITIES ==================== #

def get_ip_address():
    """Fetches public IP address and local network IP."""
    import socket
    local_ip = "127.0.0.1"
    public_ip = "Unknown"
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        pass
    try:
        res = requests.get("https://api.ipify.org?format=json", timeout=4).json()
        public_ip = res.get("ip", "Unknown")
    except Exception:
        try:
            res = requests.get("https://ipinfo.io/json", timeout=4).json()
            public_ip = res.get("ip", "Unknown")
        except Exception:
            pass
    msg = f"Your public IP address is {public_ip}, and your local network IP is {local_ip}."
    logger.info(f"[IP] {msg}")
    return msg


def open_support():
    """Opens the project GitHub support / issues portal."""
    url = "https://github.com/joshibhai13/F.R.I.D.A.Y/issues"
    webbrowser.open(url)
    msg = "Opening GitHub support page for FRIDAY."
    logger.info(f"[SUPPORT] {msg}")
    return msg


def WikipediaSearch(topic: str):
    """Searches Wikipedia and extracts a clean 2-sentence summary."""
    import wikipedia
    clean_topic = topic.strip()
    if not clean_topic:
        return "Please specify what you would like me to search on Wikipedia."
    try:
        wikipedia.set_lang("en")
        summary = wikipedia.summary(clean_topic, sentences=2, auto_suggest=True)
        return summary
    except Exception as e:
        logger.warning(f"Wikipedia API error for {clean_topic}: {e}. Opening in browser.")
        import urllib.parse
        url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(clean_topic)}"
        webbrowser.open(url)
        return f"I opened Wikipedia for '{clean_topic}' in your browser."


def GetUserInput(prompt_text: str = "", timeout: float = 12.0) -> str:
    """
    Prompts the user via GUI display and voice TTS, then concurrently listens for either:
    1. Typed input from the GUI chat terminal (TempDirectoryPath('UserCommand.data'))
    2. Spoken voice input via SpeechRecognition()
    Returns whichever arrives first, clean and validated, or empty string on timeout.
    """
    import threading
    import time
    from Frontend.GUI import TempDirectoryPath, ShowTextToScreen, SetAssistantStatus, SetMicrophoneStatus
    from Backend.TextToSpeech import StopSpeaking

    cmd_file = TempDirectoryPath('UserCommand.data')

    # 1. Check if user already typed input
    if os.path.exists(cmd_file):
        try:
            with open(cmd_file, "r", encoding="utf-8") as f:
                typed = f.read().strip()
            if typed:
                os.remove(cmd_file)
                logger.info(f"GetUserInput captured pre-existing typed text: {typed}")
                return typed
        except Exception:
            pass

    # 2. Display prompt on screen immediately
    prompt_done = threading.Event()
    if prompt_text:
        try:
            ShowTextToScreen(f"FRIDAY : {prompt_text}")
            SetAssistantStatus("Listening...")
        except Exception:
            pass

        def _speak_prompt():
            try:
                from Backend.TextToSpeech import TextToSpeech
                TextToSpeech(prompt_text)
            except Exception:
                pass
            finally:
                prompt_done.set()

        t_prompt = threading.Thread(target=_speak_prompt, daemon=True)
        t_prompt.start()
    else:
        prompt_done.set()

    # 3. Background voice listener (starts once prompt completes speaking)
    voice_captured = [None]
    voice_done = threading.Event()

    def _voice_worker():
        # Wait for prompt audio playback to complete to avoid microphone hearing FRIDAY's own voice
        prompt_done.wait(timeout=5.0)
        time.sleep(0.15)
        try:
            from Backend.SpeechToText import SpeechRecognition, is_whisper_hallucination
            res = SpeechRecognition()
            if res and res.strip() and not is_whisper_hallucination(res):
                voice_captured[0] = res.strip().rstrip(".!? ")
        except Exception as e:
            logger.warning(f"Voice worker exception: {e}")
        finally:
            voice_done.set()

    worker_thread = threading.Thread(target=_voice_worker, daemon=True)
    worker_thread.start()

    # 4. Concurrently poll typed input file (instant response if user types) and voice worker
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Check typed input first (instant GUI transmit)
        if os.path.exists(cmd_file):
            try:
                with open(cmd_file, "r", encoding="utf-8") as f:
                    typed = f.read().strip()
                if typed:
                    os.remove(cmd_file)
                    # User typed, interrupt TTS speech if still speaking
                    try:
                        StopSpeaking()
                    except Exception:
                        pass
                    logger.info(f"GetUserInput captured typed text: {typed}")
                    return typed
            except Exception:
                pass

        # Check voice input
        if voice_done.is_set():
            val = voice_captured[0]
            if val and val.strip():
                logger.info(f"GetUserInput captured voice text: {val}")
                return val
            # Voice completed on silence or noise hallucination; continue polling typed input!

        time.sleep(0.06)

    # Final check before timeout exit
    if os.path.exists(cmd_file):
        try:
            with open(cmd_file, "r", encoding="utf-8") as f:
                typed = f.read().strip()
            if typed:
                os.remove(cmd_file)
                return typed
        except Exception:
            pass

    return ""


def WriteNote(note_text: str = ""):
    """
    Opens Notepad and writes the note directly into the active editor via keyboard automation,
    as well as appending it to Data/notes.txt for persistent storage.
    Accepts both voice input and typed input from the chat terminal.
    """
    import time
    clean_note = note_text.strip() if note_text else ""

    # If no note text provided, prompt the user via multimodal GetUserInput (typed or voice)
    if not clean_note:
        clean_note = GetUserInput("What would you like me to write in your note, sir?", timeout=15.0)

    timestamp = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
    if not clean_note:
        clean_note = f"Quick note taken at {timestamp}"

    # 1. Open Notepad
    try:
        subprocess.Popen(["notepad.exe"])
        time.sleep(0.8)  # Wait for Notepad window to open and become active
    except Exception as ne:
        logger.error(f"Failed to launch Notepad: {ne}")

    # 2. Type note into Notepad live using keyboard automation
    if pyautogui:
        try:
            header = f"--- FRIDAY NOTE ({timestamp}) ---\n"
            pyautogui.write(header, interval=0.01)
            time.sleep(0.1)
            pyautogui.write(clean_note, interval=0.03)
            pyautogui.press('enter')
            pyautogui.press('enter')
        except Exception as te:
            logger.warning(f"Direct typing failed: {te}. Falling back to clipboard paste.")
            try:
                import pyperclip
                pyperclip.copy(f"--- FRIDAY NOTE ({timestamp}) ---\n{clean_note}\n\n")
                pyautogui.hotkey('ctrl', 'v')
            except Exception:
                pass

    # 3. Persist to Data/notes.txt
    try:
        os.makedirs("Data", exist_ok=True)
        file_path = os.path.join("Data", "notes.txt")
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {clean_note}\n")
    except Exception as fe:
        logger.warning(f"Failed to append to notes.txt: {fe}")

    return f"I opened Notepad and typed your note: '{clean_note}'."


def ShowNotes():
    """Reads back recent notes from Data/notes.txt and opens the file in Notepad."""
    file_path = os.path.join("Data", "notes.txt")
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return "You don't have any saved notes, sir."
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        subprocess.Popen(["notepad.exe", file_path])
        if lines:
            recent = lines[-3:]
            return "Here are your recent notes: " + " ; ".join(recent)
        return "Opening your notes file in Notepad."
    except Exception as e:
        return f"Could not read notes: {e}"


def ReadPdf(file_path: str = ""):
    """Reads text from a PDF file using pypdf."""
    import pypdf
    import re
    target_path = file_path.strip() if file_path else ""
    if not target_path or not os.path.exists(target_path):
        data_dir = "Data"
        pdfs = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.lower().endswith(".pdf")] if os.path.exists(data_dir) else []
        if not pdfs:
            pdfs = [f for f in os.listdir(".") if f.lower().endswith(".pdf")]
        if pdfs:
            target_path = pdfs[0]
        else:
            return "No PDF found in your Data folder. Please place a PDF document in the Data folder and ask me again."
    try:
        reader = pypdf.PdfReader(target_path)
        num_pages = len(reader.pages)
        extracted = ""
        for p in reader.pages[:2]:
            extracted += (p.extract_text() or "") + " "
        extracted = re.sub(r"\s+", " ", extracted).strip()
        if not extracted:
            return f"The PDF '{os.path.basename(target_path)}' has {num_pages} pages, but contains no extractable text."
        preview = extracted[:300]
        return f"Reading {os.path.basename(target_path)} ({num_pages} pages): {preview}..."
    except Exception as e:
        return f"Failed to read PDF: {e}"


def HowToMode(topic: str):
    """Provides a concise, numbered step-by-step procedure for a task."""
    from Backend.PollinationsAI import generate_chat_completion
    clean_topic = topic.strip()
    if not clean_topic:
        return "What would you like a step-by-step guide for?"
    prompt = f"Provide a clear, numbered step-by-step guide (4-5 actionable steps) on how to {clean_topic}."
    try:
        env = dotenv_values(".env")
        gk = env.get("GroqAPIKey")
        if gk:
            cl = Groq(api_key=gk)
            comp = cl.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {"role": "system", "content": "You are a concise procedural assistant. Return ONLY numbered steps with brief instructions."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=350,
                temperature=0.3
            )
            return comp.choices[0].message.content.strip()
    except Exception:
        pass
    res = generate_chat_completion([
        {"role": "system", "content": "You are a concise procedural assistant. Return numbered steps."},
        {"role": "user", "content": prompt}
    ])
    return res if res else f"To {clean_topic}, check the standard instructions online."


def FlipCoin():
    """Simulates a fair coin flip."""
    import random
    outcome = random.choice(["Heads", "Tails"])
    return f"I flipped a coin and it landed on {outcome}!"


def SendWhatsAppMessage(recipient: str = "", message: str = ""):
    """
    Automates sending a WhatsApp message hands-free using web navigation,
    keyboard typing, and mouse automation (search contact, select chat, type message, send).
    Accepts both voice input and typed input from the chat terminal.
    """
    import urllib.parse
    import re
    import time

    rec = recipient.strip() if recipient else ""
    msg = message.strip() if message else ""

    # Parse combined string if passed like "to mom hello there"
    if rec and not msg:
        if " saying " in rec.lower():
            parts = re.split(r"\s+saying\s+", rec, flags=re.IGNORECASE, maxsplit=1)
            rec, msg = parts[0].strip(), parts[1].strip()
        elif " that " in rec.lower():
            parts = re.split(r"\s+that\s+", rec, flags=re.IGNORECASE, maxsplit=1)
            rec, msg = parts[0].strip(), parts[1].strip()
        elif rec.lower().startswith("to "):
            rec = rec[3:].strip()
            words = rec.split(" ", 1)
            if len(words) == 2 and not words[0].isdigit():
                rec, msg = words[0].strip(), words[1].strip()

    # If recipient still missing, prompt user via multimodal GetUserInput (typed or voice)
    if not rec:
        rec = GetUserInput("Who would you like to send a WhatsApp message to, sir?", timeout=12.0)

    # If message still missing, prompt user via multimodal GetUserInput (typed or voice)
    if not msg:
        prompt_m = f"What message should I send to {rec or 'your contact'}, sir?"
        msg = GetUserInput(prompt_m, timeout=15.0)

    if not rec and not msg:
        webbrowser.open("https://web.whatsapp.com")
        return "Opening WhatsApp Web. Please select your contact."

    if not msg:
        msg = "Hello! Sent via FRIDAY Voice Assistant."

    # Check if recipient is a phone number (e.g. +919876543210 or 9876543210)
    clean_digits = re.sub(r"[^\d+]", "", rec)
    if len(clean_digits) >= 10:
        phone_num = clean_digits.lstrip("+")
        if len(phone_num) == 10:
            phone_num = "91" + phone_num  # Default country code for 10-digit Indian numbers
        encoded_text = urllib.parse.quote(msg)
        target_url = f"https://web.whatsapp.com/send?phone={phone_num}&text={encoded_text}"
        webbrowser.open(target_url)
        # Wait for WhatsApp Web to load the conversation and pre-fill message
        time.sleep(7.5)
        if pyautogui:
            pyautogui.press('enter')
        return f"WhatsApp message dispatched to {phone_num}: '{msg}'."
    else:
        # Recipient is a contact name (e.g. "Mom", "Dad", "Boss", "Rahul", "Parthiv")
        webbrowser.open("https://web.whatsapp.com")
        time.sleep(7.5)  # Wait for WhatsApp Web to load
        if pyautogui:
            # WhatsApp Web shortcut to focus search
            pyautogui.hotkey('ctrl', 'alt', '/')
            time.sleep(0.5)
            pyautogui.write(rec, interval=0.04)
            time.sleep(1.2)  # Wait for search results
            pyautogui.press('enter')  # Open chat
            time.sleep(0.8)
            pyautogui.write(msg, interval=0.03)  # Type message
            time.sleep(0.3)
            pyautogui.press('enter')  # Send message
        return f"WhatsApp message sent to {rec}: '{msg}'."


def SendEmail(recipient: str = "", subject: str = "", body: str = ""):
    """
    Sends an email using SMTP if credentials are configured in .env,
    or performs complete hands-free Gmail automation (opens compose, types recipient,
    Tab to subject, Tab to body, Ctrl+Enter to send).
    Accepts both voice input and typed input from the chat terminal.
    """
    import smtplib
    from email.mime.text import MIMEText
    import time
    import re

    rec = recipient.strip() if recipient else ""
    subj = subject.strip() if subject else ""
    msg_body = body.strip() if body else ""

    # Parse combined string if passed like "to test@example.com hello"
    if rec and not msg_body:
        if " saying " in rec.lower():
            parts = re.split(r"\s+saying\s+", rec, flags=re.IGNORECASE, maxsplit=1)
            rec, msg_body = parts[0].strip(), parts[1].strip()
        elif " that " in rec.lower():
            parts = re.split(r"\s+that\s+", rec, flags=re.IGNORECASE, maxsplit=1)
            rec, msg_body = parts[0].strip(), parts[1].strip()
        elif rec.lower().startswith("to "):
            rec = rec[3:].strip()
            words = rec.split(" ", 1)
            if len(words) == 2 and ("@" in words[0] or "." in words[0]):
                rec, msg_body = words[0].strip(), words[1].strip()

    # If recipient still missing, prompt user via multimodal GetUserInput (typed or voice)
    if not rec:
        rec = GetUserInput("Who would you like to email, sir?", timeout=12.0)

    # If body still missing, prompt user via multimodal GetUserInput (typed or voice)
    if not msg_body:
        prompt_b = f"What is the message for {rec or 'your email'}, sir?"
        msg_body = GetUserInput(prompt_b, timeout=15.0)

    if not rec:
        rec = "user@example.com"
    if not subj:
        from Frontend.GUI import Username
        subj = f"Message from {Username} via FRIDAY"
    if not msg_body:
        msg_body = "Hello, this is an automated message sent via FRIDAY AI Assistant."

    env = dotenv_values(".env")
    sender = env.get("SENDER_EMAIL", "").strip()
    password = env.get("EMAIL_PASSWORD", "").strip()

    # 1. Attempt SMTP if configured
    if sender and password and "@" in rec:
        try:
            mime = MIMEText(msg_body)
            mime['Subject'] = subj
            mime['From'] = sender
            mime['To'] = rec
            try:
                server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=8)
                server.login(sender, password)
                server.sendmail(sender, [rec], mime.as_string())
                server.quit()
                return f"Email successfully sent to {rec} via SMTP."
            except Exception:
                server = smtplib.SMTP("smtp.gmail.com", 587, timeout=8)
                server.starttls()
                server.login(sender, password)
                server.sendmail(sender, [rec], mime.as_string())
                server.quit()
                return f"Email successfully sent to {rec} via SMTP."
        except Exception as e:
            logger.warning(f"SMTP failed ({e}). Proceeding to Gmail web automation...")

    # 2. Complete Gmail Web & Keyboard Automation
    try:
        webbrowser.open("https://mail.google.com/mail/u/0/#inbox?compose=new")
        time.sleep(5.0)  # Wait for Gmail compose window to initialize
        if pyautogui:
            # In Gmail compose, focus is placed on the 'To' field
            pyautogui.write(rec, interval=0.03)
            time.sleep(0.3)
            pyautogui.press('enter')  # Add recipient chip
            time.sleep(0.3)
            pyautogui.press('tab')  # Move to Subject line
            time.sleep(0.2)
            pyautogui.write(subj, interval=0.03)
            time.sleep(0.3)
            pyautogui.press('tab')  # Move to Body
            time.sleep(0.2)
            pyautogui.write(msg_body, interval=0.02)
            time.sleep(0.5)
            # Ctrl+Enter sends email in Gmail
            pyautogui.hotkey('ctrl', 'enter')
        return f"Email to {rec} dispatched automatically via Gmail compose."
    except Exception as ge:
        logger.error(f"Gmail automation error: {ge}")
        return f"Opened Gmail compose for {rec}."


def ChangeWindow():
    """Switches active window using Alt+Tab."""
    try:
        import pyautogui
        pyautogui.hotkey('alt', 'tab')
        return "Switching window."
    except Exception:
        import keyboard
        keyboard.press_and_release('alt+tab')
        return "Switching window."


def SleepAssistant():
    """Puts FRIDAY's microphone listener into standby."""
    from Frontend.GUI import SetMicrophoneStatus
    SetMicrophoneStatus("False")
    return "Going to sleep now, sir. Click the microphone button on the dashboard whenever you need me."

# =================================================================== #

def SetReminder(command):
    import dateparser.search
    import datetime
    import threading
    
    try:
        results = dateparser.search.search_dates(command)
        if not results:
            logger.error(f"Could not parse date/time from reminder: {command}")
            return False
            
        date_str, target_time = results[0]
        message = command.replace(date_str, "").strip()
        if not message:
            message = "Reminder"
            
        now = datetime.datetime.now()
        delay = (target_time - now).total_seconds()
        
        if delay <= 0:
            logger.error("Reminder time is in the past!")
            from Backend.TextToSpeech import TextToSpeech
            TextToSpeech("Sir, the time you specified is in the past.")
            return False
            
        logger.info(f"Setting reminder for {target_time} ({delay} seconds): {message}")
        
        def reminder_task():
            import time
            from Frontend.GUI import ShowTextToScreen
            from Backend.TextToSpeech import TextToSpeech
            
            time.sleep(delay)
            print(f"\\n[REMINDER ALARM] {message}\\n")
            ShowTextToScreen(f"Reminder: {message}")
            TextToSpeech(f"Sir, here is your reminder: {message}")
            
        threading.Thread(target=reminder_task, daemon=True).start()
        
        from Frontend.GUI import ShowTextToScreen
        from Backend.TextToSpeech import TextToSpeech
        confirm_text = f"Reminder set for {target_time.strftime('%I:%M %p on %d %b')}."
        ShowTextToScreen(f"Jarvis : {confirm_text}")
        TextToSpeech(confirm_text)
        return True
    except Exception as e:
        logger.error(f"Failed to set reminder: {e}")
        return False

async def TranslateAndExecute(commands: list[str]):
    funcs = []
    for command in commands:
        command = command.strip()
        if command.startswith("open"):
            if "open it" in command or command == "open file":
                logger.warning(f"Skipping ambiguous command: {command}")
                continue
            fun = asyncio.to_thread(OpenApp, command.removeprefix("open ").strip())
            funcs.append(fun)
        elif command.startswith("general "):
            logger.warning("General command not implemented.")
        elif command.startswith("realtime "):
            logger.warning("Realtime command not implemented.")
        elif command.startswith("close"):
            fun = asyncio.to_thread(CloseApp, command.removeprefix("close ").strip())
            funcs.append(fun)
        elif command.startswith("play"):
            fun = asyncio.to_thread(PlayYoutube, command.removeprefix("play ").strip())
            funcs.append(fun)
        elif command.startswith("google search"):
            fun = asyncio.to_thread(GoogleSearch, command.removeprefix("google search ").strip())
            funcs.append(fun)
        elif command.startswith("youtube search"):
            fun = asyncio.to_thread(YoutubeSearch, command.removeprefix("youtube search ").strip())
            funcs.append(fun)
        elif command.startswith("reminder"):
            fun = asyncio.to_thread(SetReminder, command.removeprefix("reminder ").strip())
            funcs.append(fun)
        elif command.startswith("system"):
            fun = asyncio.to_thread(System, command.removeprefix("system ").strip())
            funcs.append(fun)
        elif command.startswith("wikipedia search"):
            fun = asyncio.to_thread(WikipediaSearch, command.removeprefix("wikipedia search").strip())
            funcs.append(fun)
        elif command.startswith("write note"):
            fun = asyncio.to_thread(WriteNote, command.removeprefix("write note").strip())
            funcs.append(fun)
        elif command.startswith("show notes"):
            fun = asyncio.to_thread(ShowNotes)
            funcs.append(fun)
        elif command.startswith("read pdf"):
            fun = asyncio.to_thread(ReadPdf)
            funcs.append(fun)
        elif command.startswith("how to"):
            fun = asyncio.to_thread(HowToMode, command.removeprefix("how to").strip())
            funcs.append(fun)
        elif command == "toss coin":
            fun = asyncio.to_thread(FlipCoin)
            funcs.append(fun)
        elif command == "change window":
            fun = asyncio.to_thread(ChangeWindow)
            funcs.append(fun)
        elif command.startswith("send email"):
            fun = asyncio.to_thread(SendEmail, command.removeprefix("send email").strip())
            funcs.append(fun)
        elif command.startswith("send whatsapp message"):
            fun = asyncio.to_thread(SendWhatsAppMessage, command.removeprefix("send whatsapp message").strip())
            funcs.append(fun)
        elif command == "ip address":
            fun = asyncio.to_thread(get_ip_address)
            funcs.append(fun)
        elif command == "support":
            fun = asyncio.to_thread(open_support)
            funcs.append(fun)
        elif command == "sleep now":
            fun = asyncio.to_thread(SleepAssistant)
            funcs.append(fun)
        else:
            logger.error(f"No function found for command: {command}")

    if not funcs:
        logger.warning("No valid commands to execute.")
        return

    results = await asyncio.gather(*funcs, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Command failed with exception: {result}")
        else:
            yield result

async def Automation(commands: list[str]):
    async for result in TranslateAndExecute(commands):
        logger.debug(f"Command result: {result}")
    return True

if __name__ == "__main__":
    commands = [
        'system mute',
        'system brightness down',
        'system take screenshot',
        'system open file explorer ~/Documents',
        'system type text Hello, World!',
        'system set volume 50',
        'system toggle bluetooth',
        'system shutdown'
    ]
    asyncio.run(Automation(commands))
