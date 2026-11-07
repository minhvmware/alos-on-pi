> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# Bring-up status

Cập nhật: 2026-10-24. Mọi checkbox còn trống nghĩa là **chưa chứng minh**, không phải “đã biết lỗi”.

## Blockers hiện tại

- [x] Pi 5 đã có; đã boot Android 17 từ USB SSD (không cần khe SD trên host).
- [x] Không cần SD card: dùng USB SSD Hynix 55.9 GB qua cổng USB 3; đã flash bằng `tools/flash_rpi5_sd.sh --boot-mode usb`.
- [x] Nguồn 27W, HDMI, USB keyboard/mouse, ADB qua Wi-Fi đã hoạt động.
- [ ] AOSP workspace `/path/to/hoshinoos/aosp-rpi5` build full vẫn bị OOM trên host 15 GiB RAM; cần máy ≥32 GiB hoặc swap lớn.
- [ ] Lấy manifest/matrix thật từ Pi image và chạy `checkvintf` trước khi ghép Aluminium system.
- [ ] Giới hạn tài nguyên: 12 CPU, 15 GiB RAM; build full phải chạy trên host khác.

## Đã hoàn thành trong Phase 0

- [x] Cài/kiểm chứng user-local host toolchain; nguồn, commit và hash tại `docs/toolchain.md`.
- [x] Audit Pi `BoardConfig`, fstab, init, build config, `mkbootimg`, `mkimg`, `wrimg` và releasetools scope; chi tiết tại `docs/rpi5_partition_layout.md`.
- [x] Extractor nhận thư mục, image riêng, MBR/GPT full disk, Android boot/vendor_boot, FAT boot, sparse, dynamic super, ext4/FAT/EROFS; đã test synthetic và chạy end-to-end trên OTA thật.
- [x] Hash và inventory input; không flash image gốc.
- [x] `docs/aluminium_partition_layout.md`
- [x] `docs/aluminium_bootflow.md`
- [x] `docs/aluminium_hal_list.md`
- [x] `docs/aluminium_vintf.md`
- [x] `docs/aluminium_sepolicy.md`
- [x] `docs/aluminium_ota_metadata.md` và `docs/hardware_compatibility_matrix.md`
- [x] Xác nhận release/SDK, ABI/page size, GKI, dynamic partitions/Virtual A/B, AVB, VINTF, HAL/APEX/init, SELinux policy và proprietary dependencies.

## Phase 0 — kết quả chính

- Aluminium là Android 17/SDK 37/arm64-v8a, build `desktop_system` + vendor HP `quartz`/Qualcomm `hamoa`.
- OTA là A/B full payload v2, 15 partition, không chứa `super.img`; dynamic partitions + Virtual A/B snapshot LZ4, super 12 GiB.
- Kernel Aluminium 6.12.81 GKI **4K pages**, 311 module vermagic 6.12.81-4k; Pi 6.18/16K nên kernel/modules Aluminium không dùng được.
- 2,432 ELF parse được (1,749 partition + 683 APEX) đều align 16K (`0x4000` hoặc `0x200000`), không có ELF 4K; 11 ELF partition không trả LOAD nên cần review. Userspace phù hợp page size Pi ở mức ELF.
- AVB chained SHA256_RSA4096; `avbtool verify_image` pass toàn bộ hash/hashtree bằng embedded key.
- VINTF target-level/sepolicy `202604`; nhiều yêu cầu desktop/QTI bắt buộc không có trong Pi source.
- SELinux policy v30, 3,901 type, 0 permissive type trong cả normal và recovery policy; trạng thái enforcing runtime chưa xác định.
- Không thể `dd` boot/system/vendor Aluminium vào Pi; cần Pi baseline M0 trước.

## Milestones

### M0 — Android 17 Pi
- [x] AOSP Android 17 nguyên trạng boots (prebuilt KonstaKANG, dựa trên Raspberry Vanilla)
- [x] adb (Wi-Fi `PI_IP:5555`)
- [x] Wi-Fi (TEST_WIFI_5G, 5 GHz, 802.11ac)
- [x] GPU acceleration bằng V3D/V3DV, không software fallback (`V3D 7.1.10.2`, Mesa 26.1.4, Vulkan broadcom)
- [x] USB (keyboard/mouse 2.4G + Apple keyboard, USB storage)
- [x] Lưu image và revision known-good (`AOSP17-20260702-KonstaKANG-rpi5.zip`, SHA256 `a83cf6f9...`)

M0 evidence: `docs/baseline_validation.md`.
Lưu ý: M0 dùng prebuilt, **không phải** build Raspberry Vanilla từ source; chỉ dùng làm baseline
phần cứng để bắt đầu port Aluminium. Known-good cho integration vẫn phải là build từ source.

### M1 — Aluminium init
- [ ] Pi kernel boots với Aluminium system
- [ ] Aluminium `/system` mounts
- [ ] init hoàn tất
- [ ] adb hoạt động

### M2 — Android framework
- [ ] zygote
- [ ] system_server
- [ ] PackageManager
- [ ] SurfaceFlinger

### M3 — Display
- [ ] HDMI
- [ ] Mesa/V3D acceleration
- [ ] Vulkan V3DV
- [ ] HWC/vsync và mouse cursor

### M4 — Desktop
- [ ] Aluminium SystemUI
- [ ] Desktop launcher/taskbar/windowing
- [ ] Keyboard/mouse và desktop input

### M5 — Connectivity
- [ ] Ethernet
- [ ] Wi-Fi (2.4/5 GHz, DHCP, reconnect)
- [ ] Bluetooth và các profile theo thiết bị test

### M6 — Multimedia
- [ ] HDMI audio
- [ ] USB audio/microphone và Bluetooth audio
- [ ] Hardware video decode có CPU-load evidence
- [ ] USB UVC camera rồi libcamera

### M7 — Daily usable
- [ ] NVMe boot
- [ ] Screen blank/reboot/shutdown/thermal; suspend nếu khả thi
- [ ] SELinux enforcing với policy từ denial thật
- [ ] AVB/custom keys và OTA

## Quy tắc evidence cho mỗi thay đổi

Ghi reproduce, log trước/sau, layer chịu trách nhiệm, upstream implementation đối chiếu, patch tối thiểu, build/boot test và commit riêng. Nếu adb/SurfaceFlinger/system_server còn sống khi desktop UI crash, xử lý framework trước; không quy kết kernel.
