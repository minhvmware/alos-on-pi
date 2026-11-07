> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# Raspberry Pi 5 Android 17 baseline validation

Status: **PASS** (M0 baseline)
Date: 2026-10-26
Device: Raspberry Pi 5 Model B Rev 1.1, boot from USB SSD (Hynix V2 55.9 GB, RTL9201)
Host: Fedora 44, ADB 37.0.0p1

## Image

| Item | Value |
|---|---|
| Image | `AOSP17-20260702-KonstaKANG-rpi5.img` |
| Source | KonstaKANG, based on Raspberry Vanilla device tree |
| SHA256 | `a83cf6f9cd596d0fd33063ad6095d6ab42762c88ded11ab58be15a51ebf1c179` |
| Size | 15,360,000,000 bytes |
| Boot mode | USB (`dtoverlay=android-usb`, `android-sdcard` disabled) |

Partition layout on `/dev/sda`:

```text
sda      55.9G
├─sda1    128M vfat  boot
├─sda2      1K
├─sda3   10.8G ext4  userdata
├─sda5      3G ext4  /        (system)
├─sda6    384M ext4  vendor
├─sda7     16M ext4  metadata
```

## Software identity

```text
ro.build.fingerprint=Raspberry/aosp_rpi5/rpi5:17/CP2A.260605.016/eng.tuomas:userdebug/dev-keys
ro.build.version.release=17
ro.build.version.sdk=37
ro.build.type=userdebug
ro.product.device=rpi5
ro.board.platform=bcm2712
ro.soc.model=BCM2712
uname: Linux localhost 6.18.26-gd03813ae6d7f-v8 #1 SMP PREEMPT ... aarch64
```

## Validation results

| Area | Result | Evidence |
|---|---|---|
| Cold boot | PASS | reboot, `sys.boot_completed=1` after ~1 min |
| ADB over Wi-Fi | PASS | `PI_IP:5555`, device online |
| Wi-Fi | PASS | `TEST_WIFI_5G`, 5 GHz, 802.11ac, 234/130 Mbps, IP PI_IP |
| GPU | PASS | `GLES: Broadcom, V3D 7.1.10.2, OpenGL ES 3.1 Mesa 26.1.4` |
| Display | PASS | HDMI `G2411P`, HWC display 0 |
| Bluetooth | PASS | `cmd bluetooth_manager enable` -> State ON |
| Audio | PASS | speaker + HDMI routes present |
| Thermal | PASS | skin ~30.1 °C, thermal status 0 |
| Crash buffer | PASS | empty after boot |
| ANR/FATAL scan | PASS | none |
| SELinux | permissive | expected for this prebuilt |
| Storage | PASS | `/data` 10 GB, `/` 2.9 GB (53% used) |

## Notes

- This is a prebuilt KonstaKANG image, not a self-built Raspberry Vanilla image.
- SELinux is permissive and userdata encryption is disabled in this build.
- The image is suitable as a known-good baseline for hardware validation and for
  starting the AluminiumOS userspace port.
- Keep the original zip/image for rollback before any partition experiment.

## Reproduce checks

```bash
ADB=/path/to/hoshinoos/aluminium-rpi5/toolchain/fedora-android-tools/usr/bin/adb
$ADB connect PI_IP:5555
$ADB -s PI_IP:5555 shell getprop ro.build.fingerprint
$ADB -s PI_IP:5555 shell dumpsys SurfaceFlinger | grep -m1 GLES
$ADB -s PI_IP:5555 shell cmd wifi status
$ADB -s PI_IP:5555 shell logcat -d -b crash -t 100
```
