#!/usr/bin/env python3
"""树莓派 GPIO 控制：将 GPIO 17 设为输出、默认低电平，并提供读写电平接口。

实现基于 Linux sysfs 接口（/sys/class/gpio），只用 Python 标准库，无需
RPi.GPIO / gpiod 等第三方库，也不影响 PyInstaller 打包（无原生依赖）。

- GPIO 17 对应 sysfs 节点 /sys/class/gpio/gpio17。
- 通过 export/unexport 申请与释放引脚，direction 写 out，value 写 0/1。

在非树莓派环境（sysfs 不存在，或当前用户无 gpio 组权限）下会自动降级为
内存模拟：API 仍能读写电平，只是不驱动真实引脚，便于在开发机 / CI 上运行。

注意：sysfs GPIO 是内核已标记 deprecated 的接口，但在 Raspberry Pi OS
Bookworm（内核 6.6）上仍可用。运行用户需属于 gpio 组（或 root）：

    sudo usermod -aG gpio <user>
"""

import os
import threading

GPIO_PIN = 17
LOW = 0
HIGH = 1

_SYSFS_BASE = "/sys/class/gpio"
_PIN_DIR = os.path.join(_SYSFS_BASE, f"gpio{GPIO_PIN}")
_EXPORT_PATH = os.path.join(_SYSFS_BASE, "export")
_UNEXPORT_PATH = os.path.join(_SYSFS_BASE, "unexport")

# 当前电平（内存跟踪），初始为低电平
_level = LOW
# 后端是否可用：None=尚未初始化，True=sysfs 可用，False=降级为内存模拟
_available = None
_lock = threading.RLock()


def _sysfs_ready() -> bool:
    """sysfs GPIO 目录与 export 文件是否存在且可写。"""
    return os.path.isdir(_SYSFS_BASE) and os.access(_EXPORT_PATH, os.W_OK)


def _write(path: str, value) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(str(value))


def _ensure_exported() -> None:
    """导出 GPIO 引脚；若目录已存在（已导出）则跳过。"""
    if not os.path.isdir(_PIN_DIR):
        _write(_EXPORT_PATH, GPIO_PIN)


def setup() -> bool:
    """初始化 GPIO 17 为输出、低电平。

    返回 True 表示真实驱动引脚；False 表示降级为内存模拟。幂等，可重复调用。
    """
    global _available, _level
    with _lock:
        if _available is False:
            return False
        try:
            if not _sysfs_ready():
                _available = False
                return False
            _ensure_exported()
            _write(os.path.join(_PIN_DIR, "direction"), "out")
            _write(os.path.join(_PIN_DIR, "value"), LOW)
            _level = LOW
            _available = True
            return True
        except OSError:
            _available = False
            return False


def set_level(value: int) -> int:
    """设置电平：1 高 / 0 低。返回设置后的电平。"""
    if type(value) is not int or value not in (LOW, HIGH):
        raise ValueError(f"无效电平 {value!r}，只能是 0（低）或 1（高）")

    global _available, _level
    with _lock:
        if _available is None:
            setup()
        if _available:
            try:
                _write(os.path.join(_PIN_DIR, "value"), value)
            except OSError:
                _available = False
        _level = value
    return _level


def get_level() -> int:
    """返回当前电平（0 低 / 1 高）。"""
    with _lock:
        return _level


def cleanup() -> None:
    """释放 GPIO 引脚（unexport），让出控制权。"""
    global _available
    with _lock:
        if _available:
            try:
                _write(_UNEXPORT_PATH, GPIO_PIN)
            except OSError:
                pass
        _available = None
