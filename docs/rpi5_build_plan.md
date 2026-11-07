> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# Raspberry Vanilla Android 17 Pi 5 — build và boot plan

## Trạng thái

- Pi 5 đã có, chưa từng chạy Android 17.
- Host: 12 CPU, 15 GiB RAM, 8 GiB swap, 182 GiB trống sau Phase 0 evidence.
- Workspace đang sync: `/path/to/hoshinoos/aosp-rpi5`.
- Chưa có SD card kết nối host, nên chưa flash.
- Chưa có UART/adb/logcat từ Pi.

## 1. Workspace và revision

Workspace dùng shallow + partial clone để giảm dung lượng:

```sh
repo init -u https://android.googlesource.com/platform/manifest \
  -b android-17.0.0_r1 --depth=1 --partial-clone --clone-filter=blob:limit=10M
cp upstream/android_local_manifest/{manifest_brcm_rpi.xml,remove_projects.xml,manifest_utilities.xml} \
  .repo/local_manifests/
repo sync -c -j4 --no-clone-bundle --no-tags --optimized-fetch --prune --fail-fast
```

- Manifest: `android-17.0.0_r1`, 1,074 project sau khi áp local manifest; `manifests/repo-remove-extra.xml` loại thêm các project lớn không cần cho tablet rpi5: `platform/cts`, VTS, `chromium-webview`, `cronet`, `crosvm`, Cuttlefish.
- Device tree Pi: `device/brcm/rpi5` branch `android-17.0`.
- Kernel prebuilt cho Android build nằm trong `device/brcm/rpi5-kernel`; kernel source 6.18 build riêng bằng `android_kernel_manifest` nếu cần.
- Repo launcher: `toolchain/bin/repo` (version 2.69), SHA256 `6ed2f6325705b6ea0af99466d6ebd04adec387a5b6a906cd77bc8c6da65123e5`.

## 2. Host dependency user-local

Không có sudo không tương tác, nên dependency build được giải nén vào `toolchain/`:

- `bison 3.8.2`, `flex 2.6.4`, `gperf 3.2.1`, `lz4 1.10.0`, `ccache 4.12.3`.
- Header/pkg-config `ncurses-devel 6.6`, `openssl-devel 3.5.9`.
- `tools/aosp_env.sh` nạp `PATH`, `CPATH`, `LIBRARY_PATH`, `PKG_CONFIG_PATH`.
- JDK dùng prebuilt trong AOSP (`prebuilts/jdk`), không cần `javac` hệ thống.
- `mkfs.vfat`, `mkfs.ext4`, `fdisk`, `kpartx`, `mtools`, `rsync`, `xmllint` đã có trên host.

## 3. Build

```sh
cd /path/to/hoshinoos/aosp-rpi5
source /path/to/hoshinoos/aluminium-rpi5/tools/aosp_env.sh
. build/envsetup.sh
lunch aosp_rpi5-cp2a-userdebug
make bootimage systemimage vendorimage -j4
./rpi5-mkimg.sh
```

Giới hạn tài nguyên:

- Dùng `-j4` (không `-j12`) để tránh OOM với 15 GiB RAM; swap 8 GiB chỉ là đệm.
- Không bật ccache cho lần đầu để tiết kiệm dung lượng; `CCACHE_DIR` trỏ vào `toolchain/ccache` nếu bật.
- Theo dõi `df -h /home`; nếu còn dưới 30 GiB phải dừng và dọn output chưa cần.
- Output cần giữ: `out/target/product/rpi5/{boot.img,system.img,vendor.img}` và disk image từ packager.
- Không xoá `out/target/product/rpi5` trước khi copy image known-good ra ngoài workspace.
- `tools/make_rpi5_image.sh` là bản rootless tương đương `mkimg.sh`: `fdisk` trên file, `dd` theo offset, `mkfs.ext4 -E offset` cho metadata/userdata. Không cần `sudo/kpartx/losetup`. Output mặc định `/path/to/hoshinoos/raspberry-vanilla/images/RaspberryVanillaAOSP17-YYYYMMDD-rpi5.img` kèm `.sha256`.

## 4. Flash khi có SD

1. Cắm SD vào host; xác định đúng device bằng `lsblk -o NAME,SIZE,TYPE,RM,MODEL,MOUNTPOINTS`.
2. Kiểm tra không mount partition của SD; `umount` nếu cần.
3. Ghi image bằng Raspberry Pi Imager hoặc `dd` với device đúng:

```sh
unzip -l AOSP17-rpi5.img.zip        # xác nhận entry
unzip -p AOSP17-rpi5.img.zip '*.img' | sudo dd of=/dev/sdX bs=4M status=progress conv=fsync
```

