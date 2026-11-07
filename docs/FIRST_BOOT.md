# First boot and known application workarounds

Complete the original setup and check the current desktop user before changing
per-user settings. The developer system uses headless-system-user mode; user0
is not necessarily the interactive desktop. Do not hardcode user10 on a new
installation or mark setup complete as a workaround for a stall.

## Display and mouse

If you have an authorized Android shell, the requested prototype preferences
can be restored with the standard shell commands:

```sh
wm density 160
settings put system pointer_speed 5
```

These are preferences, not CPU/GPU clock changes. If the framework rejects a
shell operation, use its corresponding Settings UI; do not add broad SELinux
permissions. Density overrides can be reverted with `wm density reset`.
Custom mouse settings UI, final desktop icon spacing and HoshinoOS branding
remain unfinished.

## Chrome, Gmail and YouTube

The system image's Chrome version can differ from the version previously
installed in userdata. Check the actual version before applying a workaround.
The pre-reset Gmail validation only covered its landing page; an authenticated
mailbox was not tested. YouTube had a successful user video replay, while
TikTok and wider app regressions remain to be tested.

For Chrome157, the tested command line is stored in
`patches/graphics/chrome157/chrome-command-line`:

```text
_ --use-gl=angle --use-angle=gles --disable-features=Vulkan,SkipVulkanBlocklist --enable-logging
```

It must be installed as shell-owned0644 at
`/data/local/tmp/chrome-command-line`, with Chrome's **Enable command line on
non-rooted devices** enabled, ANGLE selection set to Default, then Chrome
relaunched. Copying the file without enabling consumption is insufficient.
The exact backend value is `gles`, not `opengles`. See
[Chrome157 procedure](chrome157_gmail_fix.md) and the older
[GLES bootstrap](chrome_angle_gles_fix.md).

This uses hardware V3D GLES; it is not Chrome Vulkan support. Native V3DV
Vulkan queue/readback and Android swapchain clear/present passed separately.
Do not force Chrome Vulkan by falsifying driver feature reports.

## Check before reporting a boot or UI failure

Record Android build/version, the actual Chrome version, output of
`getprop sys.boot_completed`, which desktop user is running and the first
fatal/ANR in logcat/UART. A movable pointer with a frozen launcher does not by
itself identify a kernel bug. Keep logs local until personal identifiers and
account URLs are removed.
