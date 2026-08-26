# Display Rotation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Use a pure black background and support `0`, `90`, `180`, and `270` degree rotation through both launcher arguments and REST.

**Architecture:** Store rotation beside the existing server state under its own lock. The launcher parses and sets the initial value before serving. The page polls the rotation endpoint and applies centered CSS rotation with swapped dimensions for quarter turns.

**Tech Stack:** Python 3.11 standard library, `unittest`, HTML/CSS/JavaScript, Playwright browser validation.

## Global Constraints

- Preserve all existing state API behavior.
- Accept only integer rotations `0`, `90`, `180`, and `270`.
- Default startup rotation is `0`.
- Keep all runtime assets local and preserve offline operation.
- Do not restore the user-deleted `index2.html` or `roboface.py` files.
- Do not create Git commits unless explicitly requested.

---

### Task 1: Rotation API and Launcher Argument

**Files:**
- Modify: `server.py`
- Modify: `launcher.py`
- Modify: `tests/test_server.py`
- Modify: `tests/test_launcher.py`

**Interfaces:**
- Produces: `server.VALID_ROTATIONS = (0, 90, 180, 270)`.
- Produces: `server.set_rotation(rotation: int) -> None`.
- Produces: `GET /api/rotation` and `PUT /api/rotation`.
- Produces: `launcher.parse_args(args: list[str] | None = None) -> argparse.Namespace`.
- Changes: `launcher.main(rotation: int = 0) -> int`.

- [ ] **Step 1: Write failing REST tests**

Add tests that reset rotation to `0`, verify `GET /api/rotation`, update to `90`, and reject `45`, malformed JSON, and a JSON array with HTTP 400.

- [ ] **Step 2: Verify REST tests fail**

Run: `C:/ProgramData/anaconda3/python.exe -m unittest tests.test_server -v`

Expected: FAIL because `/api/rotation` does not exist.

- [ ] **Step 3: Implement rotation storage and routes**

Add `VALID_ROTATIONS`, `_current_rotation`, `_rotation_lock`, and `set_rotation`. Mirror the existing state route structure and return `{"rotation": value}`.

- [ ] **Step 4: Verify REST tests pass**

Run: `C:/ProgramData/anaconda3/python.exe -m unittest tests.test_server -v`

Expected: PASS.

- [ ] **Step 5: Write failing launcher argument tests**

Test default `0`, all four accepted values, rejection of `45`, and that `main(90)` calls `server.set_rotation(90)` before starting the server.

- [ ] **Step 6: Verify launcher tests fail**

Run: `C:/ProgramData/anaconda3/python.exe -m unittest tests.test_launcher -v`

Expected: FAIL because argument parsing and rotation initialization are absent.

- [ ] **Step 7: Implement launcher parsing and initialization**

Use `argparse.ArgumentParser`, `type=int`, and `choices=server.VALID_ROTATIONS`. Call `server.set_rotation(rotation)` before creating `ThreadingHTTPServer`, and pass the parsed value from `__main__`.

- [ ] **Step 8: Verify launcher and server tests pass**

Run: `C:/ProgramData/anaconda3/python.exe -m unittest tests.test_launcher tests.test_server -v`

Expected: PASS.

---

### Task 2: Black Background and Responsive Rotation

**Files:**
- Modify: `index.html`
- Modify: `tests/test_server.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `GET /api/rotation`.
- Produces: `applyRotation(rotation)` in the page module.
- Produces: black `html`, `body`, and player background.

- [ ] **Step 1: Write failing HTML contract tests**

Assert `index.html` contains `background: #000`, polls `/api/rotation`, sets `rotate(${rotation}deg)`, and uses `100vh`/`100vw` in the quarter-turn branch.

- [ ] **Step 2: Verify HTML tests fail**

Run: `C:/ProgramData/anaconda3/python.exe -m unittest tests.test_server -v`

Expected: FAIL because the current background is `#12122a` and no rotation logic exists.

- [ ] **Step 3: Implement centered rotation and black background**

Position the player at `left: 50%`, `top: 50%`; use `translate(-50%, -50%) rotate(...)`. Set dimensions to `100vh` by `100vw` for `90/270`, otherwise `100vw` by `100vh`. Poll rotation every 500 ms and only apply changed values.

- [ ] **Step 4: Document rotation usage**

Add the launcher example and `GET/PUT /api/rotation` examples to `README.md`.

- [ ] **Step 5: Run complete automated verification**

Run: `C:/ProgramData/anaconda3/python.exe -m unittest discover -s tests -v`

Run: `C:/ProgramData/anaconda3/python.exe -m py_compile launcher.py server.py`

Run: `git diff --check`

Expected: all commands exit `0`.

- [ ] **Step 6: Validate all rotations in a real browser**

Start `server.py`, load the page, PUT each valid rotation, and verify a nonblank canvas, black computed background, matching state-machine behavior, and expected player dimensions for every angle.