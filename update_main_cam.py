import sys

file_path = "main.py"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Global declaration
if "camera_process = None" not in text:
    text = text.replace("image_gen_process = None", "image_gen_process = None\ncamera_process = None")

# 2. MainExecution global declaration
if "global camera_process" not in text:
    text = text.replace("    global image_gen_process", "    global image_gen_process\n    global camera_process")

# 3. Add 'close camera' to ignore list in automation_commands
if 'and not q.startswith("close camera")' not in text:
    old_automation = """    automation_commands = [
        q for q in decision
        if not q.startswith("content")
        and not q.startswith("generate image")
        and not q.startswith("general")
        and not q.startswith("realtime")
        and not q.startswith("camera")
        and not q.startswith("exit")
    ]"""
    new_automation = """    automation_commands = [
        q for q in decision
        if not q.startswith("content")
        and not q.startswith("generate image")
        and not q.startswith("general")
        and not q.startswith("realtime")
        and not q.startswith("camera")
        and not q.startswith("close camera")
        and not q.startswith("exit")
    ]"""
    text = text.replace(old_automation, new_automation)

# 4. Modify camera intent to store process and add close camera intent
old_camera_intent = """            elif item.startswith("camera"):
                with open(TempDirectoryPath('Camera.data'), 'w') as f:
                    f.write("True")
                subprocess.Popen([sys.executable, "Backend/camera.py"])
                ShowTextToScreen(f"{Assistantname} : Activating Vision Mode on your dashboard.")
                SetAssistantStatus("Answering...")
                TextToSpeech("Activating Vision Mode.")
                return True"""

new_camera_intent = """            elif item.startswith("camera"):
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
                return True"""

text = text.replace(old_camera_intent, new_camera_intent)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(text)
