from Backend.TextToSpeech import TextToSpeech
from Frontend.GUI import ShowTextToScreen
from dotenv import dotenv_values

def jarvis_introduction():
    env_vars = dotenv_values(".env")
    Username = env_vars.get("Username", "User")
    Assistantname = env_vars.get("Assistantname", "Jarvis")
    intro_message = f"{Assistantname}: Hello {Username}! I am {Assistantname}, your AI assistant. I'm here to help with information, automation, and more. Just say or type your request!"
    ShowTextToScreen(intro_message)
    TextToSpeech(intro_message)