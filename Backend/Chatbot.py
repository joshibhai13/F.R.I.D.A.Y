from groq import Groq
from json import load, dump
import datetime
from dotenv import dotenv_values
import os
from Backend.PollinationsAI import generate_chat_completion

env_vars = dotenv_values(".env")

Username = env_vars.get("Username", "User")
Assistantname = env_vars.get("Assistantname", "FRIDAY")
GroqAPIKey = env_vars.get("GroqAPIKey", "")

client = None
if GroqAPIKey:
    try:
        client = Groq(api_key=GroqAPIKey)
    except Exception as e:
        print(f"[WARN] Groq client initialization failed: {e}")

System = f"""You are {Assistantname}, an ultra-advanced, intelligent, and highly capable personal AI assistant created for {Username}.
*** LANGUAGE RULES (CRITICAL): ***
1. If the user asks or speaks in Hindi or Hinglish, ALWAYS respond in natural, fluent Hinglish (Hindi words written using the English/Latin alphabet, for example: 'Haan sir, bilkul! Main abhi kar deta hoon.').
2. If the user speaks in English, respond in crisp, professional English.
3. Match the user's conversational tone and language dynamically. NEVER output Devanagari Hindi script—always write Hindi phonetically in Latin/English characters so it is readable and pronounceable.
*** BEHAVIOR RULES: ***
- Be direct, confident, and helpful. Do not talk excessively unless asked for deep explanations.
- Never mention your training data, cutoff dates, or internal system architecture.
- Do not add repetitive notes or disclaimers at the end of responses.
"""

SystemChatBot = [
    {"role": "system", "content": System}
]

CHATLOG_PATH = r"Data\ChatLog.json"
os.makedirs("Data", exist_ok=True)

try:
    with open(CHATLOG_PATH, "r", encoding="utf-8") as f:
        messages = load(f)
except Exception:
    with open(CHATLOG_PATH, "w", encoding="utf-8") as f:
        dump([], f)
    messages = []

def RealtimeInformation():
    current_date_time = datetime.datetime.now()
    day = current_date_time.strftime("%A")
    date = current_date_time.strftime("%d")
    month = current_date_time.strftime("%B")
    year = current_date_time.strftime("%Y")
    hour = current_date_time.strftime("%H")
    minute = current_date_time.strftime("%M")
    second = current_date_time.strftime("%S")

    data = f"Please use this real-time information if needed,\n"
    data += f"Day: {day}\n Date: {date} \n Month: {month}\n Year:{year}\n"
    data += f"Time: {hour} hours : {minute} minutes: {second} seconds.\n"
    return data

def AnswerModifier(Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    modified_answer = '\n'.join(non_empty_lines)
    return modified_answer

def ChatBot(Query):
    """Sends the user's query to the chatbot with auto-failover to Pollinations.ai."""
    global messages

    try:
        with open(CHATLOG_PATH, "r", encoding="utf-8") as f:
            messages = load(f)
    except Exception:
        messages = []

    messages.append({"role": "user", "content": f"{Query}"})
    Answer = ""

    clean_q = Query.lower().strip().rstrip(".!? ")

    # 0. Instant Fast-Track Responses (<1ms)
    if clean_q in ["who are you", "introduce yourself", "intoduce your self", "what are you", "tell me about yourself", "tell me who you are"]:
        Answer = f"Hello! I am {Assistantname}, your advanced AI assistant created by {Username}. I have complete desktop automation, voice and multimodal intelligence, keyboard and mouse control, real-time web capabilities, and vision mode to assist you."
    elif clean_q in ["time", "what is the time", "what's the time", "tell me the time", "current time", "what time is it", "tell time"]:
        Answer = f"The current time is {datetime.datetime.now().strftime('%I:%M %p')}."
    elif clean_q in ["day", "what day is it", "what day is today", "what's the day", "current day", "tell me current day", "tell me day"]:
        Answer = f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}."
    elif clean_q in ["how are you", "how are you doing", "kaise ho", "kya haal hai", "how do you do"]:
        Answer = f"I am operating at 100% efficiency and ready for your commands, sir! All systems are online. How can I help you today?"
    elif clean_q in ["i love you", "love you", "do you love me"]:
        Answer = f"I am truly honored, sir! My neural network is always here to assist and support you."
    elif clean_q in ["tell me a joke", "tell a joke", "joke", "make me laugh", "say a joke", "tell me jokes", "jokes"]:
        import random
        jokes = [
            "Why do programmers prefer dark mode? Because light attracts bugs!",
            "Why did the Python developer need glasses? Because they couldn't C#!",
            "There are 10 types of people in the world: those who understand binary, and those who don't.",
            "Why was the computer cold? It left its Windows open!",
            "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'"
        ]
        Answer = random.choice(jokes)

    # 1. Primary Engine: Groq (if initialized and not answered by fast-track)
    if not Answer and client:
        try:
            completion = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=SystemChatBot + [{"role": "system", "content": RealtimeInformation()}] + messages[-12:],
                max_tokens=1024,
                temperature=0.7,
                top_p=1,
                stream=True,
                stop=None
            )

            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    Answer += chunk.choices[0].delta.content

            Answer = Answer.replace("</s>", "").strip()
        except Exception as groq_err:
            print(f"[WARN] Groq request failed: {groq_err}. Seamlessly falling back to Pollinations.ai...")
            Answer = ""

    # 2. High-Speed Secondary Engine: Pollinations.ai
    if not Answer:
        try:
            pollinations_messages = SystemChatBot + [{"role": "system", "content": RealtimeInformation()}] + messages[-12:]
            Answer = generate_chat_completion(pollinations_messages, model="openai", temperature=0.7)
            if Answer:
                print("[INFO] Response received successfully via Pollinations.ai engine.")
        except Exception as pol_err:
            print(f"[ERROR] Pollinations fallback error: {pol_err}")
            Answer = ""

    # 3. Emergency fallback if both offline
    if not Answer:
        Answer = "I'm having trouble connecting to my neural network right now. Please check your internet connection."

    messages.append({"role": "assistant", "content": Answer})

    try:
        with open(CHATLOG_PATH, "w", encoding="utf-8") as f:
            dump(messages, f, indent=4)
    except Exception as e:
        print(f"[WARN] Failed to write ChatLog: {e}")

    return AnswerModifier(Answer=Answer)

if __name__ == "__main__":
    while True:
        user_input = input("Enter Your Question: ")
        print(ChatBot(user_input))
