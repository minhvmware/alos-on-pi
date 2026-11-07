> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# Audio extension label repair — 2026-11-04

After the SystemSuspend label fix, user reports a movable mouse cursor on a
black screen. Evidence: work/boot-review-suspend-20261104/, captured read-only
from Hynix SSD. Journal recovery was performed on userdata-copy.img only.

## Confirmed progress and next blocker

ANR anr/anr_2026-09-29-16-43-08-990 includes the SystemSuspend process
(/system/bin/hw/android.system.suspend-service, line 4045). System_server is no
longer blocked acquiring its initial suspend blocker. Its main thread now waits
in AudioService construction for IAudioPolicyService (lines 149–181).

The same ANR shows audioserver's main thread waiting in
HalAdapterVendorExtensionWrapper::getService (lines 2740–2758). The reference
source, frameworks/av/media/libaudiohal/impl/DevicesFactoryHalAidl.cpp, waits
for android.media.audio.IHalAdapterVendorExtension/default when
ro.audio.ihaladaptervendorextension_enabled is true.

Aluminium supplies the extension binary:
/system_ext/bin/hw/android.hardware.audio.parameter_parser.android-desktop.
Its init rc declares audio_parameter_parser_service in class core. The file is
labelled system_file, but shipped system_ext_file_contexts requires
audio_vendor_parameter_parser_exec. The compiled policy has the matching init
domain transition. This is another concrete consequence of the escaped-regex
prefix bug in the old relabelling script.

## Repair and validation

Rather than disabling audio, restore the labels from the shipped platform,
system_ext and product file_contexts using libselinux's matching implementation.

The corrected audit uses debugfs ea_get: ea_list truncates long xattr displays
and must not be used to infer absent labels. On the m3 image, the full-value
audit finds 23 differences among 4,995 paths, including the audio parser,
several other executable entrypoints and configuration files. The earlier
178-candidate report overstated the count because of that display limitation.

Prepared copy: work/m4-p5-labels-validated.img. After repairs, a fresh audit
finds zero differences and zero unmatched paths; e2fsck passes. Filesystem
content, uid/gid/mode, policy rules and vendor HAL libraries remain unchanged.

Applied the 23 metadata corrections directly to /dev/sda5 after checking the
Hynix serial, USB transport, mount state, partition size and all original
labels. Recovered the pending system journal first. Read back every corrected
xattr and ran e2fsck successfully (5,006 inodes / 1,298,797 blocks). Flushed
writes; no full image rewrite or SHA readback. Application evidence:
work/fix-labels-disk.log.

Boot test pending. Need verify that audio_parameter_parser_service registers,
audioserver publishes audio policy service and system_server passes AudioService
initialization. Desktop/SystemUI success is not yet established. Automatic
diagnostic logs are still absent even after userdata journal recovery; ANRs and
tombstones provide the evidence used here.
