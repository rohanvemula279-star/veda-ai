"""
Veda AI - Floating Desktop Widget
An always-on-top, movable desktop companion orb with voice dictation,
quick command input, and direct integration with Veda AI core.
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Callable, Optional

from PyQt6.QtCore import (
    QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRectF, QSize, Qt,
    QTimer, pyqtSignal,
)
from PyQt6.QtGui import (
    QAction, QBrush, QColor, QFont, QIcon, QPainter, QPen, QRadialGradient,
)
from PyQt6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton,
    QVBoxLayout, QWidget,
)

CONFIG_PATH = Path(__file__).resolve().parent / "config" / "widget_pos.json"


class VedaDesktopOrb(QWidget):
    """
    Floating circular animated orb widget.
    Draggable anywhere on the desktop, always on top.
    """
    single_clicked = pyqtSignal()
    double_clicked = pyqtSignal()
    voice_requested = pyqtSignal()
    command_submitted = pyqtSignal(str)
    position_changed = pyqtSignal(int, int)

    def __init__(self, parent: Optional[QWidget] = None, on_command: Optional[Callable[[str], Any]] = None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(96, 96)

        self._on_command = on_command
        self._state = "idle"  # idle, listening, thinking, executing, speaking, muted
        self._status_line = "Ready"
        self._hovered = False

        # Animation states
        self._anim_angle = 0.0
        self._ring2_angle = 0.0
        self._ring3_angle = 0.0
        self._breath_val = 0.0
        self._breath_dir = 1.0
        self._particle_angles = [i * 45.0 for i in range(8)]
        self._particle_trails = [[] for _ in range(8)]

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._anim_tick)
        self._anim_timer.start(25)  # 40fps

        self._single_timer = QTimer(self)
        self._single_timer.setSingleShot(True)
        self._single_timer.timeout.connect(self.single_clicked.emit)

        self._dragging = False
        self._drag_button = None
        self._drag_offset = QPoint(0, 0)
        self._press_pos = QPoint(0, 0)

        self._load_saved_position()
        self._apply_state_style()

    def _anim_tick(self):
        self._anim_angle = (self._anim_angle + 1.8) % 360.0
        self._ring2_angle = (self._ring2_angle - 1.2) % 360.0
        self._ring3_angle = (self._ring3_angle + 2.5) % 360.0
        self._breath_val += 0.025 * self._breath_dir
        if self._breath_val >= 1.0:
            self._breath_dir = -1.0
        elif self._breath_val <= 0.0:
            self._breath_dir = 1.0

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        for i in range(len(self._particle_angles)):
            speed = 0.8 + i * 0.12
            self._particle_angles[i] = (self._particle_angles[i] + speed) % 360.0
            rad = math.radians(self._particle_angles[i])
            orbit_r = 38.0 + (i % 3) * 2.5
            px = cx + math.cos(rad) * orbit_r
            py = cy + math.sin(rad) * orbit_r
            trail = self._particle_trails[i]
            trail.append((px, py))
            if len(trail) > 6:
                trail.pop(0)
        self.update()

    def set_state(self, state: str, detail: Optional[str] = None):
        self._state = (state or "idle").strip().lower()
        self._status_line = detail or self._default_status()
        self._apply_state_style()

    def _default_status(self) -> str:
        return {
            "idle": "Ready",
            "listening": "Listening...",
            "thinking": "Thinking...",
            "executing": "Executing task...",
            "speaking": "Speaking",
            "muted": "Muted",
            "error": "Error",
        }.get(self._state, "Ready")

    def _apply_state_style(self):
        self.setToolTip(
            f"Veda AI Widget\nStatus: {self._status_line}\n"
            f"• Click: Open Quick Command Bar\n"
            f"• Double-Click: Open Veda App\n"
            f"• Right-Click: Options / Voice\n"
            f"• Drag: Move anywhere"
        )
        self.update()

    def _get_colors(self):
        # Color palettes based on state
        if self._state == "listening":
            return (0, 240, 255)  # Cyan
        elif self._state in ("thinking", "executing"):
            return (180, 70, 255)  # Purple
        elif self._state == "speaking":
            return (0, 255, 170)  # Emerald
        elif self._state == "muted":
            return (255, 70, 70)  # Red
        return (255, 179, 0)  # Signature Gold

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0

        ar, ag, ab = self._get_colors()
        breath = self._breath_val
        hover_boost = 1.35 if self._hovered else 1.0

        # 1. Atmospheric Ambient Glow
        glow_alpha = int((30 + breath * 50) * hover_boost)
        glow_r = 44.0 + breath * 5.0
        glow = QRadialGradient(cx, cy, glow_r)
        glow.setColorAt(0.0, QColor(ar, ag, ab, glow_alpha))
        glow.setColorAt(0.5, QColor(ar, ag, ab, int(glow_alpha * 0.35)))
        glow.setColorAt(1.0, QColor(ar, ag, ab, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(QPointF(cx, cy), glow_r, glow_r)

        # 2. Outer Dashed Orbit Ring
        dash_pen = QPen(QColor(ar, ag, ab, int(20 + breath * 20)), 0.8)
        dash_pen.setStyle(Qt.PenStyle.DotLine)
        painter.setPen(dash_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), 41.0, 41.0)

        # 3. Rotating Orbital Arcs
        a1 = int((160 + breath * 80) * hover_boost)
        pen1 = QPen(QColor(ar, ag, ab, min(255, a1)), 2.4)
        pen1.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen1)
        painter.drawArc(QRectF(cx - 37, cy - 37, 74, 74), int(self._anim_angle * 16), int(115 * 16))

        a2 = int((90 + breath * 50) * hover_boost)
        pen2 = QPen(QColor(ar, ag, ab, min(255, a2)), 1.5)
        pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen2)
        painter.drawArc(QRectF(cx - 34, cy - 34, 68, 68), int(self._ring2_angle * 16), int(95 * 16))

        # 4. Core Glass Sphere
        core_grad = QRadialGradient(cx, cy - 4.0, 29.0)
        core_grad.setColorAt(0.0, QColor(16, 18, 24, 252))
        core_grad.setColorAt(0.85, QColor(6, 8, 12, 254))
        core_grad.setColorAt(1.0, QColor(ar, ag, ab, 30))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(core_grad))
        painter.drawEllipse(QPointF(cx, cy), 28.0, 28.0)

        # Inner Rim
        rim_alpha = int((50 + breath * 40) * hover_boost)
        rim_pen = QPen(QColor(ar, ag, ab, min(255, rim_alpha)), 1.2)
        painter.setPen(rim_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), 28.0, 28.0)

        # 5. Comet Particle Trails
        for i in range(len(self._particle_trails)):
            trail = self._particle_trails[i]
            for t_idx, (px, py) in enumerate(trail):
                frac = (t_idx + 1) / max(len(trail), 1)
                t_alpha = int(frac * (60 + breath * 90) * hover_boost)
                t_size = 0.6 + frac * (1.2 + (i % 3) * 0.4)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(ar, ag, ab, min(255, t_alpha))))
                painter.drawEllipse(QPointF(px, py), t_size, t_size)
            if trail:
                hx, hy = trail[-1]
                head_alpha = int((140 + breath * 115) * hover_boost)
                chead = QColor(ar, ag, ab).lighter(140)
                painter.setBrush(QBrush(QColor(chead.red(), chead.green(), chead.blue(), min(255, head_alpha))))
                painter.drawEllipse(QPointF(hx, hy), 2.2, 2.2)

        # 6. Typography: VEDA
        text_alpha = int((220 + breath * 35) * hover_boost)
        painter.setPen(QPen(QColor(ar, ag, ab, min(255, text_alpha))))
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        painter.setFont(font)
        painter.drawText(QRectF(cx - 26, cy - 11, 52, 22), Qt.AlignmentFlag.AlignCenter, "VEDA")

        painter.end()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._press_pos = event.globalPosition().toPoint()
            self._drag_offset = self._press_pos - self.frameGeometry().topLeft()
            self._single_timer.stop()
            self._drag_button = Qt.MouseButton.LeftButton
            event.accept()
            return
        elif event.button() == Qt.MouseButton.RightButton:
            self._dragging = False
            self._press_pos = event.globalPosition().toPoint()
            self._drag_offset = self._press_pos - self.frameGeometry().topLeft()
            self._single_timer.stop()
            self._drag_button = Qt.MouseButton.RightButton
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & (Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton):
            pos = event.globalPosition().toPoint()
            if not self._dragging and (pos - self._press_pos).manhattanLength() > 6:
                self._dragging = True
            if self._dragging:
                screen = QApplication.primaryScreen().availableGeometry()
                new_pos = pos - self._drag_offset
                new_x = max(screen.left(), min(new_pos.x(), screen.right() - self.width()))
                new_y = max(screen.top(), min(new_pos.y(), screen.bottom() - self.height()))
                self.move(new_x, new_y)
                self.position_changed.emit(new_x, new_y)
                self._save_position(new_x, new_y)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self._dragging:
            self._single_timer.start(180)
        elif event.button() == Qt.MouseButton.RightButton:
            if not self._dragging:
                self._show_context_menu(event.globalPosition().toPoint())
            self._dragging = False
            self._drag_button = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._single_timer.stop()
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)

    def _show_context_menu(self, global_pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(10, 12, 18, 245);
                color: #ffffff;
                border: 1px solid rgba(255, 179, 0, 0.3);
                border-radius: 10px;
                padding: 6px;
                font-family: 'Segoe UI';
                font-size: 12px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background: rgba(255, 179, 0, 0.18);
                color: #ffb300;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.08);
                margin: 4px 6px;
            }
        """)

        a_voice = menu.addAction("🎙️ Voice Command")
        a_cmd = menu.addAction("💬 Quick Command Bar")
        a_open = menu.addAction("🪟 Open Veda AI")
        menu.addSeparator()
        a_mute = menu.addAction("🔇 Mute / Unmute")
        a_hide = menu.addAction("❌ Hide Widget")

        a_voice.triggered.connect(self.voice_requested.emit)
        a_cmd.triggered.connect(self.single_clicked.emit)
        a_open.triggered.connect(self.double_clicked.emit)
        a_mute.triggered.connect(lambda: self.command_submitted.emit("mute"))
        a_hide.triggered.connect(self.hide)

        menu.exec(global_pos)

    def _load_saved_position(self):
        try:
            if CONFIG_PATH.exists():
                data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                x = data.get("x")
                y = data.get("y")
                if x is not None and y is not None:
                    self.move(int(x), int(y))
                    return
        except Exception:
            pass

        # Default: Bottom-right screen corner
        try:
            screen = QApplication.primaryScreen().availableGeometry()
            self.move(screen.right() - self.width() - 24, screen.bottom() - self.height() - 100)
        except Exception:
            self.move(100, 100)

    def _save_position(self, x: int, y: int):
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(json.dumps({"x": x, "y": y}, indent=2), encoding="utf-8")
        except Exception:
            pass


