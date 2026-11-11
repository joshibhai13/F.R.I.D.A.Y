from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget, QLineEdit,
    QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QLabel,
    QSizePolicy, QGraphicsDropShadowEffect, QScrollArea
)
from PyQt5.QtGui import (
    QIcon, QPainter, QMovie, QColor, QFont, QPixmap, QCursor
)
from PyQt5.QtCore import (
    Qt, QSize, QTimer, QThread, pyqtSignal, QPoint
)
from dotenv import dotenv_values
import urllib.request
import cv2
import numpy as np
import sys
import os
import math
import json
import socket
import struct

# -------------------- Environment & Paths -------------------- #
env_vars = dotenv_values(".env")
Assistantname = env_vars.get("Assistantname", "FRIDAY")
Username = env_vars.get("Username", "Pruthvi Joshi")
current_dir = os.getcwd()
TempDirPath = os.path.join(current_dir, "Frontend", "Files")
GraphicsDirPath = os.path.join(current_dir, "Frontend", "Graphics")
os.makedirs(TempDirPath, exist_ok=True)

old_chat_message = ""

# -------------------- Helpers Required by main.py & RemoteServer -------------------- #
def AnswerModifier(Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    return '\n'.join(non_empty_lines)

def QueryModifier(Query):
    new_query = Query.lower().strip()
    if not new_query:
        return ""
    words = new_query.split()
    question_words = ["how", "what", "who", "where", "when", "why", "which", "whose", "whom", "can you", "kya", "kaise", "kyun"]

    if any(word in new_query for word in question_words):
        if not new_query.endswith("?"):
            new_query = new_query.rstrip(".!,") + "?"
    else:
        if not new_query.endswith((".", "!", "?")):
            new_query += "."

    return new_query.capitalize()

def SetMicrophoneStatus(Command):
    with open(os.path.join(TempDirPath, 'Mic.data'), "w", encoding='utf-8') as file:
        file.write(str(Command))

def GetMicrophoneStatus():
    path = os.path.join(TempDirPath, 'Mic.data')
    if os.path.exists(path):
        with open(path, "r", encoding='utf-8') as file:
            return file.read().strip()
    return "True"

def SetAssistantStatus(Status):
    with open(os.path.join(TempDirPath, 'Status.data'), "w", encoding='utf-8') as file:
        file.write(str(Status))

def GetAssistantStatus():
    path = os.path.join(TempDirPath, 'Status.data')
    if os.path.exists(path):
        with open(path, "r", encoding='utf-8') as file:
            return file.read().strip()
    return "Available..."

def MicButtonInitialed():
    SetMicrophoneStatus("False")

def MicButtonClosed():
    SetMicrophoneStatus("True")

def GraphicsDirectoryPath(Filename):
    return os.path.join(GraphicsDirPath, Filename)

def TempDirectoryPath(Filename):
    return os.path.join(TempDirPath, Filename)

def ShowTextToScreen(Text):
    with open(os.path.join(TempDirPath, 'Responses.data'), "w", encoding='utf-8') as file:
        file.write(str(Text))


# -------------------- Background Workers -------------------- #
class SpaceDataWorker(QThread):
    data_ready = pyqtSignal(dict)
    def run(self):
        try:
            from Backend.SpaceAPI import space_client
            data = {
                "weather": space_client.get_weather_data(),
                "telescope_jwst": space_client.get_telescope_image("jwst"),
                "asteroids": space_client.get_asteroid_threats(),
                "launches": space_client.get_upcoming_launches()
            }
            self.data_ready.emit(data)
        except Exception:
            pass


class VisionThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    def run(self):
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('127.0.0.1', 5005))
            server_socket.listen(1)
            conn, _ = server_socket.accept()
            data = b""
            payload_size = struct.calcsize("Q")
            while True:
                while len(data) < payload_size:
                    packet = conn.recv(4 * 1024)
                    if not packet:
                        return
                    data += packet
                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack("Q", packed_msg_size)[0]
                while len(data) < msg_size:
                    packet = conn.recv(4 * 1024)
                    if not packet:
                        return
                    data += packet
                frame_data = data[:msg_size]
                data = data[msg_size:]
                nparr = np.frombuffer(frame_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    self.change_pixmap_signal.emit(frame)
        except Exception:
            pass


class ChatWorker(QThread):
    response_ready = pyqtSignal(str, str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        try:
            from Backend.Chatbot import ChatBot
            from Backend.TextToSpeech import TextToSpeech
            SetAssistantStatus("Thinking...")
            answer = ChatBot(self.query)
            ShowTextToScreen(f"{Assistantname} : {answer}")
            SetAssistantStatus("Answering...")
            self.response_ready.emit(self.query, answer)
            TextToSpeech(answer)
            SetAssistantStatus("Available...")
        except Exception as e:
            self.response_ready.emit(self.query, f"Error: {e}")
            SetAssistantStatus("Available...")


# -------------------- Discrete Message Bubble Widget -------------------- #
class MessageBubble(QWidget):
    """
    Renders an individual, beautiful glassmorphism chat bubble.
    Right-aligned for user (purple gradient), Left-aligned for FRIDAY (cyan gradient).
    """
    def __init__(self, sender: str, text: str, is_user: bool = False):
        super().__init__()
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(6, 4, 6, 4)

        card = QFrame()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 10, 14, 12)
        card_layout.setSpacing(6)

        if is_user:
            card.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(52, 24, 96, 0.94),
                        stop:1 rgba(34, 14, 66, 0.94));
                    border: 1px solid rgba(168, 85, 247, 0.45);
                    border-radius: 14px;
                }
            """)
            badge = QLabel(f"👤 {Username.upper()}")
            badge.setStyleSheet("color: #c084fc; font-weight: 700; font-size: 10px; letter-spacing: 1.5px; background: transparent; border: none;")

            body = QLabel(text)
            body.setWordWrap(True)
            body.setTextInteractionFlags(Qt.TextSelectableByMouse)
            body.setStyleSheet("color: #ffffff; font-family: 'Segoe UI', sans-serif; font-size: 13px; line-height: 1.45; background: transparent; border: none;")

            card_layout.addWidget(badge)
            card_layout.addWidget(body)

            outer_layout.addStretch(1)
            outer_layout.addWidget(card, stretch=0)
        else:
            card.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(10, 24, 50, 0.94),
                        stop:1 rgba(6, 14, 32, 0.94));
                    border: 1px solid rgba(0, 220, 255, 0.35);
                    border-radius: 14px;
                }
            """)
            badge = QLabel(f"⚡ {sender.upper()}")
            badge.setStyleSheet("color: #00e5ff; font-weight: 700; font-size: 10px; letter-spacing: 1.5px; background: transparent; border: none;")

            body = QLabel(text)
            body.setWordWrap(True)
            body.setTextInteractionFlags(Qt.TextSelectableByMouse)
            body.setStyleSheet("color: #f1f5f9; font-family: 'Segoe UI', sans-serif; font-size: 13px; line-height: 1.5; background: transparent; border: none;")

            card_layout.addWidget(badge)
            card_layout.addWidget(body)

            outer_layout.addWidget(card, stretch=0)
            outer_layout.addStretch(1)


