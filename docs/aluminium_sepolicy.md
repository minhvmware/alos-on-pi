> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# AluminiumOS — SELinux

## Bằng chứng từ image

- 99 file policy/context/CIL trong system, system_ext, product, vendor, odm và ramdisk.
- Compiled policy đọc được bằng `seinfo`:
  - `vendor/etc/selinux/precompiled_sepolicy` (normal boot)
  - `vendor_boot_vendor_ramdisk01/sepolicy` (recovery)
- Cả hai policy: **Policy Version 30**, MLS enabled, `handle unknown classes: deny`, 108 class, 325 permission, 3,901 type, 429/433 attribute, 1 user, 2 role, 0 boolean, 0 conditional, 0 neverallow, 0 permissive type.
- `seinfo --permissive` trả `Permissive Types: 0`; grep CIL cũng không tìm thấy statement `permissive`.
- CIL policy tách Treble:
  - system: `plat_sepolicy.cil`, `plat_sepolicy_genfs_202504/202604/202704.cil`, `plat_file_contexts`, `plat_property_contexts`, `plat_service_contexts`, `plat_hwservice_contexts`, `plat_seapp_contexts`, `plat_keystore2_key_contexts`, `plat_tee_service_contexts`.
  - mapping: `202404`, `202504`, `202604`, `31.0`–`34.0` kèm `.compat.cil`.
  - vendor: `vendor_sepolicy.cil`, `plat_pub_versioned.cil`, `vndservice_contexts`, contexts cho vendor/odm.
  - system_ext/product: contexts và policy tương ứng.
- Hash `plat_sepolicy_and_mapping.sha256`, `precompiled_sepolicy.*.sha256` hiện diện để kiểm tra policy tương ứng giữa các partition.

## Ý nghĩa

- Aluminium build là Android 17, sepolicy version `202604`, target FCM `202604`.
- Không có permissive domain trong compiled policy. Đây là bằng chứng policy tĩnh không bật permissive; **không** chứng minh runtime đang enforcing.
- `ro.build.selinux` không xuất hiện trong property inventory; bootconfig không có `androidboot.selinux`. Trạng thái enforcing/permissive runtime phải đọc `getenforce`/`ro.boot.selinux`/audit log khi boot.
- Policy vendor chứa type/domain cho QTI, Trusty, desktop EC/GSC, `qseecomd`, `adsprpcd`, `perf2`, v.v. Policy này gắn với vendor Aluminium và không thể dùng làm vendor policy cho Pi.
- Pi source cmdline hiện có `androidboot.selinux=permissive` cho bring-up. Nếu giữ Pi boot, Aluminium system sẽ chạy trong môi trường permissive trừ khi cmdline/policy được thay; mọi denial trên Pi phải được thu bằng `dmesg`/`logcat` trước khi siết policy.

## Hướng integration

1. Giữ SELinux permissive ở M0 Pi baseline để có adb/UART/log.
2. Chỉ mang platform/system policy Android 17 tương ứng; không trộn `vendor_sepolicy.cil`, `precompiled_sepolicy`, `vndservice_contexts` của Aluminium QTI vào Pi.
3. Build Pi vendor policy từ Raspberry Vanilla source với device/brcm/rpi5, thêm type cần cho desktop system khi có denial thật.
4. Chỉ chuyển enforcing sau khi:
   - Pi baseline M0 boot ổn định với policy Pi,
   - Aluminium system/framework chạy với denial audit sạch,
   - mapping policy version giữa system/vendor/system_ext/product khớp.