class VedaQuickCommandBar(QWidget):
    """
    Companion glassmorphic command bar positioned dynamically next to the orb.
    Allows typing commands or clicking microphone for voice dictation.
    """
    submitted = pyqtSignal(str)
    voice_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(540, 50)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        self._frame = QFrame()
        self._frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(8, 10, 16, 248),
                    stop:0.5 rgba(14, 16, 24, 252),
                    stop:1 rgba(8, 10, 16, 248));
                border: 1px solid rgba(255, 179, 0, 0.35);
                border-radius: 22px;
            }
        """)
        frame_lay = QHBoxLayout(self._frame)
        frame_lay.setContentsMargins(10, 4, 10, 4)
        frame_lay.setSpacing(8)

        # Veda Mini Badge
        badge = QLabel("VEDA")
        badge.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        badge.setStyleSheet("""
            color: #ffb300;
            background: rgba(255, 179, 0, 0.12);
            border: 1px solid rgba(255, 179, 0, 0.3);
            border-radius: 12px;
            padding: 3px 8px;
        """)
        frame_lay.addWidget(badge)

        # Input line
        self._input = QLineEdit()
        self._input.setPlaceholderText("Ask Veda AI or type any task...")
        self._input.setFont(QFont("Segoe UI", 10))
        self._input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                color: #ffffff;
                border: none;
                padding: 4px 6px;
                selection-background-color: rgba(255, 179, 0, 0.3);
            }
        """)
        self._input.returnPressed.connect(self._handle_submit)
        frame_lay.addWidget(self._input, stretch=1)

        # Mic button
        self._mic_btn = QPushButton("🎙️")
        self._mic_btn.setFixedSize(32, 32)
        self._mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mic_btn.setToolTip("Voice Input")
        self._mic_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                color: #ffffff;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(0, 240, 255, 0.2);
                border-color: #00f0ff;
            }
        """)
        self._mic_btn.clicked.connect(self.voice_clicked.emit)
        frame_lay.addWidget(self._mic_btn)

        # Send button
        self._send_btn = QPushButton("➔")
        self._send_btn.setFixedSize(32, 32)
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setToolTip("Submit Task")
        self._send_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 179, 0, 0.15);
                border: 1px solid rgba(255, 179, 0, 0.4);
                border-radius: 16px;
                color: #ffb300;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 179, 0, 0.35);
                border-color: #ffb300;
            }
        """)
        self._send_btn.clicked.connect(self._handle_submit)
        frame_lay.addWidget(self._send_btn)

        layout.addWidget(self._frame)

    def show_near_orb(self, orb: QWidget):
        geo = orb.geometry()
        screen = QApplication.primaryScreen().availableGeometry()

        # Position to the left of orb if space permits, else to the right
        if geo.left() - self.width() - 12 >= screen.left():
            x = geo.left() - self.width() - 12
        else:
            x = min(geo.right() + 12, screen.right() - self.width())

        y = max(screen.top() + 10, min(geo.center().y() - self.height() // 2, screen.bottom() - self.height() - 10))
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
        self._input.setFocus()

    def _handle_submit(self):
        text = self._input.text().strip()
        if text:
            self.submitted.emit(text)
            self._input.clear()
            self.hide()


class VedaDesktopWidget:
    """
    Manager that pairs the VedaDesktopOrb with the VedaQuickCommandBar and connects
    them directly to Veda's UI or backend callback.
    """
    def __init__(self, ui_or_app=None, on_command: Optional[Callable[[str], Any]] = None):
        self._ui = ui_or_app
        self._on_command = on_command
        self.orb = VedaDesktopOrb(on_command=on_command)
        self.bar = VedaQuickCommandBar()

        # Wire events
        self.orb.single_clicked.connect(self._toggle_bar)
        self.orb.double_clicked.connect(self._open_main_app)
        self.orb.voice_requested.connect(self._trigger_voice)
        self.bar.submitted.connect(self._execute_command)
        self.bar.voice_clicked.connect(self._trigger_voice)

    def show(self):
        self.orb.show()
        self.orb.raise_()

    def hide(self):
        self.bar.hide()
        self.orb.hide()

    def set_state(self, state: str, detail: Optional[str] = None):
        self.orb.set_state(state, detail)

    def _toggle_bar(self):
        if self.bar.isVisible():
            self.bar.hide()
        else:
            self.bar.show_near_orb(self.orb)

    def _open_main_app(self):
        if self._ui is not None:
            if hasattr(self._ui, "show_main"):
                self._ui.show_main()
            elif hasattr(self._ui, "show"):
                self._ui.show()

    def _trigger_voice(self):
        self.set_state("listening", "Listening for voice...")
        if self._ui is not None:
            if hasattr(self._ui, "_toggle_mute") and getattr(self._ui, "muted", False):
                self._ui._toggle_mute()
            if hasattr(self._ui, "on_text_command") and callable(self._ui.on_text_command):
                # Voice mode will capture in background
                pass
        # If standalone with callback:
        try:
            import speech_recognition as sr
            import threading

            def _listen_worker():
                recognizer = sr.Recognizer()
                try:
                    with sr.Microphone() as source:
                        recognizer.adjust_for_ambient_noise(source, duration=0.6)
                        audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    heard = recognizer.recognize_google(audio).strip()
                    if heard:
                        self._execute_command(heard)
                except Exception:
                    pass
                finally:
                    self.set_state("idle", "Ready")

            threading.Thread(target=_listen_worker, daemon=True).start()
        except Exception:
            pass

    def _execute_command(self, text: str):
        if not text:
            return
        self.set_state("thinking", f"Processing: {text[:20]}...")
        if self._ui is not None:
            if hasattr(self._ui, "_submit_command"):
                self._ui._submit_command(text)
            elif hasattr(self._ui, "submit_command"):
                self._ui.submit_command(text)
            elif hasattr(self._ui, "_win") and hasattr(self._ui._win, "submit_command"):
                self._ui._win.submit_command(text)
        elif self._on_command is not None:
            self._on_command(text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = VedaDesktopWidget(on_command=lambda cmd: print(f"Executing: {cmd}"))
    widget.show()
    sys.exit(app.exec())
