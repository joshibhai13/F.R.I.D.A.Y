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

    # 1. Primary Engine: Groq (if initialized)
    if client:
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
