> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# AluminiumOS ↔ Raspberry Vanilla Pi 5 — hardware compatibility matrix

## 0. M0 measured trên phần cứng thật (2026-10-26)

- Pi 5 boot Android 17 từ USB SSD, ADB `PI_IP:5555`, Wi-Fi 5 GHz, V3D/Mesa 26.1.4,
  Vulkan Broadcom, USB keyboard/mouse, reboot sạch. Chi tiết: `docs/baseline_validation.md`.
- VINTF thật của Pi: framework matrix tối thiểu (GNSS, sensors, media.c2/ffmpeg),
  vendor manifest chỉ khai báo GNSS + sensors; phần còn lại đến từ APEX fragment.
- So sánh tĩnh Aluminium system matrix với Pi source:
  - **232 HAL requirement**, **230 `NOT-DECLARED-IN-PI-SOURCE`**, 2 do Aluminium vendor khai báo.
  - Chủ yếu là `vendor.qti.*`, `com.android.desktop.*`, `vendor.google.desktop.*`,
    telephony/radio, NFC/ESE, camera/audio QTI.
  - Báo cáo: `reports/vintf_compare.txt`.
- Kết luận: **không thể dùng nguyên `compatibility_matrix.device.xml` của Aluminium**.
  M1 phải thay matrix bằng bản Pi-compatible (tối thiểu như baseline Pi), rồi boot thử.
- Dung lượng userspace Aluminium đã extract: system 1.7GB + product 3.1GB + system_ext 409MB
  ≈ **5.2GB**, lớn hơn p5 system 3GB của Pi. M1 cần:
  1. Convert EROFS → ext4 (hoặc mount EROFS nếu Pi kernel/fstab hỗ trợ).
  2. Gộp product/system_ext vào image system.
  3. Tăng p5 lên ~8GB và giảm userdata tương ứng (SSD 55.9GB còn dư).
- Chưa thực hiện thay đổi phá huỷ nào trên Pi; baseline image vẫn là known-good để rollback.

## Kết luận điều hướng

AluminiumOS là bản desktop Android 17 (SDK 37, arm64-v8a) cho HP Googlebook `quartz`, vendor Qualcomm `hamoa`. Raspberry Vanilla Pi 5 cũng là Android 17 nhưng vendor Broadcom `bcm2712`, kernel 6.18/16K, boot FAT và partition MBR tĩnh. Hai bên **khớp ở Android userspace level**, **không khớp ở boot/kernel/vendor/hardware**.

Điều này xác nhận hướng ban đầu: không port kernel/HAL/graphics Googlebook; giữ Pi BSP và chỉ chọn lọc system/framework/desktop. Nhưng Aluminium system mang theo yêu cầu desktop/QTI cụ thể, nên integration phải thay đổi framework matrix/product config, không chỉ thay `system.img`.

## 1. Mức tương thích

