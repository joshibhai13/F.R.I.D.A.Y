import speech_recognition as sr
from dotenv import dotenv_values
import os

env_vars = dotenv_values(".env")
InputLanguage = env_vars.get("InputLanguage", "en-IN")

recognizer = sr.Recognizer()

# Increase the energy threshold dynamically based on background noise
recognizer.dynamic_energy_threshold = True
recognizer.energy_threshold = 300 
recognizer.pause_threshold = 0.8 # Seconds of silence before assuming speech is done

def QueryModifier(query):
    new_query = query.lower().strip()
    if not new_query:
        return ""

    question_words = ["how", "what", "who", "where", "when", "why", "which"]

    if any(word in new_query for word in question_words):
        if not new_query.endswith("?"):
            new_query += "?"
    else:
        if not new_query.endswith("."):
            new_query += "."

    return new_query.capitalize()


def SpeechRecognition():
    try:
        with sr.Microphone() as source:
            print("[Listening...]")
            # Automatically adjust for ambient noise before listening
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            # Listen dynamically: starts recording on voice, stops on silence (pause_threshold)
            # Timeout is max wait for FIRST word, phrase_time_limit is max length of speech
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=20)

        print("[Recognizing...]")
        text = recognizer.recognize_google(audio, language=InputLanguage)
        return QueryModifier(text)

    except sr.WaitTimeoutError:
        # No speech was detected within the timeout period
        print("[STT] Listening timed out")
        return ""
    except sr.UnknownValueError:
        print("[STT] Could not understand audio")
        return ""
    except sr.RequestError as e:
        print(f"[STT ERROR] API unavailable: {e}")
        return ""
    except Exception as e:
        print(f"[STT ERROR] {e}")
        return ""

if __name__ == "__main__":
    while True:
        print(SpeechRecognition())