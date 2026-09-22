# Backend/camera.py

import cv2
import os
import numpy as np
import torch
import insightface
from insightface.app import FaceAnalysis
import time
from gesture_logic import GestureInterpreter # Nayi logic import karein

# Communication Files
GESTURE_COMMAND_FILE = "Frontend/Files/gesture_command.data"
HOLOGRAM_OBJECT_FILE = "Frontend/Files/HologramObject.data"

class VisionSystem:
    def __init__(self):
        print("[INFO] Jarvis Advanced Vision System (Precise Gestures) chalu ho raha hai...")

        if torch.cuda.is_available(): self.device = 'cuda'
        else: self.device = 'cpu'
        print(f"[INFO] Device: {self.device}")
        
        print("[INFO] AI models load ho rahe hain...")
        self.face_app = FaceAnalysis(name='buffalo_l', providers=['CUDAExecutionProvider' if self.device == 'cuda' else 'CPUExecutionProvider'])
        self.face_app.prepare(ctx_id=0, det_size=(640, 640))

        try:
            from ultralytics import YOLO
            # --- DONO MODELS KO LOAD KAREIN ---
            model_path = "Backend/Models/"
            self.object_model = YOLO("yolov8n.pt") # Changed to nano model to save GPU load
            self.object_model.to(self.device)
            print("[INFO] Body Pose model (yolov8n-pose.pt) load ho raha hai...")
            self.pose_model = YOLO(os.path.join(model_path, "yolov8n-pose.pt"))
            self.pose_model.to(self.device)
        except Exception as e:
            print(f"[FATAL ERROR] Object/Body Pose Model load nahi ho paya: {e}")
            exit()
            
        try:
            print("[INFO] Hand Pose model (yolov8n-hand-pose.pt) load ho raha hai...")
            self.hand_model = YOLO(os.path.join(model_path, "yolov8n-hand-pose.pt"))
            self.hand_model.to(self.device)
        except Exception as e:
            print(f"[WARNING] Hand Pose model load nahi ho paya. Hand gestures disabled. Error: {e}")
            self.hand_model = None
        
        print("[INFO] AI models safaltapoorvak load ho gaye.")

        # (Baaki __init__ ka code waisa hi rahega)
        self.faces_dir = "Data/faces"
        self.known_face_embeddings = []
        self.known_face_names = []
        self.load_known_faces()
        
        cam_index = 0
        try:
            with open(os.path.join("Frontend", "Files", "CameraIndex.data"), "r") as f:
                cam_index = int(f.read().strip())
        except:
            pass
        self.cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)
        
        if not self.cap.isOpened(): exit()
        self.potential_weapons = ['knife', 'scissors', 'bat', 'handgun', 'gun', 'rifle']
        self.last_known_faces = []
        self.last_known_objects = []
        
        # Keep track of unique person IDs
        self.unique_people_ids = set()
        self.last_known_poses = []
        self.gesture_interpreter = GestureInterpreter()
        self.last_gesture_time = 0
        self.gesture_cooldown = 2
        with open(GESTURE_COMMAND_FILE, "w") as f: f.write("NONE")
        print("[INFO] Advanced Vision System taiyar hai.")

    def load_known_faces(self):
        # (Yeh function waisa hi hai, ismein koi badlav nahi)
        print("[INFO] Face database load ho raha hai...")
        os.makedirs(self.faces_dir, exist_ok=True)
        self.known_face_embeddings = []
        self.known_face_names = []
        for name in os.listdir(self.faces_dir):
            person_dir = os.path.join(self.faces_dir, name)
            if os.path.isdir(person_dir):
                for filename in os.listdir(person_dir):
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                        image_path = os.path.join(person_dir, filename)
                        try:
                            img = cv2.imread(image_path)
                            faces = self.face_app.get(img)
                            if faces:
                                self.known_face_embeddings.append(faces[0].normed_embedding)
                                self.known_face_names.append(name)
                                print(f"  - {name} ka chehra load hua.")
                                break 
                        except Exception as e:
                            print(f"[ERROR] {filename} load nahi ho payi: {e}")
        print(f"[INFO] Face database taiyar. {len(self.known_face_names)} log pehchan mein.")

    def draw_aim_reticle(self, frame, center, max_radius=30, color=(0, 0, 255)):
        # (Yeh function waisa hi hai)
        tick_len = 10
        cv2.line(frame, (center[0] - max_radius, center[1] - max_radius), (center[0] - max_radius + tick_len, center[1] - max_radius), color, 2)
        cv2.line(frame, (center[0] - max_radius, center[1] - max_radius), (center[0] - max_radius, center[1] - max_radius + tick_len), color, 2)
        cv2.line(frame, (center[0] + max_radius, center[1] - max_radius), (center[0] + max_radius - tick_len, center[1] - max_radius), color, 2)
        cv2.line(frame, (center[0] + max_radius, center[1] - max_radius), (center[0] + max_radius, center[1] - max_radius + tick_len), color, 2)
        cv2.line(frame, (center[0] - max_radius, center[1] + max_radius), (center[0] - max_radius + tick_len, center[1] + max_radius), color, 2)
        cv2.line(frame, (center[0] - max_radius, center[1] + max_radius), (center[0] - max_radius, center[1] + max_radius - tick_len), color, 2)
        cv2.line(frame, (center[0] + max_radius, center[1] + max_radius), (center[0] + max_radius - tick_len, center[1] + max_radius), color, 2)
        cv2.line(frame, (center[0] + max_radius, center[1] + max_radius), (center[0] + max_radius, center[1] + max_radius - tick_len), color, 2)
        cv2.circle(frame, center, 2, color, -1)

    def draw_fancy_box(self, frame, pt1, pt2, color, thickness, r, d):
        # (Yeh function waisa hi hai)
        x1, y1 = pt1; x2, y2 = pt2
        cv2.line(frame, (x1 + r, y1), (x1 + r + d, y1), color, thickness)
        cv2.line(frame, (x1, y1 + r), (x1, y1 + r + d), color, thickness)
        cv2.ellipse(frame, (x1 + r, y1 + r), (r, r), 180, 0, 90, color, thickness)
        cv2.line(frame, (x2 - r, y1), (x2 - r - d, y1), color, thickness)
        cv2.line(frame, (x2, y1 + r), (x2, y1 + r + d), color, thickness)
        cv2.ellipse(frame, (x2 - r, y1 + r), (r, r), 270, 0, 90, color, thickness)
        cv2.line(frame, (x1 + r, y2), (x1 + r + d, y2), color, thickness)
        cv2.line(frame, (x1, y2 - r), (x1, y2 - r - d), color, thickness)
        cv2.ellipse(frame, (x1 + r, y2 - r), (r, r), 90, 0, 90, color, thickness)
        cv2.line(frame, (x2 - r, y2), (x2 - r - d, y2), color, thickness)
        cv2.line(frame, (x2, y2 - r), (x2, y2 - r - d), color, thickness)
        cv2.ellipse(frame, (x2 - r, y2 - r), (r, r), 0, 0, 90, color, thickness)

    def run(self, callback=None):
        import socket
        import struct
        import time
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connected = False
        # Retry connection to GUI server for up to 10 seconds
        for _ in range(10):
            try:
                client_socket.connect(('127.0.0.1', 5005))
                connected = True
                break
            except Exception:
                time.sleep(1)
                
        frame_count = 0
        frame_skip = 2
        
        while True:
            success, frame = self.cap.read()
            if not success: break
            
            frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_AREA)
            
            frame_count += 1
            if frame_count % frame_skip == 0:
                self.last_known_faces, self.last_known_objects, self.last_known_poses = self.process_frame(frame)

            self.draw_detections(frame, self.last_known_faces, self.last_known_objects, self.last_known_poses)

            if connected:
                try:
                    result, encimg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                    data = encimg.tobytes()
                    client_socket.sendall(struct.pack("Q", len(data)))
                    client_socket.sendall(data)
                except Exception:
                    break # GUI probably closed, exit subprocess
            else:
                break # Could not connect, exit

    def process_frame(self, frame):
        # (Face and Object detection logic waisa hi hai)
        recognized_people = {}
        detected_faces = []
        faces = self.face_app.get(frame)
        if faces:
            for face in faces:
                name = "Unidentified"
                if self.known_face_embeddings:
                    embedding = face.normed_embedding
                    scores = np.dot(self.known_face_embeddings, embedding)
                    best_match_index = np.argmax(scores)
                    if scores[best_match_index] > 0.5:
                        name = self.known_face_names[best_match_index]
                box = face.bbox.astype(int)
                recognized_people[tuple(box)] = name
                detected_faces.append((box, name))

        detected_objects = []
        obj_results = self.object_model.track(source=frame, persist=True, verbose=False, device=self.device)
        for result in obj_results:
            # Handle tracking IDs for people
            if result.boxes.id is not None:
                track_ids = result.boxes.id.int().cpu().tolist()
                for box, track_id in zip(result.boxes, track_ids):
                    if self.object_model.names[int(box.cls[0])] == 'person':
                        self.unique_people_ids.add(track_id)
                        
            # Handle objects normally
            for box in result.boxes:
                confidence = float(box.conf[0])
                class_name = self.object_model.names[int(box.cls[0])]
                if confidence > 0.6 and class_name != 'person':
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    detected_objects.append(((x1, y1, x2, y2), class_name))

        # Write the most prominent detected object to Hologram file
        if detected_objects:
            # Pick the largest object (by bounding box area)
            largest = max(detected_objects, key=lambda o: (o[0][2]-o[0][0]) * (o[0][3]-o[0][1]))
            try:
                with open(HOLOGRAM_OBJECT_FILE, "w") as f:
                    f.write(largest[1])
            except:
                pass

        # --- GESTURE & THREAT DETECTION LOGIC (UPDATED WITH FIX) ---
        body_pose_results = self.pose_model.predict(source=frame, verbose=False, device=self.device)
        hand_pose_results = self.hand_model.predict(source=frame, verbose=False, device=self.device) if self.hand_model else []

        # --- ERROR FIX --- Check karein ki result mein box hai ya nahi
        body_keypoints_list = [{'box': r.boxes.xyxy[0].cpu().numpy(), 'keypoints': r.keypoints.data[0].cpu().numpy()} for r in body_pose_results if r.keypoints is not None and r.boxes]
        hand_keypoints_list = [{'box': r.boxes.xyxy[0].cpu().numpy(), 'keypoints': r.keypoints.data[0].cpu().numpy()} for r in hand_pose_results if r.keypoints is not None and r.boxes]

        # Gesture command ko interpret karein
        current_time = time.time()
        if current_time - self.last_gesture_time > self.gesture_cooldown:
            gesture = self.gesture_interpreter.interpret(body_keypoints_list, hand_keypoints_list)
            if gesture:
                print(f"[GESTURE DETECTED] >> {gesture} <<")
                with open(GESTURE_COMMAND_FILE, "w") as f:
                    f.write(gesture)
                self.last_gesture_time = current_time

        # Threat detection (waisa hi hai, body pose par based)
        detected_poses = []
        for result in body_pose_results:
            if result.keypoints and result.boxes:
                keypoints = result.keypoints.data[0].cpu().numpy()
                box = result.boxes.xyxy[0].cpu().numpy().astype(int)
                
                person_name = "Unidentified"
                for face_box, name in recognized_people.items():
                    if not (box[2] < face_box[0] or box[0] > face_box[2] or box[3] < face_box[1] or box[1] > face_box[3]):
                        person_name = name
                        break

                eye_l, eye_r, nose = keypoints[1], keypoints[2], keypoints[0]
                eye_midpoint = ((eye_l[0] + eye_r[0]) / 2, (eye_l[1] + eye_r[1]) / 2)
                eye_nose_dist = np.linalg.norm(np.array(eye_midpoint) - np.array(nose[:2]))
                forehead_pos = (int(eye_midpoint[0]), int(eye_midpoint[1] - eye_nose_dist * 1.2))

                r_shoulder, l_shoulder = keypoints[6], keypoints[5]
                r_elbow, l_elbow = keypoints[8], keypoints[7]
                r_wrist, l_wrist = keypoints[10], keypoints[9]

                is_threat = False
                if person_name.lower() != 'pruthvi':
                    if (r_wrist[1] < r_elbow[1] and l_wrist[1] < l_elbow[1]): is_threat = True
                    dist_sr = np.linalg.norm(r_shoulder[:2] - r_wrist[:2])
                    dist_se = np.linalg.norm(r_shoulder[:2] - r_elbow[:2])
                    if dist_sr > dist_se * 1.8: is_threat = True

                for obj_box, class_name in detected_objects:
                    if class_name in self.potential_weapons:
                        if not (box[2] < obj_box[0] or box[0] > obj_box[2] or box[3] < obj_box[1] or box[1] > obj_box[3]):
                            is_threat = True
                            break
                
                status = "NEUTRAL"
                if is_threat: status = "THREAT"
                if r_wrist[1] < r_shoulder[1] and l_wrist[1] < l_shoulder[1]: status = "HANDS UP"
                
                detected_poses.append((box, status, forehead_pos))
        
        return detected_faces, detected_objects, detected_poses

    def draw_detections(self, frame, faces, objects, poses):
        # Draw HUD stats
        total_unique_people = len(self.unique_people_ids)
        verified = sum(1 for _, name in faces if name.lower() != 'unknown' and name.lower() != 'unidentified')
        unverified = sum(1 for _, name in faces if name.lower() == 'unknown' or name.lower() == 'unidentified')
        
        # Draw semi-transparent background for HUD
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (320, 100), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        cv2.putText(frame, f"TOTAL UNIQUE PEOPLE: {total_unique_people}", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"LIVE VERIFIED: {verified}", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, f"LIVE UNVERIFIED: {unverified}", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        for (box, name) in faces:
            x1, y1, x2, y2 = box
            color = (0, 255, 255)
            self.draw_fancy_box(frame, (x1, y1), (x2, y2), color, 2, 10, 25)
            cv2.putText(frame, name.upper(), (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        for (box, class_name) in objects:
            x1, y1, x2, y2 = box
            color = (255, 0, 255)
            self.draw_fancy_box(frame, (x1, y1), (x2, y2), color, 2, 10, 25)
            cv2.putText(frame, class_name.upper(), (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        for (box, status, head_pos) in poses:
            if status == "THREAT":
                self.draw_aim_reticle(frame, head_pos)
                cv2.putText(frame, status, (box[0], box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            elif status == "HANDS UP":
                cv2.putText(frame, status, (box[0], box[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

if __name__ == "__main__":
    vision_system = VisionSystem()
    vision_system.run()
