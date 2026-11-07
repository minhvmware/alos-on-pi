> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# Task Manager serviceability trial — 2026-11-04

## Reproduced failures

`com.google.android.factory.taskmanager/.MainActivity` initially throws
`android.os.RemoteException: Failed to bind to
vendor.google.desktop.serviceability.VendorServiceabilityService`.
The vendor provider package was absent from the Pi image, while the framework
JAR and `com.android.desktop.serviceability` system service were present.

Inspected the original provider APK manifest and DEX. It is a Java statistics
provider using the system shared UID, with no bundled native libraries. CPU
usage is read from `/proc/stat`; other generic metrics use procfs/sysfs.
Installed the original, unmodified signed APK for user 10:

```sh
pm install --user 10 /data/local/tmp/vendor-serviceability-trial.apk
```

Package Manager accepted its signature/shared UID. The provider now binds and
runs as `u:r:system_app:s0`. Task Manager then hits a different failure:
`java.nio.file.AccessDeniedException: /proc/stat` in the provider, followed by
a null `CpuUsageStats` dereference in `ServiceabilityManager.fetchCpuUsageInfo`.
The original vendor policy has a dedicated `serviceability` app domain with
read access to `proc_stat`, `proc_vmstat` and sysfs. That domain was not part
of the replacement Pi vendor policy. Installing the APK alone is insufficient.

## Prepared patch

`patches/sepolicy/rpi-serviceability.cil` defines a dedicated app domain with
read-only CPU/memory/sysfs statistics access. An exact package entry in
`system_ext_seapp_contexts` assigns it to the original provider installed in
userdata. The patch includes app runtime and shared-system-UID data-directory
permissions, without giving proc-stat access to every system app.

No proprietary hardware executables, native vendor drivers, permissive domain,
fabricated CPU counters or app re-signing are included. The original provider
APK remains installed in user 10's userdata for the next boot.

Prepared image: `work/m8-p5-serviceability-trial.img` from the M7 image.
Preparation tool: `tools/prepare_serviceability_trial.py`.
The tool appends the CIL, updates Android's required policy-cache metadata,
adds the exact package mapping, preserves root:root/0644 and Android labels,
compares file contents and runs e2fsck. Policy cache metadata is not disk SHA
verification. The seapp file must retain `seapp_contexts_file`, while the CIL
uses `sepolicy_file`.

Checks completed on the candidate:

- Combined policy compiles with runtime-compatible `secilc -N`, version 30.
  The existing mixed-image baseline already needs `-N`; this does not establish
  that full policy neverallow validation passes.
- Compiled policy contains no permissive types. Queries confirm proc-stat read
  for the dedicated domain, zygote transition support and app-data traversal.
- `checkseapp` with policy type validation accepts the combined platform,
  system_ext, product and Pi vendor seapp selectors.
- Candidate filesystem check passes. Source M7 image was not modified.

Build the checkseapp validator used by the preparation tool:

```sh
gcc -DLINK_SEPOL_STATIC -DHAVE_REALLOCARRAY -DPCRE2_CODE_UNIT_WIDTH=8 \
  -ffunction-sections -fdata-sections -Wl,--gc-sections \
  -I aosp-rpi5/external/selinux/libsepol/include \
  -I aosp-rpi5/external/selinux/libsepol/src \
  -o aluminium-rpi5/work/taskmanager-review/checkseapp \
  aosp-rpi5/system/sepolicy/tools/check_seapp.c \
  aosp-rpi5/external/selinux/libsepol/src/ebitmap.c \
  aosp-rpi5/external/selinux/libsepol/src/hashtab.c -lsepol -lpcre2-8
```

The extra two libsepol objects provide private helper symbols used by AOSP's
validator; unused sections are discarded. `LINK_SEPOL_STATIC` is required to
enable its type checks, although the remaining public API links libsepol.so.

## Remaining physical validation

The running SSH/UART console is UID 2000 and cannot change the root-owned
system policy or seapp file. The candidate has not been applied to the physical
SSD. Apply its three small metadata/config changes after the Hynix SSD is
host-attached, using identity/mount checks and journal recovery before edits.
Do not rewrite the entire image or userdata. Preserve the already installed APK.

On the next boot verify the provider's `rpi_serviceability` context, open
Task Manager, observe changing CPU/memory/process data and capture any further
denials or exceptions. The running Task Manager is still unresolved until that
boot check; further hardware-specific metric adaptation may be necessary.

