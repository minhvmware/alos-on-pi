> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# AluminiumOS — VINTF

## Phạm vi

- 86 file XML dưới `etc/vintf/` trong system, system_ext, product, vendor và vendor_boot ramdisk.
- Parse tĩnh bằng `tools/compare_vintf.py`; **không** chạy semantic `checkvintf` và không có runtime service registration.
- Pi source manifest gần như rỗng và APEX có thể thêm fragment lúc build, nên `NOT-DECLARED-IN-PI-SOURCE` là review item, không phải kết luận incompatibility.

## Manifest/matrix cấp cao

| File | Loại | Ghi nhận |
|---|---|---|
| `system/system/etc/vintf/manifest.xml` | framework manifest | sensor service, hidl manager/memory/netd/wifi keystore, netutils; system-sdk 29–37 |
| `system_ext/etc/vintf/manifest.xml` | framework manifest | KeyMint 5/3, SecureClock, FingerGuard/SharedSecret/KeyMintProvisioning `exclusive-to="virtual-machine"` |
| `vendor/etc/vintf/manifest.xml` | device manifest | `target-level="202604"`, sepolicy version `202604`; chỉ khai báo sepolicy, HAL vendor nằm ở các fragment `vendor/etc/vintf/manifest/*.xml` |
| `vendor/etc/vintf/compatibility_matrix.xml` | device matrix | 5 yêu cầu đặc thù Aluminium + `system-sdk 37` |
| `product/etc/vintf/compatibility_matrix.xml` | framework matrix | `vendor.google.thermal_profile` |
| `system_ext/etc/vintf/compatibility_matrix.toscana.xml` | framework matrix | `com.android.desktop.face.toscana` |
| `system/system/etc/vintf/compatibility_matrix.device.xml` | framework matrix | yêu cầu device-specific từ desktop/QTI: graphics allocator, media.c2, wifi, NFC, radio, biometrics face, GNSS, desktop audio/power/suspend, nhiều `vendor.qti.*` |
| `compatibility_matrix.202404/202504/202604.xml` | framework matrix | các level Android 15/16/17 tương ứng 2024-04, 2025-04, 2026-04 |

## Yêu cầu đặc thù bắt buộc

Từ `vendor/etc/vintf/compatibility_matrix.xml`:

| HAL | Version | Instance |
|---|---:|---|
| `android.system.desktop.security.gsc` | — | `IGsc/default` |
| `com.android.desktop.drm_network` | — | `IDrmNetworkService/default` |
| `com.android.desktop.video_chat` | 2 | `IVideoChatManager/default` |
| `com.google.android.aqueduct` | — | `IAqueduct/default` |
| `com.google.android.snapshot` | 5 | `ISnapshot/default` |

Bổ sung:

- `product`: `vendor.google.thermal_profile/IThermalProfileSetter/default`.
- `system_ext`: `com.android.desktop.face.toscana/IMicrodroid/default`.
- `system/system/etc/vintf/compatibility_matrix.device.xml`: `android.hardware.graphics.allocator/IAllocator/default`; desktop audio (`com.android.desktop.audio`, `...audio.suspend`), desktop power (`com.android.desktop.power`, `IDesktopPowerChargeControl`), `com.android.desktop.suspend_diagnostics`; và các HAL QTI như `vendor.qti.hardware.*`, `vendor.qti.qesd*`, `vendor.qti.spu`, `vendor.qti.qvirt*`.
- Ngoài ra matrix còn yêu cầu NFC, radio/radio.config, GNSS, biometrics face, `com.dsi.ant`, `com.qualcomm.qti.*`, `com.google.android.mdtool`, `com.google.android.snapshot_collector`, `com.google.desktop.disk_info`, `com.google.face.debug`.

Không có HAL nào trong nhóm trên xuất hiện trong `manifest.xml`/`product_manifest.xml`/`framework_compatibility_matrix.xml`/`device.mk` của Pi source. Nếu giữ nguyên Aluminium framework matrix khi chạy trên Pi, các yêu cầu này là gap thực tế; cách xử lý đúng là build lại framework matrix/product config cho Pi hoặc cung cấp implementation, không thể bỏ qua bằng cách đổi tên.

## HAL chung có ứng viên map

| Nhóm | Aluminium cung cấp | Pi source | Đánh giá tĩnh |
|---|---|---|---|
| Composer | `android.hardware.graphics.composer3/IComposer/default` AIDL 5 (`hwc3-drm.xml`) | package `com.android.hardware.graphics.composer.drm_hwcomposer` | Cùng package AOSP drm_hwcomposer; ứng viên map tốt nhất, version/instance phải kiểm tra sau build |
| Allocator | `android.hardware.graphics.allocator/IAllocator/default` AIDL 2 (QTI) | package `...allocator.minigbm_gbm_mesa` | Cùng interface chuẩn nhưng implementation QTI không mang sang; dùng minigbm Pi |
| Codec2 | `android.hardware.media.c2/IComponentStore/default` AIDL 2 (`c2_manifest_aidlv2_vendor`) | package `com.android.hardware.media.c2.ffmpeg`, FCM yêu cầu instance `ffmpeg` | Khác instance; Pi phải cung cấp `default` nếu Aluminium FCM yêu cầu, đồng thời giữ ffmpeg |
| Wi-Fi | `IWifi/default` v4, `IHostapd/default` v3, `ISupplicant/default` v5 | ba package wifi/hostapd/supplicant RPi | Cùng chuẩn, dùng implementation Pi; version runtime chưa xác nhận |
| USB | `IUsb/default` v3, `IUsbGadget/default` QTI | package USB và USB gadget RPi | Dùng implementation Pi |
| Health | `android.hardware.health/IHealth/default` v5 + `vendor.google.desktop.health/IDesktopHealth/default` v2 | package health RPi | Phần health chuẩn map được; phần desktop health là gap |
| Boot | `android.hardware.boot/IBootControl/default` | không thấy package boot HAL trong Pi `device.mk` | Gap source; cần bổ sung nếu framework yêu cầu |
| Power/thermal/light/suspend | Pixel/QTI/desktop services | package power, thermal, light, suspend_blocker RPi | Cùng tên HAL chuẩn nhưng desktop/QTI semantics khác; phải đối chiếu từng interface |
| Graphics khác | Adreno EGL/Vulkan, QTI display color/demura/memtrack | Mesa V3D/V3DV, minigbm, drm_hwc | Không tái sử dụng vendor Aluminium |

## Kết luận VINTF

- Aluminium là Android 17, target-level FCM `202604`, sepolicy version `202604`, system SDK 37; nền AOSP trùng Pi Android 17.
- Phần chuẩn AOSP (graphics composer/allocator interface, media c2, wifi, USB, health, power, thermal) có đường map về implementation Pi.
- Phần desktop/QTI/Google đặc thù (GSC, DRM network, video chat, aqueduct, snapshot, toscana, desktop audio/power/suspend, face/fingerprint, radio/NFC/GNSS, QTI services) không có implementation Pi trong source hiện tại.
- Chưa chạy `checkvintf`. Sau khi build Pi baseline, phải lấy manifest/matrix từ image Pi và chạy `checkvintf` với matrix Aluminium đã điều chỉnh; đây là điều kiện trước khi thử Aluminium system.
