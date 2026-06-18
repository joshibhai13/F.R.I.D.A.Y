import os
import cv2
import pytesseract
import numpy as np
from deep_translator import GoogleTranslator

# If needed on Windows, uncomment and correct this path:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


class SimpleImageRecognition:
    def __init__(self):
        self.yolo_model = None
        self.yolo_available = False

    def _load_yolo(self):
        if self.yolo_model is not None:
            return

        try:
            from ultralytics import YOLO
            self.yolo_model = YOLO("yolov8n.pt")
            self.yolo_available = True
            print("[ImageRecognition] YOLO loaded successfully.")
        except Exception as e:
            self.yolo_model = None
            self.yolo_available = False
            print(f"[ImageRecognition] YOLO not available: {e}")

    def _read_image(self, image_path):
        if not os.path.exists(image_path):
            return None, "Image file not found."

        image = cv2.imread(image_path)
        if image is None:
            return None, "Could not read image."

        return image, None

    def extract_text(self, image_path):
        image, error = self._read_image(image_path)
        if error:
            return error

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        text = pytesseract.image_to_string(gray).strip()
        if not text:
            return "No text detected in the image."

        return text

    def translate_extracted_text(self, image_path, target_lang="en"):
        text = self.extract_text(image_path)

        if text.startswith("Image file not found") or \
           text.startswith("Could not read image") or \
           text.startswith("No text detected"):
            return text

        try:
            translated = GoogleTranslator(source="auto", target=target_lang).translate(text)
            return f"Detected text:\n{text}\n\nTranslated text:\n{translated}"
        except Exception as e:
            return f"Translation failed. Detected text:\n{text}\n\nError: {e}"

    def detect_objects(self, image_path):
        image, error = self._read_image(image_path)
        if error:
            return error

        self._load_yolo()

        if not self.yolo_available or self.yolo_model is None:
            return "Object detection is not available right now."

        try:
            results = self.yolo_model(image)
            names = results[0].names

            found = []
            for box in results[0].boxes:
                cls_id = int(box.cls[0].item())
                label = names[cls_id]
                found.append(label)

            if not found:
                return "No objects detected."

            unique_found = sorted(set(found))
            return "Detected objects: " + ", ".join(unique_found)

        except Exception as e:
            return f"Object detection failed: {e}"

    def describe_image_basic(self, image_path):
        image, error = self._read_image(image_path)
        if error:
            return error

        h, w = image.shape[:2]
        return f"The image was received successfully. Resolution: {w}x{h}."

    def analyze_image(self, image_path, query):
        query = (query or "").lower().strip()

        if not query:
            return self.describe_image_basic(image_path)

        if "translate" in query and "text" in query:
            return self.translate_extracted_text(image_path, target_lang="en")

        if "translate" in query:
            return self.translate_extracted_text(image_path, target_lang="en")

        if "read" in query or "text" in query or "ocr" in query:
            text = self.extract_text(image_path)
            return f"Detected text:\n{text}"

        if "object" in query or "what is this" in query or "identify" in query:
            return self.detect_objects(image_path)

        if "describe" in query:
            return self.describe_image_basic(image_path)

        return self.describe_image_basic(image_path)


recognizer = SimpleImageRecognition()


def analyze_image(image_path, query):
    return recognizer.analyze_image(image_path, query)