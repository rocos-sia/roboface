#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
用法:
  ./install-autostart.sh --binary PATH [--rotation 0|90|180|270]
  ./install-autostart.sh --uninstall
EOF
}

is_option_token() {
    case "$1" in
        --binary|--rotation|--uninstall|-h|--help) return 0 ;;
        *) return 1 ;;
    esac
}

check_gpio_access() {
    local chip
    for chip in /dev/gpiochip*; do
        [[ -e "$chip" ]] || continue
        if [[ -r "$chip" && -w "$chip" ]]; then
            return 0
        fi
    done
    cat >&2 <<'EOF'
提示: 当前用户无法读写 /dev/gpiochip*，RoboFace 将无法驱动 GPIO 17（REST API 会降级为内存模拟）。
请检查 GPIO character device 是否存在，以及当前用户的 udev 设备权限。
EOF
}

binary=""
rotation="0"
rotation_set=false
uninstall=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --binary)
            if [[ $# -lt 2 ]] || is_option_token "$2"; then
                echo "错误: --binary 缺少路径" >&2
                exit 2
            fi
            binary="$2"
            shift 2
            ;;
        --rotation)
            if [[ $# -lt 2 ]] || is_option_token "$2"; then
                echo "错误: --rotation 缺少角度" >&2
                exit 2
            fi
            rotation="$2"
            rotation_set=true
            shift 2
            ;;
        --uninstall)
            uninstall=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "错误: 未知参数 $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

bin_dir="$HOME/.local/bin"
autostart_dir="$HOME/.config/autostart"
installed_binary="$bin_dir/roboface-linux-arm64"
desktop_entry="$autostart_dir/roboface.desktop"

if [[ "$uninstall" == true ]]; then
    if [[ -n "$binary" || "$rotation_set" == true ]]; then
        echo "错误: --uninstall 不能与安装参数同时使用" >&2
        exit 2
    fi
    rm -f -- "$desktop_entry" "$installed_binary"
    echo "RoboFace 自启动已卸载"
    exit 0
fi

if [[ -z "$binary" ]]; then
    echo "错误: 安装时必须提供 --binary PATH" >&2
    exit 2
fi

if [[ ! -f "$binary" || ! -x "$binary" ]]; then
    echo "错误: $binary 不是可执行的普通文件" >&2
    exit 2
fi

case "$rotation" in
    0|90|180|270) ;;
    *)
        echo "错误: 旋转角度必须是 0、90、180 或 270" >&2
        exit 2
        ;;
esac

mkdir -p "$bin_dir" "$autostart_dir"
temp_binary="$(mktemp "$bin_dir/.roboface-linux-arm64.XXXXXX")"
temp_desktop="$(mktemp "$autostart_dir/.roboface.desktop.XXXXXX")"
backup_binary=""
restore_binary=""
cleanup() {
    rm -f -- "$temp_binary" "$temp_desktop" "$backup_binary" "$restore_binary"
}
trap cleanup EXIT

cp -- "$binary" "$temp_binary"
chmod 755 "$temp_binary"
escaped_binary="${installed_binary//\\/\\\\}"
escaped_binary="${escaped_binary//\"/\\\"}"
escaped_binary="${escaped_binary//\$/\\$}"
escaped_binary="${escaped_binary//\`/\\\`}"
cat > "$temp_desktop" <<EOF
[Desktop Entry]
Type=Application
Name=RoboFace
Comment=RoboFace kiosk animation player
Exec="$escaped_binary" --rotation $rotation
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true
EOF
chmod 644 "$temp_desktop"

had_installed_binary=false
if [[ -f "$installed_binary" ]]; then
    backup_binary="$(mktemp "$bin_dir/.roboface-linux-arm64.backup.XXXXXX")"
    cp -p -- "$installed_binary" "$backup_binary"
    had_installed_binary=true
fi

if ! mv -f -- "$temp_binary" "$installed_binary"; then
    echo "错误: 无法更新 RoboFace 可执行文件" >&2
    exit 1
fi
temp_binary=""
if ! mv -f -- "$temp_desktop" "$desktop_entry"; then
    if [[ "$had_installed_binary" == true ]]; then
        restore_binary="$(mktemp "$bin_dir/.roboface-linux-arm64.restore.XXXXXX")"
        cp -p -- "$backup_binary" "$restore_binary"
        mv -f -- "$restore_binary" "$installed_binary"
        restore_binary=""
    else
        rm -f -- "$installed_binary"
    fi
    echo "错误: 无法更新桌面自启动项，已恢复原安装" >&2
    exit 1
fi
temp_desktop=""
rm -f -- "$backup_binary"
backup_binary=""

echo "RoboFace 已安装: $installed_binary"
echo "桌面自启动已启用: $desktop_entry"
echo "启动旋转角度: $rotation"
check_gpio_access