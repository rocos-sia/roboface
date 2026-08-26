#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
installer="$root_dir/install-autostart.sh"
temp_dir="$(mktemp -d)"
trap 'rm -rf "$temp_dir"' EXIT

export HOME="$temp_dir/home with space"
mkdir -p "$HOME"

fake_binary="$temp_dir/roboface-linux-arm64"
printf 'version-one\n' > "$fake_binary"
chmod 755 "$fake_binary"

installed_binary="$HOME/.local/bin/roboface-linux-arm64"
desktop_entry="$HOME/.config/autostart/roboface.desktop"

"$installer" --binary "$fake_binary"

test -x "$installed_binary"
cmp "$fake_binary" "$installed_binary"
test -f "$desktop_entry"
grep -F "Exec=\"$installed_binary\" --rotation 0" "$desktop_entry"
grep -F "Terminal=false" "$desktop_entry"
grep -F "X-GNOME-Autostart-enabled=true" "$desktop_entry"

printf 'version-two\n' > "$fake_binary"
chmod 755 "$fake_binary"
"$installer" --binary "$fake_binary" --rotation 90

cmp "$fake_binary" "$installed_binary"
grep -F "Exec=\"$installed_binary\" --rotation 90" "$desktop_entry"

binary_hash="$(sha256sum "$installed_binary")"
desktop_hash="$(sha256sum "$desktop_entry")"

option_named_binary="$temp_dir/--uninstall"
printf 'must-not-install\n' > "$option_named_binary"
chmod 755 "$option_named_binary"
if (cd "$temp_dir" && "$installer" --binary --uninstall); then
    echo "option token was consumed as the binary path" >&2
    exit 1
fi
test "$(sha256sum "$installed_binary")" = "$binary_hash"
test "$(sha256sum "$desktop_entry")" = "$desktop_hash"

short_option_binary="$temp_dir/-h"
printf 'must-not-install-short-option\n' > "$short_option_binary"
chmod 755 "$short_option_binary"
if (cd "$temp_dir" && "$installer" --binary -h); then
    echo "short option token was consumed as the binary path" >&2
    exit 1
fi
test "$(sha256sum "$installed_binary")" = "$binary_hash"
test "$(sha256sum "$desktop_entry")" = "$desktop_hash"

if "$installer" --binary "$fake_binary" --rotation 45; then
    echo "invalid rotation was accepted" >&2
    exit 1
fi
test "$(sha256sum "$installed_binary")" = "$binary_hash"
test "$(sha256sum "$desktop_entry")" = "$desktop_hash"

chmod 644 "$fake_binary"
if "$installer" --binary "$fake_binary"; then
    echo "non-executable binary was accepted" >&2
    exit 1
fi
test "$(sha256sum "$installed_binary")" = "$binary_hash"
test "$(sha256sum "$desktop_entry")" = "$desktop_hash"

for invalid_args in \
    "" \
    "--unknown" \
    "--binary" \
    "--rotation" \
    "--uninstall --binary $fake_binary" \
    "--uninstall --rotation 90"
do
    read -r -a args <<< "$invalid_args"
    if "$installer" "${args[@]}"; then
        echo "invalid arguments were accepted: $invalid_args" >&2
        exit 1
    fi
    test "$(sha256sum "$installed_binary")" = "$binary_hash"
    test "$(sha256sum "$desktop_entry")" = "$desktop_hash"
done

fake_tools="$temp_dir/fake-tools"
mkdir -p "$fake_tools"
real_mv="$(command -v mv)"
cat > "$fake_tools/mv" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
destination="${!#}"
if [[ "$destination" == "$FAIL_MV_DEST" && ! -e "$FAIL_MV_MARKER" ]]; then
    touch "$FAIL_MV_MARKER"
    exit 1
fi
exec "$REAL_MV" "$@"
EOF
chmod 755 "$fake_tools/mv"

chmod 755 "$fake_binary"
printf 'version-three\n' > "$fake_binary"
if PATH="$fake_tools:$PATH" \
    REAL_MV="$real_mv" \
    FAIL_MV_DEST="$desktop_entry" \
    FAIL_MV_MARKER="$temp_dir/mv-failed" \
    "$installer" --binary "$fake_binary" --rotation 180
then
    echo "injected desktop replacement failure was ignored" >&2
    exit 1
fi
test "$(sha256sum "$installed_binary")" = "$binary_hash"
test "$(sha256sum "$desktop_entry")" = "$desktop_hash"

"$installer" --uninstall
test ! -e "$installed_binary"
test ! -e "$desktop_entry"
"$installer" --uninstall

echo "AUTOSTART_TEST_OK"