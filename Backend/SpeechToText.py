import audioop
import io
import os
import re
import sys
import requests
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
DeepgramAPIKey = env_vars.get("DEEPGRAM_API_KEY", "").strip()
InputLanguage = env_vars.get("InputLanguage", "en-IN")

recognizer = sr.Recognizer()
recognizer.energy_threshold = 300
recognizer.dynamic_energy_threshold = False  # Fixed threshold prevents sensitivity drift and random noise trigger
recognizer.pause_threshold = 1.0            # 1.0s natural speech pause without mid-sentence cutoffs
recognizer.phrase_threshold = 0.25
recognizer.non_speaking_duration = 0.5

groq_client = None
if GroqAPIKey:
    try:
        groq_client = Groq(api_key=GroqAPIKey)
    except Exception as e:
        print(f"[STT] Groq client warning: {e}")


def has_cyrillic(text: str) -> bool:
    """Detects Russian/Cyrillic characters resulting from Whisper language misidentification."""
    return any(0x0400 <= ord(c) <= 0x04FF for c in text)


def is_unsupported_foreign_script(text: str) -> bool:
    """Detects Cyrillic, Arabic, CJK, Thai, etc. which are never valid English/Hinglish commands."""
    for ch in text:
        code = ord(ch)
        if 0x0400 <= code <= 0x04FF:  # Cyrillic
            return True
        if 0x0600 <= code <= 0x06FF:  # Arabic
            return True
        if (0x4E00 <= code <= 0x9FFF) or (0x3040 <= code <= 0x30FF) or (0xAC00 <= code <= 0xD7AF):  # CJK / Korean
            return True
        if 0x0E00 <= code <= 0x0E7F:  # Thai
            return True
    return False


def remove_repeated_phrases(text: str) -> str:
    """Collapses repetitive hallucination loops like 'word word' or 'phrase phrase'."""
    words = text.split()
    if len(words) >= 4:
        mid = len(words) // 2
        if " ".join(words[:mid]).lower() == " ".join(words[mid:]).lower():
            return " ".join(words[:mid])
    return text


def transcribe_deepgram(wav_data: bytes) -> str:
    """Ultra-accurate Indian English / general English transcription via Deepgram Nova-2."""
    if not DeepgramAPIKey:
        return ""
    try:
        url = "https://api.deepgram.com/v1/listen?model=nova-2&language=en-IN&smart_format=true"
        headers = {
            "Authorization": f"Token {DeepgramAPIKey}",
            "Content-Type": "audio/wav"
        }
        res = requests.post(url, headers=headers, data=wav_data, timeout=4.0)
        if res.status_code == 200:
            data = res.json()
            channels = data.get("results", {}).get("channels", [])
            if channels:
                alts = channels[0].get("alternatives", [])
                if alts:
                    return alts[0].get("transcript", "").strip()
    except Exception as de:
        print(f"[STT WARN] Deepgram fallback error: {de}")
    return ""


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
    "mbc", "sbc", "subtitles", "subtitles by", "watching", "subscribe",
    ".", "..", "...", "bye bye", "thank you", "thanks"
}

WHISPER_HALLUCINATION_PATTERNS = [
    "thank you for watching",
    "thanks for watching",
    "thank you very much for watching",
    "thanks for watching this video",
    "watching this video",
    "for watching",
    "like and subscribe",
    "please like and subscribe",
    "please subscribe",
    "subscribe to my channel",
    "subscribe to the channel",
    "subscribe to our channel",
    "welcome back to my channel",
    "subtitles by",
    "translated by",
    "amara.org",
    "opensubtitles",
    "see you in the next video",
    "see you next time",
    "all rights reserved",
    "closed captioning",
    "captions by",
    "kamu meninggal",
    "meninggal",
    "халь тут",
    "клик",
    "[music]",
    "(music)",
    "[applause]",
    "(applause)",
    "[laughter]",
    "(laughter)",
    "[silence]",
    "(silence)",
    "[sound]",
    "(sound)"
]


def is_whisper_hallucination(text: str) -> bool:
    """Returns True if the text matches silence, YouTube outro, noise artifacts, or foreign scripts."""
    if not text:
        return True
    clean = text.lower().strip(" .!?,-\"'")
    if clean in NOISE_HALLUCINATIONS or len(clean) <= 1:
        return True
    if is_unsupported_foreign_script(text):
        return True
    for pat in WHISPER_HALLUCINATION_PATTERNS:
        if pat in clean:
            return True
    return False


