import os
import requests
import json
import urllib.parse
from dotenv import dotenv_values

env_vars = dotenv_values(".env")
POLLINATIONS_API_KEY = env_vars.get("PollinationsAPIKey", "sk_jIkDUB6ABQ4RMBQkzH2TdE4E88ywL80A").strip()

BASE_URL = "https://gen.pollinations.ai"

def get_headers():
    headers = {"Content-Type": "application/json"}
    if POLLINATIONS_API_KEY:
        headers["Authorization"] = f"Bearer {POLLINATIONS_API_KEY}"
    return headers

def generate_chat_completion(messages, model="openai", temperature=0.7, max_tokens=1024, timeout=20):
    """
    Sends a chat completion request to Pollinations.ai (OpenAI-compatible).
    Returns the string answer or None if failed.
    """
    url = f"{BASE_URL}/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    try:
        resp = requests.post(url, headers=get_headers(), json=payload, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            choices = data.get("choices", [])
            if choices and "message" in choices[0]:
                return choices[0]["message"].get("content", "").strip()
        else:
            print(f"[POLLINATIONS] HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"[POLLINATIONS] Error during chat completion: {e}")

    # Fallback endpoint if /v1/chat/completions has an issue:
    try:
        # Simple text prompt fallback using last user message
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_msg = m.get("content", "")
                break
        if user_msg:
            fallback_url = f"{BASE_URL}/text/{urllib.parse.quote(user_msg)}"
            f_resp = requests.get(fallback_url, headers=get_headers(), timeout=timeout)
            if f_resp.status_code == 200 and len(f_resp.text) > 0:
                return f_resp.text.strip()
    except Exception as fe:
        print(f"[POLLINATIONS] Fallback text route error: {fe}")

    return None

def generate_image_url(prompt, model="flux", width=1024, height=1024, seed=None):
    """
    Generates a direct Pollinations image URL.
    """
    encoded_prompt = urllib.parse.quote(prompt)
    seed_str = f"&seed={seed}" if seed is not None else ""
    key_str = f"&key={POLLINATIONS_API_KEY}" if POLLINATIONS_API_KEY else ""
    return f"{BASE_URL}/image/{encoded_prompt}?model={model}{key_str}&width={width}&height={height}&nologo=true{seed_str}"

if __name__ == "__main__":
    test_msg = [{"role": "user", "content": "Respond with 'Pollinations AI is online and operational.'"}]
    res = generate_chat_completion(test_msg)
    print("Test Result:", res)
