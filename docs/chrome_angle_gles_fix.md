> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# Chrome startup crash: ANGLE GLES configuration

Applied on the running Pi, user 10, 2026-11-04. Chrome version
150.0.7871.181, Aluminium CL3B.260622.273.R1; Raspberry Vanilla Mesa 26.1.4.

## Failure and minimal fix

Default Chrome selected ANGLE's Vulkan backend on V3DV. Its GPU processes
reported `eglCreateContext ES 3.0 failed with error EGL_BAD_ATTRIBUTE`, then
Chrome native-aborted with `GPU process isn't usable. Goodbye.` The browser,
GPU process and activity disappeared within a few seconds of launch.

Set Chrome's own persistent flag:

1. Open `chrome://flags/#use-angle`.
2. Set **Choose ANGLE graphics backend** to **OpenGL ES**.
3. Click Chrome's **Relaunch** button so the preference is flushed.

This is a per-user Chrome preference, not a change to kernel, Mesa, Vulkan
driver or the system partition. A fresh Chrome profile/install needs the same
configuration. To roll back, select Default and Relaunch; on this build the
default backend reproduces the startup failure. Do not assume device reboot
or fresh-profile coverage from the app restart checks below.

## Bootstrap when Chrome cannot open its flags page

For this development device, the SSH shell temporarily used:

```sh
am set-debug-app --persistent com.android.chrome
printf '_ --use-gl=angle --use-angle=gles --enable-logging=stderr\n' > /data/local/tmp/chrome-command-line
chmod 644 /data/local/tmp/chrome-command-line
am force-stop --user 10 com.android.chrome
am start --user 10 -W -n com.android.chrome/com.google.android.apps.chrome.Main
```

ADB was already enabled. Chromium's command-line initialization allows the
temporary file for the selected debug app. The persistent debug-app setting
was needed for Chrome's Settings.Global check. The earlier nonpersistent
debug-app experiment did not enable that file. File mode 0600 also prevents
Chrome from reading a shell-owned file.

`--use-angle=gl` is invalid for this Android Chrome build: its log explicitly
lists only `opengles` and `vulkan` as supported ANGLE implementations.
`--use-angle=gles` is the working choice.

After selecting OpenGL ES in Chrome's UI and using its Relaunch action:

```sh
mv /data/local/tmp/chrome-command-line /data/local/tmp/chrome-command-line.trial-backup
am clear-debug-app
am force-stop --user 10 com.android.chrome
am start --user 10 -W -n com.android.chrome/com.google.android.apps.chrome.Main
```

The final state has no active command-line file, `debug_app=null` and
`wait_for_debugger=0`. The command-line-on-non-rooted-devices flag was not
enabled. No software rendering switch or sandbox bypass was applied.

## Validation on the physical Pi

- Chrome survived cold launch after removing the temporary file and debug
  setting, and loaded an HTTPS page.
- Browser PID 15093 and GPU process PID 15168 remained alive during the final
  observation window of more than a minute.
- `chrome://gpu` after that cold launch reports:
  - GL implementation: `(gl=egl-angle,angle=opengles)`.
  - GL renderer: `ANGLE (Broadcom, V3D 7.1.10.2, OpenGL ES 3.1 Mesa 26.1.4
    (git-1008af0815))`.
  - Canvas, compositing, rasterization and WebGL: hardware accelerated.
  - GPU sandbox: true; Skia backend: GaneshGL.
  - Vulkan disabled within Chrome with this configuration. This does not
    disable V3DV for other applications.
- Video decode/encode are advertised as hardware accelerated on the GPU page;
  actual codec/playback performance was not tested here.

Evidence: `work/chrome-live-trial.log`, `work/chrome-gpu-persistent.png`,
`work/chrome-renderer-persistent.png`, `work/chrome-example.png`, and
`work/chrome-final-state.txt`.

The linker warning about insufficient reserved space for `libmonochrome_64.so`
also appears in a GPU process that continues initializing. Earlier speculation
that it independently caused the second Chrome crash is not established;
that attempt still ended in the same GPU-unusable abort. The earlier
`--disable-gpu` experiment did not verify that its flags were read.

References: [Chromium command-line instructions](https://www.chromium.org/developers/how-tos/run-chromium-with-flags/)
and [command-line gating implementation](https://chromium.googlesource.com/chromium/src/+/main/base/android/java/src/org/chromium/base/CommandLineInitUtil.java).
