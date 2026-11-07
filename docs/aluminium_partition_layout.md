> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# AluminiumOS OTA — partition và image layout

## Nguồn và tính xác thực

- OTA: `/path/to/hoshinoos/91b269229318b3dae45e08966e69e2991e52c039.zip`
- SHA256 ZIP: `a8e5babdd6d922b28a6768a7340473c9451381a0b2adce9abd064bbd5a5d08e7`
- Kích thước ZIP: `2910908938` byte; `unzip -t` pass toàn bộ 7 entry.
- OTA metadata: `ota-type=AB`, `post-build=HP/quartz/quartz:17/CL3B.260622.273.R1/16471258:user/release-keys`, SDK 37, security patch `2026-09-01`, pre-device `quartz`.
- Payload: version 2, minor version 0 (full payload), `block_size=4096`, `signatures_size=523`.
- `payload.bin` SHA256/base64 khớp `FILE_HASH=Pl1dMO2wOKouOt5gKOrmlflfsRy22fpNsHqap46phdM=` và `FILE_SIZE=2910901802`.
- `avbtool verify_image --image vbmeta.img` xác minh SHA256_RSA4096 và hash/hashtree của mọi partition được descriptor bao phủ bằng embedded public key.

OTA ZIP không chứa `super.img`; full OTA cập nhật trực tiếp các logical partition. Vì vậy không có image super vật lý để `dd`.

## 1. Partition images trong payload

Kích thước dưới đây là file image thật do `payload-dumper-go` tạo, gồm cả AVB hashtree/footer khi có.

| Partition | File image (byte) | Filesystem | Loại |
|---|---:|---|---|
| `bluetooth` | 8,388,608 | FAT16 | Firmware Bluetooth |
| `boot` | 67,108,864 | Android boot header v4 | Kernel-only GKI boot |
| `dsp` | 78,643,200 | ext4 | Firmware DSP |
| `dtbo` | 8,388,608 | raw DTBO | Device tree overlay |
| `init_boot` | 8,388,608 | Android boot header v4 | Generic ramdisk |
| `modem` | 367,001,600 | FAT16 | Modem firmware |
| `product` | 1,969,926,144 | EROFS | Logical partition |
| `pvmfw` | 1,048,576 | Android boot header v3 | Protected VM firmware |
| `system` | 1,081,507,840 | EROFS | Logical partition |
| `system_dlkm` | 8,482,816 | EROFS | GKI modules |
| `system_ext` | 245,547,008 | EROFS | Logical partition |
| `vbmeta` | 8,192 | AVB vbmeta | Chained verification |
| `vendor` | 392,548,352 | EROFS | Logical partition |
| `vendor_boot` | 33,554,432 | Android vendor_boot header v4 | Vendor ramdisk |
| `vendor_dlkm` | 16,740,352 | EROFS | Vendor modules |

Tổng image khoảng 4.0 GiB. OTA không có `recovery`, `userdata`, `metadata`, `misc`, `persist`; các partition này thuộc physical partition table và được fstab tham chiếu.

## 2. Dynamic partitions và Virtual A/B

Payload manifest khai báo:

```text
dynamic_partition_metadata {
  groups {
    name: "google_dynamic_partitions"
    size: 12880707584
    partition_names: "system" "vendor" "product" "system_ext"
                     "system_dlkm" "vendor_dlkm"
  }
  snapshot_enabled: true
  vabc_enabled: true
  vabc_compression_param: "lz4"
  cow_version: 3
  compression_factor: 65536
  block device: super, size 12884901888
}
```

Build properties xác nhận:

```text
ro.boot.dynamic_partitions=true
ro.virtual_ab.enabled=true
ro.virtual_ab.compression.enabled=true
ro.virtual_ab.compression.xor.enabled=true
ro.virtual_ab.io_uring.enabled=true
ro.virtual_ab.ublk.enabled=true
ro.virtual_ab.userspace.snapshots.enabled=true
ro.virtual_ab.batch_writes=true
ro.vendor.build.ab_ota_partitions=bluetooth,boot,dsp,dtbo,init_boot,modem,product,pvmfw,system,system_dlkm,system_ext,vbmeta,vendor,vendor_boot,vendor_dlkm
```

`super` được khai báo 12,884,901,888 byte (12 GiB); group `google_dynamic_partitions` gần bằng toàn bộ super. Tên partition trong payload không có hậu tố `_a/_b`, nhưng fstab dùng `slotselect` và OTA là A/B. Từ static payload không thể kết luận group là slot-suffixed hay slotless; phải đọc `lpdump`/`/dev/block/mapper` trên thiết bị hoặc reconstruct super. Không được đoán slot khi `lpmake`.

