# Display Rotation Design

## Goal

Use a pure black animation background and allow RoboFace to rotate for the physical screen orientation at startup or while running.

## Rotation Controls

The packaged launcher accepts `--rotation` with the values `0`, `90`, `180`, or `270`. The default is `0`.

```bash
./roboface-linux-arm64 --rotation 90
```

The HTTP service exposes the current rotation through:

- `GET /api/rotation` returning `{"rotation": 90}`.
- `PUT /api/rotation` accepting a JSON object such as `{"rotation": 180}`.

Unsupported angles, malformed JSON, and non-object JSON return HTTP 400. Existing state endpoints and behavior remain unchanged.

## Runtime Flow

The launcher validates the command-line value before starting the server and sets the server's initial rotation. The server stores the rotation in memory under a lock, matching the existing state storage pattern.

The page polls `/api/rotation` every 500 ms. When the value changes, it rotates the `dotlottie-wc` element around the screen center. For `90` and `270` degrees, the element uses the viewport height as its unrotated width and the viewport width as its unrotated height. For `0` and `180` degrees, it uses the normal viewport dimensions. This preserves full-screen coverage without clipping after a quarter turn.

## Appearance

The document and player background are pure black (`#000`). No other animation styling changes.

## Validation

Automated tests cover command-line defaults and accepted values, launcher-to-server initialization, GET/PUT rotation behavior, invalid rotation requests, black background markup, local rotation polling, and quarter-turn dimension swapping.

Browser validation confirms rotations `0`, `90`, `180`, and `270` render a nonblank canvas, use the expected element dimensions, retain a black background, and continue responding to the existing state API.

## Scope

This change does not rotate the Raspberry Pi desktop, alter Chromium display settings, add arbitrary-angle rotation, or persist rotation across process restarts unless supplied again through `--rotation`.