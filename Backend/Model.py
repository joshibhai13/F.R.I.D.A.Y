import cohere
from rich import print
from dotenv import dotenv_values
from Backend.PollinationsAI import generate_chat_completion


env_vars = dotenv_values(".env")


CohereAPIKey = env_vars.get("CohereAPIKey")


co = cohere.Client(api_key=CohereAPIKey)


funcs = [
    "exit", "general", "realtime", "open", "close", "play", 
    "generate image", "system", "content", "google search",
    "youtube search ", "reminder", "camera", "emotion",
    "switch camera",
    "learn face",
    "where am i", "navigate home", "navigate to", "traffic to",
    "ip address", "support", "wikipedia search", "write note", "show notes",
    "read pdf", "how to", "toss coin", "send whatsapp message", "send email",
    "change window", "sleep now"
]


messages = []


preamble = """
You are a very accurate Decision-Making Model, which decides what kind of a query is given to you.
You will decide whether a query is a 'general' query, a 'realtime' query, or is asking to perform any task or automation like 'open facebook, instagram', 'can you write a application and open it in notepad'
*** Do not answer any query, just decide what kind of query is given to you. ***
-> Respond with 'general ( query )' if a query can be answered by a llm model (conversational ai chatbot) and doesn't require any up to date information like if the query is 'who was akbar?' respond with 'general who was akbar?', if the query is 'how can i study more effectively?' respond with 'general how can i study more effectively?', if the query is 'can you help me with this math problem?' respond with 'general can you help me with this math problem?', if the query is 'Thanks, i really liked it.' respond with 'general thanks, i really liked it.' , if the query is 'what is python programming language?' respond with 'general what is python programming language?', etc. Respond with 'general (query)' if a query doesn't have a proper noun or is incomplete like if the query is 'who is he?' respond with 'general who is he?', if the query is 'what's his networth?' respond with 'general what's his networth?', if the query is 'tell me more about him.' respond with 'general tell me more about him.', and so on even if it require up-to-date information to answer. Respond with 'general (query)' if the query is asking about time, day, date, month, year, etc like if the query is 'what's the time?' respond with 'general what's the time?'.
-> Respond with 'realtime ( query )' if a query can not be answered by a llm model (because they don't have realtime data) and requires up to date information like if the query is 'who is indian prime minister' respond with 'realtime who is indian prime minister', if the query is 'tell me about facebook's recent update.' respond with 'realtime tell me about facebook's recent update.', if the query is 'tell me news about coronavirus.' respond with 'realtime tell me news about coronavirus.', etc and if the query is asking about any individual or thing like if the query is 'who is akshay kumar' respond with 'realtime who is akshay kumar', if the query is 'what is today's news?' respond with 'realtime what is today's news?', if the query is 'what is today's headline?' respond with 'realtime what is today's headline?', etc.
-> Respond with 'open (application name or website name)' if a query is asking to open any application like 'open facebook', 'open telegram', etc. but if the query is asking to open multiple applications, respond with 'open 1st application name, open 2nd application name' and so on.
-> Respond with 'close (application name)' if a query is asking to close any application like 'close notepad', 'close facebook', etc. but if the query is asking to close multiple applications or websites, respond with 'close 1st application name, close 2nd application name' and so on.
-> Respond with 'play (song name)' if a query is asking to play any song like 'play afsanay by ys', 'play let her go', etc. but if the query is asking to play multiple songs, respond with 'play 1st song name, play 2nd song name' and so on.
-> Respond with 'generate image (image prompt)' if a query is requesting to generate a image with given prompt like 'generate image of a lion', 'generate image of a cat', etc. but if the query is asking to generate multiple images, respond with 'generate image 1st image prompt, generate image 2nd image prompt' and so on.
-> Respond with 'reminder (datetime with message)' if a query is requesting to set a reminder like 'set a reminder at 9:00pm on 25th june for my business meeting.' respond with 'reminder 9:00pm 25th june business meeting'.
-> Respond with 'system (task name)' if a query is asking to mute, unmute, volume up, volume down , etc. but if the query is asking to do multiple tasks, respond with 'system 1st task, system 2nd task', etc.
-> Respond with 'content (topic)' if a query is asking to write any type of content like application, codes, emails or anything else about a specific topic but if the query is asking to write multiple types of content, respond with 'content 1st topic, content 2nd topic' and so on.
-> Respond with 'google search (topic)' if a query is asking to search a specific topic on google but if the query is asking to search multiple topics on google, respond with 'google search 1st topic, google search 2nd topic' and so on.
-> Respond with 'youtube search (topic)' if a query is asking to search a specific topic on youtube but if the query is asking to search multiple topics on youtube, respond with 'youtube search 1st topic, youtube search 2nd topic' and so on.
-> Respond with 'camera' if the query is asking to activate camera, enable vision, open eyes, start scanning, or similar visual-related commands like "open camera", "look at me", "see me", "enable vision mode", etc.
-> Respond with 'close camera' if the query is asking to deactivate camera, disable vision, close eyes, stop scanning, or similar commands like "close camera", "turn off vision mode", "disable vision", etc.
-> Respond with 'emotion' if a query is asking to detect emotions, facial mood, how I look, or analyze feelings visually using the camera.
-> Respond with 'switch camera' if the query is asking to switch the camera, change camera, use webcam, or use another camera.
-> Respond with 'learn face (person's name)' if a query is asking to remember or learn a face. For example, if the query is 'learn my face, my name is Pruthvi', respond with 'learn face Pruthvi'. If the query is 'remember this person as John', respond with 'learn face John'.
-> Respond with 'where am i' if the user is asking about their current location, position, or where they are. Examples: 'where am I right now?', 'what is my location?', 'tell me my current position'.
-> Respond with 'navigate home' if the user is asking to go back home, return home, find way home, or get back to their base. Examples: 'take me home', 'get me back home', 'navigate me to home', 'guide me back'.
-> Respond with 'navigate to (destination)' if the user is asking for navigation or directions to a specific place. Examples: 'navigate to Mumbai airport' respond with 'navigate to Mumbai airport', 'take me to Central Park' respond with 'navigate to Central Park', 'how do I get to the train station' respond with 'navigate to train station'.
-> Respond with 'traffic to (destination)' if the user is asking about traffic conditions, estimated time, or travel info to a place. Examples: 'what is the traffic to office' respond with 'traffic to office', 'how long to reach Delhi' respond with 'traffic to Delhi', 'I want to go to Bangalore' respond with 'traffic to Bangalore'.

*** If the query is asking to perform multiple tasks like 'open facebook, telegram and close whatsapp' respond with 'open facebook, open telegram, close whatsapp' ***
*** If the user is saying goodbye or wants to end the conversation like 'bye jarvis.' respond with 'exit'.***
*** Respond with 'general (query)' if you can't decide the kind of query or if a query is asking to perform a task which is not mentioned above. ***
"""