## Applied to the physical SSD

2026-11-04: applied the three-file patch to `/dev/sda5` on Hynix V2 USB SSD
serial `YOUR_SSD_SERIAL`. All its partitions were unmounted. Recovered
the p5 journal before edits and confirmed the original CIL, mapping and seapp
contents matched the reviewed M7 base byte for byte. Backups are under
`work/m8-on-disk-backup/`; execution log is `work/apply-m8-disk.log`.
Readback contents, root ownership, mode and Android labels passed; e2fsck
passed and writes were flushed. Userdata, including the installed original
provider APK, was preserved. Physical boot and Task Manager validation remain
pending; the patch is not yet a confirmed runtime fix.

## M8 physical boot and follow-up

The board booted, but remained in HSUM user 0 with user 10 stopped, as it did
before M8. UART `am switch-user 10` brought `sys.boot_completed=1` and SSH
back online. Set the shell-supported override
`persist.user.hsum_boot_strategy=0`; readback is 0. Framework source maps this
to the previous foreground user strategy instead of the configured strategy 1
(system user after provisioning). Its next-reboot behavior still needs checking.

The provider now runs as `u:r:rpi_serviceability:s0`, confirming the M8 context
mapping is used. Task Manager passes its previous CPU-stat failure, then fails
in `getProcessMemoryUsage`: `Failed to get IDesktopServiceabilityService`.
Live log proves system_server's earlier `add` was denied against
`default_android_service` for the exact endpoint
`com.android.server.desktop.serviceability.IDesktopServiceabilityService/default`.
The original vendor service_contexts named this endpoint; Pi's replacement
vendor lacked it. This is not a missing implementation: the existing framework
attempted to publish it.

Also captured MLS traversal denials for the provider's user-10 system-data
parent. Prepared `patches/sepolicy/rpi-serviceability-memory.cil` to give the
specific system-UID provider the MLS trust its user-data traversal requires,
and to define an explicit memory-service type. Added a single endpoint mapping
and scoped add/find rules; no default_android_service permission was granted.

`tools/prepare_serviceability_followup.py` generated
`work/m9-p5-serviceability-memory.img` from M8. Policy compilation with the same
runtime `-N` limitation, seapp type validation, permission queries, zero
permissive types, content/metadata readback and filesystem checks pass. The
three changed files are platform CIL, platform service_contexts and Android's
policy-cache metadata. Apply tool accepts the reviewed follow-up directory:

```sh
python3 aluminium-rpi5/tools/apply_serviceability_files.py /dev/sda5 \
  aluminium-rpi5/work/m9-on-disk-backup \
  --stage aluminium-rpi5/work/m9-p5-serviceability-memory.patch-files
```

Run under the existing GUI sudo-password workflow after power-off and host
attachment. Source guards now require the current M8 bytes. Userdata and its
installed provider stay intact. M9 is prepared, not yet applied or boot-tested.
Evidence from M8: `work/taskmanager-review/m8-live-memory-endpoint.txt`.

## M9 applied — 2026-11-06

Applied the reviewed M9 three-file patch to the host-attached Hynix USB SSD
(serial YOUR_SSD_SERIAL), /dev/sda5. The tool confirmed identity, all
partitions unmounted, recovered the journal, and matched the M8 source guards
before mutation. Original files are in work/m9-on-disk-backup/. Content,
metadata and labels read back correctly; filesystem check passed and writes
were flushed. Log: work/apply-m9-disk.log. Userdata was preserved. Physical
boot and live Task Manager validation are still pending.

## M9 physical validation — 2026-11-06

Boot automatically selected user 10 with sys.boot_completed=1; no manual user
switch was issued on this boot. Wi-Fi DHCP address changed to PI_IP.
The process-memory endpoint is now found. Original provider runs in
rpi_serviceability and Task Manager remains in the foreground without a new
crash in its exit history during this check. Screenshot
work/m9-taskmanager-160.png shows the real BCM2712 four-thread CPU graph,
user/system percentages, memory/cache/free/swap values and a process table
with per-process memory and CPU figures. This resolves the reproduced startup
crash; long-duration app stability and destructive End task actions were not
tested. DPI override was changed from 120 to the user's requested 160.
