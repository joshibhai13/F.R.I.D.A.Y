# Backend/gesture_logic.py

import numpy as np

class GestureInterpreter:
    def __init__(self):
        """
        Body aur Hand keypoints ko analyze karke alag-alag advanced gestures pehchanta hai.
        """
        self.body_kp_indices = {
            'nose': 0, 'l_eye': 1, 'r_eye': 2, 'l_ear': 3, 'r_ear': 4,
            'l_shoulder': 5, 'r_shoulder': 6, 'l_elbow': 7, 'r_elbow': 8,
            'l_wrist': 9, 'r_wrist': 10
        }
        self.hand_kp_indices = {
            'wrist': 0, 'thumb_cmc': 1, 'thumb_mcp': 2, 'thumb_ip': 3, 'thumb_tip': 4,
            'index_mcp': 5, 'index_pip': 6, 'index_dip': 7, 'index_tip': 8,
            'middle_mcp': 9, 'middle_pip': 10, 'middle_dip': 11, 'middle_tip': 12,
            'ring_mcp': 13, 'ring_pip': 14, 'ring_dip': 15, 'ring_tip': 16,
            'pinky_mcp': 17, 'pinky_pip': 18, 'pinky_dip': 19, 'pinky_tip': 20
        }

    def get_angle(self, p1, p2, p3):
        """Teen points ke beech ka angle calculate karta hai."""
        # np.nan_to_num zaroori hai taaki invalid values se crash na ho
        v1 = np.nan_to_num(np.array(p1) - np.array(p2))
        v2 = np.nan_to_num(np.array(p3) - np.array(p2))
        
        dot_product = np.dot(v1, v2)
        norm_product = np.linalg.norm(v1) * np.linalg.norm(v2)
        
        if norm_product == 0:
            return 0.0 # Zero division se bachne ke liye

        cosine_angle = dot_product / norm_product
        # Cosine angle ko -1 aur 1 ke beech clamp karein
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
        
        angle = np.degrees(np.arccos(cosine_angle))
        return angle

    def interpret(self, body_keypoints_list, hand_keypoints_list):
        """
        Body aur hand keypoints se gesture pehchan kar command return karta hai.
        """
        # --- Body Gestures ---
        if body_keypoints_list:
            # Hum sabse prominent (bade) person ka pose analyze karenge
            body_keypoints = max(body_keypoints_list, key=lambda item: item['box'][2] - item['box'][0])['keypoints']
            
            # Keypoints ko aasan naam dein
            bkp = {name: body_keypoints[idx][:2] for name, idx in self.body_kp_indices.items()}
            
            l_wrist_visible = body_keypoints[self.body_kp_indices['l_wrist']][2] > 0.3
            r_wrist_visible = body_keypoints[self.body_kp_indices['r_wrist']][2] > 0.3

            if l_wrist_visible and r_wrist_visible:
                # Volume Control (Dono haath upar, ek doosre se door ya paas)
                if bkp['l_wrist'][1] < bkp['l_shoulder'][1] and bkp['r_wrist'][1] < bkp['r_shoulder'][1]:
                    wrist_dist = np.linalg.norm(bkp['l_wrist'] - bkp['r_wrist'])
                    shoulder_width = np.linalg.norm(bkp['l_shoulder'] - bkp['r_shoulder'])
                    if wrist_dist > shoulder_width * 1.5: return "VOLUME_UP"
                    if wrist_dist < shoulder_width * 0.5: return "VOLUME_DOWN"

        # --- Hand Gestures ---
        if hand_keypoints_list:
            # Hum sabse prominent (bade) haath ka gesture analyze karenge
            hand_keypoints = max(hand_keypoints_list, key=lambda item: item['box'][2] - item['box'][0])['keypoints']
            
            # Keypoints ko aasan naam dein
            hkp = {name: hand_keypoints[idx][:2] for name, idx in self.hand_kp_indices.items()}

            # Finger extension status check karein (seedhi hai ya mudi hui)
            fingers_extended = {
                'thumb': self.get_angle(hkp['thumb_cmc'], hkp['thumb_mcp'], hkp['thumb_tip']) > 150,
                'index': self.get_angle(hkp['index_mcp'], hkp['index_pip'], hkp['index_tip']) > 150,
                'middle': self.get_angle(hkp['middle_mcp'], hkp['middle_pip'], hkp['middle_tip']) > 150,
                'ring': self.get_angle(hkp['ring_mcp'], hkp['ring_pip'], hkp['ring_tip']) > 150,
                'pinky': self.get_angle(hkp['pinky_mcp'], hkp['pinky_pip'], hkp['pinky_tip']) > 150
            }

            # A. Open Palm (Stop)
            if all(fingers_extended.values()):
                return "STOP"

            # B. Victory Sign (Screenshot)
            if fingers_extended['index'] and fingers_extended['middle'] and \
               not fingers_extended['ring'] and not fingers_extended['pinky']:
                return "SCREENSHOT"
            
            # C. Thumbs Up (Confirm)
            if fingers_extended['thumb'] and not fingers_extended['index'] and \
               not fingers_extended['middle'] and not fingers_extended['ring'] and \
               not fingers_extended['pinky'] and hkp['thumb_tip'][1] < hkp['thumb_mcp'][1]:
                return "CONFIRM"

        return None