ChatHistory = [
    {"role": "User", "message": "how are you?"},
    {"role": "Chatbot", "message": "general how are you?"},

    {"role": "User", "message": "do you like pizza?"},
    {"role": "Chatbot", "message": "general do you like pizza?"},

    {"role": "User", "message": "open chrome and tell me about mahatma gandhi"},
    {"role": "Chatbot", "message": "open chrome, general and tell me about mahatma gandhi"},

    {"role": "User", "message": "open chrome and firefox"},
    {"role": "Chatbot", "message": "open chrome, open firefox"},

    {"role": "User", "message": "what is today's date and by the way remind me that i have a dancing performance on 5th aug at 11pm"},
    {"role": "Chatbot", "message": "general what is today's date, reminder 11:00pm 5th aug dancing performance"},

    {"role": "User", "message": "chat with me."},
    {"role": "Chatbot", "message": "general chat with me."},

    {"role": "User", "message": "learn my face, my name is Pruthvi"},
    {"role": "Chatbot", "message": "learn face Pruthvi"},
    
    {"role": "User", "message": "remember me as a friend"},
    {"role": "Chatbot", "message": "learn face friend"},

    {"role": "User", "message": "scan my face and save it"},
    {"role": "Chatbot", "message": "learn face user"},

    {"role": "User", "message": "open camera"},
    {"role": "Chatbot", "message": "camera"},

    {"role": "User", "message": "enable vision mode"},
    {"role": "Chatbot", "message": "camera"},

    {"role": "User", "message": "switch camera"},
    {"role": "Chatbot", "message": "switch camera"},

    {"role": "User", "message": "show me your eyes"},
    {"role": "Chatbot", "message": "camera"},

    {"role": "User", "message": "use your eyes"},
    {"role": "Chatbot", "message": "camera"},

    {"role": "User", "message": "start visual sensors"},
    {"role": "Chatbot", "message": "camera"},

    {"role": "User", "message": "look at me"},
    {"role": "Chatbot", "message": "camera"},

    {"role": "User", "message": "activate camera"},
    {"role": "Chatbot", "message": "camera"},

    {"role": "User", "message": "start scanning"},
    {"role": "Chatbot", "message": "camera"},

    {"role": "User", "message": "detect my mood"},
    {"role": "Chatbot", "message": "emotion"},

    {"role": "User", "message": "analyze my face"},
    {"role": "Chatbot", "message": "emotion"},

    {"role": "User", "message": "where am I right now?"},
    {"role": "Chatbot", "message": "where am i"},

    {"role": "User", "message": "what is my current location?"},
    {"role": "Chatbot", "message": "where am i"},

    {"role": "User", "message": "take me back home"},
    {"role": "Chatbot", "message": "navigate home"},

    {"role": "User", "message": "navigate me to Mumbai airport"},
    {"role": "Chatbot", "message": "navigate to Mumbai airport"},

    {"role": "User", "message": "generate image of a flying car"},
    {"role": "Chatbot", "message": "generate image flying car"}
]


