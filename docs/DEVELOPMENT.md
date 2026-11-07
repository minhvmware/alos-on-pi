# Developer entry points and required inputs

There are two practical paths: install the provided image, or develop against
explicit local OS inputs. See [INSTALL.md](INSTALL.md) for the first path.
The release removes the need to reconstruct old `work/` experiments just to
boot the port. Full Aluminium framework source is not part of this project;
this is image integration, not a complete open-source Android distribution.

## Linux host prerequisites

Python3; util-linux; e2fsprogs including debugfs/e2image/fuse2fs; mtools;
dosfstools; zstd; a C compiler; libselinux, libsepol and PCRE2 development
libraries; and OpenSSH client tools for optional SSH. Kernel/AOSP builds need
the separate upstream trees/toolchains documented in the pinned manifests.
Tool paths under `toolchain/` are optional local installations, not downloads
included in this repo.

## Explicit input map

| Input | Used by | How to obtain it |
|---|---|---|
| Pi baseline full disk image | hardware baseline, optional SSH binaries | Obtain the baseline described in baseline_validation.md; not the Aluminium image |
| Aluminium OTA/partition files | framework/system integration | Supply locally; identifiers in manifests/analysis-inputs.lock |
| Pi vendor ext4 partition | policy compiler inputs | Extract p6 from the Pi image with extract_disk.py |
| AOSP Android17 source | policy validators, APK/Vulkan build tools | Sync the Raspberry Vanilla manifests/revisions |
| Current port system ext4 | historical M-stage trials | Extract p5 from a release or a private matching-stage image; respect each stage guard |
| Current tested physical disk | capture_release.py | Unmounted USB disk; exact serial required; read-only source access |

Extract partitions without mount/root from a regular disk image:

```bash
python3 tools/extract_disk.py --image /absolute/path/pi-baseline.img \
  --output work/pi-baseline-parts --metadata-prefix work/pi-baseline-table

python3 tools/extract_disk.py --image /absolute/path/HoshinoOS-Pi5-20261107.img \
  --output work/release-parts --metadata-prefix work/release-table
```

## Policy tooling without a hidden workspace

```bash
bash tools/build_policy_tools.sh /absolute/path/aosp-rpi5
python3 tools/prepare_policy_workspace.py work/pi-baseline-parts/p6.img
```

These create the ignored secilc/checkseapp binaries and vendor CIL/seapp inputs
at the exact locations used by `prepare_serviceability_*` and
`prepare_media_fmq_*`. The two tools were compiled and vendor extraction was
verified during publication preparation. They require host development headers.
M-stage scripts are **historical, guarded deltas**: an M12 image already contains
the M8–M12 changes and is not an M7 input. Do not repeatedly apply all CIL files
to an existing release. Mixed user/system and userdebug/vendor policy compilation
uses `-N`; full neverallow compliance is not claimed.

## Filesystem and boot development helpers

- `fix_fsconfig.py`: reconstruct uid/gid and optionally modes from image
  fs_config blobs plus AOSP libcutils tables. It does not restore file capabilities.
- `audit_image_labels.py`: use libselinux matching to generate an xattr repair
  plan, avoiding the old hand-written regex matcher's errors.
- `fdt_fstab.py`, `fdt_set_mount.py`: inspect/edit a COPY of Android DT fstab.
  The working first-stage system mount is `/system` followed by switch-root.
- `uart_console.py`: 1152008N1 two-way serial console, Ctrl-] exits and restores
  the host terminal. Run one serial reader at a time.
- `tools/vulkan/`: source for native queue/readback and app surface probes.

Generate filesystem plans against a read-only FUSE view, **unmount it**, then
apply with debugfs. Never mutate an image while a FUSE mount holds it open.
See [filesystem workflow](FILESYSTEM.md).

## UART and optional SSH

Use an appropriate3.3V UART adapter with Pi TX to adapter RX and shared GND;
do not connect adapter5V to Pi GPIO. Hardware wiring must match the actual board.

```bash
python3 tools/uart_console.py /dev/ttyUSB0 -b 115200 -l work/uart.log
```

No personal network addresses or classpath snapshots are shipped. SSH is
opt-in and requires fresh installation-specific keys:

```bash
python3 tools/prepare_ssh_payload.py work/pi-baseline-parts/p5.img
# Make a private regular system-image COPY before installation:
cp --reflink=auto --sparse=always work/release-parts/p5.img work/p5-with-private-ssh.img
python3 tools/install_portssh.py work/p5-with-private-ssh.img
```

The prepared client/server keys and pinned known_hosts remain under ignored
work/ssh-trial/. Install that private image only on your own device using a
reviewed offline partition workflow. Do not upload it as a public release.
The image installer does not itself verify a physical block-disk identity.
Key-only shell UID2000 access does not bypass Android permissions.

After that optional endpoint is installed and tested:

```bash
tools/pi_ssh.sh PI_IP 'getprop sys.boot_completed'
python3 tools/derive_shell_classpath.py PI_IP work/port-shell-env.sh
# Explicitly install the generated fragment for this running OS only:
tools/pi_ssh.sh PI_IP 'cat > /data/local/tmp/port-shell-env.sh' < work/port-shell-env.sh
```

## Release development

[RELEASING.md](RELEASING.md) gives the exact capture/sanitize/package workflow.
Source OS construction, installing the current image and packaging a snapshot
have separate validation levels. Reproducing a new port from the original OTA
still requires the documented early integration steps; the historical notes
are not a claim of a complete unattended source build.
