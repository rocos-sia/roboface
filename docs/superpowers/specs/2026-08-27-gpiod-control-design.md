# gpiod GPIO Control Design

## Goal

Replace the raw sysfs GPIO implementation introduced in the latest GPIO commit with the official `gpiod` Python bindings. Preserve the existing GPIO REST API while avoiding the deprecated `/sys/class/gpio` interface and keeping animation handling unchanged.

## Supported Environment

- Raspberry Pi OS 64-bit with Python 3.10 or newer.
- Raspberry Pi GPIO exposed through Linux GPIO character devices under `/dev/gpiochip*`.
- GPIO 17 uses BCM numbering and is requested as an output with an initial low level.
- The packaged Raspberry Pi executable includes `gpiod==2.5.0`; Node.js and npm are not required.

Development machines, CI, and Raspberry Pi sessions without GPIO access continue to use the existing in-memory fallback so the HTTP API remains testable.

## Driver Architecture

`gpio.py` remains the only GPIO owner and keeps its public interface:

- `setup() -> bool`
- `set_level(value: int) -> int`
- `get_level() -> int`
- `cleanup() -> None`
- `GPIO_PIN`, `LOW`, and `HIGH`

The module imports `gpiod` defensively so source execution and tests still work where the Linux-only package is unavailable. During `setup()`, it scans `/dev/gpiochip*`, keeps only character devices accepted by `gpiod.is_gpiochip_device()`, and opens each chip until `Chip.line_offset_from_id("GPIO17")` succeeds. This avoids assuming that the Raspberry Pi header GPIO controller is always `/dev/gpiochip0`.

After locating the line, the module calls `gpiod.request_lines()` with consumer name `roboface`, `Direction.OUTPUT`, and `Value.INACTIVE`. The returned request stays open for the application lifetime. `set_level()` maps REST values `0` and `1` to `Value.INACTIVE` and `Value.ACTIVE`, respectively, and calls `LineRequest.set_value()`.

The official bindings are not thread-safe. The existing re-entrant lock therefore serializes setup, writes, reads, fallback transitions, and cleanup. `cleanup()` first drives the line low when possible, releases the request, and clears module state. Repeated setup and cleanup calls remain safe.

## Failure Behavior

Missing bindings, no matching `GPIO17` line, permission errors, a busy line, and runtime write errors all switch the module to memory fallback instead of stopping the animation service. A failed hardware write still updates the API's tracked level, preserving the current REST behavior, but subsequent writes remain in fallback mode.

The launcher continues logging whether real GPIO initialization succeeded. Documentation will explain that the runtime user needs read/write access to `/dev/gpiochip*`; it will no longer describe sysfs export/unexport behavior.

## Packaging

The Raspberry Pi build requirements add the pinned `gpiod==2.5.0` package. The official PyPI package vendors libgpiod and requires Python 3.10 or newer, matching the current Python 3.11 build image. PyInstaller collects the imported extension module into `roboface-linux-arm64`.

The build remains native arm64 Linux. Windows development does not install or execute `gpiod`; tests inject a fake binding at the `gpio.py` boundary.

## REST Contract

No HTTP contract changes are made:

- `GET /api/gpio` returns `pin`, numeric `value`, and `level`.
- `PUT /api/gpio` accepts only integer `0` or `1`.
- Invalid values return HTTP 400.
- Existing animation state and rotation endpoints remain unchanged.

## Validation

Automated tests will verify:

- GPIO chips are scanned and the named `GPIO17` line is selected.
- Setup requests output-low configuration through `gpiod`.
- High and low writes map to the correct `gpiod.line.Value` values.
- Cleanup drives low and releases the line request.
- Missing bindings and GPIO errors fall back to memory behavior.
- Concurrent access remains serialized by the module lock.
- Existing server, launcher, packaging, and autostart tests continue to pass.

The Raspberry Pi build additionally runs a smoke check that imports the bundled `gpiod` module. Hardware-level switching must be verified on a Raspberry Pi because CI has no GPIO character device.

## Out Of Scope

- Changing the GPIO pin number through the REST API.
- PWM, edge events, or GPIO input handling.
- Migrating the Python HTTP server to Node.js.
- Changing animation polling, rendering, or browser launch behavior.