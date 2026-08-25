#!/usr/bin/env python3
"""
RoboFace Lottie Animation Player
使用 lottie 库解析动画结构，PIL 直接渲染 PNG 帧，状态机四状态：smile / proud / unhappy / daze

依赖安装:
    pip install lottie pillow PySide6
"""

import sys
import io
import os
import zipfile

from lottie.parsers.tgs import parse_tgs   # 解析 dotlottie 内的动画 JSON

try:
    from PIL import Image
except ImportError:
    print("缺少依赖，请运行: pip install pillow")
    sys.exit(1)

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
        QWidget, QPushButton, QLabel, QGraphicsOpacityEffect,
    )
    from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QAbstractAnimation
    from PySide6.QtGui import QImage, QPixmap
except ImportError:
    print("缺少依赖，请运行: pip install PySide6")
    sys.exit(1)

FADE_MS = 66   # 4帧 @ 60fps，与 lottie 原始过渡时长一致

LOTTIE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "RoboFace.lottie")
DISPLAY_W, DISPLAY_H = 608, 288   # 40% of 1520×719

BTN_STYLE = """
QPushButton {
    background: #2d2d50; color: #e0e0ff; border: 1px solid #4a4a80;
    border-radius: 6px; font-size: 14px;
}
QPushButton:hover   { background: #3d3d70; border-color: #8080c0; }
QPushButton:pressed { background: #5050a0; }
QPushButton:checked { background: #4a4a90; border-color: #a0a0ff; }
"""


def _pil_to_pixmap(img: Image.Image) -> QPixmap:
    img = img.convert("RGBA")
    data = img.tobytes("raw", "RGBA")
    qimg = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)


def load_state_pixmaps(path: str) -> tuple[dict[str, QPixmap], list[str]]:
    """
    用 lottie 解析动画，从 markers 读取状态顺序，
    直接以 PIL 加载对应 PNG，缩放后转为 QPixmap。
    返回 (state → QPixmap 字典, 状态顺序列表)。
    """
    with zipfile.ZipFile(path) as z:
        # lottie 库：解析动画 JSON，读取 markers 获得状态定义
        animation = parse_tgs(io.BytesIO(z.read("a/main scene.json")))
        state_order = [m.comment for m in (animation.markers or [])]  # type: ignore[union-attr]

        pixmaps: dict[str, QPixmap] = {}
        for state in state_order:
            raw = z.read(f"i/{state}.png")
            img = Image.open(io.BytesIO(raw)).resize(
                (DISPLAY_W, DISPLAY_H), Image.Resampling.LANCZOS
            )
            pixmaps[state] = _pil_to_pixmap(img)

    return pixmaps, state_order


class RoboFaceWindow(QMainWindow):
    INITIAL_STATE = "smile"

    def __init__(self, pixmaps: dict[str, QPixmap], state_order: list[str]):
        super().__init__()
        self.setWindowTitle("RoboFace")
        self.setStyleSheet("background: #12122a;")
        self._pixmaps = pixmaps
        self._state = self.INITIAL_STATE
        self._pending: str | None = None
        self._build_ui(state_order)
        # 淡入/淡出效果
        self._opacity = QGraphicsOpacityEffect(self.frame_label)
        self.frame_label.setGraphicsEffect(self._opacity)
        self._anim = QPropertyAnimation(self._opacity, b"opacity", self)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._anim.finished.connect(self._on_anim_done)
        self._show(self.INITIAL_STATE)

    def _build_ui(self, state_order: list[str]):
        central = QWidget()
        self.setCentralWidget(central)
        vbox = QVBoxLayout(central)
        vbox.setContentsMargins(0, 0, 0, 12)
        vbox.setSpacing(8)

        self.frame_label = QLabel()
        self.frame_label.setFixedSize(DISPLAY_W, DISPLAY_H)
        self.frame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(self.frame_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        hbox = QHBoxLayout()
        hbox.setContentsMargins(16, 0, 16, 0)
        hbox.setSpacing(8)
        self._buttons: dict[str, QPushButton] = {}
        for state in state_order:
            btn = QPushButton(state.capitalize())
            btn.setFixedHeight(38)
            btn.setCheckable(True)
            btn.setStyleSheet(BTN_STYLE)
            btn.clicked.connect(lambda _, s=state: self._switch(s))
            self._buttons[state] = btn
            hbox.addWidget(btn)
        self._buttons[self.INITIAL_STATE].setChecked(True)
        vbox.addLayout(hbox)

        self.setFixedSize(DISPLAY_W, DISPLAY_H + 62)

    def _show(self, state: str):
        self.frame_label.setPixmap(self._pixmaps[state])

    def _fade_to(self, state: str):
        """淡出当前帧，完成后换图再淡入。"""
        self._pending = state
        self._anim.stop()
        self._anim.setDuration(FADE_MS)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.start(QAbstractAnimation.DeletionPolicy.KeepWhenStopped)

    def _on_anim_done(self):
        if self._pending is None:
            return
        self._show(self._pending)
        self._pending = None
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start(QAbstractAnimation.DeletionPolicy.KeepWhenStopped)

    def _switch(self, state: str):
        if state == self._state:
            return
        self._buttons[self._state].setChecked(False)
        self._state = state
        self._buttons[state].setChecked(True)
        self._fade_to(state)


def main():
    app = QApplication(sys.argv)
    pixmaps, state_order = load_state_pixmaps(LOTTIE_PATH)
    win = RoboFaceWindow(pixmaps, state_order)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
