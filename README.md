# HoshinoOS — AluminiumOS on Raspberry Pi 5

Experimental ARM64 port using AluminiumOS Android 17 framework/desktop with
the Raspberry Vanilla Pi 5 vendor/BSP, Linux 6.18 and Mesa V3D/V3DV.

## Download and run

Get the bootable development image from
[Releases](https://github.com/minhvmware/alos-on-pi/releases), then follow
[download, flash and SSD expansion](docs/INSTALL.md). GitHub's automatic source
ZIP is not the OS image. Download every numbered image part when a release is split.

The snapshot is based on the installation tested on Pi5, with fresh data/metadata
and personal SSH access removed. Its compact/sanitized assembly has not yet had
a separate physical boot test, so it is a development prerelease. Desktop ANRs,
Chrome Vulkan compatibility and several hardware profiles remain unfinished.

For development, start at [DEVELOPMENT.md](docs/DEVELOPMENT.md), which lists
actual inputs and commands to create policy tools/vendor inputs, restore file
metadata, use UART, provision your own SSH keys and package a release.

The Git source tree contains project scripts, patches and research notes.
Images belong in Release assets; OS inputs, extracted files, AOSP checkouts,
toolchains, credentials, logs and SSD backups stay outside Git. A complete
Aluminium framework source build is not provided; historical M-stage trials
are guarded integration steps, not a one-command source OS installer.

## Status — 2026-11-07

- Aluminium desktop, USB input and Wi-Fi booted on Pi 5 with hardware V3D GLES.
- Task Manager provider and audio/codec FMQ SELinux fixes validated before reset.
- Bluetooth enabled with no crashes during the observed session; full profile
  coverage, pairing and audio remain to be tested.
- Native V3DV Vulkan device/queue/readback and app surface/swapchain presentation
  passed. Chrome ANGLE Vulkan ES3 compatibility remains unresolved; Chrome157
  uses the documented hardware GLES configuration.
- YouTube playback was reported normal before reset; wider app/ANR stability
  and video performance remain under investigation.
- CPU schedutil tested at unchanged 1.5–2.4 GHz limits. No overclock or measured
  performance gain is claimed. USB SSD negotiated only USB2 on both Pi and host.
- Offline factory reset completed with backups; the fresh boot, original Setup
  Wizard and app regressions still need physical validation.

See [current status and next steps](docs/STATUS.md). Older notes record the
state at each experiment and may be superseded by that status.

## Start here

| Task | Guide |
|---|---|
| Install image and use full SSD capacity | [INSTALL.md](docs/INSTALL.md) |
| Set density/mouse and Chrome workaround | [FIRST_BOOT.md](docs/FIRST_BOOT.md) |
| Develop with explicit OS inputs | [DEVELOPMENT.md](docs/DEVELOPMENT.md) |
| Repair file owners and Android labels | [FILESYSTEM.md](docs/FILESYSTEM.md) |
| Capture, sanitize and package a release | [RELEASING.md](docs/RELEASING.md) |

## Layout

- `manifests/`: pinned upstream references and analysis input identifiers.
- `device/brcm/rpi5/`: diagnostic/SSH init scripts and configuration templates.
- `patches/`: minimal graphics, policy and CPU changes; some are historical trials.
- `tools/`: image inspection, build wrappers, Vulkan probes and offline maintenance.
- `docs/`: partition/BSP research and subsystem findings.
- `work/`, `logs/`, `toolchain/`, `upstream/`: local inputs/output; gitignored.

## Local workspace

Scripts generally expect the repo beside `aosp-rpi5/` and `aluminium-analysis/`:

```text
workspace/
  aluminium-rpi5/      # clone this repository here
  aosp-rpi5/           # separately synced AOSP + Pi manifests
  aluminium-analysis/ # privately obtained/extracted Aluminium inputs
```

Read [toolchain notes](docs/toolchain.md), [build plan](docs/rpi5_build_plan.md),
[baseline validation](docs/baseline_validation.md) and
[port plan](docs/m1_port_plan.md) before using the historical integration tools.
The Pi baseline used for hardware bring-up was a prebuilt; a complete source
build was not established on the original host. Downloaded toolchains are local.

```bash
source tools/env.sh
tools/extract_aluminium.sh --check
tools/build_image.sh /absolute/path/to/aosp-rpi5
tools/build_kernel.sh /absolute/path/to/kernel-workspace
```

These examples describe separate workflows, not a one-command port installer.
Offline trials rely on specific image layouts, local extracted files and prior
patch stages. Review their guards and documentation before running them.

## Device access and maintenance

SSH templates use shell UID2000, key-only authentication and pinned host keys.
Generate your own client/server keys and known_hosts; no usable keys are bundled.
Supply the Pi IP explicitly. See [SSH notes](docs/ssh_debug_access.md).

Machine-specific serial literals were replaced by the mandatory
`HOSHINO_SSD_SERIAL` environment variable in offline maintenance tools. Confirm
the disk identity and layout yourself. Under sudo, explicitly pass only this
variable if needed. Existing size/layout/unmounted checks remain; these scripts
are tailored to the tested partition layout, not generic installers. Their
historical guards use Python assertions: do not run with `python -O`.

Keep a known-good image and private backup. Factory reset/flash/expansion tools
write storage and must not be part of an unattended build or test run.

## Distribution

See [NOTICE.md](NOTICE.md) for source and license boundaries. This repository
does not grant redistribution rights to the external OS, apps or BSP inputs.
