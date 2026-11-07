> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# UI instability review — 2026-11-04

Capture: work/boot-review-ui-20261104/. SSD read only during capture; journal
replayed on userdata-copy.img and reports extracted again under recovered/.
Timestamps cross from build-time 2026-09-29 to 2026-11-04; do not order this
mixed capture solely by wall-clock filename, or attribute all retained reports
to the latest boot without considering process uptime and report contents.

## Launcher and Settings

ANR recovered/anr/anr_2026-09-29-16-51-46-434 identifies
com.google.android.apps.nexuslauncher. Main thread blocks in a synchronous
Binder transaction to IAppWidgetService.getInstalledProvidersForProfile during
CustomWidgetManager/Launcher initialization. Input dispatch for the swipe-up
gesture monitor times out after 5 seconds. This is an ANR, not a captured
Launcher Java exception. The report does not contain the system_server threads
needed to identify why the remote widget request stalls.

ANR recovered/anr/anr_2026-09-29-16-53-42-951 identifies com.android.settings.
Main thread waits in IWifiManager.getConfiguredNetworks while binding the saved
Wi-Fi networks preference. Again, remote service progress requires logcat or
system_server-side traces. Do not infer that launcher replacement, more RAM or
longer ANR timeout fixes either issue.

The Google search interactor also has a startup-time ANR in class/Dex loading.
First-boot I/O pressure is a possible contributor, not a demonstrated common
root cause of the other reports.

## Other distinct failures

- Chrome native crash: GPU process isn't usable (system_app_native_crash@
  1793779087005 and corresponding tombstone). It does not by itself explain
  Launcher's Binder wait, nor establish which GPU-process initialization failed.
- Factory task manager Java crash: failed to bind to
  vendor.google.desktop.serviceability.VendorServiceabilityService.
- gscd continues to abort because the Pi lacks /dev/tpm0.
- Existing trial boot config explicitly contains dtoverlay=disable-bt and UART0
  debug overrides absent from the original baseline config. This is a concrete
  Bluetooth configuration lead; Bluetooth HAL/runtime logs are still needed to
  establish the complete failure. No boot-config changes were made in this turn.

## Repair persistent capture before another UI test

Previous diagnostics tried to have init create /data/local/tmp/portdiag.
The combined policy allows init to create a shell_data_file directory but does
not grant add_name on its existing shell_data_file parent /data/local/tmp.
The directory remained absent even after userdata journal replay. Consequently
both capture processes were configured to write into a nonexistent directory.

Change: write directly into the existing /data/local/tmp as shell:

- portdiag-logcat.txt (4 MiB rotation, four archives)
- portdiag-state.txt (five minutes of process/service/property snapshots)

The policy allows shell directory add_name, file create/write and the logd
connection. No extra allow rules, permissive domains, app changes or timeout
changes were added. The capture still needs a boot test to confirm it runs.

tools/update_portdiag.sh backs up both existing files, updates rc/script,
reads contents back, checks root:root/0644/system_file and runs e2fsck. Tested
on work/m5-p5-logcapture-trial.img, then applied to /dev/sda5 after Hynix serial,
USB transport, mount state and size checks. Journal recovered before mutation.
Disk filesystem check passed and writes flushed. No whole-image rewrite or SHA.
Evidence: work/update-ui-capture.log; backups: work/portdiag-on-disk-backup/.

Next: reproduce Launcher hanging and Settings Wi-Fi behavior in the same boot,
wait 2–3 minutes, then read new captures. Launcher instability remains unresolved.

## Live UART follow-up — 2026-11-04

After the laptop reboot, the CH340 console was reconnected at 115200 baud and
its reader window reopened. The Pi had booted into headless system user 0; user
10 was stopped and `sys.boot_completed` was initially empty. A runtime
`am switch-user 10` completed boot. SSH at PI_IP:2222 then confirmed
user 10 running, `sys.boot_completed=1`, Launcher focused, and
`dumpsys activity lastanr` reported no ANR. Rechecked about 20 seconds later;
the same Launcher process and focus remained. This is evidence of a stable
short observation window, not yet a reboot-to-desktop fix.

Chrome was reproduced from the live session. Its first run aborted natively
after ANGLE failed to create an ES 3.0 context (`EGL_BAD_ATTRIBUTE`,
“Requested version is not supported”); Chromium then logged “GPU process isn't
usable.” SurfaceFlinger separately reports Broadcom V3D 7.1.10.2 and Mesa
OpenGL ES 3.1, so the failure is in Chrome's ANGLE/EGL initialization path, not
evidence that the Pi GPU is absent. Other first-boot startup ANRs were recorded
for Google Search interactor, Google Search app, and Play Store, each with
“failed to complete startup”; the launcher itself had no new ANR after the
user switch.

A second Chrome launch with a temporary `/data/local/tmp/chrome-command-line`
containing `--disable-gpu` failed earlier while loading Trichrome's
`libmonochrome_64.so`: Android's linker reported only 7,991,296 bytes reserved
where 209,317,888 were required. The temporary flag was cleared after the
test. This second failure is distinct from the reproduced ANGLE failure; it
means the GPU workaround is not validated. Chrome remains unresolved.

The TPM-related `gscd` abort is confirmed on a five-second restart loop because
`/dev/tpm0` is absent; it floods crash logs but is separate from the captured
Chrome EGL failure. Keep it separate from UI ANRs unless further traces show a
shared system-server stall. The live log window is tailing
`work/pi-uart-live-20261104.log`; SSH diagnostics work with the pinned host key.

## Chrome follow-up: resolved startup via GLES backend

See [chrome_angle_gles_fix.md](chrome_angle_gles_fix.md). Chrome now starts
with its persistent OpenGL ES ANGLE selection and retains V3D acceleration
after removal of temporary debug settings and a cold app restart. The earlier
linker-reservation interpretation above is unconfirmed: the second attempt
also ended in the same GPU-unusable abort, and its command-line flags were not
verified as read. The final fix uses a Chrome preference, not software rendering.
