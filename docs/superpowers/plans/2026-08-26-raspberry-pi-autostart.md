# Raspberry Pi Autostart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install RoboFace for the current Raspberry Pi desktop user and launch it automatically after desktop auto-login.

**Architecture:** A standalone Bash installer copies the selected arm64 executable into `~/.local/bin` and atomically writes an XDG autostart desktop entry. The same script removes only those two generated files. Shell integration tests run the installer against a temporary HOME.

**Tech Stack:** Bash, XDG autostart desktop entry, Python `unittest`, Raspberry Pi OS 64-bit desktop.

## Global Constraints

- Require a graphical Raspberry Pi OS desktop with desktop auto-login.
- Require `--binary` for installation and allow rotations `0`, `90`, `180`, and `270` only.
- Default rotation to `0`.
- Do not use `sudo` or modify system-wide files.
- Do not stage the pre-existing deletions of `index2.html` or `roboface.py`.
- Commit with `feat: add Raspberry Pi kiosk deployment` only after all validation passes.

---

### Task 1: XDG Autostart Installer

**Files:**
- Create: `install-autostart.sh`
- Create: `tests/test_install_autostart.sh`
- Modify: `tests/test_packaging.py`

**Interfaces:**
- Produces: `install-autostart.sh --binary PATH [--rotation ANGLE]`.
- Produces: `install-autostart.sh --uninstall`.
- Installs: `$HOME/.local/bin/roboface-linux-arm64`.
- Installs: `$HOME/.config/autostart/roboface.desktop`.

- [ ] **Step 1: Write the failing shell integration test**

Use `mktemp -d`, set a temporary `HOME`, create an executable fake binary, and assert default install, explicit rotation update, copied content, desktop fields, invalid rotation rejection without replacement, and idempotent uninstall.

- [ ] **Step 2: Verify the shell test fails**

Run: `bash tests/test_install_autostart.sh`

Expected: FAIL because `install-autostart.sh` does not exist.

- [ ] **Step 3: Implement the installer**

Parse `--binary`, `--rotation`, and `--uninstall`; reject conflicting or unknown arguments. Validate with `[[ -f "$binary" && -x "$binary" ]]` and a rotation `case`. Copy through temporary files in each destination directory, `chmod 755` the binary and `chmod 644` the desktop entry, then atomically `mv` both files.

- [ ] **Step 4: Verify shell integration and syntax**

Run: `bash tests/test_install_autostart.sh`

Run: `bash -n install-autostart.sh tests/test_install_autostart.sh`

Expected: both commands exit `0`.

- [ ] **Step 5: Extend packaging contracts**

Assert the installer and shell test exist and contain the required paths, options, XDG fields, executable invocation, and temporary-file replacement behavior.

- [ ] **Step 6: Run packaging and full Python tests**

Run: `C:/ProgramData/anaconda3/python.exe -m unittest discover -s tests -v`

Expected: all tests pass.

---

### Task 2: Raspberry Pi Setup and Operations Guide

**Files:**
- Modify: `README.md`
- Modify: `tests/test_packaging.py`

**Interfaces:**
- Documents: desktop auto-login, manual launch, install/update, reboot verification, rotation changes, uninstall, and log troubleshooting.

- [ ] **Step 1: Write failing documentation contract assertions**

Require `raspi-config`, `install-autostart.sh --binary`, `--uninstall`, `sudo reboot`, `/tmp/roboface.log`, and `~/.config/autostart/roboface.desktop` in `README.md`.

- [ ] **Step 2: Verify documentation tests fail**

Run: `C:/ProgramData/anaconda3/python.exe -m unittest tests.test_packaging -v`

Expected: FAIL because autostart instructions are absent.

- [ ] **Step 3: Add the setup and operations guide**

Document desktop auto-login through `sudo raspi-config`, copying the executable and installer, manual validation, installation with rotation, reboot verification, update behavior, uninstall, and troubleshooting commands.

- [ ] **Step 4: Run complete validation**

Run the shell integration test, all Python tests, Python/spec compilation, Bash syntax checks, vendor hashes, offline URL scan, and `git diff --check`.

- [ ] **Step 5: Review and commit the scoped changes**

Stage explicit implementation, test, documentation, packaging, workflow, vendor, and design/plan paths. Verify `index2.html` and `roboface.py` are not staged. Commit with `feat: add Raspberry Pi kiosk deployment`, then report the commit SHA and remaining unstaged deletions.