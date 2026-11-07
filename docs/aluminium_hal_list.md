> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# AluminiumOS — HAL và service inventory

## Nguồn inventory

- 86 VINTF XML, 387 file tên `android.hardware*`/`android.hidl*`, 314 khai báo `service` trong init rc, 46 APEX.
- `vendor/bin/hw` chứa implementation HAL chính; `system_ext/bin/hw` chứa desktop/KeyMint system VM.
- Chưa chạy service nào; đây là inventory file/VINTF, không phải trạng thái binder.

## Vendor HAL binaries (đọc từ `vendor/bin/hw`)

| Nhóm | Binary tiêu biểu |
|---|---|
| Graphics | `android.hardware.composer.hwc3-service.drm`, `vendor.qti.hardware.display.allocator-service`, `display.color-service`, `display.demura-service`, `MemHal-service` |
| Media/Codec2 | `vendor.qti.media.c2@1.0-service`, `modetest`, `drm_sample_app` |
| Camera | `android.hardware.camera.provider-usb-service.android-desktop`, `camera_tool`, `virtual_camera` |
| Audio | QTI AGM/PAL (`agmplay`, `agmcap`, `agmhostless`, `agmvoiceui`, `PalTest`, `vendor.qcom.amp.calib`), `audioadsprpcd`, `dspservice` |
| Bluetooth | `android.hardware.bluetooth@aidl-service-qti`, `hcitool.android-desktop`, `bt_lmp_event`/`bttpi` fragments |
| Wi-Fi | `android.hardware.wifi-service`, `hostapd`, `wpa_supplicant`, `cnss-daemon`, `wifi-crda` |
| USB | `android.hardware.usb-service.qti`, `android.hardware.usb.gadget-service.qti` |
| Security | `gatekeeper-service.trusty`, `keymint-service.trusty_tee.*`, `secretkeeper.trusty`, `weaver-service.android-desktop`, `authsecret-service.example`, `ssgqmigd`, `qseecomd` |
| Power/thermal | `power-service.pixel-libperfmgr`, `power.stats-service.desktop`, `thermal-service.pixel`, `charge-control-hal.qcom`, `suspend_notification_service`, `suspend_diagnostics` |
| Health/light | `health-service.android-desktop`, `lights-service.android-desktop`, `ec_battery_limits` |
| Sensors/input | `sensors-service.multihal`, `touchpad-inhibitor`, `keyboard_proxy_service`, `i2c-executor`, `vpd-executor`, `ec-executor`, `futility-executor` |
| Boot/dumpstate | `boot-service.android-desktop`, `dumpstate-service-desktop`, `fastboot-service.desktop` (ramdisk) |
| Desktop/Google | `disk_info_service`, `mdtool`, `snapshot_collector_service`, `gscd`, `gscutil-executor`, `storageproxyd_desktop` |
| QTI platform | `perf2-hal`, `sensorscalibrate`, `servicetrackeraidl`, `psiclient`, `pd-mapper`, `qmiproxy`, `ssr_*`, `irsc_util` |

Các binary QTI/Qualcomm, Pixel power/thermal, Trusty, Adreno và desktop firmware không thể dùng trên Pi vì phụ thuộc SoC/firmware/kernel modules.

## System_ext và framework HAL

- `system_ext/bin/hw`: `android.hardware.audio.parameter_parser.android-desktop`, `android.hardware.security.keymint-service.trusty_system_vm`, `com.google.android.desktop.super-partition-utils`.
- Framework manifest: sensor service, hidl manager/token, netd, vold, stats, keystore2, suspend, snapshot, desktop DRM network/video chat, media c2 software, camera service, location, devicestate.
- VINTF yêu cầu `exclusive-to="virtual-machine"` cho FingerGuard, SharedSecret, KeyMintProvisioning; đây là protected VM/Trusty semantics, không map sang Pi.

## Init service inventory

314 service, trong đó nhóm quan trọng:

