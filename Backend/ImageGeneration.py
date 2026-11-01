import asyncio
from random import randint
from PIL import Image
import requests
from dotenv import dotenv_values
import os
import urllib.parse
from time import sleep
import sys

env_vars = dotenv_values(".env")
POLLINATIONS_API_KEY = env_vars.get("PollinationsAPIKey", "").strip()
HUGGINGFACE_API_KEY = env_vars.get("HuggingFaceAPIKey", "").strip()

def open_images(prompt):
    folder_path = r"Data"
    safe_prompt = "".join(c for c in prompt if c.isalnum() or c in (' ', '_')).rstrip().replace(" ", "_")
    files = [f"{safe_prompt}{i}.jpg" for i in range(1, 5)]

    opened = False
    for jpg_file in files:
        image_path = os.path.join(folder_path, jpg_file)
        if os.path.exists(image_path):
            try:
                img = Image.open(image_path)
                print(f"[INFO] Opening image: {image_path}")
                img.show()
                opened = True
                sleep(0.5)
            except Exception as e:
                print(f"[WARN] Unable to open {image_path}: {e}")
    if not opened:
        print("[WARN] No generated images were available to display.")

def fetch_single_image(prompt: str, seed: int, index: int) -> bytes:
    """Fetches a single image with multiple fallback routes."""
    encoded_prompt = urllib.parse.quote(prompt)
    
    # 1. Primary: Pollinations Gen API with User Key (FLUX model)
    if POLLINATIONS_API_KEY:
        url = f"https://gen.pollinations.ai/image/{encoded_prompt}?model=flux&key={POLLINATIONS_API_KEY}&width=1024&height=1024&nologo=true&seed={seed}"
        try:
            headers = {"Authorization": f"Bearer {POLLINATIONS_API_KEY}"}
            resp = requests.get(url, headers=headers, timeout=25)
            if resp.status_code == 200 and len(resp.content) > 2000:
                print(f"[POLLINATIONS] Image {index} generated successfully via FLUX.")
                return resp.content
        except Exception as e:
            print(f"[WARN] Pollinations Gen endpoint failed for image {index}: {e}")

    # 2. Secondary: Pollinations direct image endpoint
    url2 = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model=flux&nologo=true&seed={seed}"
    try:
        resp = requests.get(url2, timeout=20)
        if resp.status_code == 200 and len(resp.content) > 2000:
            print(f"[POLLINATIONS] Image {index} generated via secondary route.")
            return resp.content
    except Exception as e:
        print(f"[WARN] Pollinations secondary route failed for image {index}: {e}")

    # 3. Tertiary Fallback: Hugging Face if key available
    if HUGGINGFACE_API_KEY:
        hf_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
        headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
        payload = {"inputs": f"{prompt}, 4k, sharp, high quality, seed = {seed}"}
        try:
            resp = requests.post(hf_url, headers=headers, json=payload, timeout=25)
            if resp.status_code == 200 and len(resp.content) > 2000:
                print(f"[HUGGINGFACE] Image {index} generated via SDXL fallback.")
                return resp.content
        except Exception as e:
            print(f"[WARN] HuggingFace fallback failed: {e}")

    return b""

async def generate_images(prompt: str):
    tasks = []
    # Generate 2 ultra-high-definition variations concurrently for speed & quality
    num_images = 2
    for i in range(1, num_images + 1):
        seed = randint(1, 9999999)
        task = asyncio.to_thread(fetch_single_image, prompt, seed, i)
        tasks.append(task)

    image_bytes_list = await asyncio.gather(*tasks)
    safe_prompt = "".join(c for c in prompt if c.isalnum() or c in (' ', '_')).rstrip().replace(" ", "_")
    os.makedirs("Data", exist_ok=True)

    saved_count = 0
    for i, image_bytes in enumerate(image_bytes_list):
        if image_bytes and len(image_bytes) > 2000:
            file_path = os.path.join("Data", f"{safe_prompt}{i + 1}.jpg")
            with open(file_path, "wb") as f:
                f.write(image_bytes)
            saved_count += 1
        else:
            print(f"[WARN] Image {i + 1} could not be generated.")

    print(f"[INFO] Successfully saved {saved_count} images to Data directory.")

def GenerateImages(prompt: str):
    print(f"\n[INFO] Generating images for '{prompt}' using Pollinations AI (FLUX)...")
    asyncio.run(generate_images(prompt))
    print("[INFO] Image generation complete. Opening preview...")
    open_images(prompt)

if __name__ == "__main__":
    data_file_path = r"Frontend\Files\ImageGeneration.data"
    
    if not os.path.exists(data_file_path):
        os.makedirs(os.path.dirname(data_file_path), exist_ok=True)
        with open(data_file_path, "w", encoding="utf-8") as f:
            f.write("False,False")

    print("[INFO] F.R.I.D.A.Y. ImageGeneration Service Active (Powered by Pollinations.ai FLUX).")

    while True:
        try:
            with open(data_file_path, "r", encoding="utf-8") as f:
                data = f.read().strip()

            if data and "," in data:
                Prompt, Status = data.split(",", 1)

                if Status.strip().lower() == "true":
                    print(f"[TASK] Received image prompt: {Prompt}")
                    GenerateImages(prompt=Prompt.strip())

                    with open(data_file_path, "w", encoding="utf-8") as f:
                        f.write("False,False")
            
            sleep(1.5)

        except Exception as e:
            print(f"[ERROR in ImageGeneration loop]: {e}")
            with open(data_file_path, "w", encoding="utf-8") as f:
                f.write("False,False")
            sleep(2)
