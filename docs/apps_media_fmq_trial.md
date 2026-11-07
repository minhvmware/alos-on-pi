> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# Gmail/YouTube crashes and TikTok lag — 2026-11-06

User clarified TikTok plays video with substantial lag; Gmail and YouTube
crash. Do not describe all three as network/loading failures.

Reproduction log: work/apps-reproduce-live.log (227MiB; local capture ended
when Pi shut down). Gmail installed version ends .twa; YouTube is also TWA.
Log shows both launch Chrome custom tabs for mail.google.com/youtube.com.
Chrome user10 uid1010167 then aborts GPU process isn't usable, with
ANGLE Vulkan vkGetInstanceProcAddr initialization failures. This revisits
the earlier Chrome issue; the old GLES flag fix is not currently proven
persistent/working for these launches. No Gmail account data was inspected.

TikTok log contains 340039 ajvoice open failed retries. Concurrent observed
FMQ denials include hal_audio_default write tmpfs:file, mediaswcodec write
tmpfs:file, mediaswcodec read/write system_server_tmpfs:file and
appdomain_tmpfs:file. Audio retry storm plausibly contributes to lag; actual
playback/decode/frame timing and audio validation remain needed. Do not claim
it is the only cause or hardware video decode works.

Prepared M10 trial, NOT applied:

- patches/sepolicy/rpi-media-fmq-compat.cil: four explicit domain/type rules
  matching the observed denials; no permissive domains, no allow-everything.
- tools/prepare_media_fmq_trial.py builds from the current M9 reference image.
- work/m10-p5-media-fmq.img and .patch-files directory, with byte guards,
  apply-manifest.json, compiled policy, readback and filesystem check logs.
- Compiler uses runtime-compatible -N due existing mixed user/userdebug base
  neverallow incompatibilities; full neverallow validation is NOT claimed.
- This grants fallback tmpfs:file access to specific media domains, a broader
  object scope than modern memfd_file policy. Treat as development
  compatibility trial; investigate kernel/userspace memfd labeling alignment
  before making it a final production policy.

Offline application after exact USB serial and unmounted checks:

    python3 aluminium-rpi5/tools/apply_serviceability_files.py \
      /dev/sda5 aluminium-rpi5/work/m10-on-disk-backup \
      --stage aluminium-rpi5/work/m10-p5-media-fmq.patch-files

Use GUI sudo askpass; verify actual device path/serial first. Existing tool
backs up targets, checks exact source bytes and filesystem, and verifies
labels/modes/readback. No userdata rewrite/format is required.

After reboot validate Bluetooth audio provider creation, media codec queue
creation, TikTok audio and video smoothness, and whether matching denials
stop. If no improvement/other regressions, restore backed-up policy files.
Chrome/Gmail/YouTube still need separate GLES bootstrap/UI flag persistence
repair per chrome_angle_gles_fix.md and custom-tab launch validation.

Current connectivity: Pi powered down (UART final line reboot: Power down);
laptop sees neither SSD nor ttyUSB. SSH .15 no route to host. User was asked
to attach SSD for patch or boot Pi for Chrome trial. Pending response.

## Applied offline — 2026-11-06 22:36

Exact Hynix USB serial checked, SSD unmounted. M10 applied to sda5 via guarded
installer, two policy files changed. Content, root0644, SELinux labels and
filesystem check passed. Backups work/m10-on-disk-backup; apply log
work/apply-m10-disk.log. Data partition not reformatted. Installer output
was corrected to report actual number of changes and tree-based mounted
checks are now explicit.

Chrome Local State inspection confirms use-angle@1 persisted. Therefore old
GLES preference was NOT lost. Chrome was still trying the Vulkan feature
path. Added ONLY enable-vulkan@2 to browser.enabled_labs_experiments offline,
preserving the existing GLES flag and all other JSON content. This is a
trial to avoid failing Vulkan initialization inside the Chrome host of TWAs.
System Vulkan/V3DV remains untouched. Must validate TWA survival/rendering
and actual command line chrome://version after boot; no success claimed yet.

Exact Chrome150 source mapping checked:
https://github.com/chromium/chromium/blob/150.0.7871.181/chrome/browser/about_flags.cc
(kUseAngleChoicesAndroid index1 is GLES; enable-vulkan maps features::kVulkan)
https://github.com/chromium/chromium/blob/150.0.7871.181/components/webui/flags/feature_entry.cc
(feature value options Default/Enabled/Disabled, index2 disabled).
Downloaded copies are under work/chrome-150-*.cc.

Tool tools/patch_chrome_vulkan_pref.py guards device/flags, backs up profile
Local State, writes the existing inode, checks unchanged ownership/mode/
SELinux label and semantic equality of all other JSON, unmounts and checks
filesystem. Backup work/chrome-vulkan-pref-20261106-223842 (private profile
metadata, keep local); it contains Local State.before and Local State.after.
Userdata fsck clean before and after. SSD flushed. To roll back the Chrome
trial, restore the backed-up Local State before starting Chrome, or remove
only enable-vulkan@2 using Chrome UI after boot. Roll back policy via the
M10 file backups if a regression is identified.

## M10 physical boot and M11 follow-up — 2026-11-06 22:45

