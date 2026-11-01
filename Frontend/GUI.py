from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QStackedWidget, QWidget, QLineEdit, QGridLayout, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QLabel, QSizePolicy, QGraphicsDropShadowEffect
from PyQt5.QtGui import QIcon, QPainter, QMovie, QColor, QTextCharFormat, QFont, QPixmap, QTextBlockFormat
from PyQt5.QtCore import Qt, QSize, QTimer, QThread, pyqtSignal
import urllib.request
import cv2
import numpy as np
from PyQt5 import QtGui
from dotenv import dotenv_values
import sys
import os
import math
import json

env_vars = dotenv_values(".env")
Assistantname = env_vars.get("Assistantname")
current_dir = os.getcwd()
old_chat_message = ""
TempDirPath = rf"{current_dir}\Frontend\Files"
GraphicsDirPath = rf"{current_dir}\Frontend\Graphics"

def AnswerModifier(Answer):
      lines = Answer.split('\n')
      non_empty_lines = [line for line in lines if line.strip()]
      modified_answer = '\n' .join(non_empty_lines)
      return modified_answer

def QueryModifier(Query):

      new_query = Query.lower().strip()
      Query_words = new_query.split()
      question_words = ["how", "what", "who", "where", "when", "why", "which", "whose", "whom", "can you", "what's", "where's", "how's"]

      if any(word + " " in new_query for word in question_words):
            if Query_words[-1][-1] in ['.', '?', '!']:
                  new_query = new_query[:-1] + "?"
            else:
                  new_query += "?"

      else:
            if Query_words[-1][-1] in ['.', '?', '!']:
                  new_query = new_query[:-1] + "."
            else:
                  new_query += "."    

      return new_query.capitalize()

def SetMicrophoneStatus(Command):
      with open(rf'{TempDirPath}\Mic.data', "w", encoding='utf-8') as file:
            file.write(Command)
            
def GetMicrophoneStatus():  
      with open(rf'{TempDirPath}\Mic.data', "r", encoding='utf-8') as file:          
            Status = file.read()
      return Status

def SetAssistantStatus(Status):
      with open(rf'{TempDirPath}\Status.data', "w", encoding='utf-8') as file:
            file.write(Status)

def GetAssistantStatus():
      with open(rf'{TempDirPath}\Status.data', "r", encoding='utf-8') as file:   
            Status = file.read()
      return Status

def MicButtonInitialed():
      SetMicrophoneStatus("False")

def MicButtonClosed():
      SetMicrophoneStatus("True")

def GraphicsDirectoryPath(Filename):
      Path = os.path.join(current_dir, "Frontend", "Graphics", Filename)
      return Path

def TempDirectoryPath(Filename):
      Path = rf'{TempDirPath}\{Filename}'
      return Path

def ShowTextToScreen(Text):
      with open(rf'{TempDirPath}\Responses.data', "w", encoding='utf-8') as file:
            file.write(Text)

