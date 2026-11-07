> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# AluminiumOS OTA metadata và extraction evidence

## Input

| Trường | Giá trị |
|---|---|
| Path | `/path/to/hoshinoos/91b269229318b3dae45e08966e69e2991e52c039.zip` |
| Size | `2910908938` byte |
| SHA256 | `a8e5babdd6d922b28a6768a7340473c9451381a0b2adce9abd064bbd5a5d08e7` |
| ZIP entries | 7 |
| `unzip -t` | pass toàn bộ entry |
| zipinfo | `signed by SignApk` trong comment, không thay thế kiểm tra chữ ký |

`META-INF/com/android/otacert` có subject/issuer `CN=test`, serial `26477596ADD7A9D23E7B8963725BA7EB774C1B4D`, SHA256 fingerprint `51:6E:A1:B4:17:0E:56:CC:1C:8D:02:7A:AC:74:5E:26:EC:DC:5E:52:5B:B8:CB:D6:43:08:24:C8:FB:E7:9E:51`, hiệu lực 2026-05-29 đến 2036-05-26. Chứng chỉ test không phải trust anchor; chưa chạy verifier chữ ký toàn OTA.

## OTA metadata

```text
ota-type=AB
post-build=HP/quartz/quartz:17/CL3B.260622.273.R1/16471258:user/release-keys
post-build-incremental=16471258
post-sdk-level=37
post-security-patch-level=2026-09-01
post-timestamp=1790700063
pre-device=quartz
```

## Payload properties

```text
FILE_HASH=Pl1dMO2wOKouOt5gKOrmlflfsRy22fpNsHqap46phdM=
FILE_SIZE=2910901802
METADATA_HASH=QtlVb7tPjAdzPBAGspBntYxYiaNgHtqJRbbafrsaArk=
METADATA_SIZE=32347
```

`FILE_HASH` và `FILE_SIZE` đã được kiểm tra độc lập bằng `openssl dgst -sha256 -binary | base64`; khớp. Payload manifest: version 2, minor version 0, block size 4096, signature offset 2910868409, signature size 523.

## Payload partitions

`bluetooth`, `boot`, `dsp`, `dtbo`, `init_boot`, `modem`, `product`, `pvmfw`, `system`, `system_dlkm`, `system_ext`, `vbmeta`, `vendor`, `vendor_boot`, `vendor_dlkm`.

Dynamic metadata và Virtual A/B flags nằm trong `docs/aluminium_partition_layout.md`.

## APEX metadata

`apex_info.pb` decode bằng AOSP `update_metadata.proto` (`android-17.0.0_r1`) cho 46 entry. Payload APEX được extract riêng:

- 46/46 `apex_manifest.pb` decode thành công bằng `apex_manifest.proto` Android 17.
- Payload filesystem: 44 EROFS + 2 ext4.
- 683 ELF trong APEX có LOAD alignment `0x4000`/`0x200000`, không có 4K.
- Chi tiết phân loại APEX nằm trong `docs/aluminium_hal_list.md`.

## Tooling

- `payload-dumper-go` `v0.0.0-20260923043722-c3a50ba8d784` (commit `c3a50ba8d784764c06143c1f82971cd81a77f9d6`), build bằng Go 1.27.0.
- Dumper đọc trực tiếp OTA ZIP, verify operation/output SHA256 và tạo dm-verity FEC; extraction dùng mặc định, không `-no-verify`/`-no-fec`.
- `avbtool 1.4.0` verify vbmeta và hash/hashtree; `protoc 3.19.6` decode metadata/APEX; `fsck.erofs 1.9.4` extract EROFS; `magiskboot v31.0` decompress/extract boot ramdisk và kernel LZ4.
- Nguồn, commit và hash tool nằm trong `docs/toolchain.md`.

## Evidence layout

Output ngoài repository:

```text
/path/to/hoshinoos/aluminium-analysis/91b269229318b3dae45e08966e69e2991e52c039/
  ota/                 metadata, payload.bin, properties, otacert
  images/              15 partition image
  extracted/           raw, filesystem extract, ramdisks, metadata, reports
  apex-images/         apex_payload.img cho 46 APEX
  apex-extracted/      filesystem extract của APEX
  apex-manifests/      apex_manifest.pb
  evidence/            hash, payload manifest, AVB, kernel, SELinux, ELF, VINTF
```

Không có file image nào được flash; input ZIP và image giữ nguyên.