Pi baseline không có `super`, dynamic partitions hay Virtual A/B. Vì vậy **không thể `dd` các image Aluminium vào p5/p6 Pi**. Cần một trong hai hướng sau khi Phase 0 xong: reconstruct super đúng metadata rồi thêm partition `super`, hoặc chuyển logical image thành physical ext4/EROFS partition và bỏ slot/AVB/snapshot semantics—mỗi hướng đều là thay đổi boot/partition lớn, không phải thay file đơn giản.

## 3. Physical partition và fstab

`vendor/etc/fstab.android-desktop` (và bản first-stage giống hệt trong `vendor_boot` ramdisk) yêu cầu:

| Partition | Mount | Flags chính |
|---|---|---|
| `system`, `vendor`, `product`, `system_ext`, `system_dlkm`, `vendor_dlkm` | `/system`, `/vendor`, `/product`, `/system_ext`, `/system_dlkm`, `/vendor_dlkm` | `logical`, `first_stage_mount`, `slotselect`, `avb=vbmeta` |
| `boot` | `/boot` | `slotselect`, `avb=boot`, `first_stage_mount` |
| `init_boot` | `/init_boot` | `slotselect`, `avb=init_boot`, `first_stage_mount` |
| `vendor_boot` | `/vendor_boot` | `slotselect`, `avb=vendor_boot`, `first_stage_mount` |
| `vbmeta` | `/vbmeta` | `slotselect`, `first_stage_mount` |
| `userdata` | `/data` | ext4, `fileencryption=aes-256-xts:aes-256-cts`, `checkpoint=block` |
| `metadata` | `/metadata` | ext4, `first_stage_mount`, `check` |
| `misc` | `/misc` | raw |
| `persist` | `/mnt/vendor/persist` | ext4 |
| `modem` | `/vendor/firmware_mnt` | vfat, `slotselect` |
| `dsp` | `/vendor/dsp` | ext4, `slotselect` |
| `bluetooth` | `/vendor/bt_firmware` | vfat, `slotselect` |

Pi MBR chỉ có p1 FAT boot, p5 system, p6 vendor, p7 metadata, p3 userdata. Pi thiếu `super`, `init_boot`, `vendor_boot`, `vbmeta`, `misc`, `persist`, `modem`, `dsp`, `bluetooth`; đồng thời system/vendor Pi là physical ext4 không slot/AVB. Đây là gap partition lớn hơn nhiều so với việc thay `system.img`.

## 4. AVB

`vbmeta.img`:

- Algorithm `SHA256_RSA4096`, public key SHA1 `e6923481e34adf55a9600499bf085ed83564f1d2`, rollback index 1339, flags 0.
- Prop descriptors cho fingerprint/os_version/security_patch của `boot`, `init_boot`, `system`, `vendor`, `product`, `system_ext`, `system_dlkm`, `vendor_dlkm`, `dtbo`, `pvmfw`, `vendor_boot`; các partition có OS metadata ghi `os_version=17` và security patch `2026-09-01`.
- Hash descriptor cho `boot`, `dtbo`, `init_boot`, `pvmfw`, `vendor_boot`.
- Hashtree descriptor dm-verity v1 cho `bluetooth`, `dsp`, `modem`, `product`, `system`, `system_dlkm`, `system_ext`, `vendor`, `vendor_dlkm`; FEC roots bằng 0.
- `avbtool verify_image` xác minh thành công vbmeta và toàn bộ hash/hashtree bằng embedded public key.

Đây là xác minh tính toàn vẹn nội bộ, **không phải** xác nhận khóa này được bootloader tin cậy trên Pi. Pi baseline không có AVB/vbmeta flow; nếu giữ Pi boot thì không thể kỳ vọng chain này chạy nguyên trạng.

## 5. Chưa xác định từ static image

- Slot suffix thực tế và layout super slot-suffixed/slotless.
- Partition table vật lý của thiết bị quartz (GPT entries, slot size, super offset).
- Trạng thái `ro.boot.verifiedbootstate`, `ro.boot.veritymode` runtime.
- `misc`/`persist` layout và encryption key state của `userdata`.
- F2FS: không partition nào trong OTA dùng F2FS; tất cả đã extract được bằng ext4/FAT/EROFS.
