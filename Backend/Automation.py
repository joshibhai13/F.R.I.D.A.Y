import asyncio
import os
import subprocess
import webbrowser
import requests
import platform
import logging
import time
import datetime
try:
    from AppOpener import close, open as appopen
    from pywhatkit import search, playonyt
    from dotenv import dotenv_values
    from bs4 import BeautifulSoup
    from rich import print
    from groq import Groq
    import keyboard
except ImportError as e:
    print(f"Import error: {e}. Ensure all dependencies are installed.")
try:
    from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
    from comtypes import CLSCTX_ALL
except ImportError:
    print("pycaw not installed. Mute/unmute will use keyboard fallback.")
try:
    import wmi
except ImportError:
    print("wmi not installed. Brightness and power commands may not work on Windows.")
try:
    import pyautogui
except ImportError:
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
                model="llama-3.3-70b-versatile",
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
    try:
        playonyt(query)
        logger.info(f"Playing YouTube: {query}")
        return True
    except Exception as e:
        logger.error(f"PlayYouTube failed: {e}")
        return False

def OpenApp(app, sess=requests.session()):
    try:
        appopen(app, match_closest=True, output=True, throw_error=True)
        logger.info(f"Successfully opened {app}.")
        return True
    except Exception as e:
        logger.error(f"Failed to open {app} locally: {e}")
        app_name = app.lower().replace(' ', '')
        potential_urls = [f"https://{app_name}.com", f"https://{app_name}.in"]
        for url in potential_urls:
            try:
                response = sess.head(url, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    webbrowser.open(url)
                    logger.info(f"Opened site for {app}: {url}")
                    return True
                else:
                    logger.debug(f"URL {url} did not respond with 200.")
            except requests.RequestException as re:
                logger.error(f"Could not connect to {url}: {re}")
        
        def search_google(query):
            url = f"https://www.google.com/search?q={query} official site"
            headers = {"User-Agent": useragent}
            try:
                response = sess.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    return response.text
                else:
                    logger.error(f"Google search failed with status: {response.status_code}")
                    return None
            except Exception as e:
                logger.error(f"Google search request failed: {e}")
                return None

        def extract_links(html):
            if html is None:
                return []
            soup = BeautifulSoup(html, 'html.parser')
            links = soup.find_all('a', {"jsname": 'UWckNb'})
            return [link.get('href') for link in links if link.get('href')]

        html = search_google(app)
        if html:
            links = extract_links(html)
            if links:
                actual_url = links[0].split('=')[1].split('&')[0] if '=q=' in links[0] else links[0]
                webbrowser.open("https://" + actual_url)
                logger.info(f"Opened site for {app}: {actual_url}")
                return True
            else:
                logger.warning(f"No links found for {app}. Opening Google search.")
                webbrowser.open(f"https://www.google.com/search?q={app} official site")
                return False
        else:
            logger.error("Google search failed to return HTML.")
            webbrowser.open(f"https://www.google.com/search?q={app} official site")
            return False

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
        if 'pyautogui' not in globals():
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
        if 'pyautogui' not in globals():
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

    command = command.strip().lower()
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
        "toggle wifi": toggle_wifi
    }
    parts = command.split(" ", 2)
    cmd_key = parts[0] if parts[0] in ["mute", "unmute", "volume up", "volume down", "brightness up", "brightness down", "take screenshot", "open file explorer", "toggle bluetooth", "shutdown", "sleep", "lock screen", "toggle wifi"] else parts[0] + " " + parts[1]
    param = parts[2] if len(parts) > 2 else ""
    
    func = commands.get(cmd_key)
    if func:
        if param and cmd_key in ["set volume", "type text", "open file explorer"]:
            return func(param)
        elif not param:
            return func()
        else:
            logger.error(f"Command {cmd_key} does not accept parameters: {param}")
            return False
    else:
        logger.error(f"Unknown system command: {command}")
        return False

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
