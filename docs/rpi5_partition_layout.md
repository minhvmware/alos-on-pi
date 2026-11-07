> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# Raspberry Vanilla Pi 5 — partition và image packaging

## Phạm vi và nguồn bằng chứng

Tài liệu này mô tả cấu hình source của Raspberry Vanilla `android-17.0`, không phải kết quả đo trên một Pi 5 đang chạy.

- Device tree: `device/brcm/rpi5`, commit `25a7ccffe9d769039906859f5641967e1aaa7564`.
- Local manifest: commit `a155dda7f0db82d9b8076c1f39f41db4167fcb73`.
- Nguồn chính: `BoardConfig.mk`, `device.mk`, `aosp_rpi5*.mk`, `ramdisk/fstab.rpi5`, `ramdisk/init.rpi5.rc`, `mkbootimg.mk`, `mkimg.sh`, `wrimg.sh`, `boot/config.txt`.
- Chưa có generated disk image, UART log, `sfdisk --dump` hay `/proc/mounts` từ Pi 5. Những mục cần artifact/runtime được đánh dấu riêng.

## 1. Build products và điểm vào packaging

Cả tablet (`aosp_rpi5`), TV (`aosp_rpi5_tv`) và Automotive (`aosp_rpi5_car`) kế thừa cùng `device.mk`; không product nào thay partition/boot flow.

```sh
make bootimage systemimage vendorimage -j"$(nproc)"
```

Sau đó `rpi5-mkimg.sh` gọi `device/brcm/rpi5/mkimg.sh` để tạo full SD image. Writer trực tiếp `wrimg.sh` là phương án khác: nó ghi từng image vào SD đã có đúng partition table, không tạo lại partition table.

| Output | Định dạng theo build config | Đích trong SD flow |
|---|---|---|
| `boot.img` | FAT32, LABEL `boot`, 128 MiB; **không phải Android boot image** | p1 |
| `system.img` | ext4; sparse ext bị tắt trong device config | p5 |
| `vendor.img` | ext4 | p6 |
| `userdata.img` nếu build riêng | ext4, kích thước build target 128 MiB | Không được `mkimg.sh` dùng để tạo p3 |

`BOARD_USERDATAIMAGE_PARTITION_SIZE := 128M` chỉ là kích thước của build target userdata. Nó **không phải** kích thước p3: `mkimg.sh` format p3 trên toàn vùng trống còn lại của SD.

## 2. Full disk image: MBR/DOS

`mkimg.sh` tạo file đúng `15360000000` byte, tương đương `30000000` sector nếu logical sector là 512 byte. Lệnh `fdisk` dùng `o` để tạo DOS partition table. Đây là MBR với extended/logical partitions, không phải GPT.

| MBR entry | Vai trò | Kích thước khai báo | Sectors ở 512 B/sector | Type / trạng thái | Filesystem LABEL |
|---|---|---:|---:|---:|---|
| p1, primary | Firmware + kernel + ramdisk | 128 MiB / 134217728 B | 262144 | `0x0c` W95 FAT32 LBA; active | `boot` |
| p2, extended | Container của p5/p6/p7 | 3476 MiB | 7118848 | Extended do `fdisk` tạo | Không áp dụng |
| p3, primary | Android data | Phần còn lại | Không cố định | Linux mặc định | `userdata` |
| p5, logical | Android system | 3072 MiB / 3221225472 B | 6291456 | Linux mặc định | Writer yêu cầu `/` |
| p6, logical | Android vendor | 384 MiB / 402653184 B | 786432 | Linux mặc định | `vendor` |
| p7, logical | Android metadata | 16 MiB / 16777216 B | 32768 | Linux mặc định | `metadata` |

Không có p4. p2 là container; không `dd` một filesystem vào p2. Extended boot records và alignment giải thích phần dung lượng container ngoài tổng p5+p6+p7.

### Những giá trị chưa thể lấy chính xác từ script

`mkimg.sh` leaves the `First sector` prompt unanswered, so start LBA is selected by the installed `fdisk` version. Script cũng không chỉ định CHS geometry hoặc logical/physical sector size. Vì vậy tài liệu này không gán start/end LBA, CHS hoặc dung lượng p3 bằng phỏng đoán. Bảng sectors ở trên chỉ là phép đổi kích thước khai báo với điều kiện 512 B/sector.

Khi có image, lưu bằng chứng bằng:

```sh
sfdisk --json rpi5.img >rpi5.partition-table.json
sfdisk --dump rpi5.img >rpi5.sfdisk.dump
fdisk -l rpi5.img >rpi5.fdisk.txt
```

`tools/extract_aluminium.sh` đọc MBR/GPT bằng `sfdisk --json` và tách partition bằng byte offset, không mount hoặc sửa input.


## 3. Cách `boot.img` được tạo và boot

`BoardConfig.mk` đặt `BOARD_CUSTOM_BOOTIMG := true` và include `mkbootimg.mk`. Recipe tạo file zero-filled 128 MiB, format FAT32 LABEL `boot`, rồi dùng `mcopy` đưa `boot/config.txt`, kernel `Image`, `bcm2712*-rpi-*.dtb`, overlays, `ramdisk.img` và `cmdline.txt` vào FAT image.

