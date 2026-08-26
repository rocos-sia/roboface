#!/usr/bin/env python3
"""
RoboFace 桌面启动器（用于打包成 exe）

双击后:
    1. 在后台线程启动 HTTP 服务（复用 server.py）
    2. 用系统浏览器（Edge/Chrome）全屏(kiosk)打开页面
    3. 服务持续运行，随时可通过 RESTful API 切换动画状态

退出方式: 关闭浏览器或按 Ctrl+C，程序会同时停止 HTTP 服务。
"""

import argparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer

import server


def log(msg: str) -> None:
    """窗口化 exe 无控制台，把关键信息写进临时日志便于排查。"""
    path = os.path.join(tempfile.gettempdir(), "roboface.log")
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except OSError:
        pass


def find_free_port(start: int = 8000, tries: int = 50) -> int:
    for port in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    raise RuntimeError("没有可用的端口")


def find_browser(platform: str | None = None) -> str | None:
    platform = platform or sys.platform
    if platform.startswith("linux"):
        for command in ("chromium", "chromium-browser"):
            path = shutil.which(command)
            if path:
                return path
        return None

    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def wait_until_ready(url: str, timeout: float = 10.0) -> bool:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=0.5)
            return True
        except OSError:
            time.sleep(0.2)
    return False


def build_browser_args(browser: str, url: str, user_data_dir: str) -> list[str]:
    return [
        browser,
        "--kiosk",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-session-crashed-bubble",
        f"--user-data-dir={user_data_dir}",
        url,
    ]


def open_fullscreen(
    browser: str, url: str, user_data_dir: str
) -> subprocess.Popen | None:
    """用独立的 user-data-dir 启动浏览器，确保 kiosk 全屏真正生效
    （避免被已运行的浏览器实例吞掉 --kiosk 参数）。"""
    try:
        return subprocess.Popen(build_browser_args(browser, url, user_data_dir))
    except OSError:
        return None


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RoboFace 全屏动画播放器")
    parser.add_argument(
        "--rotation",
        type=int,
        choices=server.VALID_ROTATIONS,
        default=0,
        help="动画顺时针旋转角度（默认: 0）",
    )
    return parser.parse_args(args)


def main(rotation: int = 0) -> int:
    server.set_rotation(rotation)
    port = find_free_port()
    url = f"http://localhost:{port}/"
    httpd = ThreadingHTTPServer(("0.0.0.0", port), server.RoboFaceHandler)
    user_data_dir = None
    proc = None

    # 服务在后台线程运行
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    log(f"服务已启动: {url}  (REST API: GET/PUT {url}api/state)")

    try:
        if not wait_until_ready(url):
            log("HTTP 服务未能及时就绪")
            return 1

        browser = find_browser()
        if browser is None:
            log("未找到 Chromium，无法启动全屏界面")
            return 1

        user_data_dir = tempfile.mkdtemp(prefix="roboface-browser-")
        proc = open_fullscreen(browser, url, user_data_dir)
        if proc is not None:
            log(f"全屏浏览器已启动: {browser}")
            if proc.wait() != 0:
                log("Chromium 异常退出")
                return 1
        else:
            log("Chromium 启动失败")
            return 1
    except KeyboardInterrupt:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
    finally:
        httpd.shutdown()
        httpd.server_close()
        if user_data_dir is not None:
            shutil.rmtree(user_data_dir, ignore_errors=True)
        log("服务已停止")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(parse_args().rotation))
    except Exception as e:  # 窗口化模式下兜底记录错误
        log(f"启动失败: {e}")
        raise