def QueryModifier(query: str) -> str:
    if not query:
        return ""

    new_query = query.strip()

    # Convert Devanagari to Hinglish if present
    if is_devanagari(new_query):
        new_query = devanagari_to_hinglish(new_query)

    # Clean stripped check
    if is_whisper_hallucination(new_query):
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
    Captures audio from microphone and transcribes with maximum accuracy and zero foreign hallucinations:
    1. Primary: Groq Whisper (whisper-large-v3) locked to English (temperature=0.0, prompt-primed)
    2. Secondary: Deepgram Nova-2 (language=en-IN)
    3. Tertiary: Google Speech Recognition (language=en-IN / en-US)
    """
    global groq_client, _calibrated

    try:
        with sr.Microphone() as source:
            if not _calibrated:
                print("[STT] Calibrating microphone for ambient noise...")
                try:
                    recognizer.adjust_for_ambient_noise(source, duration=0.8)
                    recognizer.energy_threshold = max(300, min(recognizer.energy_threshold, 900))
                except Exception:
                    pass
                _calibrated = True

            print("[Listening...]")
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=15)

        # 0. Noise & Minimum Duration Filter (rejects ambient hum and keyboard taps below 130 RMS)
        raw_audio_bytes = audio.get_raw_data()
        duration_sec = len(raw_audio_bytes) / (audio.sample_rate * audio.sample_width)
        rms = audioop.rms(raw_audio_bytes, 2)

        if duration_sec < 0.35 or rms < 130:
            return ""

        print("[Recognizing...]")
        raw_text = ""
        # Convert to pristine 16kHz mono WAV for Whisper & Deepgram
        wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)

        # 1. Primary Engine: Groq Whisper API (whisper-large-v3)
        if groq_client:
            try:
                audio_file = io.BytesIO(wav_bytes)
                audio_file.name = "input.wav"

                whisper_prompt = (
                    "FRIDAY voice assistant. Open YouTube, search Google, play music, "
                    "take note, send email, WhatsApp message, check weather, tell time, goodbye, exit."
                )

                # LANGUAGE='en' PREVENTS WHISPER AUTO-DETECTING RUSSIAN OR INDONESIAN
                # TEMPERATURE=0.0 FORCES DETERMINISTIC GREEDY DECODING WITHOUT RANDOM HALLUCINATIONS
                transcription = groq_client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3",
                    language="en",
                    prompt=whisper_prompt,
                    response_format="text",
                    temperature=0.0
                )
                cand = str(transcription).strip()
                # Reject if language confused or silence/outro hallucination
                if cand and not is_whisper_hallucination(cand):
                    raw_text = cand
            except Exception as ge:
                print(f"[STT WARN] Groq Whisper error: {ge}. Trying Deepgram / Google...")
                raw_text = ""

        # 2. Secondary Engine: Deepgram Nova-2 (Accurate Indian English & Hinglish)
        if not raw_text and DeepgramAPIKey:
            try:
                cand = transcribe_deepgram(wav_bytes)
                if cand and not is_whisper_hallucination(cand):
                    raw_text = cand
            except Exception as dge:
                print(f"[STT WARN] Deepgram failed: {dge}")

        # 3. Tertiary Engine: Google Speech Recognition (Fallback)
        if not raw_text:
            try:
                cand = recognizer.recognize_google(audio, language=InputLanguage)
                if cand and not is_whisper_hallucination(cand):
                    raw_text = cand
            except Exception:
                try:
                    cand = recognizer.recognize_google(audio, language="en-IN")
                    if cand and not is_whisper_hallucination(cand):
                        raw_text = cand
                except Exception:
                    try:
                        cand = recognizer.recognize_google(audio, language="en-US")
                        if cand and not is_whisper_hallucination(cand):
                            raw_text = cand
                    except Exception as gre:
                        print(f"[STT ERROR] Google fallback failed: {gre}")

        if not raw_text:
            return ""

        # 4. Filter noise artifacts & single-character hallucinations
        if is_whisper_hallucination(raw_text):
            print(f"[STT] Discarded noise hallucination: {raw_text!r}")
            return ""

        # 5. Remove repetitive loop hallucinations (e.g. repeated phrases)
        raw_text = remove_repeated_phrases(raw_text)

        # 6. Transliterate Devanagari to Hinglish if present
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
