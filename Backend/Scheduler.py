import time
import threading
import datetime
import asyncio
import webbrowser
from Backend.SpaceAPI import space_client
from Backend.Automation import Automation
from Frontend.GUI import ShowTextToScreen, SetAssistantStatus, TempDirectoryPath
from Backend.TextToSpeech import TextToSpeech

class BackgroundScheduler:
    def __init__(self):
        self.running = False
        self.thread = None
        self.last_daily_run = None
        self.last_iss_alert = None
        self.launch_alerted = set()  # Track which launches we already alerted for

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            print("[Scheduler] Background tasks started.")

    def stop(self):
        self.running = False

    def schedule_command(self, command, delay_seconds):
        """Schedule an automation command to run after a delay."""
        def delayed_task():
            time.sleep(delay_seconds)
            print(f"[Scheduler] Executing delayed command: {command}")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(Automation([command]))
            loop.close()
            
        threading.Thread(target=delayed_task, daemon=True).start()
        return True

    def _run_loop(self):
        while self.running:
            now = datetime.datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            
            # Daily Tasks (run once per day)
            if self.last_daily_run != today_str:
                self.last_daily_run = today_str
                self._run_daily_tasks()
            
            # ISS Overhead Check (every 3 minutes)
            self._check_iss_overhead()
            
            # Launch Autopilot (every 60 seconds)
            self._check_launch_autopilot()
            
            # Write ISS data to file for GUI polling
            self._update_iss_data_file()
            
            time.sleep(60)

    def _check_iss_overhead(self):
        """Check if ISS is overhead and alert the user."""
        try:
            iss = space_client.get_iss_position()
            if iss and iss["is_overhead"]:
                now = datetime.datetime.now()
                # Only alert once every 30 minutes
                if self.last_iss_alert is None or (now - self.last_iss_alert).total_seconds() > 1800:
                    self.last_iss_alert = now
                    msg = f"Sir, the International Space Station is currently passing over {iss['user_city']} at {iss['distance_km']} km distance! Look up towards the sky!"
                    print(f"[Scheduler] ISS OVERHEAD ALERT: {msg}")
                    ShowTextToScreen(f"FRIDAY : {msg}")
                    SetAssistantStatus("Answering...")
                    TextToSpeech(msg)
        except Exception as e:
            print(f"[Scheduler] ISS check failed: {e}")

    def _check_launch_autopilot(self):
        """Auto-open YouTube livestream when a launch is 5 min away."""
        try:
            launches = space_client.get_launch_countdown()
            for l in launches:
                countdown = l.get("countdown_seconds", -1)
                name = l.get("name", "Unknown")
                vid_url = l.get("vidURL")
                
                # If countdown is between 0 and 300 seconds (5 min) and we haven't alerted
                if 0 < countdown <= 300 and name not in self.launch_alerted:
                    self.launch_alerted.add(name)
                    msg = f"Sir! Rocket launch '{name}' is T-minus {countdown // 60} minutes away! Opening the livestream now!"
                    print(f"[Scheduler] LAUNCH AUTOPILOT: {msg}")
                    ShowTextToScreen(f"FRIDAY : {msg}")
                    SetAssistantStatus("Answering...")
                    TextToSpeech(msg)
                    
                    if vid_url:
                        webbrowser.open(vid_url)
                    else:
                        # Fallback: search YouTube
                        search_query = name.replace(" ", "+")
                        webbrowser.open(f"https://www.youtube.com/results?search_query={search_query}+launch+live")
        except Exception as e:
            print(f"[Scheduler] Launch autopilot failed: {e}")

    def _update_iss_data_file(self):
        """Write ISS telemetry to a file for GUI to read."""
        try:
            iss = space_client.get_iss_position()
            if iss:
                import json
                data_path = TempDirectoryPath('ISS.data')
                with open(data_path, 'w') as f:
                    json.dump(iss, f)
        except Exception as e:
            pass

    def _run_daily_tasks(self):
        print(f"[Scheduler] Running daily tasks for {self.last_daily_run}")
        
        # 1. Update NASA APOD Wallpaper
        try:
            apod = space_client.get_apod()
            if apod and "local_path" in apod:
                import os
                static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Frontend", "remote", "static"))
                full_path = os.path.join(static_dir, "apod.jpg")
                if os.path.exists(full_path):
                    space_client.set_wallpaper(full_path)
                    print("[Scheduler] NASA APOD Wallpaper updated.")
        except Exception as e:
            print(f"[Scheduler] APOD task failed: {e}")

        # 2. Check Asteroids
        try:
            threats = space_client.get_asteroid_threats()
            hazardous = [t for t in threats if t["is_hazardous"]]
            if hazardous:
                msg = f"Alert: There are {len(hazardous)} potentially hazardous asteroids approaching Earth today."
                print(f"[Scheduler] {msg}")
        except Exception as e:
            print(f"[Scheduler] Asteroid task failed: {e}")

scheduler = BackgroundScheduler()