class ChatSection(QWidget):

      def __init__(self):
            super(ChatSection, self).__init__()

            layout = QVBoxLayout(self)
            layout.setContentsMargins(30, 20, 30, 20)
            layout.setSpacing(14)

            # Modern Glass Chat Container
            self.chat_container = QFrame()
            self.chat_container.setStyleSheet("""
                  QFrame {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                              stop:0 rgba(10, 15, 32, 0.88),
                              stop:0.5 rgba(13, 20, 42, 0.82),
                              stop:1 rgba(8, 12, 26, 0.88));
                        border: 1px solid rgba(0, 220, 255, 0.22);
                        border-radius: 16px;
                  }
            """)
            chat_inner_layout = QVBoxLayout(self.chat_container)
            chat_inner_layout.setContentsMargins(18, 16, 18, 16)
            chat_inner_layout.setSpacing(10)

            # Chat header row
            header_layout = QHBoxLayout()
            status_dot = QLabel("\u25CF")
            status_dot.setStyleSheet("color: #00e5ff; font-size: 9px; border: none; background: transparent;")
            header_title = QLabel(f"{str(Assistantname).upper()} TERMINAL CONVERSATION")
            header_title.setStyleSheet("color: rgba(0, 229, 255, 0.9); font-family: 'Segoe UI', sans-serif; font-size: 11px; font-weight: 700; letter-spacing: 2px; border: none; background: transparent;")
            header_layout.addWidget(status_dot)
            header_layout.addWidget(header_title)
            header_layout.addStretch()

            self.chat_text_edit = QTextEdit()
            self.chat_text_edit.setReadOnly(True)
            self.chat_text_edit.setTextInteractionFlags(Qt.NoTextInteraction)
            self.chat_text_edit.setFrameStyle(QFrame.NoFrame)
            self.chat_text_edit.setStyleSheet("""
                  QTextEdit {
                        background: transparent;
                        color: #f1f5f9;
                        border: none;
                        padding: 8px;
                        font-family: 'Segoe UI', sans-serif;
                  }
            """)

            chat_inner_layout.addLayout(header_layout)
            chat_inner_layout.addWidget(self.chat_text_edit)
            layout.addWidget(self.chat_container, stretch=1)

            # Status bar at bottom
            bottom_bar = QHBoxLayout()
            bottom_bar.setContentsMargins(8, 0, 8, 4)

            self.gif_label = QLabel()
            self.gif_label.setStyleSheet("border: none; background: transparent;")
            self.movie = QMovie(GraphicsDirectoryPath('Jarvis.gif'))
            self.movie.setScaledSize(QSize(50, 50))
            self.gif_label.setMovie(self.movie)
            self.gif_label.setAlignment(Qt.AlignCenter)
            self.movie.stop()
            self.movie.jumpToFrame(0)

            self.label = QLabel("Awaiting input...")
            self.label.setStyleSheet("color: rgba(0, 220, 255, 0.85); font-family: 'Segoe UI', sans-serif; font-size: 12px; font-weight: 600; letter-spacing: 2px; border: none; background: transparent;")
            
            bottom_bar.addWidget(self.gif_label)
            bottom_bar.addSpacing(10)
            bottom_bar.addWidget(self.label)
            bottom_bar.addStretch()

            layout.addLayout(bottom_bar)

            # Modern Minimalist Scrollbar & Widget Stylesheet
            self.setStyleSheet("""
                  QWidget {
                        background: qradialgradient(cx:0.5, cy:0.3, radius:0.85, fx:0.5, fy:0.3, stop:0 #090e24, stop:0.55 #040610, stop:1 #020308);
                  }
                  QScrollBar:vertical {
                        border: none;
                        background: rgba(0, 0, 0, 0.25);
                        width: 6px;
                        margin: 0px;
                        border-radius: 3px;
                  }
                  QScrollBar::handle:vertical {
                        background: rgba(0, 220, 255, 0.3);
                        min-height: 20px;
                        border-radius: 3px;
                  }
                  QScrollBar::handle:vertical:hover {
                        background: rgba(0, 220, 255, 0.6);
                  }
                  QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                        height: 0px;
                  }
            """)

            font = QFont()
            font.setPointSize(11)
            self.chat_text_edit.setFont(font)

            self.timer = QTimer(self)
            self.timer.timeout.connect(self.loadMessages)
            self.timer.timeout.connect(self.SpeechRecogText)
            self.timer.start(100)

            self.chat_text_edit.viewport().installEventFilter(self)
            self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))

      def loadMessages(self):
            global old_chat_message

            try:
                  with open(TempDirectoryPath('Responses.data'), "r", encoding='utf-8') as file:
                        messages = file.read()
            except:
                  messages = ""

            if not messages or len(messages) <= 1:
                  return

            if str(old_chat_message) == str(messages):
                  return

            self.addMessage(message=messages)
            old_chat_message = messages

      def SpeechRecogText(self):
            try:
                  with open(TempDirectoryPath('Status.data'), "r", encoding='utf-8') as file:
                        status = file.read().strip()
            except:
                  status = ""

            self.label.setText(status if status else "Standby...")

            if "answering" in status.lower():
                  if self.movie.state() != QMovie.Running:
                        self.movie.start()
            else:
                  if self.movie.state() == QMovie.Running:
                        self.movie.stop()
                        self.movie.jumpToFrame(0)

      def addMessage(self, message, color='White'):
            message = message.strip()
            if not message:
                  return

            sender = "ASSISTANT"
            content = message

            if ":" in message:
                  parts = message.split(":", 1)
                  prefix = parts[0].strip()
                  body = parts[1].strip()
                  if prefix.lower() in ["jarvis", "friday", str(Assistantname).lower()]:
                        sender = str(Assistantname).upper()
                        content = body
                  elif prefix.lower() in ["user", "you", "me"]:
                        sender = "YOU"
                        content = body
                  else:
                        sender = prefix.upper()
                        content = body

            if sender == "YOU":
                  bubble_html = f"""
                  <div style="margin: 6px 0; text-align: right;">
                        <span style="background: rgba(168, 85, 247, 0.18); color: #c084fc; font-weight: 700; font-size: 10px; letter-spacing: 1.5px; padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(168, 85, 247, 0.3);">YOU</span>
                        <div style="margin-top: 4px; display: inline-block; padding: 10px 14px; background: rgba(30, 22, 54, 0.85); color: #f8fafc; border: 1px solid rgba(168, 85, 247, 0.35); border-radius: 12px; font-size: 13px; font-family: 'Segoe UI', sans-serif; line-height: 1.45; text-align: left; max-width: 80%;">
                              {content}
                        </div>
                  </div>
                  """
            else:
                  bubble_html = f"""
                  <div style="margin: 6px 0; text-align: left;">
                        <span style="background: rgba(0, 229, 255, 0.15); color: #00e5ff; font-weight: 700; font-size: 10px; letter-spacing: 1.5px; padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(0, 229, 255, 0.3);">{sender}</span>
                        <div style="margin-top: 4px; display: inline-block; padding: 10px 14px; background: rgba(12, 20, 38, 0.85); color: #f8fafc; border: 1px solid rgba(0, 220, 255, 0.25); border-radius: 12px; font-size: 13px; font-family: 'Segoe UI', sans-serif; line-height: 1.45; max-width: 85%;">
                              {content}
                        </div>
                  </div>
                  """

            cursor = self.chat_text_edit.textCursor()
            cursor.movePosition(cursor.End)
            self.chat_text_edit.setTextCursor(cursor)
            self.chat_text_edit.insertHtml(bubble_html + "<br>")
            self.chat_text_edit.verticalScrollBar().setValue(self.chat_text_edit.verticalScrollBar().maximum())


class SpaceDataWorker(QThread):
      data_ready = pyqtSignal(dict)
      def run(self):
            try:
                  from Backend.SpaceAPI import space_client
                  data = {
                        "map": space_client.get_map_tile(),
                        "weather": space_client.get_weather_data(),
                        "telescope_jwst": space_client.get_telescope_image("jwst"),
                        "telescope_hubble": space_client.get_telescope_image("hubble"),
                        "asteroids": space_client.get_asteroid_threats(),
                        "launches": space_client.get_upcoming_launches()
                  }
                  self.data_ready.emit(data)
            except Exception as e:
                  print(f"Worker Error: {e}")

import socket
import struct

