import asyncio
from random import randint 
from PIL import Image
import requests
from dotenv import get_key
import os
from time import sleep
import sys

def open_images(prompt):
    folder_path = r"Data"
    safe_prompt = "".join(c for c in prompt if c.isalnum() or c in (' ', '_')).rstrip().replace(" ", "_")
    Files = [f"{safe_prompt}{i}.jpg" for i in range (1, 5)]

    for jpg_file in Files:
        image_path = os.path.join(folder_path, jpg_file)
        try:
            img = Image.open(image_path)
            print(f"Opening image: {image_path}")
            img.show()
            sleep(1)
        except IOError:
            print(f"Unable to open {image_path}")

API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
headers = {"Authorization": f"Bearer {get_key('.env', 'HuggingFaceAPIKey')}"}

async def query(payload):
    response = await asyncio.to_thread(requests.post, API_URL, headers=headers, json=payload)
    return response.content

async def generate_images(prompt: str):
    tasks = []
    for _ in range (4):
        payload = { "inputs": f"{prompt}, 4k, sharp, high quality, detailed, seed = {randint(0, 1000000)}" }
        tasks.append(asyncio.create_task(query(payload)))

    image_bytes_list = await asyncio.gather(*tasks)
    safe_prompt = "".join(c for c in prompt if c.isalnum() or c in (' ', '_')).rstrip().replace(" ", "_")
    os.makedirs("Data", exist_ok=True)

    for i, image_bytes in enumerate(image_bytes_list):
        if image_bytes and len(image_bytes) > 1000:
            with open(fr"Data\{safe_prompt}{i + 1}.jpg", "wb") as f:
                f.write(image_bytes)
        else:
            print(f"Image {i+1} generate nahi ho payi (API se khali response mila).")

def GenerateImages(prompt: str):
    print(f"\n[INFO] '{prompt}' ke liye images generate ho rahi hain...")
    asyncio.run(generate_images(prompt))
    print("[INFO] Images generate ho gayi hain. Ab unhein khola ja raha hai...")
    open_images(prompt)     

# --- AAPKA ORIGINAL LOGIC (FIXED) ---
# Ab yeh script file se command padhega
if __name__ == "__main__":
    # File ka path
    data_file_path = r"Frontend\Files\ImageGeneration.data"
    
    # Ensure the file exists with a default state
    if not os.path.exists(data_file_path):
        with open(data_file_path, "w") as f:
            f.write("False,False")

    while True:
        try: 
            with open(data_file_path, "r") as f:
                data = f.read()

            if data:
                Prompt, Status = data.split(",", 1)

                if Status == "True":
                    print(f"Generating Images for prompt: {Prompt}")
                    GenerateImages(prompt=Prompt)

                    # Kaam hone ke baad file ko reset karein
                    with open(data_file_path, "w") as f:
                        f.write("False,False")
            
            sleep(2) # CPU usage kam karne ke liye

        except Exception as e:
            print(f"[ERROR in ImageGeneration loop]: {e}")
            # Error aane par file ko reset karein
            with open(data_file_path, "w") as f:
                f.write("False,False")
            sleep(2)

