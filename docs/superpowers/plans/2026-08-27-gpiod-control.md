# gpiod GPIO Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace RoboFace's deprecated raw sysfs GPIO implementation with the official `gpiod` Python bindings while preserving the GPIO REST API and memory fallback.

**Architecture:** Keep `gpio.py` as the sole GPIO owner. Discover the named `GPIO17` line across Linux GPIO character devices, hold one output `LineRequest` for the application lifetime, and serialize access with the existing re-entrant lock. Preserve `server.py` and `launcher.py` call sites and update only dependency, packaging, and operator documentation around the new backend.

**Tech Stack:** Python 3.11, `gpiod==2.5.0`, `unittest`, PyInstaller 6.15.0, Raspberry Pi OS 64-bit.

## Global Constraints

- Use the official `gpiod==2.5.0` package and its v2 API.
- Keep `GPIO_PIN = 17`, `LOW = 0`, and `HIGH = 1`.
- Preserve `setup()`, `set_level()`, `get_level()`, and `cleanup()` public behavior.
- Preserve `GET/PUT /api/gpio` response and validation behavior.
- Scan `/dev/gpiochip*` and resolve the line by name `GPIO17`; do not hard-code `/dev/gpiochip0`.
- Keep in-memory fallback when the binding, device, permission, line, or write is unavailable.
- Keep GPIO request access serialized because the official Python bindings are not thread-safe.
- Do not change animation polling, rendering, state handling, rotation, or browser launch behavior.
- Do not create Git commits unless the user explicitly requests one.

---

### Task 1: gpiod Output Driver

**Files:**
- Modify: `tests/test_gpio.py`
- Modify: `gpio.py`

**Interfaces:**
- Consumes: `gpiod.is_gpiochip_device(path)`, `gpiod.Chip(path)`, `Chip.line_offset_from_id("GPIO17")`, `gpiod.request_lines(...)`, `gpiod.LineSettings`, `gpiod.line.Direction`, and `gpiod.line.Value`.
- Produces: unchanged `setup() -> bool`, `set_level(value: int) -> int`, `get_level() -> int`, and `cleanup() -> None`.
- Stores: `_request`, `_line_offset`, `_available`, `_level`, and `_lock` as module state.

- [ ] **Step 1: Replace sysfs setup tests with failing gpiod discovery and request tests**

Create fake `gpiod` objects in `tests/test_gpio.py` and patch `gpio.gpiod` plus `gpio.os.scandir`. Verify that `setup()` skips non-GPIO entries, opens the matching chip, resolves `GPIO17`, and requests the line as output-low:

```python
def test_setup_finds_named_line_and_requests_output_low(self):
    gpio.gpiod = self.binding
    self.binding.is_gpiochip_device.side_effect = lambda path: path.endswith("gpiochip4")
    self.binding.Chip.return_value.__enter__.return_value.line_offset_from_id.return_value = 17

    self.assertTrue(gpio.setup())

    self.binding.request_lines.assert_called_once_with(
        "/dev/gpiochip4",
        consumer="roboface",
        config={17: self.binding.LineSettings.return_value},
    )
    self.binding.LineSettings.assert_called_once_with(
        direction=self.binding.line.Direction.OUTPUT,
        output_value=self.binding.line.Value.INACTIVE,
    )
```

- [ ] **Step 2: Run the focused setup test and verify RED**

Run: `py -3.11 -m unittest tests.test_gpio.GpioGpiodTests.test_setup_finds_named_line_and_requests_output_low -v`

Expected: FAIL because the existing implementation checks `/sys/class/gpio` and has no `gpiod` binding or line request.

- [ ] **Step 3: Implement defensive import, chip discovery, and output request**

Replace sysfs paths and `_write()` helpers in `gpio.py` with:

```python
try:
    import gpiod
except ImportError:
    gpiod = None

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
```

In `setup()`, request the discovered line with `Direction.OUTPUT` and initial `Value.INACTIVE`. Catch `ImportError`-equivalent absence and `OSError`, set `_available = False`, and retain `_level = LOW`.

- [ ] **Step 4: Run the focused setup test and verify GREEN**

Run: `py -3.11 -m unittest tests.test_gpio.GpioGpiodTests.test_setup_finds_named_line_and_requests_output_low -v`

Expected: PASS.

- [ ] **Step 5: Add failing write, fallback, and cleanup tests**

Add tests that verify:

```python
def test_set_level_maps_high_to_active(self):
    gpio._available = True
    gpio._request = self.request
    gpio._line_offset = 17
    gpio.set_level(gpio.HIGH)
    self.request.set_value.assert_called_once_with(17, self.binding.line.Value.ACTIVE)

def test_write_error_falls_back_and_tracks_requested_level(self):
    self.request.set_value.side_effect = OSError("busy")
    gpio._available = True
    gpio._request = self.request
    gpio._line_offset = 17
    self.assertEqual(gpio.set_level(gpio.HIGH), gpio.HIGH)
    self.assertFalse(gpio._available)

def test_cleanup_drives_low_and_releases_request(self):
    gpio._available = True
    gpio._request = self.request
    gpio._line_offset = 17
    gpio.cleanup()
    self.request.set_value.assert_called_once_with(17, self.binding.line.Value.INACTIVE)
    self.request.release.assert_called_once_with()
```