class VisionThread(QThread):
      change_pixmap_signal = pyqtSignal(np.ndarray)
      def run(self):
            try:
                  server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                  server_socket.bind(('127.0.0.1', 5005))
                  server_socket.listen(1)
                  conn, addr = server_socket.accept()
                  data = b""
                  payload_size = struct.calcsize("Q")
                  while True:
                        while len(data) < payload_size:
                              packet = conn.recv(4*1024)
                              if not packet: break
                              data += packet
                        if len(data) < payload_size: break
                        packed_msg_size = data[:payload_size]
                        data = data[payload_size:]
                        msg_size = struct.unpack("Q", packed_msg_size)[0]
                        while len(data) < msg_size:
                              data += conn.recv(4*1024)
                        frame_data = data[:msg_size]
                        data = data[msg_size:]
                        nparr = np.frombuffer(frame_data, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        if frame is not None:
                              self.change_pixmap_signal.emit(frame)
            except Exception as e:
                  print(f"Vision Thread Server Error: {e}")


class HologramWidget(QWidget):
      """Custom widget that draws spinning 3D wireframe objects."""
      def __init__(self, parent=None):
            super().__init__(parent)
            self.object_name = ""
            self.angle = 0
            self.setMinimumHeight(150)
            self.setStyleSheet("background: transparent; border: none;")
            
            self.holo_timer = QTimer(self)
            self.holo_timer.timeout.connect(self._rotate)
            self.holo_timer.start(50)  # 20 FPS rotation
      
      def set_object(self, name):
            self.object_name = name.lower().strip()
            self.update()
      
      def _rotate(self):
            self.angle += 2
            if self.angle >= 360:
                  self.angle = 0
            if self.object_name:
                  self.update()
      
      def _project(self, x, y, z, cx, cy, scale=60):
            """Simple 3D to 2D projection."""
            rad = math.radians(self.angle)
            # Rotate around Y axis
            rx = x * math.cos(rad) - z * math.sin(rad)
            rz = x * math.sin(rad) + z * math.cos(rad)
            # Rotate slightly around X axis for perspective
            ry = y * math.cos(math.radians(15)) - rz * math.sin(math.radians(15))
            rz2 = y * math.sin(math.radians(15)) + rz * math.cos(math.radians(15))
            # Perspective division
            factor = 200 / (200 + rz2)
            sx = int(cx + rx * scale * factor)
            sy = int(cy + ry * scale * factor)
            return sx, sy
      
      def paintEvent(self, event):
            if not self.object_name:
                  return
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            cx = self.width() // 2
            cy = self.height() // 2
            
            # Neon glow pen
            from PyQt5.QtGui import QPen
            from PyQt5.QtCore import QPoint
            pen = QPen(QColor(0, 255, 255, 200), 2)
            painter.setPen(pen)
            
            vertices, edges = self._get_shape()
            
            projected = []
            for v in vertices:
                  px, py = self._project(v[0], v[1], v[2], cx, cy)
                  projected.append((px, py))
            
            for e in edges:
                  p1 = projected[e[0]]
                  p2 = projected[e[1]]
                  painter.drawLine(p1[0], p1[1], p2[0], p2[1])
            
            # Draw vertices as dots
            dot_pen = QPen(QColor(0, 255, 200, 255), 4)
            painter.setPen(dot_pen)
            for p in projected:
                  painter.drawPoint(p[0], p[1])
            
            # Label
            painter.setPen(QColor(0, 255, 255, 180))
            painter.drawText(cx - 40, cy + 90, self.object_name.upper())
            painter.end()
      
      def _get_shape(self):
            name = self.object_name
            if name in ("cell phone", "remote", "laptop", "book", "tablet"):
                  # Flat rectangle (phone shape)
                  v = [(-1,-1.8,-.2),(1,-1.8,-.2),(1,1.8,-.2),(-1,1.8,-.2),
                       (-1,-1.8,.2),(1,-1.8,.2),(1,1.8,.2),(-1,1.8,.2)]
                  e = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
            elif name in ("bottle", "cup", "vase", "wine glass"):
                  # Cylinder approximation
                  v = []
                  e = []
                  n = 8
                  for i in range(n):
                        a = math.radians(i * 360 / n)
                        v.append((math.cos(a), -1.5, math.sin(a)))
                  for i in range(n):
                        a = math.radians(i * 360 / n)
                        v.append((math.cos(a)*0.7, 1.5, math.sin(a)*0.7))
                  for i in range(n):
                        e.append((i, (i+1) % n))
                        e.append((n+i, n + (i+1) % n))
                        e.append((i, n+i))
            elif name in ("ball", "sports ball", "orange", "apple"):
                  # Sphere wireframe
                  v = []
                  e = []
                  rings = 6
                  segs = 8
                  for r in range(rings):
                        phi = math.pi * (r+1) / (rings+1)
                        for s in range(segs):
                              theta = 2 * math.pi * s / segs
                              x = math.sin(phi) * math.cos(theta)
                              y = math.cos(phi)
                              z = math.sin(phi) * math.sin(theta)
                              v.append((x, y, z))
                  for r in range(rings):
                        for s in range(segs):
                              idx = r * segs + s
                              next_s = r * segs + (s+1) % segs
                              e.append((idx, next_s))
                              if r < rings - 1:
                                    e.append((idx, idx + segs))
            else:
                  # Default: Cube
                  v = [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                       (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]
                  e = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
            return v, e

class InitialScreen(QWidget):
      def __init__(self, parent=None):
            super().__init__(parent)
            desktop = QApplication.desktop()
            screen_width = desktop.screenGeometry().width()
            screen_height = desktop.screenGeometry().height()
            
            # --- Premium Dark Gradient Background ---
            self.setStyleSheet("background: qradialgradient(cx:0.5, cy:0.35, radius:0.85, fx:0.5, fy:0.35, stop:0 #090d21, stop:0.5 #050713, stop:1 #020307);")
            
            main_layout = QGridLayout()
            main_layout.setContentsMargins(25, 20, 25, 20)
            main_layout.setSpacing(18)

            # --- Left Column ---
            left_layout = QVBoxLayout()
            left_layout.setSpacing(14)
            self.map_box, self.map_content, self.map_img = self.create_box("GEO COMMAND", "Acquiring GPS Lock...", hide_img_initially=False, accent_color=(50, 200, 120))
            # Map mode toggle buttons
            self.map_btn_layout = QHBoxLayout()
            map_btn_active = "background-color: rgba(50, 200, 120, 0.25); color: rgba(80, 220, 150, 0.95); border: 1px solid rgba(50, 200, 120, 0.5); border-radius: 4px; padding: 4px 8px; font-family: 'Segoe UI'; font-weight: 600; font-size: 9px; letter-spacing: 1px;"
            map_btn_inactive = "background-color: rgba(20, 20, 40, 0.4); color: rgba(100, 110, 140, 0.6); border: 1px solid rgba(80, 80, 120, 0.25); border-radius: 4px; padding: 4px 8px; font-family: 'Segoe UI'; font-weight: 600; font-size: 9px; letter-spacing: 1px;"
            self.btn_map = QPushButton("MAP")
            self.btn_weather = QPushButton("WEATHER")
            self.btn_wind = QPushButton("WIND")
            self.btn_map.setStyleSheet(map_btn_active)
            self.btn_weather.setStyleSheet(map_btn_inactive)
            self.btn_wind.setStyleSheet(map_btn_inactive)
            self.btn_map.setCursor(Qt.PointingHandCursor)
            self.btn_weather.setCursor(Qt.PointingHandCursor)
            self.btn_wind.setCursor(Qt.PointingHandCursor)
            self.btn_map.clicked.connect(lambda: self._switch_map_mode("map"))
            self.btn_weather.clicked.connect(lambda: self._switch_map_mode("weather"))
            self.btn_wind.clicked.connect(lambda: self._switch_map_mode("wind"))
            self.map_btn_layout.addWidget(self.btn_map)
            self.map_btn_layout.addWidget(self.btn_weather)
            self.map_btn_layout.addWidget(self.btn_wind)
            # Zoom buttons
            zoom_btn_style = "background-color: rgba(50, 200, 120, 0.2); color: rgba(80, 220, 150, 0.9); border: 1px solid rgba(50, 200, 120, 0.4); border-radius: 4px; padding: 2px 8px; font-family: 'Segoe UI'; font-weight: 700; font-size: 12px;"
            self.btn_zoom_in = QPushButton("+")
            self.btn_zoom_out = QPushButton("-")
            self.btn_zoom_in.setStyleSheet(zoom_btn_style)
            self.btn_zoom_out.setStyleSheet(zoom_btn_style)
            self.btn_zoom_in.setCursor(Qt.PointingHandCursor)
            self.btn_zoom_out.setCursor(Qt.PointingHandCursor)
            self.btn_zoom_in.setFixedSize(28, 22)
            self.btn_zoom_out.setFixedSize(28, 22)
            self.btn_zoom_in.clicked.connect(lambda: self._zoom_map(1))
            self.btn_zoom_out.clicked.connect(lambda: self._zoom_map(-1))
            self.map_btn_layout.addWidget(self.btn_zoom_in)
            self.map_btn_layout.addWidget(self.btn_zoom_out)
            self.map_box.layout().insertLayout(1, self.map_btn_layout)
            self._map_mode = "map"
            self._map_zoom = 11
            self._map_data = {}
            self._weather_data = {}
            self.camera_box, self.camera_content, self.camera_img = self.create_box("VISION SYSTEM", "Offline — Say 'Open Vision Mode'", hide_img_initially=False, accent_color=(0, 255, 140))
            self.asteroid_box, self.asteroid_content, _ = self.create_box("ISS TRACKER / THREATS", "Acquiring ISS Telemetry...", accent_color=(0, 180, 255))
            
            left_layout.addWidget(self.map_box)
            left_layout.addWidget(self.camera_box)
            left_layout.addWidget(self.asteroid_box)

            # --- Center Column: Avatar + Status ---
            mid_layout = QVBoxLayout()
            mid_layout.setSpacing(10)
            
            # Avatar with glow container
            avatar_container = QFrame()
            avatar_container.setStyleSheet("background: transparent; border: none;")
            avatar_inner = QVBoxLayout(avatar_container)
            avatar_inner.setAlignment(Qt.AlignCenter)
            
            self.gif_label = QLabel()
            self.movie = QMovie(GraphicsDirectoryPath('Jarvis.gif'))
            self.movie.setScaledSize(QSize(140, 140))
            self.gif_label.setMovie(self.movie)
            self.gif_label.setAlignment(Qt.AlignCenter)
            self.gif_label.setStyleSheet("border: none; background: transparent;")
            self.movie.stop()
            self.movie.jumpToFrame(0)
            avatar_inner.addWidget(self.gif_label)
            
            # Status label
            self.label = QLabel("")
            self.label.setStyleSheet("color: rgba(0, 220, 255, 0.9); font-family: 'Segoe UI', sans-serif; font-size: 13px; font-weight: 600; letter-spacing: 3px; border: none; background: transparent;")
            self.label.setAlignment(Qt.AlignCenter)
            
            # Mic button
            self.icon_label = QLabel()
            pixmap = QPixmap(GraphicsDirectoryPath('Mic_on.png'))
            self.icon_label.setPixmap(pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.icon_label.setFixedSize(48, 48)
            self.icon_label.setAlignment(Qt.AlignCenter)
            self.icon_label.setStyleSheet("border: 1px solid rgba(0, 220, 255, 0.3); border-radius: 24px; background: rgba(0, 220, 255, 0.05);")
            self.icon_label.setCursor(Qt.PointingHandCursor)
            self.toggled = True
            self.toggle_icon()
            self.icon_label.mousePressEvent = self.toggle_icon
            
            # System info label
            self.sys_info = QLabel("FRIDAY AI v3.0 — ONLINE")
            self.sys_info.setStyleSheet("color: rgba(100, 140, 180, 0.6); font-family: 'Segoe UI', sans-serif; font-size: 9px; letter-spacing: 2px; border: none; background: transparent;")
            self.sys_info.setAlignment(Qt.AlignCenter)
            
            mid_layout.addStretch(2)
            mid_layout.addWidget(avatar_container, alignment=Qt.AlignCenter)
            mid_layout.addSpacing(8)
            mid_layout.addWidget(self.label, alignment=Qt.AlignCenter)
            mid_layout.addSpacing(4)
            mid_layout.addWidget(self.icon_label, alignment=Qt.AlignCenter)
            mid_layout.addSpacing(10)
            mid_layout.addWidget(self.sys_info, alignment=Qt.AlignCenter)
            mid_layout.addStretch(2)

            # --- Right Column ---
            right_layout = QVBoxLayout()
            right_layout.setSpacing(14)
            self.telescope_box, self.telescope_content, self.telescope_img = self.create_box("SPACE TELESCOPE", "Connecting to Deep Space Network...", accent_color=(160, 100, 255))
            # Add Hubble/JWST toggle buttons
            self.telescope_btn_layout = QHBoxLayout()
            self.btn_jwst = QPushButton("JAMES WEBB")
            self.btn_hubble = QPushButton("HUBBLE")
            btn_style_active = "background-color: rgba(160, 100, 255, 0.25); color: rgba(180, 140, 255, 0.95); border: 1px solid rgba(160, 100, 255, 0.5); border-radius: 4px; padding: 5px 10px; font-family: 'Segoe UI', sans-serif; font-weight: 600; font-size: 10px; letter-spacing: 1px;"
            btn_style_inactive = "background-color: rgba(20, 20, 40, 0.4); color: rgba(100, 110, 140, 0.6); border: 1px solid rgba(80, 80, 120, 0.25); border-radius: 4px; padding: 5px 10px; font-family: 'Segoe UI', sans-serif; font-weight: 600; font-size: 10px; letter-spacing: 1px;"
            self.btn_jwst.setStyleSheet(btn_style_active)
            self.btn_hubble.setStyleSheet(btn_style_inactive)
            self.btn_jwst.setCursor(Qt.PointingHandCursor)
            self.btn_hubble.setCursor(Qt.PointingHandCursor)
            self.btn_jwst.clicked.connect(lambda: self._switch_telescope("jwst"))
            self.btn_hubble.clicked.connect(lambda: self._switch_telescope("hubble"))
            self.telescope_btn_layout.addWidget(self.btn_jwst)
            self.telescope_btn_layout.addWidget(self.btn_hubble)
            # Telescope zoom buttons
            tel_zoom_style = "background-color: rgba(160, 100, 255, 0.2); color: rgba(180, 140, 255, 0.9); border: 1px solid rgba(160, 100, 255, 0.4); border-radius: 4px; padding: 2px 8px; font-family: 'Segoe UI'; font-weight: 700; font-size: 12px;"
            self.btn_tel_zoom_in = QPushButton("+")
            self.btn_tel_zoom_out = QPushButton("-")
            self.btn_tel_zoom_in.setStyleSheet(tel_zoom_style)
            self.btn_tel_zoom_out.setStyleSheet(tel_zoom_style)
            self.btn_tel_zoom_in.setCursor(Qt.PointingHandCursor)
            self.btn_tel_zoom_out.setCursor(Qt.PointingHandCursor)
            self.btn_tel_zoom_in.setFixedSize(28, 22)
            self.btn_tel_zoom_out.setFixedSize(28, 22)
            self.btn_tel_zoom_in.clicked.connect(lambda: self._zoom_telescope(1))
            self.btn_tel_zoom_out.clicked.connect(lambda: self._zoom_telescope(-1))
            self.telescope_btn_layout.addWidget(self.btn_tel_zoom_in)
            self.telescope_btn_layout.addWidget(self.btn_tel_zoom_out)
            self.telescope_box.layout().insertLayout(1, self.telescope_btn_layout)
            self._active_telescope = "jwst"
            self._telescope_data = {}
            self._telescope_scale = 1.0
            self.launches_box, self.launches_content, _ = self.create_box("ORBITAL LAUNCHES", "Fetching Telemetry...", accent_color=(255, 120, 50))
            self.hologram_box, self.hologram_content, _ = self.create_box("3D HOLOGRAM", "Awaiting Target Object Scan...", accent_color=(255, 50, 180))
            self.hologram_widget = HologramWidget()
            self.hologram_box.layout().insertWidget(2, self.hologram_widget)
            
            right_layout.addWidget(self.telescope_box)
            right_layout.addWidget(self.launches_box)
            right_layout.addWidget(self.hologram_box)

            main_layout.addLayout(left_layout, 0, 0)
            main_layout.addLayout(mid_layout, 0, 1)
            main_layout.addLayout(right_layout, 0, 2)
            
            # Balanced proportions
            main_layout.setColumnStretch(0, 5)
            main_layout.setColumnStretch(1, 3)
            main_layout.setColumnStretch(2, 5)

            self.setLayout(main_layout)
            self.setFixedHeight(screen_height)
            self.setFixedWidth(screen_width)
            
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.SpeechRecogText)
            self.timer.start(5)
            
            # Start Space Data
            self.worker = SpaceDataWorker()
            self.worker.data_ready.connect(self.update_widgets)
            self.worker.start()

            self.vision_thread = None

      def create_box(self, title_text, content_text, hide_img_initially=True, accent_color=None):
            if accent_color is None:
                  accent_color = (0, 220, 255)  # Default cyan
            r, g, b = accent_color
            
            frame = QFrame()
            frame.setStyleSheet(f"""
                  QFrame {{ 
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                              stop:0 rgba(11, 16, 32, 0.88),
                              stop:0.5 rgba(15, 22, 44, 0.82),
                              stop:1 rgba(8, 12, 26, 0.88));
                        border: 1px solid rgba({r}, {g}, {b}, 0.24);
                        border-radius: 14px;
                  }}
            """)
            
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(r, g, b, 35))
            shadow.setOffset(0, 3)
            frame.setGraphicsEffect(shadow)

            layout = QVBoxLayout(frame)
            layout.setContentsMargins(16, 12, 16, 12)
            layout.setSpacing(6)
            
            # Title row with status dot
            title_row = QHBoxLayout()
            status_dot = QLabel("\u25CF")
            status_dot.setStyleSheet(f"color: rgba({r}, {g}, {b}, 0.95); font-size: 8px; border: none; background: transparent;")
            title = QLabel(title_text)
            title.setStyleSheet(f"color: rgba({r}, {g}, {b}, 0.95); font-family: 'Segoe UI', sans-serif; font-weight: 700; font-size: 10px; border: none; background: transparent; letter-spacing: 2.5px; text-transform: uppercase;")
            title_row.addWidget(status_dot)
            title_row.addWidget(title)
            title_row.addStretch()
            
            # Gradient accent line
            line = QFrame()
            line.setFixedHeight(1)
            line.setStyleSheet(f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba({r},{g},{b},0.55), stop:0.4 rgba({r},{g},{b},0.12), stop:1 transparent); border: none;")
            
            content = QLabel(content_text)
            content.setStyleSheet("color: rgba(160, 180, 205, 0.88); font-family: 'Segoe UI', sans-serif; font-size: 11px; border: none; background: transparent; padding-top: 2px; line-height: 1.45;")
            content.setWordWrap(True)
            content.setAlignment(Qt.AlignTop)
            
            img_label = QLabel()
            img_label.setStyleSheet("border: none; background: transparent; border-radius: 8px;")
            img_label.setAlignment(Qt.AlignCenter)
            if hide_img_initially:
                  img_label.hide()
            
            layout.addLayout(title_row)
            layout.addWidget(line)
            layout.addWidget(img_label)
            layout.addWidget(content)
            layout.addStretch()
            return frame, content, img_label

      def update_camera_image(self, cv_img):
            rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
            p = convert_to_Qt_format.scaled(480, 360, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.camera_img.setPixmap(QPixmap.fromImage(p))
            self.camera_content.setText("LIVE - YOLOv8 Tracking Active")

      def update_widgets(self, data):
            # Map data
            if data.get("map"):
                  self._map_data = data["map"]
            if data.get("weather"):
                  self._weather_data = data["weather"]
            self._display_map_mode(self._map_mode)
            
            # Store telescope data for toggle switching
            for t in ["jwst", "hubble"]:
                  tkey = f"telescope_{t}"
                  if data.get(tkey):
                        self._telescope_data[t] = data[tkey]
            # Display the active telescope
            self._display_telescope(self._active_telescope)
            
            if data.get("asteroids"):
                  txt = ""
                  for a in data["asteroids"][:4]:
                        txt += f"\u2022 {a['name']} | Hazard: {'YES' if a['is_hazardous'] else 'NO'}\n"
                  self.asteroid_content.setText(txt)
            else:
                  self.asteroid_content.setText("No objects detected.")
                  
            if data.get("launches"):
                  txt = ""
                  for l in data["launches"][:3]:
                        name = l.get('name', 'Unknown')
                        date = l.get('window_start', 'Unknown')[:10]
                        txt += f"\u25B6 {name}\n  {date}\n\n"
                  self.launches_content.setText(txt.strip())
                  # Start countdown refresh timer
                  if not hasattr(self, '_countdown_timer'):
                        self._countdown_timer = QTimer(self)
                        self._countdown_timer.timeout.connect(self._refresh_countdown)
                        self._countdown_timer.start(1000)  # Every second

      def _switch_map_mode(self, mode):
            self._map_mode = mode
            active = "background-color: rgba(50, 200, 120, 0.25); color: rgba(80, 220, 150, 0.95); border: 1px solid rgba(50, 200, 120, 0.5); border-radius: 4px; padding: 4px 8px; font-family: 'Segoe UI'; font-weight: 600; font-size: 9px; letter-spacing: 1px;"
            inactive = "background-color: rgba(20, 20, 40, 0.4); color: rgba(100, 110, 140, 0.6); border: 1px solid rgba(80, 80, 120, 0.25); border-radius: 4px; padding: 4px 8px; font-family: 'Segoe UI'; font-weight: 600; font-size: 9px; letter-spacing: 1px;"
            self.btn_map.setStyleSheet(active if mode == "map" else inactive)
            self.btn_weather.setStyleSheet(active if mode == "weather" else inactive)
            self.btn_wind.setStyleSheet(active if mode == "wind" else inactive)
            self._display_map_mode(mode)

      def _display_map_mode(self, mode):
            if mode == "map":
                  # Show the OpenStreetMap tile
                  map_path = self._map_data.get("path", "")
                  if map_path and os.path.exists(map_path):
                        pixmap = QPixmap(map_path)
                        self.map_img.setPixmap(pixmap.scaled(420, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        self.map_img.show()
                  city = self._map_data.get("city", "")
                  lat = self._map_data.get("lat", 0)
                  lon = self._map_data.get("lon", 0)
                  self.map_content.setText(f"\u25CF {city}  |  {lat:.4f}, {lon:.4f}")

            elif mode == "weather":
                  self.map_img.hide()
                  w = self._weather_data
                  if w:
                        txt = f"\u2600 {w.get('condition', 'N/A')}\n\n"
                        txt += f"\u2022 Temperature: {w.get('temp', 0)}\u00B0C  (Feels {w.get('feels_like', 0)}\u00B0C)\n"
                        txt += f"\u2022 Humidity: {w.get('humidity', 0)}%\n"
                        txt += f"\u2022 Cloud Cover: {w.get('clouds', 0)}%\n"
                        txt += f"\u2022 Precipitation: {w.get('precipitation', 0)} mm\n"
                        txt += f"\u2022 Pressure: {w.get('pressure', 0)} hPa\n\n"
                        txt += f"\u25B6 {w.get('city', '')}  |  Next 12h Forecast Available"
                        self.map_content.setText(txt)
                  else:
                        self.map_content.setText("Fetching weather data...")

            elif mode == "wind":
                  self.map_img.hide()
                  w = self._weather_data
                  if w:
                        # Wind direction to compass
                        dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
                        wind_dir = w.get("wind_dir", 0)
                        compass = dirs[int((wind_dir + 11.25) / 22.5) % 16]
                        
                        txt = f"\u27A4 WIND ANALYSIS\n\n"
                        txt += f"\u2022 Speed: {w.get('wind_speed', 0)} km/h\n"
                        txt += f"\u2022 Direction: {wind_dir}\u00B0 ({compass})\n"
                        txt += f"\u2022 Pressure: {w.get('pressure', 0)} hPa\n\n"
                        # Show hourly wind speeds
                        hourly = w.get("hourly_wind", [])
                        if hourly:
                              txt += "12h Wind Trend:\n"
                              bar_max = max(hourly) if hourly else 1
                              for i, v in enumerate(hourly[:6]):
                                    bar_len = int(v / bar_max * 12) if bar_max > 0 else 0
                                    block_char = '\u2588'
                                    txt += f"  +{i}h  {block_char * bar_len} {v} km/h\n"
                        self.map_content.setText(txt)
                  else:
                        self.map_content.setText("Fetching wind data...")

      def _switch_telescope(self, telescope):
            self._active_telescope = telescope
            btn_active = "background-color: rgba(160, 100, 255, 0.25); color: rgba(180, 140, 255, 0.95); border: 1px solid rgba(160, 100, 255, 0.5); border-radius: 4px; padding: 5px 10px; font-family: 'Segoe UI', sans-serif; font-weight: 600; font-size: 10px; letter-spacing: 1px;"
            btn_inactive = "background-color: rgba(20, 20, 40, 0.4); color: rgba(100, 110, 140, 0.6); border: 1px solid rgba(80, 80, 120, 0.25); border-radius: 4px; padding: 5px 10px; font-family: 'Segoe UI', sans-serif; font-weight: 600; font-size: 10px; letter-spacing: 1px;"
            if telescope == "jwst":
                  self.btn_jwst.setStyleSheet(btn_active)
                  self.btn_hubble.setStyleSheet(btn_inactive)
            else:
                  self.btn_hubble.setStyleSheet(btn_active)
                  self.btn_jwst.setStyleSheet(btn_inactive)
            self._display_telescope(telescope)

      def _display_telescope(self, telescope):
            data = self._telescope_data.get(telescope)
            if data:
                  self.telescope_content.setText(f"{data.get('title', '')}\n{data.get('date_created', '')}")
                  full_path = data.get("local_full_path", "")
                  if not full_path:
                        current_dir = os.getcwd()
                        full_path = os.path.join(current_dir, "Frontend", "remote", "static", f"telescope_{telescope}.jpg")
                  if os.path.exists(full_path):
                        pixmap = QPixmap(full_path)
                        self.telescope_img.setPixmap(pixmap.scaled(480, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        self.telescope_img.show()
            else:
                  self.telescope_content.setText(f"Fetching {telescope.upper()} imagery...")
                  self.telescope_img.hide()

      def _refresh_countdown(self):
            try:
                  from Backend.SpaceAPI import space_client
                  launches = space_client.get_launch_countdown()
                  if launches:
                        txt = ""
                        for l in launches[:3]:
                              name = l.get('name', 'Unknown')
                              countdown = l.get('countdown_str', 'TBD')
                              txt += f"\u25B6 {name}\n  {countdown}\n\n"
                        self.launches_content.setText(txt.strip())
            except:
                  pass

      def SpeechRecogText(self):
            try:
                  with open(TempDirectoryPath('Status.data'), "r", encoding='utf-8') as file:
                        messages = file.read().strip()
            except:
                  messages = ""

            self.label.setText(messages)

            if "answering" in messages.lower():
                  if self.movie.state() != QMovie.Running:
                        self.movie.start()
            else:
                  if self.movie.state() == QMovie.Running:
                        self.movie.stop()
                        self.movie.jumpToFrame(0)

            # --- Check Camera Status ---
            try:
                  with open(TempDirectoryPath('Camera.data'), "r", encoding='utf-8') as file:
                        camera_status = file.read().strip()
            except:
                  camera_status = "False"

            if camera_status == "True" and self.vision_thread is None:
                  self.camera_content.setText("Initializing Advanced Vision...")
                  self.vision_thread = VisionThread()
                  self.vision_thread.change_pixmap_signal.connect(self.update_camera_image)
                  self.vision_thread.start()
            elif camera_status == "False" and self.vision_thread is not None:
                  self.camera_content.setText("Offline - Say 'Open Vision Mode'")
                  self.camera_img.clear()
                  self.vision_thread = None

            # --- ISS Telemetry ---
            try:
                  with open(TempDirectoryPath('ISS.data'), "r", encoding='utf-8') as file:
                        iss_data = json.loads(file.read().strip())
                  iss_txt = f"\u2022 ISS Position: {iss_data['iss_lat']:.1f}, {iss_data['iss_lon']:.1f}\n"
                  iss_txt += f"\u2022 Distance: {iss_data['distance_km']} km from {iss_data['user_city']}\n"
                  if iss_data.get('is_overhead'):
                        iss_txt += "\u26A0 ISS IS OVERHEAD! LOOK UP!"
                  else:
                        iss_txt += "\u2022 Status: In Orbit"
                  self.asteroid_content.setText(iss_txt)
            except:
                  pass

            # --- Hologram Object Detection ---
            try:
                  with open(TempDirectoryPath('HologramObject.data'), "r", encoding='utf-8') as file:
                        obj_name = file.read().strip()
                  if obj_name and obj_name != "NONE":
                        self.hologram_widget.set_object(obj_name)
                        self.hologram_content.setText(f"Projecting: {obj_name.upper()}")
            except:
                  pass

      def load_icon(self, path, width=60, height=60):
            pixmap = QPixmap(path)
            new_pixmap = pixmap.scaled(width, height)
            self.icon_label.setPixmap(new_pixmap)

      def toggle_icon(self, event=None):
            if self.toggled:
                  self.load_icon(GraphicsDirectoryPath('Mic_on.png'),40, 40)
                  MicButtonInitialed()
            else:
                  self.load_icon(GraphicsDirectoryPath('Mic_off.png'),40, 40)
                  MicButtonClosed()
            self.toggled = not self.toggled 
class MessageScreen(QWidget):

        def __init__(self, parent = None):
              super().__init__(parent) 
              desktop = QApplication.desktop()
              screen_width = desktop.screenGeometry().width()
              screen_height = desktop.screenGeometry().height()
              layout = QVBoxLayout()
              label = QLabel("")
              layout.addWidget(label)
              chat_section = ChatSection()
              layout.addWidget(chat_section)
              self.setLayout(layout)
              self.setStyleSheet("background-color: #020208;")
              self.setFixedHeight(screen_height)
              self.setFixedWidth(screen_width)

class CustomTopBar(QWidget):

        def __init__(self, parent, stacked_widget):
            super().__init__(parent)   
            self.initUI()
            self.current_screen = None
            self.stacked_widget = stacked_widget

        def initUI(self):
              self.setFixedHeight(42)
              self.setStyleSheet("background: rgba(6, 9, 20, 0.94); border-bottom: 1px solid rgba(0, 220, 255, 0.12);")
              layout = QHBoxLayout(self)
              layout.setContentsMargins(18, 0, 10, 0)
              layout.setSpacing(8)
              
              nav_btn_style = """
                    QPushButton { 
                        height: 28px; padding: 0 16px; 
                        background: rgba(0, 220, 255, 0.06); 
                        color: rgba(0, 220, 255, 0.85); 
                        border: 1px solid rgba(0, 220, 255, 0.18); 
                        border-radius: 6px; 
                        font-family: 'Segoe UI', sans-serif; 
                        font-size: 11px; 
                        font-weight: 600;
                        letter-spacing: 1px;
                    }
                    QPushButton:hover { 
                        background: rgba(0, 220, 255, 0.16); 
                        border-color: rgba(0, 220, 255, 0.45); 
                        color: #ffffff;
                    }
              """
              ctrl_btn_style = """
                    QPushButton { 
                        width: 30px; height: 26px; 
                        background: transparent; 
                        border: none; 
                        border-radius: 4px;
                        color: rgba(148, 163, 184, 0.7);
                        font-size: 13px;
                    }
                    QPushButton:hover { background: rgba(255, 255, 255, 0.08); color: #ffffff; }
              """
              close_btn_style = """
                    QPushButton { 
                        width: 30px; height: 26px; 
                        background: transparent; 
                        border: none; 
                        border-radius: 4px;
                        color: rgba(148, 163, 184, 0.7);
                        font-size: 13px;
                    }
                    QPushButton:hover { background: rgba(239, 68, 68, 0.75); color: #ffffff; }
              """
              
              title_container = QHBoxLayout()
              title_dot = QLabel("\u25CF")
              title_dot.setStyleSheet("color: #00e5ff; font-size: 10px; border: none; background: transparent;")
              title_label = QLabel(f" {str(Assistantname).upper()} AI")
              title_label.setStyleSheet("color: rgba(241, 245, 249, 0.9); font-family: 'Segoe UI', sans-serif; font-size: 12px; font-weight: 700; letter-spacing: 2px; background: transparent; border: none;")
              title_container.addWidget(title_dot)
              title_container.addWidget(title_label)
              
              home_button = QPushButton()
              home_icon = QIcon(GraphicsDirectoryPath("Home.png"))
              home_button.setIcon(home_icon)
              home_button.setText(" Dashboard")
              home_button.setStyleSheet(nav_btn_style)
              home_button.setCursor(Qt.PointingHandCursor)
              
              message_button = QPushButton()
              message_icon = QIcon(GraphicsDirectoryPath("Chats.png"))
              message_button.setIcon(message_icon)
              message_button.setText(" Chat Terminal")
              message_button.setStyleSheet(nav_btn_style)
              message_button.setCursor(Qt.PointingHandCursor)
              
              minimize_button = QPushButton("—")
              minimize_button.setStyleSheet(ctrl_btn_style)
              minimize_button.clicked.connect(self.minimizeWindow)
              
              self.maximize_button = QPushButton("□")
              self.maximize_icon = QIcon(GraphicsDirectoryPath('Maximize.png'))
              self.restore_icon = QIcon(GraphicsDirectoryPath('Minimize.png'))
              self.maximize_button.setStyleSheet(ctrl_btn_style)
              self.maximize_button.clicked.connect(self.maximizeWindow)
              
              close_button = QPushButton("✕")
              close_button.setStyleSheet(close_btn_style)
              close_button.clicked.connect(self.closeWindow)
              
              home_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
              message_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
              
              layout.addLayout(title_container)
              layout.addStretch(1)
              layout.addWidget(home_button)
              layout.addWidget(message_button)
              layout.addStretch(1)
              layout.addWidget(minimize_button)
              layout.addWidget(self.maximize_button)
              layout.addWidget(close_button)
              self.draggable = True 
              self.offset = None 

        def paintEvent(self, event):
              super().paintEvent(event) 

        def minimizeWindow(self):
              self.parent().showMinimized()

        def maximizeWindow(self):
              if self.parent().isMaximized():
                    self.parent().showNormal()
                    self.maximize_button.setIcon(self.maximize_icon)
              else:
                    self.parent().showMaximized()
                    self.maximize_button.setIcon(self.restore_icon)

        def closeWindow(self):
              self.parent().close()

        def mousePressEvent(self, event):
              if self.draggable:
                    self.offset = event.pos()

        def mouseMoveEvent(self, event):
              if self.draggable and self.offset:
                    new_pos = event.globalPos() - self.offset
                    self.parent().move(new_pos)


class MainWindow(QMainWindow):

        def __init__(self):
              super().__init__()
              self.setWindowFlag(Qt.FramelessWindowHint)
              self.initUI()

        def initUI(self):
              desktop = QApplication.desktop()
              screen_width = desktop.screenGeometry().width()
              screen_height = desktop.screenGeometry().height()
              stacked_widget = QStackedWidget(self)
              initial_screen = InitialScreen()
              message_screen = MessageScreen()
              stacked_widget.addWidget(initial_screen)
              stacked_widget.addWidget(message_screen)
              self.setGeometry(0, 0, screen_width, screen_height)
              self.setStyleSheet("background-color: black;")
              top_bar = CustomTopBar(self, stacked_widget)
              self.setMenuWidget(top_bar)
              self.setCentralWidget(stacked_widget)




                                                                                                                                                
def GraphicalUserInterface():
    import subprocess
    import time
    import webbrowser
    import os

    time.sleep(2.0)
    url = "https://localhost:5000"

    browsers = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]

    browser_proc = None
    for b_path in browsers:
        if os.path.exists(b_path):
            try:
                cmd = [
                    b_path,
                    f"--app={url}",
                    "--window-size=1366,840",
                    "--ignore-certificate-errors",
                    "--disable-infobars"
                ]
                print(f"[UI] Launching Modern F.R.I.D.A.Y. HUD via {os.path.basename(b_path)}...")
                browser_proc = subprocess.Popen(cmd)
                break
            except Exception as e:
                print(f"[UI WARN] Failed to launch {b_path}: {e}")

    if not browser_proc:
        print("[UI] Opening F.R.I.D.A.Y. HUD in default browser...")
        webbrowser.open(url)

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    GraphicalUserInterface()
