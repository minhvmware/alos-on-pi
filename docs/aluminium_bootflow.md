> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# AluminiumOS — boot flow từ image thật

## Boot images

| Image | Header | Nội dung đọc được |
|---|---|---|
| `boot.img` | Android boot header v4 | kernel 20,445,831 byte; ramdisk size 0; cmdline rỗng; os_version `17.0.0`, patch `2026-09` |
| `init_boot.img` | Android boot header v4 | kernel size 0; generic ramdisk 2,724,177 byte; os_version `17.0.0`, patch `2026-09` |
| `vendor_boot.img` | vendor_boot header v4 | vendor ramdisk tổng 29,726,581 byte, hai fragment: `vendor_ramdisk00` (type 0x1, 5,459,125 byte) và `vendor_ramdisk01` (type 0x2, name `recovery`, 24,267,456 byte); vendor cmdline Qualcomm/desktop; bootconfig 147 byte |
| `pvmfw.img` | Android boot header v3 | protected VM firmware kernel 850,176 byte, ramdisk 0, os_version `17.0.0` |

`boot.img` không có ramdisk là cấu hình GKI bình thường: generic ramdisk nằm ở `init_boot.img`, vendor ramdisk ở `vendor_boot.img`. `vendor_ramdisk01` được đánh type recovery và chứa `init.recovery.*.rc`, policy recovery và `modules.load.recovery`; normal boot dùng `vendor_ramdisk00`.

## Kernel

`boot.img` kernel là LZ4; sau `magiskboot decompress`:

```text
Linux version 6.12.81-android16-6-g08dd7534bf44-ab16287118-4k
(kleaf@build-host) ... clang 19.0.1, LLD 19.0.1
#1 SMP PREEMPT Tue Sep 8 10:57:08 UTC 2026
```

- `file`: `Linux kernel ARM64 boot executable Image, little-endian, 4K pages`.
- IKCONFIG extract được 224,763 byte.
- Config quan trọng: `CONFIG_ARM64_4K_PAGES=y`, `CONFIG_LOCALVERSION="-4k"`, `CONFIG_PREEMPT=y`, `CONFIG_MODVERSIONS=y`, `CONFIG_MODULE_SIG=y`, `CONFIG_MODULE_SIG_ALL=y`, `CONFIG_ANDROID_BINDER_IPC=y`, `CONFIG_SECURITY_SELINUX=y`, `CONFIG_DEBUG_INFO=y`.
- `system_dlkm` có 111 module, `vendor_dlkm` có 200 module. Vermagic duy nhất:
  - `6.12.81-android16-6-g9d9ec4d18995-ab16464475-4k SMP preempt mod_unload modversions aarch64` (200 module vendor)
  - `6.12.81-android16-6-g08dd7534bf44-ab16287118-4k SMP preempt mod_unload modversions aarch64` (111 module system)

Pi baseline dùng kernel manifest `common-android17-6.18-lts` và device config chọn 16 KiB pages. Khác major/minor, khác localversion, khác page size và `CONFIG_MODVERSIONS`: không thể boot kernel Aluminium bằng boot flow Pi, và không thể nạp module Aluminium vào kernel Pi. Kernel Pi 6.18 phải được giữ và build lại vendor modules/hal theo nó.

## Vendor ramdisk và first-stage

- `vendor_ramdisk00/first_stage_ramdisk/fstab.android-desktop` giống bản trong `vendor/etc/fstab.android-desktop`, gồm `logical`, `first_stage_mount`, `slotselect`, `avb=vbmeta`.
- `init_boot` ramdisk chứa `init` generic; không chứa `init.rc` bình thường vì system/vendor cung cấp tiếp.
- `vendor_ramdisk01` recovery chứa `sepolicy`, `plat_*_contexts`, `vendor_*_contexts`, `init.recovery.android-desktop.rc`, `init.recovery.qcom.rc`.
- Bootconfig chỉ có:

```text
androidboot.baseband=apq
androidboot.hardware.platform=android-desktop
androidboot.hardware=android-desktop
androidboot.load_modules_parallel=true
```

Không có `androidboot.selinux=...`, không có `androidboot.verifiedbootstate`, không có `slot_suffix` trong các file static. Các giá trị này chỉ có ở runtime hoặc do bootloader truyền.

## AVB

`vbmeta.img` dùng `SHA256_RSA4096`, rollback index 1339, descriptor cho boot/init_boot/vendor_boot/dtbo/pvmfw và hashtree cho các partition EROFS/FAT. `avbtool verify_image` xác minh thành công mọi descriptor bằng embedded key. Điều này chứng minh image tự nhất quán, không chứng minh Pi bootloader có key này.

## So với Raspberry Pi 5

| Thành phần | Aluminium | Pi baseline |
|---|---|---|
| Boot container | `boot.img` Android v4 + `init_boot` + `vendor_boot` + `vbmeta` | `boot.img` FAT32 chứa `Image`, `ramdisk.img`, DTB, overlays; không có Android boot header |
| Kernel | 6.12.81 GKI, 4K pages, LZ4 | 6.18 LTS, 16K pages |
| Modules | vendor/system_dlkm vermagic 6.12.81-4k | build cùng kernel Pi 6.18/16K |
| Ramdisk | generic ở `init_boot`, vendor ở `vendor_boot` | `ramdisk.img` trên FAT boot |
| AVB | chained vbmeta bắt buộc theo fstab | không cấu hình trong device/packaging source |
| Slot | `slotselect` trong fstab, OTA A/B | không slot |

Kết luận: boot chain Aluminium không thể chạy trên Pi. Baseline Pi phải boot bằng firmware FAT + kernel 6.18 trước; sau đó mới thử mount userspace Aluminium bằng fstab/init phù hợp Pi.

## Chưa xác nhận runtime

Chưa có UART, dmesg, `ro.boot.*`, `lpdump`, `dm-verity` state hay logcat từ thiết bị Aluminium gốc hoặc Pi. Mọi kết luận “boot thành công” vẫn trống.