Retain invalid-value and memory round-trip coverage. Add missing-binding, no-named-line, and permission-error setup cases that assert `setup()` returns `False`.

- [ ] **Step 6: Run all GPIO tests and verify RED**

Run: `py -3.11 -m unittest tests.test_gpio -v`

Expected: FAIL in write and cleanup tests because the implementation does not yet map values or release `LineRequest`.

- [ ] **Step 7: Implement value mapping, fallback transition, and cleanup**

Map integer values explicitly:

```python
line_value = (
    gpiod.line.Value.ACTIVE if value == HIGH else gpiod.line.Value.INACTIVE
)
```

Call `_request.set_value(_line_offset, line_value)` under `_lock`. On `OSError`, release the request if possible, clear `_request` and `_line_offset`, and set `_available = False` before updating `_level`. In `cleanup()`, attempt output-low, always release, clear all request state, reset `_level = LOW`, and set `_available = None`.

- [ ] **Step 8: Run GPIO and API tests and verify GREEN**

Run: `py -3.11 -m unittest tests.test_gpio tests.test_server tests.test_launcher -v`

Expected: all GPIO tests pass and the existing `/api/gpio` and launcher lifecycle tests remain green.

---

### Task 2: ARM64 Dependency and Operator Documentation

**Files:**
- Modify: `requirements-build.txt`
- Modify: `tests/test_packaging.py`
- Modify: `build-raspberry-pi.sh`
- Modify: `install-autostart.sh`
- Modify: `tests/test_install_autostart.sh`
- Modify: `README.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: `gpiod==2.5.0` from PyPI during native arm64 build.
- Produces: a PyInstaller executable containing the official binding and an install-time GPIO character-device permission diagnostic.

- [ ] **Step 1: Write failing packaging and installer assertions**

Update `tests/test_packaging.py` so the pinned build requirements must be:

```python
["pyinstaller==6.15.0", "gpiod==2.5.0"]
```

Also require `build-raspberry-pi.sh` to run:

```bash
python -c "import gpiod; print(gpiod.__version__)"
```

Update `tests/test_install_autostart.sh` to assert the installer refers to `/dev/gpiochip` access rather than the obsolete `gpio` group/sysfs advice.

- [ ] **Step 2: Run packaging tests and verify RED**

Run: `py -3.11 -m unittest tests.test_packaging -v`

Run in WSL: `bash tests/test_install_autostart.sh`

Expected: FAIL because the dependency, smoke import, and new permission text are absent.

- [ ] **Step 3: Add the pinned dependency and build smoke import**

Set `requirements-build.txt` to:

```text
pyinstaller==6.15.0
gpiod==2.5.0
```

After dependency installation in `build-raspberry-pi.sh`, run the import/version command before tests and PyInstaller.

- [ ] **Step 4: Replace sysfs and gpio-group operator guidance**

Change `install-autostart.sh` to inspect writable `/dev/gpiochip*` devices and print a diagnostic when none are writable. Update `README.md` and `CLAUDE.md` to describe the gpiod character-device backend, `GPIO17` named-line discovery, packaged dependency, and memory fallback. Remove statements that the implementation uses sysfs or only the Python standard library.

- [ ] **Step 5: Run packaging and installer checks and verify GREEN**

Run: `py -3.11 -m unittest tests.test_packaging -v`

Run in WSL: `bash -n build-raspberry-pi.sh install-autostart.sh tests/test_install_autostart.sh`

Run in WSL: `bash tests/test_install_autostart.sh`

Expected: all checks pass and the installer test ends with `AUTOSTART_TEST_OK`.

---

### Task 3: Full Regression Validation

**Files:**
- Validate all modified files.

**Interfaces:**
- Consumes: completed Tasks 1 and 2.
- Produces: evidence that the driver, API, packaging metadata, and shell installer agree.

- [ ] **Step 1: Run the complete Python suite**

Run: `py -3.11 -m unittest discover -s tests -v`

Expected: all tests pass with zero failures and zero errors.

- [ ] **Step 2: Validate Python syntax and editor diagnostics**

Run: `py -3.11 -m py_compile gpio.py server.py launcher.py`

Check VS Code diagnostics for all modified Python files and fix only errors introduced by this migration.

- [ ] **Step 3: Validate shell scripts**

Run in WSL: `bash -n build-raspberry-pi.sh install-autostart.sh tests/test_install_autostart.sh`

Run in WSL: `bash tests/test_install_autostart.sh`

Expected: syntax checks exit zero and integration output ends with `AUTOSTART_TEST_OK`.

- [ ] **Step 4: Inspect the final diff**

Run: `git diff --check`

Run: `git status --short`

Confirm the diff contains no raw `/sys/class/gpio` runtime implementation, no unrelated animation changes, and no generated build artifacts.

- [ ] **Step 5: Record hardware validation boundary**

Report that automated tests validate the gpiod API integration with fakes, while actual GPIO17 voltage switching and bundled extension loading still require the native arm64 Raspberry Pi build and hardware smoke test.