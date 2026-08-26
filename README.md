# RoboFace

RoboFace 在 Chromium kiosk 模式中全屏播放 dotLottie 机器人表情，并通过 REST API 在 `smile`、`proud`、`unhappy` 和 `daze` 状态之间切换。

## 树莓派运行

运行环境为 Raspberry Pi OS 64-bit（arm64，Bookworm 或兼容的新版本），系统需要图形桌面和 Chromium。可执行文件已经包含 Python 服务、动画以及固定版本的 JavaScript/WASM 播放器，运行时可完全离线。

```bash
sudo apt update
sudo apt install -y chromium
chmod +x roboface-linux-arm64
./roboface-linux-arm64
```

屏幕安装方向需要调整时，通过 `--rotation` 设置启动角度（顺时针，仅支持 `0`、`90`、`180`、`270`）：

```bash
./roboface-linux-arm64 --rotation 90
```

程序从端口 `8000` 开始查找空闲端口，监听所有网络接口，然后自动启动 Chromium 全屏界面。关闭 Chromium 或在启动终端按 `Ctrl+C` 会同时停止服务。实际 URL 和错误信息记录在 `/tmp/roboface.log`；如果 `8000` 已占用，请从该日志读取实际端口。

## 配置开机自启动

自启动依赖 Raspberry Pi OS 图形桌面和当前用户的桌面自动登录。先运行：

```bash
sudo raspi-config
```

在菜单中选择 **System Options > Boot / Auto Login > Desktop Autologin**，保存后先不要重启。不同 Raspberry Pi OS 版本的菜单文字可能略有差异，目标是让当前用户开机后自动进入桌面。

将 `roboface-linux-arm64` 和 `install-autostart.sh` 放在同一目录，先手动确认 Chromium、动画和旋转方向正常：

```bash
chmod +x roboface-linux-arm64 install-autostart.sh
./roboface-linux-arm64 --rotation 90
```

关闭全屏浏览器后，为当前用户安装自启动。不要对安装脚本使用 `sudo`，否则会安装到 root 用户目录：

```bash
./install-autostart.sh --binary ./roboface-linux-arm64 --rotation 90
cat ~/.config/autostart/roboface.desktop
sudo reboot
```

重启并自动进入桌面后，RoboFace 应自动全屏运行。脚本将可执行文件复制到 `~/.local/bin/roboface-linux-arm64`，因此安装完成后不依赖原下载目录。

更换程序版本或启动旋转角度时，用新的可执行文件重新运行安装命令即可覆盖更新：

```bash
./install-autostart.sh --binary ./roboface-linux-arm64 --rotation 270
```

停用自启动并删除已安装副本：

```bash
./install-autostart.sh --uninstall
```

如果重启后没有出现动画，先确认桌面自动登录和 Chromium 已安装，然后检查日志与自启动文件：

```bash
tail -n 100 /tmp/roboface.log
command -v chromium || command -v chromium-browser
cat ~/.config/autostart/roboface.desktop
```

排查期间只需重命名桌面项即可暂时禁用自动启动，不会删除已安装程序：

```bash
mv ~/.config/autostart/roboface.desktop ~/.config/autostart/roboface.desktop.disabled
# 恢复自启动
mv ~/.config/autostart/roboface.desktop.disabled ~/.config/autostart/roboface.desktop
```

确认不再使用 RoboFace 时，再运行 `./install-autostart.sh --uninstall` 删除自启动项和已安装副本。

## REST API

- `GET /api/state`：读取当前状态。
- `PUT /api/state`：修改当前状态。
- `GET /api/states`：列出所有合法状态。
- `GET /api/rotation`：读取当前旋转角度。
- `PUT /api/rotation`：动态修改旋转角度。

将 `<raspberry-pi-ip>` 替换为树莓派的局域网地址：

```bash
curl http://<raspberry-pi-ip>:8000/api/states
curl -X PUT http://<raspberry-pi-ip>:8000/api/state \
  -H 'Content-Type: application/json' \
  -d '{"state":"daze"}'
curl http://<raspberry-pi-ip>:8000/api/state
curl -X PUT http://<raspberry-pi-ip>:8000/api/rotation \
  -H 'Content-Type: application/json' \
  -d '{"rotation":270}'
curl http://<raspberry-pi-ip>:8000/api/rotation
```

## 构建 arm64 可执行文件

PyInstaller 不支持从 Windows 直接交叉编译 Linux arm64 程序。请在 64 位 Raspberry Pi OS 上安装构建依赖并执行脚本：

```bash
sudo apt update
sudo apt install -y python3 python3-venv
chmod +x build-raspberry-pi.sh
./build-raspberry-pi.sh
```

产物位于 `dist/roboface-linux-arm64`。也可以在 GitHub Actions 中手动运行 **Build Raspberry Pi executable** 工作流并下载同名 artifact；该流程在 arm64 Debian Bookworm 容器中构建。

## 本地源码运行

```bash
python3 server.py
```

浏览器访问 `http://localhost:8000/`。源码运行与打包运行都使用仓库内的播放器资源，不访问 CDN。

## 固定资源版本

- `@lottiefiles/dotlottie-wc` 0.9.27
- `@lottiefiles/dotlottie-web` 0.79.2

SHA-256：

```text
676B51D5CF689F2CB92CC836DFF80E2C33946D294BD5C93D90245D77D81A631F  vendor/dotlottie-wc.js
4E061FC44985E12C1CBF2AA20E8A9ACDBEF9B80F74079F815E1A5709BC2E3782  vendor/dotlottie-player.wasm
779CEC663B3C6590082566F2A000170D7A4D1A4BFC6F954E61EFA4ADDDC652A8  vendor/LICENSE.dotlottie-wc.txt
```

## Raspberry Pi 用户名及密码

用户名：sia

密码： a

Bonjour地址： sia.local