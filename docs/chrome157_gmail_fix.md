> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# Chrome157 Gmail compatibility fix — 2026-11-06

## Result

Gmail TWA now opens and renders its public Gmail landing page on physical Pi.
Screenshot work/gmail-fixed-final.png. Browser PID21531 survived cold startup,
with debug_app=null and command-line consumption logged. No account credentials
entered, no mailbox messages read/sent, no app data cleared or downgrade.
Browser sign-in onboarding was skipped; Gmail still needs user web sign-in.
YouTube wrapper also launched using the same surviving Chrome PID21531;
video playback/frame-rate validation remains separate.

## Actual fix

Chrome157.0.8103.38 replaced the previously tested150.0.7871.181. The old GLES
flag alone no longer ensured a GL fallback. Exact157 source initializes
supports_gpu_mode_hardware_gl_ to !features::kSkipVulkanBlocklist on Android.
With Vulkan disabled and SkipVulkanBlocklist enabled, fallback_modes_ can be
empty and the browser intentionally aborts at GPU process isn't usable.

Set the active /data/local/tmp/chrome-command-line to the project copy at
patches/graphics/chrome157/chrome-command-line. Exact working backend switch
is --use-angle=gles. 'opengles' is the reported GL implementation name, NOT
the accepted command-line value on this build. Several intermediate attempts
used that wrong token; they were not valid backend tests and were corrected.

Working flags: --use-gl=angle --use-angle=gles
--disable-features=Vulkan,SkipVulkanBlocklist --enable-logging.

In Chrome flags enabled 'Enable command line on non-rooted devices', selected
ANGLE Default so the profile does not override the backend file, and pressed
Relaunch. File is shell-owned0644, persists in userdata. Cold launch confirmed
file consumption after am clear-debug-app. Persistent debug selection removed,
wait_for_debugger not enabled. No in-process GPU/disable-sandbox/disable-gpu
flags remain. This is a development compatibility configuration dependent on
that local flag/file; factory reset/new profile needs setup again. Do not
claim immutable production-image coverage or reboot validation yet.

GPU page before clearing the profile override showed GaneshGL, V3D7.1/Mesa
26.1.4, hardware canvas/compositing/raster/WebGL and sandbox=true. GLES final
configuration uses that same driver path. Driver/video capability labels
alone are not playback performance evidence.

## Vulkan test and limit

An early CLI Vulkan trial was overridden by profile use-angle@1, confirmed
in chrome://gpu command line (both switches visible; later profile switch won).
It was NOT a successful Vulkan render. After setting profile ANGLE Default
and using Relaunch, the real Vulkan trial reproduced Requested version is not
supported / eglCreateContext ES3.0 EGL_BAD_ATTRIBUTE. Restored GLES afterward.

Physical vkjson reports standardSampleLocations=0. The exact ANGLE revision
751417514a52 embedded in this Chrome limits its Vulkan backend to ES2.0 when
that property is false; Chrome requires ES3.0. This is one verified limiting
condition, not a complete audit of all ANGLE caps. Native V3DV Vulkan1.3.354
queue/readback test passed earlier. Do not change the advertised driver limit
to true without implementing correct sample-location semantics. General
Vulkan app compatibility and swapchain/render tests remain unfinished.

Sources inspected (exact revisions):
https://github.com/chromium/chromium/blob/157.0.8103.38/content/browser/gpu/gpu_data_manager_impl_private.cc
https://github.com/google/angle/blob/751417514a52/src/libANGLE/renderer/vulkan/vk_renderer.cpp
https://github.com/chromium/chromium/blob/157.0.8103.38/chrome/browser/about_flags.cc

## Evidence and rollback

work/gmail-final-no-debug-cold.txt, gmail-final-no-debug-log.txt,
gmail-fixed-final.png, chrome157-vulkan-gpu.png, chrome-vulkan-real-trial-log.txt,
youtube-final-launch.txt. Earlier trial logs remain for reproducibility.
To roll back: move the command-line file aside and reset the non-rooted
command-line flag in Chrome; this can reproduce the original crash. Earlier
profile Local State backups remain untouched under work/chrome-vulkan-pref-*.