- Core Android: `servicemanager`, `vndservicemanager`, `init`, `ueventd`, `logd`, `apexd`, `installd`, `netd`, `vold`, `zygote`, `surfaceflinger`, `media`, `cameraserver`, `keystore2`, `gatekeeperd`, `update_engine`, `snapuserd`, `snapuserd_proxy`.
- Desktop: `suspend_notification_service`, `suspend_diagnostics`, `disk_info_service`, `mdtool_service`, `snapshot_collector_service`, `touchpad-inhibitor`, `keyboard_proxy_service`, `blank_screen`, `poweroffhandler`.
- QTI/SoC: `qcom-sh`, `qcom-post-boot`, `init.qcom.*`, `qti-media`, `perf2-hal`, `MemHal`, `pd-mapper`, `qseecomd`, `adsprpcd`, `dspservice`, `ssr_diag`, `rpmb_mock_*`, `qti-testscripts`.
- Trusty/VM: `trusty_security_vm_launcher`, `trusty_security_protected_vm_launcher`, `system.keymint-service.desktop_trusty_system_vm`, `toscana_runner`, `aisealhostservice`.
- Firmware/EC: `fwupd`, `fwupd_script`, `ec_crash_collector`, `power_off_alarm`, `pm-service`, `lowbatteryalert`.

## APEX

46 package. Phân loại để quyết định giữ/drop khi port:

- **AOSP/system framework, ứng viên giữ nếu build lại đúng Pi:** `com.android.runtime`, `com.android.i18n`, `com.google.android.art`, `com.google.android.conscrypt`, `com.google.android.media`, `com.google.android.media.swcodec`, `com.google.android.mediaprovider`, `com.google.android.adbd`, `com.google.android.adservices`, `com.google.android.appsearch`, `com.google.android.bt`, `com.google.android.configinfrastructure`, `com.google.android.crashrecovery`, `com.google.android.devicelock`, `com.google.android.extservices`, `com.google.android.healthfitness`, `com.google.android.ipsec`, `com.google.android.neuralnetworks`, `com.google.android.nfcservices`, `com.google.android.ondevicepersonalization`, `com.google.android.os.statsd`, `com.google.android.permission`, `com.google.android.profiling`, `com.google.android.resolv`, `com.google.android.rkpd`, `com.google.android.scheduling`, `com.google.android.sdkext`, `com.google.android.telephonycore`, `com.google.android.tethering`, `com.google.android.tzdata6`, `com.google.android.uprobestats`, `com.google.android.uwb`, `com.google.android.virt`, `com.google.android.webapp`, `com.google.android.wifi`, `com.google.android.compos`, `com.android.npumanager`, `com.android.apex.cts.shim`.
- **Vendor/QTI/desktop, không thể mang sang Pi:** `com.android.hardware.audio.desktop` (require `libpalclient.so`, `libar-pal.so`, `libagm*`, QTI libs), `com.android.hardware.cas`, `com.android.hardware.fingerprint.crosfp`, `com.android.hardware.biometrics.fingerprint.virtual`, `com.android.hardware.keymint.strongbox.desktop` (bootstrap), `com.google.android.hardware.biometrics.face`, `com.google.android.widevine`, `com.google.android.gmssystem.prodvic`.
- APEX payload dùng 44 EROFS + 2 ext4; `apex_manifest.pb` decode được đủ 46 package.
- APEX signature/activation chưa xác minh runtime; `apex_pubkey` và `META-INF` hiện diện trong mỗi APEX.

## Proprietary/firmware dependencies

- `vendor/firmware`: modem, DSP, Venus, VPU, Adreno, Zap, Trusty và nhiều `.mbn`.
- QTI userspace: `libqti-perfd-client`, `libQnnHtp*`, `libar-pal`, `libagm*`, `libsdsprpc`, `libadsprpc`, `libcdsprpc`, `libfastcv*`.
- Graphics: Adreno EGL/Vulkan, ANGLE (`ro.hardware.egl=angle`), `ro.hardware.vulkan=adreno`.
- Security: Trusty `qseecomd`, `gatekeeper.trusty`, `keymint.trusty`, `weaver`, StrongBox APEX.
- Desktop hardware: GSC/EC/futility/fwupd/charge-control/suspend notification, camera USB pipeline, touchpad EC.

Các thành phần này phải bị loại khỏi integration Pi. Pi cung cấp Mesa/V3D, drm_hwcomposer, minigbm, FFmpeg Codec2, brcmfmac, health/light/power/thermal RPi và nonsecure Gatekeeper/KeyMint.
