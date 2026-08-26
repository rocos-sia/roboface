# Raspberry Pi ARM64 Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a single `roboface-linux-arm64` executable that launches RoboFace in Chromium kiosk mode, works without internet access, and retains the REST state API.

**Architecture:** Keep `server.py` as the HTTP and API owner. Refactor `launcher.py` only enough to discover Linux Chromium, build a testable kiosk command, and tie server lifetime to the browser process. Bundle the fixed dotLottie JavaScript/WASM assets and application files with PyInstaller, then build on native arm64 Linux locally or in GitHub Actions.

**Tech Stack:** Python 3.11 standard library, `unittest`, Chromium, PyInstaller 6.15.0, `@lottiefiles/dotlottie-wc` 0.9.27, `@lottiefiles/dotlottie-web` 0.79.2, GitHub Actions.

## Global Constraints

- Target Raspberry Pi OS 64-bit on arm64, based on Debian Bookworm or a compatible newer release.
- Runtime operation must not require Python, Node.js, npm, or internet access.
- Chromium is an external prerequisite and must be available as `chromium` or `chromium-browser` on Linux.
- Preserve `GET /api/state`, `PUT /api/state`, and `GET /api/states` behavior and the four states `smile`, `proud`, `unhappy`, and `daze`.
- The executable binds to `0.0.0.0`, tries ports from `8000`, and writes the selected endpoint to the temporary log.
- Closing Chromium or pressing `Ctrl+C` shuts down the HTTP server.
- Do not restore the user-deleted `index2.html` or `roboface.py` files.
- Do not create Git commits unless the user explicitly requests them.

---

### Task 1: Cross-Platform Kiosk Launcher

**Files:**
- Create: `tests/test_launcher.py`
- Modify: `launcher.py`

**Interfaces:**
- Produces: `find_browser(platform: str | None = None) -> str | None`
- Produces: `build_browser_args(browser: str, url: str, user_data_dir: str) -> list[str]`
- Produces: `open_fullscreen(browser: str, url: str, user_data_dir: str) -> subprocess.Popen | None`
- Produces: `main() -> int`, which returns `1` when Chromium is unavailable or fails to launch and otherwise waits for the browser process.

- [ ] **Step 1: Write failing browser discovery tests**

Create `tests/test_launcher.py` with `unittest` cases that patch `launcher.shutil.which` and verify Linux lookup order:

```python
import unittest
from unittest.mock import patch

import launcher


class BrowserDiscoveryTests(unittest.TestCase):
    @patch("launcher.shutil.which")
    def test_linux_prefers_chromium(self, which):
        which.side_effect = lambda name: "/usr/bin/chromium" if name == "chromium" else None
        self.assertEqual(launcher.find_browser("linux"), "/usr/bin/chromium")
        self.assertEqual(which.call_args_list[0].args, ("chromium",))

    @patch("launcher.shutil.which", return_value=None)
    def test_linux_returns_none_without_chromium(self, which):
        self.assertIsNone(launcher.find_browser("linux"))
```

- [ ] **Step 2: Run the browser tests and verify RED**

Run: `python -m unittest tests.test_launcher.BrowserDiscoveryTests -v`

Expected: FAIL because `find_browser` does not accept a platform and never checks Linux commands.

- [ ] **Step 3: Implement Linux and Windows browser discovery**

Import `shutil`, use `platform or sys.platform`, check `("chromium", "chromium-browser")` with `shutil.which` on Linux, and retain the existing Edge/Chrome paths on Windows.

- [ ] **Step 4: Run the browser tests and verify GREEN**

Run: `python -m unittest tests.test_launcher.BrowserDiscoveryTests -v`

Expected: both tests PASS.

- [ ] **Step 5: Write failing kiosk command and lifecycle tests**

Add tests that assert `build_browser_args()` includes `--kiosk`, `--no-first-run`, `--no-default-browser-check`, `--disable-session-crashed-bubble`, the exact `--user-data-dir`, and the URL. Add a `main()` test with patched server, browser process, temporary directory, and readiness check that asserts `proc.wait()` and `httpd.shutdown()` are called. Add failure cases for missing Chromium and failed `Popen`, both expecting return code `1` and server cleanup.

- [ ] **Step 6: Run lifecycle tests and verify RED**

Run: `python -m unittest tests.test_launcher -v`

Expected: FAIL because command construction is embedded in `open_fullscreen`, browser lifetime is not awaited, and launch failure does not return a non-zero code.

- [ ] **Step 7: Implement the minimal lifecycle changes**

Use `tempfile.mkdtemp(prefix="roboface-browser-")` for each run, pass it into `open_fullscreen`, wait on the returned process, and remove the profile with `shutil.rmtree(..., ignore_errors=True)` during cleanup. Use `tempfile.gettempdir()` in `log()`. Log a clear browser-not-found or browser-launch-failed message before returning `1`.

