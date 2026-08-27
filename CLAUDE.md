# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

RoboFace 是一个机器人脸动画播放器。核心资产是 `RoboFace.lottie`（dotLottie 格式的 ZIP 包），包含一个状态机驱动的四个表情状态：`smile` / `proud` / `unhappy` / `daze`。

仓库里有三种并列的播放实现（互不依赖，可独立运行）：

- **`server.py` + `index.html`** — Web 版（主实现）：Python 标准库 HTTP 服务器 + 全屏 Web 组件播放，通过 RESTful API 切换状态。
- **`index2.html`** — Web 版（JS API 直连）：用 `@lottiefiles/dotlottie-web` 的 JS API + 按钮切换状态。
- **`roboface.py`** — 桌面版：PySide6 GUI，直接读取 `.lottie` 内的 PNG 帧并做淡入淡出切换。

## 常用命令

```bash
# 启动 Web 服务（默认 0.0.0.0:8000；真实 GPIO 需要 gpiod）
pip install gpiod==2.5.0  # 仅 Linux/树莓派；其他环境自动使用内存模拟
python server.py
python server.py --port 9000
./run.bat   # Windows
./run.sh    # macOS/Linux

# 桌面版（需先安装依赖）
pip install lottie pillow PySide6
python roboface.py
```

本地服务启动后浏览器打开 `http://localhost:8000/`。

切换状态的 REST API 调用（注意 Windows 下引号规则，见下）：

```bash
# Linux/macOS/Git Bash
curl -X PUT http://localhost:8000/api/state -H "Content-Type: application/json" -d '{"state":"daze"}'

# Windows cmd.exe（单引号不生效，需 \" 转义）
curl -X PUT http://localhost:8000/api/state -H "Content-Type: application/json" -d "{\"state\":\"daze\"}"

# 最稳妥、跨 shell 通用（文件传 JSON 体）
echo {"state":"daze"} > body.json
curl -X PUT http://localhost:8000/api/state -H "Content-Type: application/json" --data-binary @body.json
```

## 架构

### RoboFace.lottie 内部结构

ZIP 包，含四个文件：

- `manifest.json` — dotLottie 版本 2 清单，声明动画 `main scene` 和状态机 `StateMachine1`。
- `a/main scene.json` — Lottie 动画 JSON。4 个图层（`daze`/`unhappy`/`proud`/`smile`），每个图层引用 `i/` 下的 PNG；通过 `markers`（帧 5/75/145/215，各 60 帧）把时间轴切成四段。
- `i/{smile,proud,unhappy,daze}.png` — 预渲染的表情帧。
- `s/StateMachine1.json` — 状态机定义。

### 状态机工作原理

状态机采用「一个 GLOBAL STATE + 四个 PlaybackState」结构：

- GLOBAL STATE 上挂 4 条 transition，guard 是字符串输入 `states` 等于 `smile`/`proud`/`unhappy`/`daze` 时触发。
- 每个 PlaybackState 通过 `segment` 字段引用 `main scene.json` 中同名 marker 的帧区间，`autoplay`/`loop` 为 true。
- 因此切换表情 = 设置输入 `states` 的值，状态机自动跳转到对应播放段。这是前端唯一需要调用的方法（`stateMachineSetStringInput("states", <state>)`）。

### Web 版数据流

```
浏览器(index.html, 全屏 dotlottie-wc) --每500ms轮询 GET /api/state--> server.py
                                                                        ^
外部调用方 --PUT /api/state {state}--> server.py (内存 _current_state, 线程锁保护)
```

- `server.py` 用 `ThreadingHTTPServer` + 内存变量 `_current_state` 存当前状态，`threading.Lock` 保护。静态文件路径做了 `normpath` 目录穿越防护，`PUT` 校验状态合法性（非法返回 400）。
- `index.html` 前端轮询 `GET /api/state`，状态变化时调用 `stateMachineSetStringInput`。有就绪保护：等 `dotLottie.isLoaded`（或 `load` 事件）后才首次应用状态。

### GPIO 控制

- `gpio.py` 使用官方 `gpiod==2.5.0` Python bindings 和 Linux GPIO character device，把 GPIO 17（BCM）设为输出、默认低电平。
- 初始化时遍历 `/dev/gpiochip*`，按名称 `GPIO17` 定位 line，不硬编码 gpiochip 编号；`LineRequest` 在程序生命周期内保持打开，所有操作用 `RLock` 串行化。
- `server.py` 与 `launcher.py` 启动时调用 `gpio.setup()`，退出时 `gpio.cleanup()`。在非树莓派、缺少依赖、设备权限不足、line 被占用或写入失败时自动降级为内存模拟（`_available=False`），API 照常读写电平但不驱动引脚。
- REST API：`GET /api/gpio` 读电平，`PUT /api/gpio` 写电平（`{"value": 1}` 高 / `{"value": 0}` 低），响应含 `pin`/`value`/`level`。
- 运行用户需能读写对应的 `/dev/gpiochip*`；安装脚本会检查设备权限并提示。arm64 PyInstaller 产物内置 gpiod，无需运行时安装。

## 关键依赖与版本（易踩坑）

- **`gpiod` Python bindings**：固定 `2.5.0`，使用 v2 API；旧的非官方 `gpiod<=1.5.4` API 不兼容。该包只支持 Linux，Windows/CI 无设备环境通过内存模拟和 fake binding 测试。
- **`dotlottie-web` 的 CDN 路径已变更**：`dist/dotlottie-web.js` 现已 404。正确做法是用 ESM import `@lottiefiles/dotlottie-web@0.79.2/+esm` 或 `dist/index.js`。当前已锁定 `0.79.2`，不要用 `@latest`（破坏性更新风险）。
- **`dotlottie-web` 状态机 API 方法名**：新版是 `stateMachineLoad` / `stateMachineStart` / `stateMachineSetStringInput`（旧名 `loadStateMachine` / `startStateMachine` / `setStateMachineStringInput` 已废弃）。
- **`dotlottie-wc`（Web 组件）**：自定义元素 `<dotlottie-wc>`；`stateMachineId` 属性名在 HTML 里是全小写 `statemachineid`；组件实例通过 `.dotLottie` 属性暴露。
- **`.lottie` 文件必须经 HTTP 加载**：`dotlottie-web` 用 `fetch` 读 `.lottie`，不能直接 `file://` 打开 HTML（会被 CORS 拦截）。所以务必走 `server.py` 或 `python -m http.server`。
- **Windows curl 引号规则**：cmd 不认单引号，JSON 体需 `\"` 转义或用 `--data-binary @file`；PowerShell 里 `curl` 是 `Invoke-WebRequest` 别名，需用 `curl.exe`。
