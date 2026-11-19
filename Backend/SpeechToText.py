import audioop
import io
import os
import re
import sys
import speech_recognition as sr
from dotenv import dotenv_values
from groq import Groq

# Ensure Windows terminal handles Unicode/Devanagari text without crashing
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

env_vars = dotenv_values(".env")
GroqAPIKey = env_vars.get("GroqAPIKey", "")
InputLanguage = env_vars.get("InputLanguage", "en-IN")

recognizer = sr.Recognizer()
recognizer.energy_threshold = 400
recognizer.dynamic_energy_threshold = True
recognizer.dynamic_energy_adjustment_damping = 0.15
recognizer.dynamic_energy_ratio = 1.5
recognizer.pause_threshold = 0.8
recognizer.phrase_threshold = 0.3
recognizer.non_speaking_duration = 0.5

groq_client = None
if GroqAPIKey:
    try:
        groq_client = Groq(api_key=GroqAPIKey)
    except Exception as e:
        print(f"[STT] Groq client warning: {e}")


def is_devanagari(text: str) -> bool:
    """Checks if text contains Devanagari (Hindi) script characters."""
    return any('\u0900' <= char <= '\u097F' for char in text)


# Comprehensive Devanagari to Hinglish (Roman script) transliteration
VOWELS = {
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ऋ': 'ri',
    'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'अं': 'an', 'अः': 'ah'
}

MATRAS = {
    'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'ृ': 'ri',
    'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ं': 'n', 'ँ': 'n', 'ः': 'h', '़': ''
}

CONSONANTS = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
    'क्ष': 'ksh', 'त्र': 'tr', 'ज्ञ': 'gya'
}

HALANT = '्'


def devanagari_to_hinglish(text: str) -> str:
    """Accurately transliterates Devanagari script into readable Roman Hinglish."""
    if not is_devanagari(text):
        return text

    out = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in VOWELS:
            out.append(VOWELS[c])
            i += 1
        elif c in CONSONANTS:
            c_rom = CONSONANTS[c]
            if i + 1 < n:
                next_c = text[i + 1]
                if next_c == HALANT:
                    out.append(c_rom)
                    i += 2
                elif next_c == 'ं':
                    # Anusvara following consonant (e.g. बंद -> band)
                    out.append(c_rom + 'an')
                    i += 2
                elif next_c in MATRAS:
                    out.append(c_rom + MATRAS[next_c])
                    i += 2
                elif next_c in CONSONANTS or next_c in VOWELS:
                    out.append(c_rom + 'a')
                    i += 1
                else:
                    out.append(c_rom)
                    i += 1
            else:
                out.append(c_rom)
                i += 1
        elif c in MATRAS:
            out.append(MATRAS[c])
            i += 1
        else:
            out.append(c)
            i += 1

    converted = ''.join(out)
    converted = re.sub(r'\s+', ' ', converted).strip()
    return converted if converted else text


# Known Whisper hallucinations on silence, breathing, or background noise
NOISE_HALLUCINATIONS = {
    "the", "the.", "a", "an", "you", "you.",
    "mbc", "subtitles", "subtitles by", "watching", "subscribe",
    ".", "..", "..."
}


def QueryModifier(query: str) -> str:
    if not query:
        return ""

    new_query = query.strip()

    # Convert Devanagari to Hinglish if present
    if is_devanagari(new_query):
        new_query = devanagari_to_hinglish(new_query)

    # Clean stripped check
    clean_check = new_query.lower().strip(" .!?,-\"'")
    if clean_check in NOISE_HALLUCINATIONS or len(clean_check) <= 1:
        return ""

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


_calibrated = False


def SpeechRecognition() -> str:
    """
    Captures audio from microphone and transcribes using Groq Whisper (large-v3, multilingual).
    Rejects ambient noise/clicks, converts Devanagari to Roman Hinglish, and falls back to Google STT.
    """
    global groq_client, _calibrated

    try:
        with sr.Microphone() as source:
            if not _calibrated:
                print("[STT] Calibrating microphone for ambient noise...")
                try:
                    recognizer.adjust_for_ambient_noise(source, duration=0.6)
                    # Enforce reasonable bounds so threshold is neither deaf nor hyper-sensitive
                    recognizer.energy_threshold = max(350, min(recognizer.energy_threshold, 1200))
                except Exception:
                    pass
                _calibrated = True

            print("[Listening...]")
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=15)

        # 0. Noise & Minimum Duration Filter (prevents hallucinations on clicks/whispers)
        raw_audio_bytes = audio.get_raw_data()
        duration_sec = len(raw_audio_bytes) / (audio.sample_rate * audio.sample_width)
        rms = audioop.rms(raw_audio_bytes, 2)

        if duration_sec < 0.5 or rms < 220:
            return ""

        print("[Recognizing...]")
        raw_text = ""

        # 1. Primary Engine: Groq Whisper API (whisper-large-v3)
        if groq_client:
            try:
                wav_bytes = audio.get_wav_data()
                audio_file = io.BytesIO(wav_bytes)
                audio_file.name = "input.wav"

                # Natural conversation prompt style (NOT a meta-instruction)
                transcription = groq_client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3",
                    prompt="Hello Friday. Open YouTube. Kaise ho, kya chal raha hai?",
                    response_format="text"
                )
                raw_text = str(transcription).strip()
            except Exception as ge:
                print(f"[STT WARN] Groq Whisper failed: {ge}. Falling back to Google STT...")
                raw_text = ""

        # 2. Secondary Engine: Google Speech Recognition (Fallback)
        if not raw_text:
            try:
                raw_text = recognizer.recognize_google(audio, language=InputLanguage)
            except Exception:
                try:
                    raw_text = recognizer.recognize_google(audio, language="hi-IN")
                except Exception as gre:
                    print(f"[STT ERROR] Google fallback failed: {gre}")

        if not raw_text:
            return ""

        # 3. Filter noise artifacts & single-word hallucinations
        clean_cand = raw_text.lower().strip(" .!?,-\"'")
        if clean_cand in NOISE_HALLUCINATIONS or len(clean_cand) <= 1:
            print(f"[STT] Discarded noise hallucination: {raw_text!r}")
            return ""

        # 4. Transliterate Devanagari to Hinglish if necessary
        if is_devanagari(raw_text):
            raw_text = devanagari_to_hinglish(raw_text)

        final_query = QueryModifier(raw_text)
        if not final_query or final_query.strip(" .!?,") == "":
            return ""

        print(f"[Heard]: {final_query}")
        return final_query

    except sr.WaitTimeoutError:
        return ""
    except sr.UnknownValueError:
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