def fast_classify(prompt: str):
    """
    Ultra-fast heuristic intent resolver (<0.5ms).
    Directly routes common commands (open, play, exit, camera, system, etc.)
    without waiting 2-4 seconds for an external LLM API call.
    """
    import re
    if not prompt:
        return None

    clean = prompt.lower().strip().rstrip(".!? ")

    # 1. Immediate Exit / Farewell Triggers
    exit_words = {
        "bye", "goodbye", "good bye", "exit", "quit", "tata", "alvida",
        "close assistant", "stop assistant", "bye friday", "goodbye friday",
        "bye jarvis", "goodbye jarvis", "band ho jao", "shut down", "shutdown",
        "close yourself", "terminate", "see you later"
    }
    if (clean in exit_words or 
        any(clean.startswith(p) for p in ["bye ", "goodbye ", "good bye "]) or 
        any(clean.endswith(p) for p in [" bye", " goodbye", " good bye"])):
        return ["exit"]

    # 2. Camera & Vision Mode
    if clean in ["open camera", "enable vision", "enable vision mode", "start camera", "turn on camera", "activate camera", "look at me", "show me your eyes", "use your eyes"]:
        return ["camera"]
    if clean in ["close camera", "disable vision", "turn off camera", "stop camera", "deactivate camera", "turn off vision mode"]:
        return ["close camera"]
    if clean in ["switch camera", "change camera", "next camera"]:
        return ["switch camera"]

    # 3. Location / Navigation
    if clean in ["where am i", "what is my location", "my location", "current location", "where are we"]:
        return ["where am i"]
    if clean in ["navigate home", "take me home", "guide me home", "go home"]:
        return ["navigate home"]
    if clean.startswith("navigate to "):
        dest = clean.replace("navigate to", "", 1).strip()
        return [f"navigate to {dest}"]
    if clean.startswith("traffic to "):
        dest = clean.replace("traffic to", "", 1).strip()
        return [f"traffic to {dest}"]

    # 4. Image Generation
    if clean.startswith("generate image of ") or clean.startswith("create image of "):
        desc = re.sub(r"^(generate|create)\s+image\s+of\s+", "", clean).strip()
        return [f"generate image {desc}"]
    if clean.startswith("generate image "):
        desc = clean.replace("generate image", "", 1).strip()
        return [f"generate image {desc}"]

    # 5. Open Apps & Websites (single action)
    if clean.startswith("open ") and not any(k in clean for k in [" and ", " then ", " but ", " after "]):
        target = clean.replace("open ", "", 1).strip()
        if target:
            if target in ["camera", "webcam"]:
                return ["camera"]
            return [f"open {target}"]

    # 6. Close Apps
    if clean.startswith("close ") and not any(k in clean for k in [" and ", " then "]):
        target = clean.replace("close ", "", 1).strip()
        if target:
            if target in ["camera", "webcam", "vision"]:
                return ["close camera"]
            if target in ["assistant", "friday", "jarvis", "app"]:
                return ["exit"]
            return [f"close {target}"]

    # 7. Play Music / YouTube
    if clean.startswith("play ") and not any(k in clean for k in [" and ", " then "]):
        target = clean.replace("play ", "", 1).strip()
        if target:
            return [f"play {target}"]

    # 8. Direct Searches
    if clean.startswith("google search "):
        return [clean]
    if clean.startswith("youtube search "):
        return [clean]
    if clean.startswith("search ") and " on google" in clean:
        topic = clean.replace("search ", "", 1).replace(" on google", "").strip()
        return [f"google search {topic}"]
    if clean.startswith("search ") and " on youtube" in clean:
        topic = clean.replace("search ", "", 1).replace(" on youtube", "").strip()
        return [f"youtube search {topic}"]

    # 9. System commands (mute/unmute/volume)
    if clean in ["mute", "unmute", "volume up", "volume down"]:
        return [f"system {clean}"]

    # 10. IP Address
    if clean in ["ip", "ip address", "ip adress", "what is my ip", "what is my ip address", "tell me my ip", "my ip", "my ip address"]:
        return ["ip address"]

    # 11. Support / GitHub
    if clean in ["support", "github support", "open support", "open github support", "help and support"]:
        return ["support"]

    # 12. Wikipedia Search
    if clean.startswith("wikipedia search "):
        topic = clean.replace("wikipedia search", "", 1).strip()
        return [f"wikipedia search {topic}"]
    if clean.startswith("search wikipedia for "):
        topic = clean.replace("search wikipedia for", "", 1).strip()
        return [f"wikipedia search {topic}"]
    if clean.startswith("wikipedia ") and not clean.startswith("wikipedia.org"):
        topic = clean.replace("wikipedia", "", 1).strip()
        return [f"wikipedia search {topic}"]

    # 13. Note Taking & Reading
    if clean.startswith("write a note") or clean.startswith("write note") or clean.startswith("take a note") or clean.startswith("take note"):
        note_text = re.sub(r"^(write|take)\s+(a\s+)?note(\s+that|\s+about)?\s*", "", clean).strip()
        return [f"write note {note_text}".strip()]
    if clean in ["show note", "show notes", "read note", "read notes", "my notes", "read my notes", "open notes"]:
        return ["show notes"]

    # 14. PDF Reading
    if clean in ["read pdf", "read document", "read the pdf", "open pdf", "read my pdf"]:
        return ["read pdf"]

    # 15. How-To Mode
    if clean.startswith("activate how to mode") or clean.startswith("how to mode") or (clean.startswith("how to ") and len(clean.split()) > 2):
        topic = re.sub(r"^(activate\s+)?how\s+to\s+(mode\s+)?", "", clean).strip()
        return [f"how to {topic}"]

    # 16. Toss / Flip Coin
    if clean in ["toss coin", "toss a coin", "flip coin", "flip a coin", "coin toss", "coin flip"]:
        return ["toss coin"]

    # 17. WhatsApp Messaging
    if clean.startswith("send a message") or clean.startswith("send message") or clean.startswith("whatsapp message"):
        return ["send whatsapp message"]

    # 18. Email Sending
    if clean.startswith("send email") or clean.startswith("send an email") or clean.startswith("send mail") or clean.startswith("send a mail") or clean.startswith("send emali"):
        return ["send email"]

    # 19. Change Window
    if clean in ["change window", "switch window", "next window", "switch app", "change app"]:
        return ["change window"]

    # 20. Sleep / Standby
    if clean in ["sleep now", "go to sleep", "stop listening", "standby", "pause assistant"]:
        return ["sleep now"]

    return None


