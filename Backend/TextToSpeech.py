import asyncio
import audioop
import os
import random
import tempfile
import threading
import time
import urllib.parse
import edge_tts
import pygame
import requests
from dotenv import dotenv_values

print("[DEBUG] Backend.TextToSpeech imported")

# Load .env
env_vars = dotenv_values(".env")
AssistantVoice = env_vars.get("AssistantVoice", "en-US-JennyNeural")
PollinationsAPIKey = env_vars.get("PollinationsAPIKey", "sk_jIkDUB6ABQ4RMBQkzH2TdE4E88ywL80A")

# Initialize pygame mixer once
try:
    pygame.mixer.init()
except Exception as e:
    print(f"[TTS WARN] pygame.mixer init error: {e}")

_current_audio_file = None
_process_lock = threading.Lock()
_is_speaking = False
_stop_speaking_flag = threading.Event()


def is_speaking() -> bool:
    """Returns True if the assistant is currently speaking."""
    return _is_speaking


def StopSpeaking():
    """Immediately stops audio playback and cleans up audio files."""
    global _current_audio_file, _is_speaking
    _stop_speaking_flag.set()
    _is_speaking = False

    with _process_lock:
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            # CRITICAL: unload() releases the Windows file lock preventing WinError 32
            if hasattr(pygame.mixer.music, "unload"):
                pygame.mixer.music.unload()
        except Exception as e:
            pass

        try:
            if _current_audio_file and os.path.exists(_current_audio_file):
                time.sleep(0.05)
                os.remove(_current_audio_file)
        except Exception:
            pass
        finally:
            _current_audio_file = None


def _monitor_interruption(stop_event):
    """
    Background listener that detects user voice during TTS playback.
    If the user speaks (barge-in), it halts playback immediately.
    """
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )

        voice_detected_count = 0
        THRESHOLD = 1100  # Voice RMS threshold

        while not stop_event.is_set():
            try:
                data = stream.read(1024, exception_on_overflow=False)
                rms = audioop.rms(data, 2)
                if rms > THRESHOLD:
                    voice_detected_count += 1
                    if voice_detected_count >= 2:
                        print("[TTS] User interruption detected! Stopping speech.")
                        StopSpeaking()
                        break
                else:
                    voice_detected_count = max(0, voice_detected_count - 1)
            except Exception:
                break

        stream.stop_stream()
        stream.close()
        p.terminate()
    except Exception:
        pass


async def _generate_edge_tts(text: str, output_file: str):
    communicate = edge_tts.Communicate(text=text, voice=AssistantVoice)
    await communicate.save(output_file)


def _generate_pollinations_audio(text: str, output_file: str) -> bool:
    """Fallback TTS using Pollinations Audio API."""
    try:
        encoded_text = urllib.parse.quote(text[:300])
        url = f"https://gen.pollinations.ai/audio/{encoded_text}?voice=nova"
        headers = {}
        if PollinationsAPIKey:
            headers["Authorization"] = f"Bearer {PollinationsAPIKey}"
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200 and len(resp.content) > 1000:
            with open(output_file, "wb") as f:
                f.write(resp.content)
            return True
    except Exception as e:
        print(f"[TTS WARN] Pollinations Audio failed: {e}")
    return False


def _generate_pyttsx3_fallback(text: str):
    """Last-resort offline TTS engine."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        return True
    except Exception as pe:
        print(f"[TTS ERROR] pyttsx3 fallback error: {pe}")
        return False


def TTS(text: str):
    global _current_audio_file, _is_speaking

    if not text or not str(text).strip():
        return

    text = str(text).strip()

    try:
        StopSpeaking()
        _stop_speaking_flag.clear()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            temp_path = temp_audio.name

        generated = False

        # 1. Primary: edge-tts (fast, high-quality neural voice)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_generate_edge_tts(text, temp_path))
            loop.close()
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 500:
                generated = True
        except Exception as e:
            print(f"[TTS WARN] edge-tts generation failed: {e}. Trying Pollinations audio...")

        # 2. Secondary: Pollinations Audio API
        if not generated:
            generated = _generate_pollinations_audio(text, temp_path)

        # 3. Offline fallback: pyttsx3
        if not generated:
            print("[TTS WARN] Cloud TTS unavailable, using local voice engine...")
            _generate_pyttsx3_fallback(text)
            return

        # Play generated audio
        with _process_lock:
            _current_audio_file = temp_path
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            _is_speaking = True

        # Start interruption listener in daemon thread
        monitor_stop = threading.Event()
        interruption_thread = threading.Thread(
            target=_monitor_interruption, args=(monitor_stop,), daemon=True
        )
        interruption_thread.start()

        # Playback loop
        while pygame.mixer.music.get_busy() and not _stop_speaking_flag.is_set():
            pygame.time.Clock().tick(15)

        monitor_stop.set()

    except Exception as e:
        print(f"[DEBUG TTS ERROR] {e}")

    finally:
        _is_speaking = False
        with _process_lock:
            try:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
                if hasattr(pygame.mixer.music, "unload"):
                    pygame.mixer.music.unload()
            except Exception:
                pass

            try:
                if _current_audio_file and os.path.exists(_current_audio_file):
                    time.sleep(0.04)
                    os.remove(_current_audio_file)
            except Exception as e:
                # Silently catch cleanup glitch on Windows
                pass
            finally:
                _current_audio_file = None


def TextToSpeech(Text: str):
    if not Text:
        return

    Text = str(Text).strip()
    if not Text:
        return

    print(f"[DEBUG TTS CALLED] {Text}")
    print(f"FRIDAY: {Text}")

    data = Text.split(".")

    responses = [
        "The rest of the result has been printed to the chat screen, kindly check it out sir.",
        "The rest of the text is now on the chat screen, sir, please check it.",
        "You can see the rest of the text on the chat screen, sir.",
        "The remaining part of the text is now on the chat screen, sir.",
        "The rest of the answer is now on the chat screen, sir."
    ]

    if len(data) > 4 and len(Text) > 250:
        short_text = " ".join(Text.split(".")[0:2]).strip() + ". " + random.choice(responses)
        TTS(short_text)
    else:
        TTS(Text)


if __name__ == "__main__":
    while True:
        user_input = input("Text to speak (or type 'exit'): ").strip()
        if user_input.lower() == "exit":
            break
        TextToSpeech(user_input)
