# Rotation Aspect Ratio Design

## Goal

Preserve the animation's original aspect ratio after rotating the display. The complete image remains visible, with black letterboxing when the screen and animation ratios differ.

## Root Cause

For a quarter turn, the page changes the `dotlottie-wc` host from viewport width/height to swapped dimensions. Browser validation showed that the host changed from `2115x1245` to `1245x2115`, while the component's internal canvas remained `2115x1245`. CSS then stretched the old canvas bitmap into the new host dimensions, visibly distorting the image.

## Rendering Behavior

When dotLottie is loaded, the page sets its layout to `contain` with center alignment:

```javascript
dotLottie.setLayout({ fit: "contain", align: [0.5, 0.5] });
```

Rotation continues to swap host width and height for `90` and `270` degrees. The page temporarily removes rotation, reads the host's layout width to force the browser to apply its new dimensions, calls `dotLottie.resize()`, and restores rotation in the same JavaScript task. This synchronizes the internal canvas dimensions without exposing an unrotated frame or depending on animation frames that Chromium may throttle in a background or temporarily blank page.

The page background and player background remain black, so unused space appears as black letterboxing rather than stretching or cropping the animation.

## Validation

Automated tests require explicit `contain` layout, centered alignment, forced layout before `dotLottie.resize()`, resize-before-rotate ordering, and serialized rotation polling.

Real-browser validation checks all four supported rotations. The host and internal canvas dimensions must match after each rotation, the canvas must remain nonblank, the background must remain black, and existing state-machine and rotation APIs must continue working.

## Scope

This change does not add a selectable fill mode, crop animation content, alter the Lottie asset, or change the existing rotation API.