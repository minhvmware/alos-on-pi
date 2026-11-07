> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# SystemSuspend label trial — 2026-11-04

## New runtime evidence after allocator policy trial

User observed animated Googlebook logo followed by black screen. The new
userdata capture is `work/boot-review-mapper-20261104/`. The original SSD was
read only during capture; journal replay was performed on userdata-copy.img.

Readable current tombstones show repeated gscd failures for missing /dev/tpm0.
No new gpuservice abort was found in that retained set; this is not proof that
gpuservice never crashed, because the tombstone ring overwrites old reports.

ANR `recovered/anr/anr_1970-01-01-00-07-22-712:150` shows system_server main:

    AServiceManager_waitForService
    getSystemSuspendServiceOnce
    acquire_wake_lock
    nativeAcquireSuspendBlocker
    PowerManagerService.<init>
    SystemServer.startBootstrapServices

Watchdog reports blocked main handler (15s/65s), repeatedly. The native stack
is direct evidence of framework waiting on SystemSuspend, rather than a
launcher-only failure. ANRs contain SurfaceFlinger running its message loop,
plus allocator and composer process stacks. Display composition is active at
least to that extent; complete UI/display correctness remains unproven.

`/local/tmp`, bootstat and dropbox remain empty after journal recovery, so the
new diagnostics still have not produced files. Their execution needs separate
runtime evidence; do not rely on automatic shutdown or capture completion.

## Root cause and smallest change

The image labels /system/bin/hw/android.system.suspend-service as system_file.
The shipped platform file_contexts requires system_suspend_exec. Policy
contains `type_transition init system_suspend_exec:process system_suspend`
but no corresponding transition for system_file. Init's executable-context
check refuses a service without a domain transition.

Old work/relabel-ext4.py calculated the number of decoded prefix characters,
then sliced the raw regex by that number. For escaped dots this left backslashes
in the startswith prefix, incorrectly excluding the specific file_contexts rule.
That helper now decodes the literal prefix itself; an escaped Android service
path regression check passes. The preferred new audit uses libselinux's own
file_contexts matching via tools/audit_image_labels.py.

The first audit produced 178 candidates, but ea_list omits values longer than
40 bytes, causing false missing-label reports. The audit was corrected to use
ea_get. A later full-value audit on the SystemSuspend trial found 23 remaining
label differences (work/label-audit-fullvalues-20261104/). Those remaining
differences were not applied in the initial single-file SystemSuspend trial.
FUSE's SELinux xattrs may be substituted by the host, so the audit reads actual
image xattrs through debugfs rather than getxattr on the mount.

Only SystemSuspend's security.selinux xattr is changed in this trial. The
offline copy work/m3-p5-suspend-label-trial.img passes e2fsck and reads back
system_suspend_exec. No new allow rules or permissive domains are added.

Disk application checks the Hynix serial, USB transport, no mounted partitions,
partition size, and previous diagnostic rc contents. Recover pending journal
before modifying ext4 metadata, apply the xattr, flush, inspect the new label
and run filesystem check. No full image rewrite and no SHA readback.

Next boot must establish that SystemSuspend registers and system_server passes
PowerManagerService initialization. Other desktop/TPM dependencies may remain.

Applied to SSD 2026-11-04: pending system journal recovered, xattr updated to
system_suspend_exec, post-change e2fsck clean (5,006 inodes / 1,298,797 blocks),
write flushed. Evidence: work/fix-suspend-label-disk-final.log. No SHA reader
was started. Physical boot test remains pending.
