#!/usr/bin/env python3
"""使用 gpiod 控制树莓派 GPIO 17 输出，并提供内存降级。"""

import os
import threading

try:
    import gpiod
except ImportError:
    gpiod = None

GPIO_PIN = 17
LOW = 0
HIGH = 1

# 当前电平（内存跟踪），初始为低电平
_level = LOW
# 后端是否可用：None=尚未初始化，True=gpiod 可用，False=降级为内存模拟
_available = None
_lock = threading.RLock()
_request = None
_line_offset = None


def _find_line():
    if gpiod is None:
        return None
    for entry in os.scandir("/dev"):
        if not gpiod.is_gpiochip_device(entry.path):
            continue
        with gpiod.Chip(entry.path) as chip:
            try:
                return entry.path, chip.line_offset_from_id(f"GPIO{GPIO_PIN}")
            except OSError:
                continue
    return None


def _release_request(drive_low: bool) -> None:
    global _request, _line_offset
    if _request is None:
        _line_offset = None
        return
    try:
        if drive_low and _line_offset is not None:
            _request.set_value(_line_offset, gpiod.line.Value.INACTIVE)
    except OSError:
        pass
    try:
        _request.release()
    except OSError:
        pass
    _request = None
    _line_offset = None


def setup() -> bool:
    """初始化 GPIO 17 为输出、低电平。

    返回 True 表示真实驱动引脚；False 表示降级为内存模拟。幂等，可重复调用。
    """
    global _available, _level, _request, _line_offset
    with _lock:
        if _available is True:
            return True
        if _available is False:
            return False
        try:
            line = _find_line()
            if line is None:
                _available = False
                return False
            chip_path, _line_offset = line
            settings = gpiod.LineSettings(
                direction=gpiod.line.Direction.OUTPUT,
                output_value=gpiod.line.Value.INACTIVE,
            )
            _request = gpiod.request_lines(
                chip_path,
                consumer="roboface",
                config={_line_offset: settings},
            )
            _level = LOW
            _available = True
            return True
        except OSError:
            _release_request(drive_low=False)
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
                line_value = (
                    gpiod.line.Value.ACTIVE
                    if value == HIGH
                    else gpiod.line.Value.INACTIVE
                )
                _request.set_value(_line_offset, line_value)
            except OSError:
                _release_request(drive_low=False)
                _available = False
        _level = value
    return _level


def get_level() -> int:
    """返回当前电平（0 低 / 1 高）。"""
    with _lock:
        return _level


def cleanup() -> None:
    """将 GPIO 17 拉低并释放 gpiod line request。"""
    global _available, _level
    with _lock:
        _release_request(drive_low=_available is True)
        _level = LOW
        _available = None
