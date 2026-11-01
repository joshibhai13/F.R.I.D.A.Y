import io
import os
import re
import speech_recognition as sr
from dotenv import dotenv_values
from groq import Groq

env_vars = dotenv_values(".env")
GroqAPIKey = env_vars.get("GroqAPIKey", "")
InputLanguage = env_vars.get("InputLanguage", "en-IN")

recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.energy_threshold = 300
recognizer.pause_threshold = 0.8  # Seconds of silence before assuming speech is done

groq_client = None
if GroqAPIKey:
    try:
        groq_client = Groq(api_key=GroqAPIKey)
    except Exception as e:
        print(f"[STT] Groq client warning: {e}")


def is_devanagari(text: str) -> bool:
    """Checks if text contains Devanagari (Hindi) script characters."""
    return any('\u0900' <= char <= '\u097F' for char in text)


# Basic Devanagari to Roman transliteration mapping for fallback
DEVANAGARI_MAP = {
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ऋ': 'ri',
    'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'अं': 'an', 'अः': 'ah',
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
    'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'ृ': 'ri',
    'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', '्': '', 'ं': 'n', 'ँ': 'n', 'ः': 'h',
    '़': '', '।': '.', '॥': '.'
}

def devanagari_to_hinglish(text: str) -> str:
    """Converts Devanagari text to readable Hinglish (Roman script)."""
    if not is_devanagari(text):
        return text
    
    # Try quick phonetics conversion
    result = []
    i = 0
    while i < len(text):
        char = text[i]
        if char in DEVANAGARI_MAP:
            result.append(DEVANAGARI_MAP[char])
        else:
            result.append(char)
        i += 1
    converted = "".join(result)
    # Clean up double vowels/spaces
    converted = re.sub(r'\s+', ' ', converted).strip()
    return converted if converted else text


def QueryModifier(query: str) -> str:
    if not query:
        return ""
    
    new_query = query.strip()
    
    # Convert Devanagari to Hinglish if present
    if is_devanagari(new_query):
        new_query = devanagari_to_hinglish(new_query)
        
    lower_q = new_query.lower()
    question_words = [
        "how", "what", "who", "where", "when", "why", "which", "whose", "whom",
        "kya", "kaise", "kyun", "kab", "kahan", "kaun", "kiska", "kitna"
    ]

    has_question_word = any(
        re.search(r'\b' + re.escape(w) + r'\b', lower_q) for w in question_words
    )

    if has_question_word:
        if not new_query.endswith("?"):
            new_query = new_query.rstrip(".!?,") + "?"
    else:
        if not new_query.endswith((".", "!", "?")):
            new_query += "."

    return new_query[0].upper() + new_query[1:] if len(new_query) > 1 else new_query.upper()


def SpeechRecognition() -> str:
    """
    Captures audio from microphone and transcribes using Groq Whisper (ultra-fast, multilingual).
    Supports Hindi, English, and Hinglish. Falls back to Google STT if Groq fails.
    """
    global groq_client

    try:
        with sr.Microphone() as source:
            print("[Listening...]")
            recognizer.adjust_for_ambient_noise(source, duration=0.4)
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=20)

        print("[Recognizing...]")
        raw_text = ""

        # 1. Primary Engine: Groq Whisper API (whisper-large-v3-turbo)
        if groq_client:
            try:
                wav_bytes = audio.get_wav_data()
                audio_file = io.BytesIO(wav_bytes)
                audio_file.name = "input.wav"

                transcription = groq_client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3-turbo",
                    prompt="Hinglish conversation. Hindi words written in English alphabet (Roman script). Examples: kya kar rahe ho, kaise ho, what is the weather, play songs, open camera.",
                    response_format="text"
                )
                raw_text = str(transcription).strip()
            except Exception as ge:
                print(f"[STT WARN] Groq Whisper failed: {ge}. Falling back to Google STT...")
                raw_text = ""

        # 2. Secondary Engine: Google Speech Recognition (Fallback)
        if not raw_text:
            try:
                # Try Indian English or Hindi
                raw_text = recognizer.recognize_google(audio, language=InputLanguage)
            except Exception:
                try:
                    raw_text = recognizer.recognize_google(audio, language="hi-IN")
                except Exception as gre:
                    print(f"[STT ERROR] Google fallback failed: {gre}")

        if not raw_text:
            return ""

        final_query = QueryModifier(raw_text)
        print(f"[Heard]: {final_query}")
        return final_query

    except sr.WaitTimeoutError:
        print("[STT] Listening timed out")
        return ""
    except sr.UnknownValueError:
        print("[STT] Could not understand audio")
        return ""
    except Exception as e:
        print(f"[STT ERROR] {e}")
        return ""


if __name__ == "__main__":
    print("Testing SpeechRecognition (Say something in English or Hindi)...")
    while True:
        res = SpeechRecognition()
        if res:
            print(f"Recognized: {res}")
