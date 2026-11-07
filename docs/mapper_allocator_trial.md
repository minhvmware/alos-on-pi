> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# Pi graphics allocator trial — 2026-11-04

## Evidence and diagnosis

`work/boot-review-20261104/tombstones/tombstone_48:1691` contains the
log preceding the abort: `isDeclared` for
`android.hardware.graphics.allocator.IAllocator/default` returns EX_SECURITY,
with `SELinux denied for service`. Gralloc5 therefore reports unloaded, the HIDL
fallback has no hwservicemanager, and `GraphicBufferMapper` aborts.
This is a confirmed cause of gpuservice crashing; whether it explains the entire
stuck-logo failure requires another boot.

The Pi allocator APEX contains both allocator AIDL v3 and native mapper v5
manifests, plus `lib64/hw/mapper.minigbm_gbm_mesa.so`. Copying or replacing Mesa
libraries is not justified by the evidence.

The Aluminium platform CIL omits gpuservice from
hal_graphics_allocator_client. Its gpu_sphal_domain membership alone does not
grant the allocator/mapper service lookup permissions.

## Change

`patches/sepolicy/gpuservice-allocator-client.cil` implements the existing
Treble `hal_client_domain(gpuservice, hal_graphics_allocator)` macro: client
attributes and matching memfd rules. Upstream source equivalent is to add that
macro invocation in system/sepolicy/private/gpuservice.te.

`tools/prepare_mapper_trial.py` patches a copy of the ext4 system image, updates
the platform policy/mapping SHA256, and verifies replacement contents, modes,
owners and labels. Input image remains unchanged.

The old zzz init diagnostics used shell commands without an explicit seclabel.
Init rejects a service when context computation produces no domain transition;
the original policy has no init→shell transition rule inferred from shell_exec.
This is a source-based explanation for the empty capture directory, not a
runtime-confirmed diagnosis. The replacement diagnostics explicitly use shell
domain (existing init→shell transition permission), shell UID, and a directory
created/relabelled by init. They collect rolling logcat and five minutes of
service/process snapshots under /data/local/tmp/portdiag. No manual suspend
launch, early_hal override or scheduled shutdown remains in this diagnostic rc.

## Offline validation

- Baseline and modified combined platform/system_ext/product/vendor policy
  compile at policy version 30 with the same `-N` option used by Android init.
- A full neverallow check of the unmodified mixed user/userdebug baseline fails
  on existing vendor debug rules. This trial does not claim a production policy
  build passes neverallow checks.
- sesearch: baseline has no gpuservice→allocator service find rule; patched
  policy grants allocator and mapper lookup, and Binder call to allocator server.
- Patched combined policy has zero permissive types.
- The CIL in the prepared image matches the compiled trial input.
- Filesystem check passes; four replaced/added files are root:root, 0644,
  system_file, and read back byte-for-byte correctly.

Output: `work/m2-p5-allocator-trial.img` (8 GiB, system partition only).
Boot validation pending: compare gpuservice state/crashes, allocator registration,
SurfaceFlinger, system_suspend and sys.boot_completed. The TPM failure remains
unmodified in this trial to keep the graphics change separately observable.

## Flash trial

2026-11-04: Wrote all 8,589,934,592 bytes to Hynix V2 serial
YOUR_SSD_SERIAL, /dev/sda5. dd completed successfully with conv=fsync
(349.562 seconds); disk flush completed. Full readback hashing was started by
the original script; user subsequently said checksum comparison is unnecessary.
Boot testing can proceed once the write/flush has completed. Userdata and vendor
were not written. Result pending physical boot on Pi.
