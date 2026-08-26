# Raspberry Pi ARM64 Packaging Design

## Goal

Deliver RoboFace as a single executable for 64-bit Raspberry Pi OS. Running the executable starts the existing HTTP and REST service, opens Chromium in kiosk mode, and displays the dotLottie animation without requiring Python or internet access at runtime.

## Supported Environment

- Raspberry Pi OS 64-bit on arm64, based on Debian Bookworm or a compatible newer release.
- A graphical desktop session with Chromium installed as `chromium` or `chromium-browser`.
- Network access is optional at runtime. Remote REST clients must be able to reach the Raspberry Pi and its selected TCP port.

The executable is architecture-specific. It must be built in an arm64 Linux environment; a Windows PyInstaller build cannot produce the required Linux arm64 binary.

## Packaging

PyInstaller builds `launcher.py` in one-file mode and embeds:

- `index.html`
- `RoboFace.lottie`
- The pinned dotLottie Web Component JavaScript and WebAssembly runtime assets

The release artifact is named `roboface-linux-arm64`. A Raspberry Pi build script creates the artifact natively. A GitHub Actions workflow may run the same build inside an arm64 Debian Bookworm environment so the output remains compatible with Raspberry Pi OS Bookworm.

## Runtime Architecture

The launcher finds a free port starting at `8000`, binds the existing `ThreadingHTTPServer` to `0.0.0.0`, and waits until the root page responds. It then locates Chromium from supported Linux command names and starts it with:

- Kiosk mode
- First-run and default-browser prompts disabled
- A dedicated temporary browser profile
- The local RoboFace URL

The HTTP server continues serving the page and REST API while Chromium is running. Closing Chromium causes the launcher to shut down the server and exit. `Ctrl+C` also performs an orderly shutdown.

If Chromium is unavailable or cannot start, the launcher records a clear error in the temporary log and exits with a non-zero status instead of silently leaving only the HTTP server running.

## Offline Frontend

`index.html` imports the pinned dotLottie Web Component from a local static path. All transitive runtime files required by the component, including WebAssembly, are packaged beside it in the PyInstaller resource bundle. No CDN request is made while displaying or switching animations.

The existing polling flow remains unchanged:

1. The page polls `GET /api/state` every 500 ms.
2. A state change invokes `stateMachineSetStringInput("states", state)`.
3. The dotLottie state machine switches among `smile`, `proud`, `unhappy`, and `daze`.

## REST Contract

The existing API remains compatible:

- `GET /api/state` returns the current state.
- `PUT /api/state` accepts a JSON object such as `{"state":"proud"}`.
- `GET /api/states` returns all supported states.
- Invalid JSON or unsupported states return HTTP 400.

The selected port is written to the launcher log. The default is `8000`; higher ports are selected only when it is unavailable.

## Validation

Automated tests cover:

- Free-port selection and exhaustion.
- Linux Chromium discovery.
- Chromium kiosk command construction and lifecycle handling.
- Static delivery of the HTML, animation, JavaScript, and WebAssembly assets.
- Successful and rejected REST state updates.
- PyInstaller resource lookup in source and frozen modes where practical.

The arm64 build is additionally smoke-tested by launching the executable, requesting the root page and API, changing every supported state, and confirming the process exits after Chromium closes. Browser-based validation confirms the animation renders in an offline context at desktop resolution.

## Scope

This change does not configure operating-system startup, install Chromium, package a browser, or create a Debian package. It does not restore the currently deleted `index2.html` or `roboface.py` files.