| # | Lĩnh vực | Aluminium (image thật) | Pi baseline (source) | Trạng thái | Hành động |
|---|---|---|---|---|---|
| 1 | Android release | 17, release_or_codename 17 | AOSP 17 | MATCH | Giữ cùng branch/revision khi build |
| 2 | SDK | 37 (sdk_full 37.1) | Shipping API 37 | MATCH | Kiểm tra `min_supported_target_sdk=28` |
| 3 | ABI | arm64-v8a, abilist32 rỗng | arm64-v8a, armv8-a | MATCH | Audit lại ABI sau khi build Pi |
| 4 | SoC/platform | `ro.board.platform=hamoa`, HP/quartz | `bcm2712`, Raspberry Pi 5 | INCOMPATIBLE | Không mang vendor Aluminium |
| 5 | Kernel | 6.12.81-android16-6, 4K pages, LZ4 | 6.18 LTS, 16K pages | INCOMPATIBLE | Giữ kernel Pi; bỏ kernel Aluminium |
| 6 | Kernel modules | 311 module vermagic 6.12.81-4k, modversions | build theo kernel Pi 6.18/16K | INCOMPATIBLE | Build lại mọi module Pi; không dùng module Aluminium |
| 7 | Boot container | boot v4 + init_boot + vendor_boot + vbmeta + pvmfw | FAT32 boot chứa Image/ramdisk/DTB | INCOMPATIBLE | Boot bằng firmware Pi; Aluminium boot images không dùng |
| 8 | Partition scheme | dynamic super 12 GiB, Virtual A/B, `logical`, `slotselect` | MBR tĩnh p1/p3/p5/p6/p7, không super/slot | INCOMPATIBLE | Chọn reconstruct super hoặc chuyển physical; không `dd` |
| 9 | AVB | chained vbmeta SHA256_RSA4096, hashtree bắt buộc | không AVB trong source | INCOMPATIBLE (policy) | Tắt/không dùng vbmeta Aluminium; giữ verifiedbootstate bring-up |
| 10 | Userdata/metadata | fstab yêu cầu fileencryption AES-256-XTS, checkpoint, metadata riêng | Pi p3 userdata, p7 metadata ext4 | PARTIAL | Pi đã có userdata/metadata; encryption/checkpoint cần test riêng |
| 11 | Missing physical partitions | misc, persist, modem, dsp, bluetooth, super | Pi không có | GAP | Bỏ service phụ thuộc; hoặc thêm partition nếu thật cần |
| 12 | Userspace page alignment | 2,432 ELF parse được (1,749 partition + 683 APEX) min align `0x4000`/`0x200000`; 0 ELF 4K; 11 ELF partition không trả LOAD | kernel Pi 16K | COMPATIBLE (static) | Vẫn cần boot test; APEX payload 44 EROFS + 2 ext4 |
| 13 | Graphics EGL/Vulkan | ANGLE + Adreno, `ro.hardware.egl=angle`, `vulkan=adreno` | Mesa V3D + Broadcom Vulkan | INCOMPATIBLE | Dùng Mesa/V3DV/drm_hwcomposer/minigbm Pi |
| 14 | Composer | `composer3/IComposer/default` AIDL 5 từ drm_hwcomposer | package drm_hwcomposer Pi | CANDIDATE | Build Pi HWC cùng version range FCM 4–5; checkvintf + runtime |
| 15 | Allocator | `allocator/IAllocator/default` AIDL 2 QTI | minigbm_gbm_mesa Pi | CANDIDATE | Dùng minigbm Pi, bỏ QTI allocator |
| 16 | Codec2 | AIDL 2 `default`, HIDL default/software | FFmpeg C2 instance `ffmpeg` | PARTIAL/GAP | Giữ FFmpeg Pi; bổ sung alias/default nếu Aluminium FCM yêu cầu |
| 17 | Audio | QTI AGM/PAL, desktop audio AIDL, audio parameter parser | ALSA/USB/BT RPi | PARTIAL | Giữ audio RPi; desktop audio HAL phải thay/loại |
| 18 | Wi-Fi/BT | QTI wifi + `cnss`, BT QTI AIDL | brcmfmac, wifi/hostapd/supplicant/bt RPi | PARTIAL | Giữ HAL Pi; xác nhận version/instance với FCM |
| 19 | USB | QTI USB/gadget | USB/gadget RPi | CANDIDATE | Giữ implementation Pi |
| 20 | Health | health v5 + `vendor.google.desktop.health` v2 | health RPi | PARTIAL | Health chuẩn map; desktop health là gap |
| 21 | Power/thermal | Pixel power, QTI thermal, desktop suspend/charge | power/thermal/suspend_blocker RPi | PARTIAL/GAP | Map power/thermal chuẩn; bỏ Pixel/QTI/EC; desktop suspend cần thay |
| 22 | Security | Trusty KeyMint/Gatekeeper/Weaver/StrongBox, GSC, protected VM | nonsecure Gatekeeper/KeyMint RPi | GAP | Không mang Trusty; dùng nonsecure bring-up; siết sau |
| 23 | Camera | USB camera provider desktop + virtual camera | external UVC + libcamera Pi | PARTIAL | Dùng camera Pi, bỏ desktop pipeline |
| 24 | Sensors/input | multihal + touchpad/EC/keyboard proxy | không có tương đương | GAP | Bỏ hoặc implement cho Pi |
| 25 | Modem/telephony | modem FAT, QTI RIL, radio HAL bắt buộc | không có | GAP | Bỏ telephony/modem khỏi product Pi |
| 26 | NFC/GNSS/UWB | NFC AIDL/HIDL, GNSS, UWB bắt buộc | không có | GAP | Bỏ hoặc đánh dấu không hỗ trợ trong FCM/product |
| 27 | Desktop Google HAL | GSC, snapshot v5, aqueduct, drm_network, video_chat v2, toscana | không có | GAP | Bỏ/thay bằng implementation Pi hoặc feature flag |
| 28 | VINTF | target-level 202604, sepolicy 202604, system SDK37 | cùng AOSP17 nhưng manifest Pi thiếu fragment sinh từ APEX | REVIEW | checkvintf trên build Pi với matrix đã điều chỉnh |
| 29 | SELinux | policy v30, 3,901 type, 0 permissive, vendor QTI policy | Pi bring-up permissive, vendor policy RPi | PARTIAL | Không trộn policy; audit denial runtime |
| 30 | OTA | A/B payload v2, 15 partition, Virtual A/B snapshot LZ4 | không OTA/slot flow | INCOMPATIBLE | Không dùng OTA Aluminium; tự quản lý SD image |

## 2. Điều kiện trước khi thử ghép

1. M0 Pi baseline phải boot với image Raspberry Vanilla chưa sửa, có UART/adb/logcat và lưu known-good image + revision.
2. Phải build Pi và lấy manifest/matrix thật, chạy `checkvintf` với Aluminium matrix đã cắt bỏ desktop/QTI requirement.
3. Phải quyết định partition strategy: Pi static physical hay thêm super. Không được dùng metadata phỏng đoán cho `lpmake`.
4. Phải xác nhận page size/ABI bằng boot thật; ELF 16K alignment là điều kiện cần, chưa phải điều kiện đủ.
5. Chỉ sau đó mới thay system/framework/desktop theo từng bước, giữ Pi boot/vendor/HAL/graphics và audit denial/log từng layer.

## 3. Không được kết luận gì

- Không nói Aluminium chạy được trên Pi chỉ vì cùng Android 17/SDK 37/arm64.
- Không nói Mesa/V3DV hoạt động chỉ vì Pi source chọn package.
- Không nói AVB/SELinux/OTA tương thích chỉ vì verify tĩnh pass.
- Không nói các GAP HAL là optional nếu chưa chạy `checkvintf` và boot runtime.
