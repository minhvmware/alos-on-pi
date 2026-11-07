# Current development status

Updated 2026-11-07, Asia/Ho_Chi_Minh. This file supersedes old milestone lists.

Publication update: a compact release image was assembled from the current SSD,
with new data/metadata, fresh FAT/free space and the configured SSH endpoint
removed. Filesystem/privacy checks passed; separate fresh-image hardware boot
is still pending. Install via INSTALL.md; developer prerequisites and the
previously local UART/metadata/policy setup helpers are now in DEVELOPMENT.md.
The new policy bootstrap compiled both validators and reproduced the M12
policy trial from an M11 input, including readback and fsck.

The pre-reset hybrid system booted Aluminium Android17/API37 desktop on a
Pi5 Linux6.18.26/Raspberry Vanilla vendor stack, Mesa26.1.4 V3D/V3DV. Native
ARM64, hardware GLES, USB keyboard/mouse and Wi-Fi worked. Framework still
identifies as the original Googlebook device; full HoshinoOS branding is pending.

Task Manager, FMQ and Bluetooth bring-up fixes are documented in
[Task Manager](taskmanager_serviceability_trial.md),
[FMQ](apps_media_fmq_trial.md) and [Bluetooth](bluetooth_restore.md).
SELinux remained enforcing; mixed user/userdebug compilation used `-N`, so
full neverallow validation is not claimed. No new permissive domains were added.

[Chrome157 GLES fix](chrome157_gmail_fix.md) rendered the Gmail landing page;
account/mailbox flows were not tested. YouTube later played normally in the
user replay; cause of the earlier network error was not isolated. TikTok and
startup ANRs still need regression testing. Native Vulkan queue and Android
swapchain clear/present passed; this is not game/shader/MSAA/conformance coverage.
Chrome ANGLE caps ES2 when V3DV reports standardSampleLocations=false; a GLES
workaround does not establish Chrome Vulkan support. See
[Vulkan validation](vulkan_validation.md).

CPU schedutil was boot-verified at unchanged min1.5/max2.4GHz. No voltage,
GPU-clock or thermal override. The security VM still consumed about one core;
it was not disabled. No controlled performance gain has been established.
The SSD link negotiated USB2 on Pi and laptop despite the reported USB3 cable;
the limiting component remains unproven.

The latest action was an authorized offline factory reset of data/metadata after
private verified backups. Expanded data47.4GiB and port patches were preserved.
The original signed serviceability provider was preinstalled in system_ext and
the desktop boot default retained. Fresh physical boot is NOT tested yet.

## Next steps

1. Run original Google/Aluminium setup, reconnect Wi-Fi, check actual user IDs,
   SSH, boot completion, launcher/ANRs, Task Manager, Bluetooth and CPU governor.
2. Restore requested density160 and mouse speed; reapply Chrome compatibility
   for the installed version. Data-held app updates/flags were erased by reset.
3. Retest Gmail/YouTube/TikTok with logs and measured playback/CPU evidence.
4. Investigate ANGLE/Vulkan capability compatibility without faking driver caps.
5. Continue compact desktop/settings and Pixel7 Android16 file/phone integration.
6. Validate real thermal readings, audio/video hardware paths, AVB/signing and
   policy constraints before daily-use or release claims.

Raw logs, screenshots, app profiles, proprietary binaries and backups remain
local; links in historical notes name evidence that is intentionally not public.
