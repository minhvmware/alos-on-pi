> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# Raspberry Vanilla Android 17 Pi 5 — source baseline

Ngày kiểm tra: 2026-10-24. Đây là phân tích **Pi BSP**, không phải kết quả Phase 0 của AluminiumOS.

## Revision và release

| Thành phần | Giá trị đã xác nhận | Bằng chứng |
|---|---|---|
| AOSP manifest | `android-17.0.0_r1` | `android_local_manifest/README.md` |
| Pi target | `aosp_rpi5-cp2a-userdebug` | `android_local_manifest/README.md` |
| Shipping API | 37 | `device.mk` |
| Kernel manifest | `common-android17-6.18-lts` | `android_kernel_manifest/README.md` |
| Kernel source override | `raspberry-vanilla/android_kernel_brcm_rpi`, branch `android-17.0` | `manifest_brcm_rpi.xml` |
| ISA/CPU build variant | `arm64`, `arm64-v8a`, `cortex-a76` | `BoardConfig.mk` |
| Platform | `bcm2712` | `BoardConfig.mk` |

Revision đầy đủ được khóa trong `../manifests/upstream-revisions.lock`. Branch có thể thay đổi; cần giữ commit của mọi known-good build.

## Boot và partition layout thực tế

Chi tiết partition table, build targets, `dd` flow, first-stage mount và giới hạn source/runtime nằm trong `rpi5_partition_layout.md`.

Pi firmware load `Image` và `ramdisk.img` từ boot partition FAT32; `boot/config.txt` khai báo `kernel=Image`, `initramfs ramdisk.img followkernel`, cùng `vc4-kms-v3d`. `mkbootimg.mk` tạo `boot.img` 128 MiB là **FAT32 disk image**, không phải Android `boot.img` có Android boot header.

`mkimg.sh` tạo MBR bằng `fdisk` (có extended/logical partitions) với:

| Partition | Mục đích | Kích thước upstream |
|---|---|---|
| p1 | boot FAT32, boot flag | 128 MiB |
| p5 (logical) | `/system` ext4 | 3072 MiB |
| p6 (logical) | `/vendor` ext4 | 384 MiB |
| p7 (logical) | `/metadata` ext4 | 16 MiB |
| p3 | `/data` ext4 | phần còn lại |

Device/build packaging source không cấu hình `super`, `vendor_boot`, `init_boot`, `dtbo` partition hay dynamic partitions trong flow mặc định. DTB và overlays được copy vào boot FAT. Fstab mặc định hard-code `/dev/block/mmcblk0p*`; NVMe/USB boot cần một thay đổi boot storage riêng và phải test sau SD baseline.

Kernel command line hiện có `androidboot.hardware=rpi5`, `androidboot.verifiedbootstate=orange` và `androidboot.selinux=permissive`. Đây là cấu hình bring-up upstream, không phải trạng thái final mong muốn.

## Graphics và media cần giữ nguyên

`device.mk` chọn:

- `com.android.hardware.egl.mesa`
- `com.android.hardware.graphics.allocator.minigbm_gbm_mesa`
- `com.android.hardware.graphics.composer.drm_hwcomposer`
- `com.android.hardware.vulkan.broadcom`

Manifest thay Mesa, drm_hwcomposer và minigbm bằng repo Raspberry Vanilla. Chưa build/run nên chưa thể xác nhận version Mesa runtime, Vulkan conformance, HWC, vsync hay mức tăng tốc thực tế. Không được ghi “V3DV works” chỉ từ tên package.

`vendor.prop` bật `persist.vendor.ffmpeg_codec2.v4l2.h265=true`; `media_codecs_ffmpeg_c2.xml` khai báo HEVC tới 4096×4096. Đây là cấu hình source, chưa phải bằng chứng hardware decode trên Pi. Pi 5 không có hardware H.264 decode nên kết quả H.264 phải được đo, không suy ra từ H.265.

## HAL/subsystem có sẵn trong source

- Audio AIDL (`audio/`), HDMI/USB/Bluetooth routing.
- Bluetooth HCI service (`bluetooth/`).
- Wi-Fi supplicant/hostapd services và `wificond`; `brcmfmac` phải được xác nhận ở kernel/runtime.
- External USB camera và libcamera/libpisp.
- Health, light, HDMI CEC/connection, USB gadget, suspend blocker.
- FFmpeg Codec2, nonsecure Gatekeeper/KeyMint. Không thay các nonsecure implementation này bằng tuyên bố về security level chưa được kiểm chứng.

## VINTF

`manifest.xml` chỉ khai báo `target-level="202604"`; nhiều HAL manifest được tạo từ APEX service metadata lúc build. `framework_compatibility_matrix.xml` thêm yêu cầu AIDL `android.hardware.media.c2/IComponentStore/ffmpeg`. Vì vậy không thể coi một file `manifest.xml` source là toàn bộ vendor manifest của image. Phải chạy `checkvintf` trên build output và sau khi ghép Aluminium system.

## Điều kiện chuyển phase

Chưa có build hay boot trong môi trường hiện tại. M0 chỉ được đánh dấu sau khi có image Pi nguyên trạng, serial/logcat/dmesg, `adb`, DRM/Mesa/SurfaceFlinger và test USB/Wi-Fi. Không dùng kết quả build thành công để thay cho boot thành công.
