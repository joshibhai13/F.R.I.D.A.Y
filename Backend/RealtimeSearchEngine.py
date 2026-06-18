from duckduckgo_search import DDGS
from groq import Groq
from json import load, dump
import datetime
from dotenv import dotenv_values
import os


env_vars = dotenv_values(".env")

Username = env_vars.get("Username", "User")
Assistantname = env_vars.get("Assistantname", "Jarvis")
GroqAPIKey = env_vars.get("GroqAPIKey")

client = Groq(api_key=GroqAPIKey)

System = f"""Hello, I am {Username}. You are a very accurate and advanced AI chatbot named {Assistantname} which has real-time up-to-date information from the internet.
*** Provide answers in a professional way, make sure to add full stops, commas, question marks, and use proper grammar. ***
*** Answer only from the provided real-time data and the user query. If the search data is weak or incomplete, say so clearly instead of guessing. ***
*** Prefer the freshest and most relevant information from the provided search results. ***
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
    {"role": "assistant", "content": "Hello, how can I help you?"}
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

    # save user query in chat log
    messages.append({"role": "user", "content": f"{prompt}"})

    # fetch real-time search results
    search_context = RealtimeSearch(prompt)

    # add search results as SYSTEM context, not user content
    realtime_context = [
        {"role": "system", "content": Information()},
        {"role": "system", "content": search_context}
    ]

    # keep only recent chat history to avoid overloading the model
    recent_messages = messages[-10:]

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=SystemChatBot + realtime_context + recent_messages,
            temperature=0.4,
            max_tokens=1024,
            top_p=1,
            stream=True,
            stop=None
        )

        answer = ""

        for chunk in completion:
            if chunk.choices[0].delta.content:
                answer += chunk.choices[0].delta.content

        answer = answer.strip().replace("</s>", "")

        if not answer:
            answer = "I could not generate a proper real-time answer."

    except Exception as e:
        answer = f"Real-time answer generation failed. Error: {e}"

    messages.append({"role": "assistant", "content": answer})
    save_chatlog(messages)

    return AnswerModifier(answer)


if __name__ == "__main__":
    while True:
        prompt = input("Enter Your Query: ").strip()
        if prompt.lower() in ["exit", "quit"]:
            break
        print(RealtimesearchEngine(prompt))