- [ ] **Step 8: Run launcher tests and syntax validation**

Run: `python -m unittest tests.test_launcher -v`

Run: `python -m py_compile launcher.py server.py`

Expected: all tests PASS and compilation exits `0`.

---

### Task 2: Offline Player and REST Regression Coverage

**Files:**
- Create: `tests/test_server.py`
- Create: `vendor/dotlottie-wc.js`
- Create: `vendor/dotlottie-player.wasm`
- Create: `vendor/LICENSE.dotlottie-wc.txt`
- Modify: `index.html`
- Modify: `server.py`

**Interfaces:**
- Consumes: `server.RoboFaceHandler`, `server.ROOT_DIR`, and the existing REST routes.
- Produces: local browser assets at `/vendor/dotlottie-wc.js` and `/vendor/dotlottie-player.wasm`.
- Produces: `application/wasm` static MIME support.

- [ ] **Step 1: Write failing static and REST integration tests**

Create `tests/test_server.py`. Start `ThreadingHTTPServer(("127.0.0.1", 0), RoboFaceHandler)` in a daemon thread for each test class and use `urllib.request` to assert:

```python
def test_offline_assets_are_served(self):
    for path, content_type in (
        ("/", "text/html"),
        ("/RoboFace.lottie", "application/octet-stream"),
        ("/vendor/dotlottie-wc.js", "application/javascript"),
        ("/vendor/dotlottie-player.wasm", "application/wasm"),
    ):
        with urllib.request.urlopen(self.base_url + path) as response:
            self.assertEqual(response.status, 200)
            self.assertIn(content_type, response.headers["Content-Type"])
            self.assertTrue(response.read())
```

Also test that `GET /api/states` returns all four states, valid `PUT /api/state` updates `GET /api/state`, and an unsupported state returns HTTP 400.

- [ ] **Step 2: Run server tests and verify RED**

Run: `python -m unittest tests.test_server -v`

Expected: the vendor asset requests fail with HTTP 404 and the WASM MIME assertion cannot pass.

- [ ] **Step 3: Vendor the pinned runtime files**

Download exact-version files during development:

```powershell
Invoke-WebRequest https://cdn.jsdelivr.net/npm/@lottiefiles/dotlottie-wc@0.9.27/dist/dotlottie-wc.js -OutFile vendor/dotlottie-wc.js
Invoke-WebRequest https://cdn.jsdelivr.net/npm/@lottiefiles/dotlottie-web@0.79.2/dist/dotlottie-player.wasm -OutFile vendor/dotlottie-player.wasm
Invoke-WebRequest https://cdn.jsdelivr.net/npm/@lottiefiles/dotlottie-wc@0.9.27/LICENSE -OutFile vendor/LICENSE.dotlottie-wc.txt
```

Record SHA-256 hashes in the build documentation so later updates are intentional and reviewable.

- [ ] **Step 4: Make the page initialize WASM locally before creating the component**

Replace the static `<dotlottie-wc>` element with a plain mount node. In the module script, import both exports, set the local WASM URL, create the component, set `src`, `autoplay`, `loop`, and `statemachineid`, then append it before calling `watchReady()`:

```javascript
import { setWasmUrl } from "./vendor/dotlottie-wc.js";

setWasmUrl("./vendor/dotlottie-player.wasm");
const player = document.createElement("dotlottie-wc");
player.id = "roboface";
player.src = "./RoboFace.lottie";
player.autoplay = true;
player.loop = true;
player.setAttribute("statemachineid", "StateMachine1");
document.body.appendChild(player);
```

This order ensures the local WASM URL is configured before the custom element is connected and initializes its player.

- [ ] **Step 5: Add WASM MIME support**

Map `.wasm` to `application/wasm` in `RoboFaceHandler._serve_static()`.

- [ ] **Step 6: Run server and full unit tests**

Run: `python -m unittest discover -s tests -v`

Expected: static asset, REST, and launcher tests PASS.

- [ ] **Step 7: Verify the HTML has no remote module import**

Run: `Select-String -Path index.html -Pattern 'https://|cdn.jsdelivr|unpkg.com'`

Expected: no matches.

---

### Task 3: PyInstaller One-File Build

**Files:**
- Create: `roboface.spec`
- Create: `requirements-build.txt`
- Create: `build-raspberry-pi.sh`
- Create: `tests/test_packaging.py`

**Interfaces:**
- Consumes: `launcher.py`, `server.py`, `index.html`, `RoboFace.lottie`, and `vendor/`.
- Produces: `dist/roboface-linux-arm64`.

- [ ] **Step 1: Write failing packaging manifest tests**

Create `tests/test_packaging.py` to load `roboface.spec` as text and assert it names every required data source and destination:

