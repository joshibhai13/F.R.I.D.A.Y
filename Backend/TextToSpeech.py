import asyncio
import os
import random
import tempfile
import threading

import edge_tts
import pygame
from dotenv import dotenv_values

print("[DEBUG] Backend.TextToSpeech imported")

# Load .env
env_vars = dotenv_values(".env")
AssistantVoice = env_vars.get("AssistantVoice", "en-US-JennyNeural")

# Init pygame mixer once
pygame.mixer.init()

_current_audio_file = None
_process_lock = threading.Lock()


def StopSpeaking():
    global _current_audio_file
    with _process_lock:
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
        except Exception as e:
            print(f"[DEBUG STOP ERROR] {e}")

        try:
            if _current_audio_file and os.path.exists(_current_audio_file):
                os.remove(_current_audio_file)
        except Exception:
            pass
        finally:
            _current_audio_file = None


async def _generate_tts_audio(text: str, output_file: str):
    communicate = edge_tts.Communicate(text=text, voice=AssistantVoice)
    await communicate.save(output_file)


def TTS(text: str):
    global _current_audio_file

    if not text or not str(text).strip():
        return

    text = str(text).strip()

    try:
        StopSpeaking()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            temp_path = temp_audio.name

        asyncio.run(_generate_tts_audio(text, temp_path))

        with _process_lock:
            _current_audio_file = temp_path
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

    except Exception as e:
        print(f"[DEBUG TTS ERROR] {e}")

    finally:
        with _process_lock:
            try:
                if _current_audio_file and os.path.exists(_current_audio_file):
                    os.remove(_current_audio_file)
            except Exception as e:
                print(f"[DEBUG CLEANUP ERROR] {e}")
            finally:
                _current_audio_file = None


def TextToSpeech(Text: str):
    if not Text:
        return

    Text = str(Text).strip()
    if not Text:
        return

    print(f"[DEBUG TTS CALLED] {Text}")
    print(f"Jarvis: {Text}")
    print(f"[DEBUG VOICE] Using voice: {AssistantVoice}")

    data = Text.split(".")

    responses = [
        "The rest of the result has been printed to the chat screen, kindly check it out sir.",
        "The rest of the text is now on the chat screen, sir, please check it.",
        "You can see the rest of the text on the chat screen, sir.",
        "The remaining part of the text is now on the chat screen, sir.",
        "Sir, you'll find more text on the chat screen for you to see.",
        "The rest of the answer is now on the chat screen, sir.",
        "Sir, please look at the chat screen, the rest of the answer is there.",
        "You'll find the complete answer on the chat screen, sir.",
        "The next part of the text is on the chat screen, sir.",
        "Sir, please check the chat screen for more information."
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