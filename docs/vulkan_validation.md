> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# Vulkan support and validation

User requested Vulkan support in addition to performance/Setup Wizard work.
The existing Raspberry Pi BSP already includes the Broadcom Vulkan APEX,
Mesa V3DV. Its rc selects ro.hardware.vulkan=broadcom and ro.vulkan.apex=
com.android.hardware.vulkan.broadcom. Its permissions advertise Vulkan1.3,
hardware level1 and compute0. These are declarations, not runtime test results.
The ALOS original Adreno driver must not replace this Pi driver.

Chrome's persistent ANGLE OpenGL ES preference is retained. Earlier Chrome
Vulkan ANGLE failed EGL context creation. A successful native Vulkan test
will not automatically establish compatibility with Chrome's ANGLE backend.

New diagnostic: tools/vulkan/v3dv_smoke.c builds as an Android ARM64 PIE via
tools/vulkan/build.sh using the local AOSP toolchain. Build passed with
-Wall -Wextra -Werror. Loader is /system/bin/linker64. The test uses the
system Vulkan loader, selects a Broadcom integrated GPU (not CPU rendering),
creates a device/graphics queue, fills a 4096-byte buffer through a submitted
GPU command, waits for completion and validates all 1024 words on the CPU.
It uses proper transfer-to-host visibility and coherent mapped memory.
This is a basic Vulkan1.0 command path test, not a Vulkan1.3 conformance,
rendering/swapchain, game compatibility or performance certification.

On next Pi boot run:

    bash aluminium-rpi5/tools/vulkan/check_live.sh PI_IP

This uploads a diagnostic to /data/local/tmp, captures cmd gpu vkjson and
feature declarations, and runs the hardware test with a 45-second timeout.
It does not alter driver selections, app preferences or system settings.
It records failures and succeeds only on Broadcom hardware readback PASS.
Outputs under work/vulkan/live-TIMESTAMP. Captures may contain device details;
keep local. No hardware test has yet run: Pi is offline, SSD at laptop.

Next: inspect actual runtime loader/device extensions and smoke result; only
patch an observed failure. Do not force Vulkan globally for all apps or
change Chrome's working backend merely because the driver is installed.

## Runtime result — 2026-11-06 17:47

PASS on actual Pi: V3D7.1.10.2, vendor0x14e4, integrated GPU,
Vulkan1.3.354. Device creation, queue submission and 4096-byte GPU fill/readback
passed. Evidence work/vulkan/live-20261106-174725/. No driver replacement
needed for this native Vulkan path. Chrome ANGLE and presentation are separate
unverified paths. Nonfatal AApexInfo PathNotFromApex messages were printed for
the diagnostic executable under /data/local/tmp.
