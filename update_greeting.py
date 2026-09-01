import os

file_path = "main.py"

with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# Replace old jarvis_introduction
old_intro = '''# -------------------- Intro -------------------- #
def jarvis_introduction():
    intro_message = (
        f"{Assistantname}: Hello {Username}! I am {Assistantname}, your AI assistant. "
        f"I'm here to help with information, automation, and more. Just say or type your request!"
    )
    ShowTextToScreen(intro_message)
    TextToSpeech(intro_message)'''

new_intro = '''# -------------------- Intro -------------------- #
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
              f"End by asking 'What's on your mind today, or should we continue our previous conversation about \\"{last_topic}\\"?'")
              
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
        
    print(f"\\n[STARTUP] {msg}\\n")
    # Show on GUI and speak
    ShowTextToScreen(f"{Assistantname} : {msg}")
    TextToSpeech(msg)'''

text = text.replace(old_intro, new_intro)

# Start the greeting thread in main block
old_main = '''# -------------------- App Start -------------------- #
if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    worker_thread = threading.Thread(target=FirstThread, daemon=True)
    worker_thread.start()

    SecondThread()'''

new_main = '''# -------------------- App Start -------------------- #
if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    worker_thread = threading.Thread(target=FirstThread, daemon=True)
    worker_thread.start()
    
    # Start the startup greeting in the background
    greeting_thread = threading.Thread(target=advanced_startup_greeting, daemon=True)
    greeting_thread.start()

    SecondThread()'''

text = text.replace(old_main, new_main)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(text)

print("Startup greeting logic added successfully.")