# -------------------- Rebuilt Modern Chat Section -------------------- #
class ChatSection(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        # Main Glass Card Container
        self.chat_card = QFrame()
        self.chat_card.setStyleSheet("""
            QFrame {
                background: rgba(10, 14, 28, 0.82);
                border: 1px solid rgba(0, 220, 255, 0.18);
                border-radius: 14px;
            }
        """)
        card_layout = QVBoxLayout(self.chat_card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        dot = QLabel("●")
        dot.setStyleSheet("color: #00e5ff; font-size: 11px; background: transparent; border: none;")
        title = QLabel(f"{str(Assistantname).upper()} NEURAL CONVERSATION TERMINAL")
        title.setStyleSheet("""
            color: rgba(0, 229, 255, 0.95);
            font-family: 'Segoe UI', sans-serif;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 2px;
            background: transparent;
            border: none;
        """)
        header.addWidget(dot)
        header.addWidget(title)
        header.addStretch()

        btn_clear = QPushButton("Clear History")
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                color: rgba(148, 163, 184, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 10px;
                font-family: 'Segoe UI';
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.2);
                color: #ff5555;
                border-color: rgba(239, 68, 68, 0.4);
            }
        """)
        btn_clear.clicked.connect(self.clearChat)
        header.addWidget(btn_clear)
        card_layout.addLayout(header)

        # Scroll Area for Message Cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameStyle(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: rgba(4, 7, 16, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 12px;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(0, 0, 0, 0.3);
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 220, 255, 0.35);
                border-radius: 3px;
                min-height: 25px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(0, 220, 255, 0.65);
            }
        """)

        self.messages_container = QWidget()
        self.messages_container.setStyleSheet("background: transparent;")
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(10, 10, 10, 10)
        self.messages_layout.setSpacing(10)
        self.messages_layout.addStretch(1)

        self.scroll_area.setWidget(self.messages_container)
        card_layout.addWidget(self.scroll_area, stretch=1)

        # Integrated Modern Prompt Input Bar
        input_container = QFrame()
        input_container.setStyleSheet("""
            QFrame {
                background: rgba(13, 19, 38, 0.95);
                border: 1px solid rgba(0, 220, 255, 0.28);
                border-radius: 22px;
                padding: 2px 8px;
            }
        """)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(10, 4, 10, 4)
        input_layout.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask FRIDAY anything in English or Hinglish (Press Enter)...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                padding: 6px;
            }
        """)
        self.input_field.returnPressed.connect(self.sendMessage)

        self.send_btn = QPushButton("Transmit ▶")
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d4ff, stop:1 #0088cc);
                color: #000000;
                font-family: 'Segoe UI';
                font-weight: 700;
                font-size: 11px;
                border: none;
                border-radius: 15px;
                padding: 6px 16px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: #50fa7b;
            }
        """)
        self.send_btn.clicked.connect(self.sendMessage)

        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setCursor(Qt.PointingHandCursor)
        self.mic_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 220, 255, 0.1);
                color: #00d4ff;
                border: 1px solid rgba(0, 220, 255, 0.3);
                border-radius: 15px;
                font-size: 13px;
                width: 32px;
                height: 30px;
            }
            QPushButton:hover {
                background: rgba(80, 250, 123, 0.2);
                border-color: #50fa7b;
            }
        """)
        self.mic_btn.clicked.connect(self.toggleMic)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        input_layout.addWidget(self.mic_btn)

        card_layout.addWidget(input_container)
        layout.addWidget(self.chat_card)

        # Polling Timer for Live Responses
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.syncIncomingMessages)
        self.timer.start(100)

        # Load initial past chat cleanly
        self.loadInitialChatlog()

    def addBubble(self, sender: str, text: str, is_user: bool = False):
        text = text.strip()
        if not text:
            return
        bubble = MessageBubble(sender, text, is_user=is_user)
        count = self.messages_layout.count()
        self.messages_layout.insertWidget(count - 1, bubble)
        QTimer.singleShot(60, self.scrollToBottom)

    def scrollToBottom(self):
        sb = self.scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def clearChat(self):
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def loadInitialChatlog(self):
        chatlog_path = os.path.join(current_dir, "Data", "ChatLog.json")
        if os.path.exists(chatlog_path):
            try:
                with open(chatlog_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data[-16:]:
                        role = item.get("role", "")
                        content = item.get("content", "").strip()
                        if not content:
                            continue
                        is_user = (role == "user")
                        sender = "YOU" if is_user else Assistantname.upper()
                        self.addBubble(sender, content, is_user=is_user)
            except Exception:
                pass

    def toggleMic(self):
        current = GetMicrophoneStatus()
        new_state = "False" if current == "True" else "True"
        SetMicrophoneStatus(new_state)

    def sendMessage(self):
        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.clear()
        self.addBubble("YOU", text, is_user=True)

        self.worker = ChatWorker(text)
        self.worker.response_ready.connect(lambda q, r: self.addBubble(Assistantname.upper(), r, is_user=False))
        self.worker.start()

    def syncIncomingMessages(self):
        global old_chat_message
        try:
            with open(os.path.join(TempDirPath, 'Responses.data'), "r", encoding='utf-8') as file:
                msg = file.read().strip()
        except:
            msg = ""

        if not msg or msg == str(old_chat_message):
            return

        old_chat_message = msg

        # Parse the message line by line to prevent any merging
        lines = [l.strip() for l in msg.split("\n") if l.strip()]
        for line in lines:
            sender = Assistantname.upper()
            content = line
            is_user = False
            if ":" in line:
                parts = line.split(":", 1)
                prefix = parts[0].strip()
                body = parts[1].strip()
                if prefix.lower() in ["user", "you", Username.lower()]:
                    sender = "YOU"
                    content = body
                    is_user = True
                elif prefix.lower() in ["friday", "jarvis", str(Assistantname).lower()]:
                    sender = Assistantname.upper()
                    content = body
                    is_user = False
                else:
                    sender = prefix.upper()
                    content = body
                    is_user = False
            self.addBubble(sender, content, is_user=is_user)


# -------------------- Modern HUD Dashboard -------------------- #
class InitialScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.vision_thread = None
        self.toggled_mic = True
        self.initUI()

    def initUI(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(24, 18, 24, 18)
        main_layout.setSpacing(16)

        # Ensure mic is active and listening continuously by default
        SetMicrophoneStatus("True")

        # ── Left Column: Vision & Telemetry ──
        left_col = QVBoxLayout()
        left_col.setSpacing(14)

        self.cam_card, self.cam_label, self.cam_img = self.create_box("VISION SYSTEM", "Vision Offline — Say 'Open Vision Mode'", (0, 255, 140))
        cam_btn_row = QHBoxLayout()
        btn_cam_toggle = QPushButton("Toggle Vision")
        btn_cam_toggle.setCursor(Qt.PointingHandCursor)
        btn_cam_toggle.setStyleSheet(self.btn_style_cyan())
        btn_cam_toggle.clicked.connect(self.toggleVisionMode)

        btn_cam_switch = QPushButton("Switch Camera")
        btn_cam_switch.setCursor(Qt.PointingHandCursor)
        btn_cam_switch.setStyleSheet(self.btn_style_cyan())
        btn_cam_switch.clicked.connect(self.switchCamera)

        cam_btn_row.addWidget(btn_cam_toggle)
        cam_btn_row.addWidget(btn_cam_switch)
        self.cam_card.layout().insertLayout(2, cam_btn_row)

        self.weather_card, self.weather_label, _ = self.create_box("ENVIRONMENT & SENSORS", "Acquiring telemetry...", (0, 200, 255))
        left_col.addWidget(self.cam_card, stretch=5)
        left_col.addWidget(self.weather_card, stretch=3)

        # ── Center Column: Arc Reactor / Status / Controls ──
        center_col = QVBoxLayout()
        center_col.setSpacing(12)
        center_col.setAlignment(Qt.AlignCenter)

        center_card = QFrame()
        center_card.setStyleSheet("""
            QFrame {
                background: rgba(10, 15, 32, 0.78);
                border: 1px solid rgba(0, 220, 255, 0.2);
                border-radius: 16px;
            }
        """)
        c_layout = QVBoxLayout(center_card)
        c_layout.setAlignment(Qt.AlignCenter)
        c_layout.setContentsMargins(20, 24, 20, 24)
        c_layout.setSpacing(14)

        # Animated Reactor GIF
        self.gif_label = QLabel()
        self.movie = QMovie(GraphicsDirectoryPath('Jarvis.gif'))
        self.movie.setScaledSize(QSize(150, 150))
        self.gif_label.setMovie(self.movie)
        self.gif_label.setAlignment(Qt.AlignCenter)
        self.gif_label.setStyleSheet("border: none; background: transparent;")
        self.movie.start()
        c_layout.addWidget(self.gif_label, alignment=Qt.AlignCenter)

        # Status Label
        self.status_label = QLabel("SYSTEMS ONLINE — LISTENING")
        self.status_label.setStyleSheet("""
            color: #00e5ff;
            font-family: 'Segoe UI', sans-serif;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 3px;
            border: none;
            background: transparent;
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(self.status_label, alignment=Qt.AlignCenter)

        # Mic Toggle Icon Button
        self.mic_icon = QLabel()
        self.mic_icon.setCursor(Qt.PointingHandCursor)
        self.updateMicIcon(True)
        self.mic_icon.mousePressEvent = self.onMicClick
        c_layout.addWidget(self.mic_icon, alignment=Qt.AlignCenter)

        # Stop Voice Barge-in Button
        self.stop_btn = QPushButton("⏹ Stop Voice Playback")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 85, 85, 0.15);
                color: #ff5555;
                border: 1px solid rgba(255, 85, 85, 0.35);
                border-radius: 12px;
                padding: 6px 18px;
                font-family: 'Segoe UI';
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(255, 85, 85, 0.35);
                color: #ffffff;
            }
        """)
        self.stop_btn.clicked.connect(self.stopVoice)
        c_layout.addWidget(self.stop_btn, alignment=Qt.AlignCenter)

        sys_info = QLabel(f"F.R.I.D.A.Y. CORE v3.0 | USER: {Username.upper()}")
        sys_info.setStyleSheet("color: rgba(148, 163, 184, 0.6); font-size: 9px; letter-spacing: 2px; border: none; background: transparent;")
        c_layout.addWidget(sys_info, alignment=Qt.AlignCenter)

        center_col.addWidget(center_card)

        # ── Right Column: Space & Quick Control Shortcuts ──
        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        self.space_card, self.space_label, self.space_img = self.create_box("DEEP SPACE INTEL (JWST)", "Scanning deep space manifest...", (160, 100, 255))
        
        actions_card = QFrame()
        actions_card.setStyleSheet("""
            QFrame {
                background: rgba(10, 15, 32, 0.78);
                border: 1px solid rgba(255, 120, 50, 0.22);
                border-radius: 14px;
            }
        """)
        act_layout = QVBoxLayout(actions_card)
        act_layout.setContentsMargins(14, 12, 14, 12)
        act_layout.setSpacing(10)

        act_title = QLabel("SYSTEM CONTROLS")
        act_title.setStyleSheet("color: rgba(255, 120, 50, 0.95); font-family: 'Segoe UI'; font-weight: 700; font-size: 10px; letter-spacing: 2px;")
        act_layout.addWidget(act_title)

        grid = QGridLayout()
        grid.setSpacing(8)

        btn_mute = self.make_action_btn("🔇 Mute", lambda: self.exec_sys("system mute"))
        btn_unmute = self.make_action_btn("🔊 Unmute", lambda: self.exec_sys("system unmute"))
        btn_vup = self.make_action_btn("🔈 Vol +", lambda: self.exec_sys("system volume up"))
        btn_vdown = self.make_action_btn("🔉 Vol −", lambda: self.exec_sys("system volume down"))
        btn_shot = self.make_action_btn("📸 Screenshot", lambda: self.exec_sys("system take screenshot"))
        btn_files = self.make_action_btn("📂 Files", lambda: self.exec_sys("system open file explorer"))

        grid.addWidget(btn_mute, 0, 0)
        grid.addWidget(btn_unmute, 0, 1)
        grid.addWidget(btn_vup, 1, 0)
        grid.addWidget(btn_vdown, 1, 1)
        grid.addWidget(btn_shot, 2, 0)
        grid.addWidget(btn_files, 2, 1)

        act_layout.addLayout(grid)

        right_col.addWidget(self.space_card, stretch=5)
        right_col.addWidget(actions_card, stretch=3)

        main_layout.addLayout(left_col, 4)
        main_layout.addLayout(center_col, 3)
        main_layout.addLayout(right_col, 4)

        # Polling Timer
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.pollStatus)
        self.poll_timer.start(100)

        # Space Data Worker
        self.worker = SpaceDataWorker()
        self.worker.data_ready.connect(self.onSpaceData)
        self.worker.start()

    def create_box(self, title_text, content_text, accent_rgb):
        r, g, b = accent_rgb
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: rgba(10, 15, 32, 0.78);
                border: 1px solid rgba({r}, {g}, {b}, 0.22);
                border-radius: 14px;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        title = QLabel(f"● {title_text}")
        title.setStyleSheet(f"color: rgba({r}, {g}, {b}, 0.95); font-family: 'Segoe UI'; font-weight: 700; font-size: 10px; letter-spacing: 2px;")
        
        img = QLabel()
        img.setAlignment(Qt.AlignCenter)
        img.setStyleSheet("border-radius: 8px;")
        img.hide()

        content = QLabel(content_text)
        content.setStyleSheet("color: rgba(148, 163, 184, 0.9); font-size: 11px; line-height: 1.4;")
        content.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(img)
        layout.addWidget(content)
        layout.addStretch()
        return frame, content, img

    def make_action_btn(self, text, handler):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                color: #f1f5f9;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 6px;
                font-family: 'Segoe UI';
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(0, 220, 255, 0.15);
                border-color: rgba(0, 220, 255, 0.4);
            }
        """)
        btn.clicked.connect(handler)
        return btn

    def btn_style_cyan(self):
        return """
            QPushButton {
                background: rgba(0, 220, 255, 0.12);
                color: #00e5ff;
                border: 1px solid rgba(0, 220, 255, 0.3);
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(0, 220, 255, 0.28);
            }
        """

    def exec_sys(self, cmd):
        try:
            from Backend.Automation import Automation
            import asyncio
            asyncio.run(Automation([cmd]))
        except Exception:
            pass

    def stopVoice(self):
        try:
            from Backend.TextToSpeech import StopSpeaking
            StopSpeaking()
            SetAssistantStatus("Available...")
        except Exception:
            pass

    def toggleVisionMode(self):
        cam_file = TempDirectoryPath('Camera.data')
        try:
            with open(cam_file, "r") as f:
                cur = f.read().strip()
        except:
            cur = "False"
        new_state = "False" if cur == "True" else "True"
        with open(cam_file, "w") as f:
            f.write(new_state)

    def switchCamera(self):
        cam_idx_file = TempDirectoryPath('CameraIndex.data')
        try:
            with open(cam_idx_file, "r") as f:
                idx = int(f.read().strip())
        except:
            idx = 0
        new_idx = (idx + 1) % 3
        with open(cam_idx_file, "w") as f:
            f.write(str(new_idx))

    def onMicClick(self, event=None):
        self.toggled_mic = not self.toggled_mic
        self.updateMicIcon(self.toggled_mic)
        SetMicrophoneStatus("True" if self.toggled_mic else "False")

    def updateMicIcon(self, active):
        file = 'Mic_on.png' if active else 'Mic_off.png'
        pix = QPixmap(GraphicsDirectoryPath(file))
        self.mic_icon.setPixmap(pix.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        bg = "rgba(0, 220, 255, 0.1)" if active else "rgba(255, 85, 85, 0.1)"
        border = "rgba(0, 220, 255, 0.3)" if active else "rgba(255, 85, 85, 0.3)"
        self.mic_icon.setStyleSheet(f"border: 1px solid {border}; border-radius: 24px; background: {bg}; padding: 6px;")

    def pollStatus(self):
        try:
            with open(TempDirectoryPath('Status.data'), "r", encoding='utf-8') as f:
                status = f.read().strip()
        except:
            status = "Available..."

        self.status_label.setText(status.upper() if status else "STANDBY...")

        # Update mic icon state based on file
        mic_on = (GetMicrophoneStatus() == "True")
        if mic_on != self.toggled_mic:
            self.toggled_mic = mic_on
            self.updateMicIcon(mic_on)

        # Update Vision Mode frame
        try:
            with open(TempDirectoryPath('Camera.data'), "r") as f:
                cam_active = (f.read().strip() == "True")
        except:
            cam_active = False

        if cam_active and self.vision_thread is None:
            self.cam_label.setText("Acquiring Vision Feed...")
            self.vision_thread = VisionThread()
            self.vision_thread.change_pixmap_signal.connect(self.onFrameReceived)
            self.vision_thread.start()
        elif not cam_active and self.vision_thread is not None:
            self.vision_thread.terminate()
            self.vision_thread = None
            self.cam_img.hide()
            self.cam_label.setText("Vision Mode Deactivated")

    def onFrameReceived(self, frame):
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        from PyQt5.QtGui import QImage
        qimg = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        self.cam_img.setPixmap(pixmap.scaled(320, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.cam_img.show()
        self.cam_label.setText("Vision Feed Active (Live Object & Person Tracking)")

    def onSpaceData(self, data):
        w = data.get("weather", {})
        if w:
            city = w.get("city", "Unknown")
            temp = w.get("temp", "--")
            cond = w.get("condition", "--")
            hum = w.get("humidity", "--")
            self.weather_label.setText(f"Location: {city}\nTemperature: {temp}°C | {cond}\nHumidity: {hum}%\nAtmosphere: Stable")

        t = data.get("telescope_jwst", {})
        if t:
            full_path = t.get("local_full_path", "")
            if not full_path or not os.path.exists(full_path):
                full_path = os.path.join(current_dir, "Frontend", "remote", "static", "telescope_jwst.jpg")
            if os.path.exists(full_path):
                pix = QPixmap(full_path)
                self.space_img.setPixmap(pix.scaled(320, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.space_img.show()
                self.space_label.setText(t.get("title", "JWST Deep Field Observatory"))


# -------------------- Custom Minimal Top Navigation Bar -------------------- #
class CustomTopBar(QWidget):
    def __init__(self, parent, stacked_widget):
        super().__init__(parent)
        self.stacked_widget = stacked_widget
        self.draggable = True
        self.offset = None
        self.initUI()

    def initUI(self):
        self.setFixedHeight(44)
        self.setStyleSheet("""
            background: rgba(6, 10, 22, 0.96);
            border-bottom: 1px solid rgba(0, 220, 255, 0.15);
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 12, 0)
        layout.setSpacing(12)

        # Brand / Logo
        logo = QLabel("⚡ F.R.I.D.A.Y.")
        logo.setStyleSheet("""
            color: #00e5ff;
            font-family: 'Segoe UI', sans-serif;
            font-size: 13px;
            font-weight: 800;
            letter-spacing: 2px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(logo)

        layout.addStretch(1)

        # Navigation Tab Buttons (Segmented Pill)
        nav_style_active = """
            QPushButton {
                background: rgba(0, 220, 255, 0.18);
                color: #00e5ff;
                border: 1px solid rgba(0, 220, 255, 0.45);
                border-radius: 6px;
                padding: 4px 18px;
                font-family: 'Segoe UI';
                font-weight: 700;
                font-size: 11px;
                letter-spacing: 1px;
            }
        """
        nav_style_inactive = """
            QPushButton {
                background: rgba(255, 255, 255, 0.04);
                color: rgba(148, 163, 184, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 4px 18px;
                font-family: 'Segoe UI';
                font-weight: 600;
                font-size: 11px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: rgba(0, 220, 255, 0.1);
                color: #ffffff;
            }
        """

        self.btn_dash = QPushButton("🎛️ HUD Dashboard")
        self.btn_dash.setCursor(Qt.PointingHandCursor)
        self.btn_dash.setStyleSheet(nav_style_active)

        self.btn_chat = QPushButton("💬 Chat Terminal")
        self.btn_chat.setCursor(Qt.PointingHandCursor)
        self.btn_chat.setStyleSheet(nav_style_inactive)

        self.btn_dash.clicked.connect(lambda: self.switchTab(0, nav_style_active, nav_style_inactive))
        self.btn_chat.clicked.connect(lambda: self.switchTab(1, nav_style_active, nav_style_inactive))

        layout.addWidget(self.btn_dash)
        layout.addWidget(self.btn_chat)

        layout.addStretch(1)

        # Global Quick Mic Toggle in Header
        self.top_mic_btn = QPushButton("🎙️ MIC: ACTIVE")
        self.top_mic_btn.setCursor(Qt.PointingHandCursor)
        self.top_mic_btn.setStyleSheet("""
            QPushButton {
                background: rgba(80, 250, 123, 0.15);
                color: #50fa7b;
                border: 1px solid rgba(80, 250, 123, 0.45);
                border-radius: 6px;
                padding: 4px 12px;
                font-family: 'Segoe UI';
                font-weight: 700;
                font-size: 11px;
                letter-spacing: 1px;
            }
        """)
        self.top_mic_btn.clicked.connect(self.toggleTopMic)
        layout.addWidget(self.top_mic_btn)

        # Global Quick Stop Voice Button in Header
        self.top_stop_btn = QPushButton("⏹ STOP VOICE")
        self.top_stop_btn.setCursor(Qt.PointingHandCursor)
        self.top_stop_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 85, 85, 0.12);
                color: #ff5555;
                border: 1px solid rgba(255, 85, 85, 0.35);
                border-radius: 6px;
                padding: 4px 10px;
                font-family: 'Segoe UI';
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(255, 85, 85, 0.3);
                color: #ffffff;
            }
        """)
        self.top_stop_btn.clicked.connect(self.stopVoice)
        layout.addWidget(self.top_stop_btn)

        # Window Controls
        ctrl_style = """
            QPushButton {
                background: transparent;
                border: none;
                color: rgba(148, 163, 184, 0.8);
                font-size: 13px;
                width: 28px;
                height: 26px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                color: #ffffff;
            }
        """
        close_style = """
            QPushButton {
                background: transparent;
                border: none;
                color: rgba(148, 163, 184, 0.8);
                font-size: 13px;
                width: 28px;
                height: 26px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.8);
                color: #ffffff;
            }
        """

        btn_min = QPushButton("—")
        btn_min.setStyleSheet(ctrl_style)
        btn_min.clicked.connect(lambda: self.parent().showMinimized())

        self.btn_max = QPushButton("□")
        self.btn_max.setStyleSheet(ctrl_style)
        self.btn_max.clicked.connect(self.toggleMaximize)

        btn_close = QPushButton("✕")
        btn_close.setStyleSheet(close_style)
        btn_close.clicked.connect(lambda: sys.exit(0))

        layout.addWidget(btn_min)
        layout.addWidget(self.btn_max)
        layout.addWidget(btn_close)

        # Timer to keep mic status indicator accurate
        self.mic_sync_timer = QTimer(self)
        self.mic_sync_timer.timeout.connect(self.updateTopMicDisplay)
        self.mic_sync_timer.start(250)

    def toggleTopMic(self):
        current = GetMicrophoneStatus()
        new_state = "False" if current == "True" else "True"
        SetMicrophoneStatus(new_state)
        self.updateTopMicDisplay()

    def updateTopMicDisplay(self):
        active = (GetMicrophoneStatus() == "True")
        if active:
            self.top_mic_btn.setText("🎙️ MIC: ACTIVE")
            self.top_mic_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(80, 250, 123, 0.15);
                    color: #50fa7b;
                    border: 1px solid rgba(80, 250, 123, 0.45);
                    border-radius: 6px;
                    padding: 4px 12px;
                    font-family: 'Segoe UI';
                    font-weight: 700;
                    font-size: 11px;
                }
            """)
        else:
            self.top_mic_btn.setText("🔇 MIC: PAUSED")
            self.top_mic_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 85, 85, 0.15);
                    color: #ff5555;
                    border: 1px solid rgba(255, 85, 85, 0.45);
                    border-radius: 6px;
                    padding: 4px 12px;
                    font-family: 'Segoe UI';
                    font-weight: 700;
                    font-size: 11px;
                }
            """)

    def stopVoice(self):
        try:
            from Backend.TextToSpeech import StopSpeaking
            StopSpeaking()
            SetAssistantStatus("Available...")
        except Exception:
            pass

    def switchTab(self, idx, style_active, style_inactive):
        self.stacked_widget.setCurrentIndex(idx)
        if idx == 0:
            self.btn_dash.setStyleSheet(style_active)
            self.btn_chat.setStyleSheet(style_inactive)
        else:
            self.btn_dash.setStyleSheet(style_inactive)
            self.btn_chat.setStyleSheet(style_active)

    def toggleMaximize(self):
        if self.parent().isMaximized():
            self.parent().showNormal()
            self.btn_max.setText("□")
        else:
            self.parent().showMaximized()
            self.btn_max.setText("❐")

    def mousePressEvent(self, event):
        if self.draggable and event.button() == Qt.LeftButton:
            self.offset = event.globalPos() - self.parent().frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self.draggable and self.offset and event.buttons() == Qt.LeftButton:
            self.parent().move(event.globalPos() - self.offset)


# -------------------- Main Application Window -------------------- #
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.initUI()

    def initUI(self):
        self.resize(1260, 800)
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - 1260) // 2
        y = (screen.height() - 800) // 2
        self.move(max(20, x), max(20, y))

        self.setStyleSheet("""
            QMainWindow {
                background: qradialgradient(cx:0.5, cy:0.2, radius:0.95, fx:0.5, fy:0.2,
                    stop:0 #0a1126,
                    stop:0.45 #050814,
                    stop:1 #020308);
                border: 1px solid rgba(0, 220, 255, 0.22);
            }
        """)

        stacked = QStackedWidget(self)
        initial_screen = InitialScreen()
        message_screen = ChatSection()
        stacked.addWidget(initial_screen)
        stacked.addWidget(message_screen)

        top_bar = CustomTopBar(self, stacked)
        self.setMenuWidget(top_bar)
        self.setCentralWidget(stacked)


# -------------------- Desktop GUI Runner -------------------- #
def GraphicalUserInterface():
    """Starts the native, modern, ultra-fast F.R.I.D.A.Y. PyQt5 Desktop GUI."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    GraphicalUserInterface()
