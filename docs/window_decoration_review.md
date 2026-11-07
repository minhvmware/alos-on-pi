> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# Window decoration review — 2026-11-04

User reports that application windows look like Android phone desktop mode.
Live SSH inspection and a Settings launch established:

- SystemUI is `/system_ext/priv-app/SystemUITitan/SystemUITitan.apk`.
  Byte comparison with the extracted original Aluminium APK passes.
- `/product/overlay/SystemUIDesktopOverlay.apk` also matches the original
  Aluminium APK byte for byte. No hashes were used.
- Desktop overlays for SystemUI and the framework are enabled for user 10.
- WM Shell reports `DesktopModeWindowDecorViewModel`, `DesktopModeStatus=true`,
  default display desktop eligibility, and desktop-first display mode.
- Pi's SystemUI overlay changes Quick Settings tiles only; its resource source
  contains no caption or window decoration override.
- Display is 1920x1080, density 240; original quartz vendor property specifies
  density 260. No forced density is set. Different physical screens prevent
  treating this alone as a defect.
- Settings opens successfully with app icon/title, dropdown, minimize,
  restore/maximize and close controls. Screenshot: `work/window-settings.png`.

The earlier suggestion that Pi supplied the window decorations is unsupported
by these observations. No UI configuration was changed. Await clarification
whether the discrepancy is the caption styling, opening animation, or initial
window size before selecting a targeted fix. APK and overlay identity alone do
not prove that every runtime flag or resource resolves as on original hardware.

Evidence: `work/window-systemui-live.txt`, `work/window-shell-live.txt`,
`work/window-current.png`, `work/window-settings.png`.

## Density and composition trial

User requested a smaller desktop and reported further rendering defects.
Applied `wm density 200` (physical density 240, display remains 1920x1080).
Screenshot: `work/desktop-density-200.png`. Undo with `wm density reset`.

Kernel log contains repeated vc4-drm `Failed to allocate LBM entry: -28`,
including during window transitions and the density change. This is a concrete
display-plane allocation failure, but its relationship to the user's visual
symptom is still unconfirmed. Temporarily set SurfaceFlinger transaction 1008
to 1 (forced GPU/client composition). Transaction 1010 reports the final flag
as 1, and SurfaceFlinger still reports Broadcom V3D hardware rendering.
Undo the trial with `service call SurfaceFlinger 1008 i32 0`; it is a runtime
trial rather than a persistent boot property. No driver or kernel was replaced.
Need the user's symptom description and comparable window activity before
claiming this resolves the remaining rendering defect.

User clarified that the remaining symptom is stutter, then requested density
120. Applied `wm density 120`; runtime override confirmed as 120. Physical
resolution remains 1920x1080. Forced client composition trial remains enabled.
The earlier CPU dump was a stale interval and does not establish the cause
of current stutter.

2026-11-06: user selected 160 as the preferred saved desktop density while
retaining adjustment through Settings > Display > Display size & text. Applied
wm density 160 for current desktop user 10; readback is physical 240, override
160. This is a persistent user preference, not a boot script that forces
160 repeatedly; the underlying factory density property remains 240.

2026-11-06 mouse/icon preference: changed user-10 Settings.System.pointer_speed
from 0 to +5. Input dispatcher dump confirms Pointer Speed 5. DPI remains 160.
No icon-size setting has been changed yet: current main workspace profile is
48 px and taskbar profile 44 px (rendered adaptive icon bounds can be smaller).
Home Settings and its inline desktop menu offer no standalone icon-size slider.
Requested clarification whether the user means matching icon size or reducing
the large grid spacing. Evidence: work/launcher-dump-live.txt,
work/desktop-icons-before.png, work/desktop-inline-settings.png.