```python
class PackagingManifestTests(unittest.TestCase):
    def test_spec_bundles_runtime_assets(self):
        spec = Path("roboface.spec").read_text(encoding="utf-8")
        for required in (
            "index.html",
            "RoboFace.lottie",
            "vendor/dotlottie-wc.js",
            "vendor/dotlottie-player.wasm",
            "vendor/LICENSE.dotlottie-wc.txt",
        ):
            self.assertIn(required, spec)
```

Also assert the build script rejects non-Linux and non-`aarch64` hosts, creates a virtual environment, installs `requirements-build.txt`, runs all unit tests, invokes `pyinstaller --clean --noconfirm roboface.spec`, and checks that `dist/roboface-linux-arm64` is executable.

- [ ] **Step 2: Run packaging tests and verify RED**

Run: `python -m unittest tests.test_packaging -v`

Expected: FAIL because the spec and build files do not exist.

- [ ] **Step 3: Add pinned build dependency**

Create `requirements-build.txt` containing:

```text
pyinstaller==6.15.0
```

- [ ] **Step 4: Add the one-file PyInstaller spec**

Create `roboface.spec` with `Analysis(["launcher.py"])`, explicit `datas` entries for the five runtime assets, a `PYZ`, and one `EXE` named `roboface-linux-arm64`. Use `console=True` so launch failures remain diagnosable from a terminal as well as in `/tmp/roboface.log`.

- [ ] **Step 5: Add the native arm64 build script**

Create executable `build-raspberry-pi.sh` with `set -euo pipefail`. Check `uname -s` equals `Linux` and `uname -m` equals `aarch64`; create `.venv-build`, install the pinned requirements, run `python -m unittest discover -s tests -v`, run PyInstaller, and print the artifact path plus `sha256sum`.

- [ ] **Step 6: Run packaging and full unit tests**

Run: `python -m unittest discover -s tests -v`

Expected: all tests PASS.

- [ ] **Step 7: Validate shell syntax on Linux**

Run: `bash -n build-raspberry-pi.sh`

Expected: exit code `0`.

---

### Task 4: ARM64 Build Automation and Operator Guide

**Files:**
- Create: `.github/workflows/build-raspberry-pi.yml`
- Create: `README.md`
- Modify: `tests/test_packaging.py`

**Interfaces:**
- Consumes: `build-raspberry-pi.sh` and all repository tests.
- Produces: downloadable GitHub Actions artifact `roboface-linux-arm64`.
- Produces: installation, launch, API, offline, and troubleshooting instructions.

- [ ] **Step 1: Extend packaging tests for CI and documentation**

Assert the workflow uses an arm64 runner, invokes `build-raspberry-pi.sh`, and uploads `dist/roboface-linux-arm64`. Assert `README.md` contains the Chromium prerequisite, Raspberry Pi OS 64-bit requirement, local build command, executable launch command, all three REST endpoints, a `curl` state-change example, log path `/tmp/roboface.log`, and offline behavior.

- [ ] **Step 2: Run the new tests and verify RED**

Run: `python -m unittest tests.test_packaging -v`

Expected: FAIL because the workflow and README do not exist.

- [ ] **Step 3: Add the arm64 workflow**

Create a manually dispatchable workflow that also runs on tagged releases. Use `runs-on: ubuntu-24.04-arm` with the `python:3.11-bookworm` job container so the generated glibc dependency remains compatible with Raspberry Pi OS Bookworm. Check out the repository, execute `chmod +x build-raspberry-pi.sh`, run the build script, and upload `dist/roboface-linux-arm64` with `actions/upload-artifact`.

- [ ] **Step 4: Add concise Raspberry Pi instructions**

Document:

```bash
sudo apt update
sudo apt install -y chromium
chmod +x roboface-linux-arm64
./roboface-linux-arm64
```

Include `curl http://<raspberry-pi-ip>:8000/api/states`, a valid `PUT /api/state` example, the dynamic-port log behavior, how to close the kiosk, and native build instructions.

- [ ] **Step 5: Run all local validation**

Run: `python -m unittest discover -s tests -v`

Run: `python -m py_compile launcher.py server.py`

Run: `git diff --check`

Expected: all tests PASS, compilation exits `0`, and the diff check has no output.

- [ ] **Step 6: Build and smoke-test on arm64 Raspberry Pi OS**

Run: `./build-raspberry-pi.sh`

Run: `./dist/roboface-linux-arm64`

From a second terminal, run:

```bash
curl http://127.0.0.1:8000/api/states
curl -X PUT http://127.0.0.1:8000/api/state \
  -H 'Content-Type: application/json' \
  -d '{"state":"daze"}'
curl http://127.0.0.1:8000/api/state
```

Expected: Chromium displays the animation full-screen without network access, all states can be selected, and closing Chromium terminates the executable. If port `8000` was occupied, read the selected URL from `/tmp/roboface.log` and repeat against that port.