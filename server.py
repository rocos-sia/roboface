#!/usr/bin/env python3
"""
RoboFace 动画播放服务（RESTful API + 静态文件托管）

功能:
    1. 托管 index.html 与 RoboFace.lottie，浏览器全屏播放动画。
    2. 提供 RESTful API 切换动画状态（smile / proud / unhappy / daze）。

仅依赖 Python 标准库，无需 pip install。

用法:
    python server.py [--host 0.0.0.0] [--port 8000]

RESTful API:
    GET  /api/state            获取当前动画状态  -> {"state": "smile"}
    PUT  /api/state            设置动画状态      请求体: {"state": "proud"}
    GET  /api/states           列出所有可用状态   -> {"states": ["smile", "proud", "unhappy", "daze"]}
"""

import argparse
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# 与 .lottie 状态机输入 "states" 对应的合法取值
VALID_STATES = ["smile", "proud", "unhappy", "daze"]

# 当前状态（内存存储），初始为 smile
_current_state = "smile"
_state_lock = threading.Lock()


class RoboFaceHandler(BaseHTTPRequestHandler):
    """静态文件 + REST API 请求处理器。"""

    # ---------- 静态文件 ----------

    def _serve_static(self):
        # 规范化路径，防止目录穿越
        raw_path = self.path.split("?", 1)[0]
        if raw_path == "/":
            raw_path = "/index.html"

        rel = raw_path.lstrip("/")
        file_path = os.path.normpath(os.path.join(ROOT_DIR, rel))

        if not file_path.startswith(ROOT_DIR):
            return self._send_json(403, {"error": "forbidden"})

        if not os.path.isfile(file_path):
            return self._send_json(404, {"error": "not found"})

        ext = os.path.splitext(file_path)[1].lower()
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".lottie": "application/octet-stream",
        }.get(ext, "application/octet-stream")

        with open(file_path, "rb") as f:
            body = f.read()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    # ---------- REST API ----------

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length == 0:
            return None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?", 1)[0]

        if path == "/api/state":
            with _state_lock:
                return self._send_json(200, {"state": _current_state})

        if path == "/api/states":
            return self._send_json(200, {"states": VALID_STATES})

        return self._serve_static()

    def do_PUT(self):
        path = self.path.split("?", 1)[0]

        if path == "/api/state":
            body = self._read_json_body()
            if body is None or not isinstance(body, dict):
                return self._send_json(400, {"error": "请求体必须是 JSON 对象"})

            state = body.get("state")
            if state not in VALID_STATES:
                return self._send_json(
                    400,
                    {"error": f"无效状态 {state!r}，可用: {VALID_STATES}"},
                )

            global _current_state
            with _state_lock:
                _current_state = state
            return self._send_json(200, {"state": state})

        return self._send_json(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        # 精简日志，隐藏静态资源噪音
        if "/api/" in fmt:
            super().log_message(fmt, *args)


def main():
    parser = argparse.ArgumentParser(description="RoboFace 动画播放服务")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), RoboFaceHandler)
    print(f"RoboFace 服务已启动: http://localhost:{args.port}")
    print("REST API:")
    print("  GET /api/state")
    print("  PUT /api/state   body: {\"state\": \"proud\"}")
    print("  GET /api/states")
    print("按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