Boot completed1 and SSH reachable. Bluetooth still OFF with nine recorded
crashes; latest matching fatal remains openProvider A2DP software encoding.
Matching FMQ denials have advanced from write to map. Counts in captured
m10-runtime-all.log:42 audio tmpfs map;16 mediaswcodec system_server_tmpfs map;
14 mediaswcodec tmpfs map;12 mediaswcodec appdomain_tmpfs map (duplicated
logcat/audit messages possible). No claim Bluetooth works from M10.

Prepared NOT APPLIED M11: patches/sepolicy/rpi-media-fmq-map.cil adds map
only on the four M10 source/target pairs. tools/prepare_media_fmq_map_trial.py
requires M10 marker, appends these rules, compiles runtime-compatible policy,
produces guarded manifest and checks content/metadata/filesystem. Output
work/m11-p5-media-fmq-map.img and matching .patch-files. Same -N/base policy
limitation applies. Need SSD at laptop to apply with existing guarded tool
and a fresh m11-on-disk-backup directory; then boot and Bluetooth validation.

UART now reader session20139 on /dev/ttyUSB0 at115200, log
work/pi-uart-m10-20261106.log. Visible kitty tails file (session93405).
Console helper now puts its own terminal stdin into raw mode and restores
it on exit; Ctrl-C reaches Pi instead of terminating the reader. Actual
Ctrl-C recovery plus echo marker and getprop returned marker and1. Only one
serial reader runs. Initial garbled input was cleared; live lines readable.

## M11 applied — 2026-11-06 22:57

User reattached the expected Hynix USB SSD, all partitions unmounted.
Guarded apply tool matched current M10 source bytes and applied M11's two
policy files. Content/owner/mode/SELinux label verification and final e2fsck
passed. Sync and block-device flush completed. Backups:
work/m11-on-disk-backup; log work/apply-m11-disk.log. Userdata not modified.
Need physical reboot to validate Bluetooth ON, audio provider and codecs.

## M11 boot / M12 prepared — 2026-11-06 23:00

UART remained live and confirmed sys.boot_completed=1. Bluetooth still aborts;
new denials are hal_audio_default tmpfs:file read, after M11 map checks passed.
M11 was insufficient. Policy inspection found hal_audio_default/tmpfs and
mediaswcodec/tmpfs only had write/map. Other two codec pairs had read/write/map.

Prepared M12 NOT APPLIED: rpi-media-fmq-access.cil explicitly supplies the
standard shared-memory access set read/write/getattr/map on the SAME four
pairs; getattr covers shared-memory size queries. No additional domains or
object types and no execute/create/unlink grants. Inspected compiled policy
with SETools to assert all four permissions and absence of those other grants
on each pair. Compiler/readback/metadata/fsck passed, same -N baseline caveat.
Tool prepare_media_fmq_access_trial.py requires M11 marker and rejects M12.
Image work/m12-p5-media-fmq-access.img and matching .patch-files.

User chose to keep using Pi and has NOT moved SSD yet. Do not shut Pi down
or change the running image. UART reader session20139 and kitty tail remain
active. Apply M12 only after SSD attached/unmounted with exact serial, through
apply_serviceability_files.py and fresh m12-on-disk-backup. Then verify real
Bluetooth ON and provider operation, not just boot/property state.

## M12 applied — 2026-11-06 23:03

Actual Hynix SSD reattached, exact serial/unmounted/source guards passed.
Applied two policy files with backup work/m12-on-disk-backup and log
work/apply-m12-disk.log. Content readback, root0644, SELinux labels and final
filesystem check passed; synced/flushed. Userdata and Chrome unchanged.
Need physical boot to validate Bluetooth and media; no runtime success claim.

## M12 physical validation — 2026-11-06 23:09–23:14

Pi sys.boot_completed1, desktop user10. Bluetooth automatically reached ON
in~3.7seconds; ON uptime8m33s with0 crashes at last check. Captured full boot
log m12-runtime-all.log contains0 audio/codec FMQ denials,0 audio-open retry
messages and0 A2DP FetchAudioProvider fatal messages. TikTok was not yet
replayed during that capture, so no frame-rate or playback cure claimed.
Bluetooth pairing/audio hardware tests still pending user/phone action.
Evidence m12-bt-runtime.txt and m12-bt-final-state.txt.

Gmail/YouTube wrappers launch, but Chrome host STILL crashes. Installed Chrome
is now157.0.8103.38 (updated /data APK, libchrome.so); baseline was150.0.7871.181.
Exact failure still GPU process isn't usable. New native-only sandboxed child
uses Android zygote_next. Do not assume why it fails without deeper capture.
Temporary persistent-debug-app + GLES/Vulkan-disabled CLI bootstrap also did
not produce a surviving browser; command-line consumption was not verified.
Removed active command-line file to chrome-command-line.m12-trial-backup and
cleared debug_app afterward. No profile clearing or update removal performed.
Evidence m12-gmail-test.txt, m12-youtube-test.txt, m12-twa-postlaunch.txt,
m12-chrome-package.txt, m12-chrome157-bootstrap*.txt.

UART USB reconnect changed port to /dev/ttyUSB1. Granted ACL via GUI askpass;
new reader PTY4804 appends pi-uart-m10-20261106.log, existing kitty tail stays
live. Old disconnected ttyUSB0 reader was terminated. Exactly one active
serial reader should remain. User can test Bluetooth pairing now.