`config.txt` có `kernel=Image`, `initramfs ramdisk.img followkernel` và `auto_initramfs=0`. Firmware Raspberry Pi load kernel và initramfs từ p1. `BOARD_KERNEL_CMDLINE` được ghi thành `cmdline.txt`; không có `root=`.

Do đó không được đưa `boot.img` này cho `unpack_bootimg` như thể nó có `ANDROID!` header. Extractor nhận diện FAT và dùng `mcopy`; Android boot/vendor_boot chỉ được unpack khi magic tương ứng. `TARGET_NO_BOOTLOADER := true` nghĩa là không build Android bootloader image; firmware Raspberry Pi vẫn tham gia boot flow.

## 4. Cách system/vendor được đóng gói

Các biến liên quan trong `BoardConfig.mk`:

- `TARGET_USERIMAGES_USE_EXT4 := true`
- `TARGET_USERIMAGES_SPARSE_EXT_DISABLED := true`
- `BOARD_SYSTEMIMAGE_FILE_SYSTEM_TYPE := ext4`
- `BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := ext4`
- `BOARD_SYSTEMIMAGE_PARTITION_SIZE := 3072M`
- `BOARD_VENDORIMAGE_PARTITION_SIZE := 384M`
- `BOARD_METADATAIMAGE_PARTITION_SIZE := 16M`
- `BOARD_FLASH_BLOCK_SIZE := 4096`

Trong `mkimg.sh`, sau khi `sfdisk` tạo filesystem:

```text
boot.img   -> dd -> p1
system.img -> dd -> p5
vendor.img -> dd -> p6
```

Không có bước ghép system/vendor vào `super.img`, không `lpmake`, không resize system/vendor trong recipe. `wrimg.sh` cũng `dd` trực tiếp vào p1/p5/p6 và kiểm tra kích thước/LABEL trước khi cho phép ghi.

## 5. Root, first-stage mount và data

Cấu hình phù hợp với system-as-root dùng first-stage ramdisk:

- `device.mk` copy `fstab.rpi5` vào ramdisk và `/vendor/etc`.
- p5/p6/p7 có `first_stage_mount`, lần lượt mount tại `/system`, `/vendor`, `/metadata`.
- p3 mount tại `/data` trong late-fs.
- Không block device nào trong fstab mount trực tiếp tại `/`; root ban đầu đến từ initramfs.
- `init.rpi5.rc` gọi `mount_all --early` trong `on fs` và `mount_all --late` trong `on late-fs`.

fstab hard-code `/dev/block/mmcblk0p5`, `mmcblk0p6`, `mmcblk0p7`, `mmcblk0p3`. Việc các node này đúng với mọi phương thức boot chỉ có thể xác nhận trên runtime.

## 6. Các cơ chế không có trong flow đã kiểm tra

| Cơ chế | Bằng chứng trong scope source |
|---|---|
| Dynamic partitions / `super.img` | Không có biến cấu hình, rule packaging, fstab slot hay bước flash; system/vendor được ghi trực tiếp p5/p6 |
| A/B hoặc Virtual A/B | Không có `AB_OTA_*`, slot, `_a/_b`, `boot_control` hoặc `update_engine` trong device config |
| Recovery | `TARGET_NO_RECOVERY := true` |
| `vendor_boot.img` | Không kích thước, rule tạo image hoặc bước flash |
| `init_boot.img` | Không kích thước, rule tạo image hoặc bước flash |
| AVB/vbmeta | Không thấy `BOARD_AVB_ENABLE`, key/signing config, `vbmeta.img` hoặc bước flash |
| Device-specific releasetools/OTA | Không có thư mục/tham chiếu `releasetools` hoặc `ota_from_target_files` trong device tree |

`androidboot.verifiedbootstate=orange` trong cmdline không tự nó chứng minh AVB được bật. Tương tự, absence trong device tree không phải kết quả `get_build_var` trên toàn build. Local manifest thay `platform/build` bằng `raspberry-vanilla/android_build`, nhưng full build tree chưa được sync; không kết luận ngoài phạm vi source hiện có.

## 7. Runtime evidence còn cần

Không build/flash chỉ để điền tài liệu này trước Phase 0. Khi baseline được boot hợp lệ, capture:

```sh
adb shell 'cat /proc/cmdline; cat /proc/mounts'
adb shell 'ls -l /dev/block/by-name /dev/block/mapper 2>/dev/null'
adb shell 'getprop ro.boot.slot_suffix; getprop ro.boot.dynamic_partitions; getprop ro.boot.verifiedbootstate; getprop ro.boot.veritymode'
adb shell 'ls -l /sys/block/mmcblk0; cat /sys/block/mmcblk0/queue/logical_block_size'
```

UART vẫn cần cho firmware, ramdisk và first-stage mount. Các lệnh trên xác nhận runtime; chúng không được thay bằng giá trị giả định trong report.
