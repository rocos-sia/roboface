#!/usr/bin/env python3
"""
RoboFace 桌面启动器（用于打包成 exe）

双击后:
    1. 在后台线程启动 HTTP 服务（复用 server.py）
    2. 用系统浏览器（Edge/Chrome）全屏(kiosk)打开页面
    3. 服务持续运行，随时可通过 RESTful API 切换动画状态

退出方式: 关闭浏览器后，可通过任务管理器结束 RoboFace.exe 进程。
"""

import os
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
    path = os.path.join(os.environ.get("TEMP", os.getcwd()), "roboface.log")
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


def find_browser() -> str | None:
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


def open_fullscreen(browser: str, url: str) -> subprocess.Popen | None:
    """用独立的 user-data-dir 启动浏览器，确保 kiosk 全屏真正生效
    （避免被已运行的浏览器实例吞掉 --kiosk 参数）。"""
    user_data = os.path.join(tempfile.gettempdir(), "roboface-browser-profile")
    args = [
        browser,
        "--kiosk",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={user_data}",
        url,
    ]
    try:
        return subprocess.Popen(args)
    except OSError:
        return None


def main() -> int:
    port = find_free_port()
    url = f"http://localhost:{port}/"
    httpd = ThreadingHTTPServer(("0.0.0.0", port), server.RoboFaceHandler)

    # 服务在后台线程运行
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    log(f"服务已启动: {url}  (REST API: GET/PUT {url}api/state)")

    browser = find_browser()
    if browser and wait_until_ready(url):
        proc = open_fullscreen(browser, url)
        if proc is not None:
            log(f"全屏浏览器已启动: {browser}")
        else:
            log("全屏浏览器启动失败，请手动打开 " + url)
    else:
        import webbrowser

        webbrowser.open(url)
        log("使用系统默认浏览器打开（未找到 Edge/Chrome 或服务未就绪）")

    # 服务持续运行以响应 API，不随浏览器进程退出
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.shutdown()
        httpd.server_close()
        log("服务已停止")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # 窗口化模式下兜底记录错误
        log(f"启动失败: {e}")
        raise
