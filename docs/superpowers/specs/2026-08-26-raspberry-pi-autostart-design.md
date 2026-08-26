# Raspberry Pi Autostart Design

## Goal

Provide a repeatable script that installs the RoboFace arm64 executable for the current Raspberry Pi desktop user and starts it automatically after desktop login.

## Environment

The supported environment is Raspberry Pi OS 64-bit with a graphical desktop, Chromium, and desktop auto-login enabled. RoboFace starts through XDG autostart after the graphical session exists; it does not run as a pre-login system service.

## Installer Interface

The repository provides `install-autostart.sh`:

```bash
./install-autostart.sh --binary ./roboface-linux-arm64 --rotation 90
./install-autostart.sh --uninstall
```

`--binary` is required when installing and must point to an executable regular file. `--rotation` defaults to `0` and accepts only `0`, `90`, `180`, or `270`. Unknown arguments, missing values, invalid angles, and missing or non-executable binaries exit nonzero without replacing an existing valid installation.

## Installed Files

Installation creates:

- `~/.local/bin/roboface-linux-arm64`, copied from the selected binary and made executable.
- `~/.config/autostart/roboface.desktop`, containing an absolute `Exec` command with the selected rotation, `Terminal=false`, and `X-GNOME-Autostart-enabled=true`.

The script creates parent directories as needed and writes the desktop entry through a temporary file before replacing the destination. Running the installer again updates the installed binary and rotation.

Uninstall removes both generated files. It leaves unrelated files and parent directories intact and succeeds when the files are already absent.

## Documentation

`README.md` documents:

- Enabling Raspberry Pi OS desktop auto-login with `raspi-config`.
- Installing Chromium and the RoboFace executable.
- Running RoboFace once manually before enabling autostart.
- Installing, updating, verifying after reboot, and uninstalling autostart.
- Changing startup rotation by rerunning the installer.
- Reading `/tmp/roboface.log` and disabling the desktop entry when troubleshooting.

## Validation

Automated tests execute the installer against a temporary `HOME` and a fake executable. They verify installed paths, copied content, desktop entry fields, default and explicit rotation, idempotent updates, invalid-input rejection, and uninstall behavior. Bash syntax, the complete Python test suite, and repository diff formatting are checked before committing.

## Git Commit

After validation, stage the implementation, tests, documentation, packaging, offline runtime, and rotation files created during this work. Do not stage the pre-existing deletions of `index2.html` or `roboface.py`. Commit with:

```text
feat: add Raspberry Pi kiosk deployment
```