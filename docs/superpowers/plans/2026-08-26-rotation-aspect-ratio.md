# Rotation Aspect Ratio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent rotated RoboFace animations from stretching by using centered `contain` layout and synchronizing the internal canvas after host resizing.

**Architecture:** Keep the existing host width/height swap for quarter turns. Configure dotLottie to render with `contain`, temporarily remove rotation, force browser layout, and call `dotLottie.resize()` before restoring rotation so the internal canvas matches the host.

**Tech Stack:** HTML/CSS/JavaScript, dotLottie Web Component 0.9.27, Python `unittest`, Playwright browser validation.

## Global Constraints

- Preserve existing state and rotation APIs.
- Preserve black backgrounds and offline assets.
- Display the complete image without cropping; letterboxing is allowed.
- Do not stage or restore the pre-existing deletions of `index2.html` and `roboface.py`.

---

### Task 1: Contain Layout and Canvas Synchronization

**Files:**
- Modify: `index.html`
- Modify: `tests/test_server.py`

**Interfaces:**
- Produces: `configureLayout()` applying `{ fit: "contain", align: [0.5, 0.5] }` after load.
- Produces: `applyRotation(rotation)` that updates host geometry, forces layout, calls `dotLottie.resize()`, and then restores rotation.

- [ ] **Step 1: Write the failing HTML contract test**

Require `setLayout({ fit: "contain", align: [0.5, 0.5] })`, forced layout, and resize-before-rotate ordering in the page module.

- [ ] **Step 2: Verify the test fails**

Run: `C:/ProgramData/anaconda3/python.exe -m unittest tests.test_server.RoboFaceServerTests.test_html_preserves_aspect_ratio_after_rotation -v`

Expected: FAIL because layout and explicit resize are absent.

- [ ] **Step 3: Implement contain and resize**

Configure layout when dotLottie is loaded. Update host styles, temporarily remove rotation, force layout by reading the host width, resize the loaded dotLottie instance, and restore rotation. Keep the current black background and width/height rules.

- [ ] **Step 4: Run complete automated tests**

Run: `C:/ProgramData/anaconda3/python.exe -m unittest discover -s tests -v`

Expected: all tests pass.

- [ ] **Step 5: Run real-browser rotation validation**

Start the local server and PUT `0`, `90`, `180`, and `270`. After each change, require host dimensions and internal canvas dimensions to match, nonblank pixels, black background, local-only resources, and successful state-machine input changes.

- [ ] **Step 6: Run final syntax and diff checks**

Run Python compilation, Bash syntax checks, vendor hash checks, offline URL scan, and `git diff --check`.