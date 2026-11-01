from duckduckgo_search import DDGS
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

System = f"""You are {Assistantname}, an ultra-advanced real-time intelligence assistant for {Username}.
*** LANGUAGE INSTRUCTIONS: ***
1. If the user query is in Hindi or Hinglish, formulate your answer in natural, fluent Hinglish (Hindi words written in the English/Roman alphabet). NEVER output Devanagari script.
2. If the user query is in English, respond in clear, professional English.
3. Match the user's conversational language dynamically.
*** ACCURACY INSTRUCTIONS: ***
- Synthesize answers directly from the provided fresh search results and real-time context.
- Keep responses professional, well-structured, and concise.
"""

CHATLOG_PATH = r"Data\ChatLog.json"
os.makedirs("Data", exist_ok=True)

try:
    with open(CHATLOG_PATH, "r", encoding="utf-8") as f:
        messages = load(f)
except Exception:
    with open(CHATLOG_PATH, "w", encoding="utf-8") as f:
        dump([], f, indent=4)
    messages = []

def RealtimeSearch(query):
    """
    Fetches real-time search results using ddgs.
    """
    try:
        results = DDGS().text(
            query,
            max_results=8,
            region="in-en",
            safesearch="moderate"
        )

        if not results:
            return f"No real-time search results were found for '{query}'."

        answer = f"Real-time search results for '{query}':\n[start]\n"

        for i, item in enumerate(results, start=1):
            title = item.get("title", "").strip()
            body = item.get("body", "").strip()
            link = item.get("href", "").strip()

            answer += (
                f"Result {i}:\n"
                f"Title: {title}\n"
                f"Description: {body}\n"
                f"Link: {link}\n\n"
            )

        answer += "[end]"
        return answer

    except Exception as e:
        return f"Search failed for '{query}'. Error: {e}"

def AnswerModifier(answer):
    lines = answer.split("\n")
    non_empty_lines = [line for line in lines if line.strip()]
    modified_answer = "\n".join(non_empty_lines)
    return modified_answer

SystemChatBot = [
    {"role": "system", "content": System},
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello! Systems online. How can I help you today?"}
]

def Information():
    current_date_time = datetime.datetime.now()
    day = current_date_time.strftime("%A")
    date = current_date_time.strftime("%d")
    month = current_date_time.strftime("%B")
    year = current_date_time.strftime("%Y")
    hour = current_date_time.strftime("%H")
    minute = current_date_time.strftime("%M")
    second = current_date_time.strftime("%S")

    data = ""
    data += "Use this real-time information if needed:\n"
    data += f"Day: {day}\n"
    data += f"Date: {date}\n"
    data += f"Month: {month}\n"
    data += f"Year: {year}\n"
    data += f"Time: {hour} hours, {minute} minutes, {second} seconds.\n"
    return data

def load_chatlog():
    try:
        with open(CHATLOG_PATH, "r", encoding="utf-8") as f:
            return load(f)
    except Exception:
        return []

def save_chatlog(messages_to_save):
    with open(CHATLOG_PATH, "w", encoding="utf-8") as f:
        dump(messages_to_save, f, indent=4)

def RealtimesearchEngine(prompt):
    global SystemChatBot

    messages = load_chatlog()
    messages.append({"role": "user", "content": f"{prompt}"})

    search_context = RealtimeSearch(prompt)

    realtime_context = [
        {"role": "system", "content": Information()},
        {"role": "system", "content": search_context}
    ]

    recent_messages = messages[-8:]
    full_messages = SystemChatBot + realtime_context + recent_messages
    answer = ""

    # 1. Primary: Groq
    if client:
        try:
            completion = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=full_messages,
                temperature=0.4,
                max_tokens=1024,
                top_p=1,
                stream=True,
                stop=None
            )

            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    answer += chunk.choices[0].delta.content

            answer = answer.strip().replace("</s>", "")
        except Exception as groq_err:
            print(f"[WARN] Groq real-time search failed: {groq_err}. Falling back to Pollinations.ai...")
            answer = ""

    # 2. Secondary: Pollinations.ai fallback
    if not answer:
        try:
            answer = generate_chat_completion(full_messages, model="openai", temperature=0.4)
            if answer:
                print("[INFO] Real-time answer synthesized via Pollinations.ai.")
        except Exception as pol_err:
            print(f"[ERROR] Pollinations real-time search fallback failed: {pol_err}")
            answer = ""

    if not answer:
        answer = "I could not retrieve and synthesize real-time data at this moment."

    messages.append({"role": "assistant", "content": answer})
    save_chatlog(messages)

    return AnswerModifier(answer)

if __name__ == "__main__":
    while True:
        prompt = input("Enter Your Query: ").strip()
        if prompt.lower() in ["exit", "quit"]:
            break
        print(RealtimesearchEngine(prompt))
