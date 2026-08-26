#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "错误: 只能在 Linux arm64 环境构建。" >&2
    exit 1
fi

if [[ "$(uname -m)" != "aarch64" ]]; then
    echo "错误: 当前架构是 $(uname -m)，需要 aarch64。" >&2
    exit 1
fi

python3 -m venv .venv-build
source .venv-build/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
pyinstaller --clean --noconfirm roboface.spec

test -x dist/roboface-linux-arm64
sha256sum dist/roboface-linux-arm64
echo "构建完成: $(pwd)/dist/roboface-linux-arm64"