Không chạy `dd` khi chưa xác nhận `/dev/sdX` là SD, không phải NVMe hệ thống. Nếu không có quyền sudo tương tác, dùng Raspberry Pi Imager GUI.

4. Cắm SD vào Pi 5, nguồn 5V/5A, HDMI, USB keyboard/mouse, cáp USB-C data nếu dùng adb.
5. Lần boot đầu có thể mất vài phút; capture UART nếu có adapter.

## 5. M0 validation checklist

- [ ] Firmware Pi load `Image`/`ramdisk.img`, không panic trước Android init.
- [ ] `adb devices` thấy thiết bị qua USB-C.
- [ ] `adb shell getprop ro.build.version.release` = `17`, `ro.build.version.sdk` = `37`.
- [ ] `adb shell getprop ro.board.platform` = `bcm2712`, `ro.hardware` = `rpi5`.
- [ ] `adb shell cat /proc/cmdline` và `/proc/mounts` lưu vào `logs/`.
- [ ] `adb shell dmesg` không có lỗi DRM/V3D/USB/Wi-Fi nghiêm trọng.
- [ ] SurfaceFlinger và compositor chạy; HDMI hiển thị.
- [ ] `adb shell dumpsys SurfaceFlinger | head` có display active.
- [ ] V3D/V3DV: kiểm tra `dumpsys SurfaceFlinger`, `logcat` và renderer, không chỉ đọc tên package.
- [ ] Wi-Fi scan/connect và DHCP.
- [ ] USB keyboard/mouse/storage.
- [ ] Lưu image, revision, log và hash trước khi thay bất kỳ thành phần Aluminium.

## 6. Ghi chú về prebuilt cộng đồng

Có bản `AOSP17-20260702-KonstaKANG-rpi5.zip` dựa trên Raspberry Vanilla (kernel 6.18.26, V3D/Vulkan, adb USB-C, SELinux permissive) với SHA256 `a83cf6f9cd596d0fd33063ad6095d6ab42762c88ded11ab58be15a51ebf1c179`. Bản này có thể dùng để thử nhanh phần cứng, nhưng:

- Không phải build Raspberry Vanilla nguyên trạng; có thêm thay đổi và license non-commercial.
- Link tải là Filen public link; Filen CLI không hỗ trợ tải anonymous, nên không dùng trong workflow tự động.
- Không dùng làm known-good baseline cho integration. Known-good phải là build từ source ở mục 3, có revision và hash.

## 7. Resume sau khi tạm dừng

Trạng thái mới nhất (đã tạm dừng để tắt máy): workspace khoảng 123 GB, source đã sync gần đủ, Soong đã chạy tới bước module analysis; build chưa xong, chưa có image. Các nhánh Trusty/Virtualization guest/SDV/automotive test không cần cho Pi đã được loại để giảm lỗi module. Trạng thái lưu ở `/path/to/hoshinoos/raspberry-vanilla/BUILD_STATUS.txt`.

Khi có thời gian, chạy lại trực tiếp build (không cần repo sync):

```sh
cd /path/to/hoshinoos/aluminium-rpi5
tools/build_pi_chain.sh \
  /path/to/hoshinoos/aosp-rpi5 \
  /path/to/hoshinoos/raspberry-vanilla/images
```

Chain sẽ:
1. `repo sync` resume với mirror AOSP (`mirrors.tuna.tsinghua.edu.cn`), `depth=1` khi clone project mới, retry fetch.
2. Build `aosp_rpi5-cp2a-userdebug` với `JOBS` (mặc định 4, có thể `JOBS=6`).
3. Đóng gói rootless image + SHA256.

Theo dõi:

```sh
tail -f /tmp/aosp-chain.log
ls -lh /path/to/hoshinoos/raspberry-vanilla/images/
```

Lưu ý các project từng bị full-history (`frameworks/base`, `Settings`, `prebuilts/build-tools`, `prebuilts/clang/host/linux-x86`) đã được xoá gitdir để clone lại shallow; nếu sync vẫn kẹt, kiểm tra lock stale:

```sh
find /path/to/hoshinoos/aosp-rpi5/.repo -name '*.lock' -delete
```

## 8. Sau M0

Chỉ sau khi M0 pass:

1. Lưu manifest/revision/image/hash Pi known-good.
2. Lấy manifest/matrix thật từ Pi image, chạy `checkvintf` với Aluminium matrix đã điều chỉnh.
3. Quyết định partition strategy (MBR tĩnh hay thêm super) dựa trên layout thật.
4. Thay system/framework/desktop theo từng bước, giữ Pi boot/vendor/HAL/graphics.