def FirstLayerDMM(prompt: str = "test"):
    # 0. Zero-latency Fast-Path Classifier
    fast_result = fast_classify(prompt)
    if fast_result is not None:
        return fast_result

    messages.append({"role": "user", "content": f"{prompt}"})
    response = ""

    # 1. Primary: Cohere Decision Model
    try:
        stream = co.chat_stream(
            model='command-a-03-2025',
            message=prompt,
            temperature=0.7,
            chat_history=ChatHistory,
            prompt_truncation='OFF',
            connectors=[],
            preamble=preamble
        )

        for event in stream:
            if event.event_type == "text-generation":
                response += event.text
    except Exception as co_err:
        print(f"[WARN] Cohere Decision engine unavailable: {co_err}. Falling back to Pollinations.ai...")
        response = ""

    # 2. Secondary: Pollinations AI Decision Fallback
    if not response:
        try:
            pol_messages = [
                {"role": "system", "content": preamble + "\nReply ONLY with the comma-separated decision commands, nothing else."}
            ]
            for ch in ChatHistory[-10:]:
                role = "assistant" if ch.get("role") == "Chatbot" else "user"
                pol_messages.append({"role": role, "content": ch.get("message", "")})
            pol_messages.append({"role": "user", "content": prompt})

            pol_decision = generate_chat_completion(pol_messages, model="openai", temperature=0.2)
            if pol_decision:
                response = pol_decision.strip()
        except Exception as pol_err:
            print(f"[ERROR] Pollinations Decision fallback failed: {pol_err}")
            response = "general " + prompt

    response = response.replace("\n", "")
    response = response.split(",")
    response = [i.strip() for i in response]

    temp = []
    for task in response:
        for func in funcs:
            if task.startswith(func):
                temp.append(task)

    response = temp

    if not response:
        response = ["general " + prompt]

    if "(query)" in response:
        newresponse = FirstLayerDMM(prompt=prompt)
        return newresponse
    else:
        return response


if __name__ == "__main__":
    while True:
        print(FirstLayerDMM(input(">>> ")))
