> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# M1 — AluminiumOS userspace trên Pi 5 (image thử)

Ngày tạo: 2026-10-26
Trạng thái: **đã flash lên SSD, chờ boot thử trên Pi 5**

## Thành phần

| Partition | Nội dung | Kích thước |
|---|---|---|
| p1 | boot Pi baseline (FAT32, `android-usb`) | 128 MB |
| p5 | Aluminium system + product + system_ext, ext4 label `/` | 8 GB |
| p6 | vendor Pi baseline (ext4) | 384 MB |
| p7 | metadata ext4 mới | 16 MB |
| p3 | userdata ext4 mới | ~5.8 GB |

- Image: `work/m1-rpi5.img` (15,360,000,000 bytes)
- SHA256: `8801718cc18756b166c3908c61e92936b7a8dbd4b9b6a1b89dc71cd56c43218c`
- System image riêng: `work/m1-system.img` (8 GiB, label `/`)

## Đã thay đổi so với Aluminium gốc

1. Gộp `system` (1.7GB) + `product` (3.1GB) + `system_ext` (409MB) vào p5 8GB.
2. Thay toàn bộ `compatibility_matrix*.xml` trong `/system/etc/vintf` bằng bản Pi baseline
   (matrix tối thiểu: GNSS, sensors, media.c2/ffmpeg).
3. Xoá `product/etc/vintf/compatibility_matrix.xml` (yêu cầu `vendor.google.thermal_profile`).
4. Xoá `system_ext/etc/vintf/compatibility_matrix.toscana.xml` (yêu cầu desktop face HAL).
5. Giữ nguyên Pi boot, Pi vendor, Pi kernel; không dùng kernel/module/boot Aluminium.

## Rủi ro đã biết

- File trong system image giữ uid/gid 1000 (extract bằng user), không phải root:root.
- Không có SELinux xattr/label; Pi đang permissive nên có thể boot tiếp.
- Thiếu 230 HAL QTI/desktop; system_server hoặc service desktop có thể crash.
- `product`/`system_ext` nằm trực tiếp trong p5, không mount riêng; init Aluminium có thể
  kỳ vọng logical partition/super.
- Aluminium build là `user`; Pi vendor là `userdebug`; property mismatch có thể xảy ra.

## Flash / rollback

Flash M1 (khi SSD đã cắm vào laptop):

```bash
ADB_ASKPASS=/tmp/askpass-sudo.sh
# dùng cùng quy trình askpass như lần flash baseline
sudo -A dd if=work/m1-rpi5.img of=/dev/sda bs=4M status=progress conv=fsync
sync
```

Rollback baseline:

```bash
sudo -A dd if=/path/to/hoshinoos/raspberry-vanilla/images/AOSP17-20260702-KonstaKANG-rpi5.img \
  of=/dev/sda bs=4M status=progress conv=fsync
sync
```

Sau khi flash, cắm SSD vào Pi 5 USB 3, boot, theo dõi HDMI/UART/ADB. Nếu không lên:
quay lại baseline ngay, không sửa mò.

## Boot test log

- 2026-10-26: flash M1 đầy đủ → **bootloop** (chưa có UART/adb để lấy log).
- Đã sửa `cmdline.txt` trong p1 thành một dòng:
  `console=ttyAMA10,115200 androidboot.hardware=rpi5 androidboot.selinux=permissive selinux=0 androidboot.force_normal_boot=1`
  và ghi lại p1 (128MB) thành công (`P1B_OK`).
- Chưa kết luận nguyên nhân; cần boot lại và/hoặc UART log. Nếu vẫn bootloop, rollback baseline
  trước khi thử M1b (root ownership, metadata lớn hơn, policy).
- 2026-10-27: UART capture được 2 chu kỳ bootloop. Kernel/USB/partition đều tốt: `sda`, `sda5`,
  `sda6`, `sda7` mount thành công; lỗi xảy ra sau first-stage init. Nguyên nhân là p1 đã bị sửa
  khác baseline ở hai điểm:
  1. `cmdline.txt` thêm `androidboot.force_normal_boot=1`, làm init switch sang
     `/first_stage_ramdisk` rỗng trước khi mount system.
  2. `android-usb.dtbo` thêm `mnt_point=/` cho system. Giả thuyết ban đầu: baseline không có
     property này nên system mount tại `/system` rồi `SwitchRoot("/system")`, qua đó giữ được
     `/dev`, `/proc`, `/sys`. Giả thuyết này **đã bị thực nghiệm bác bỏ một phần** ở lần boot
     p1fix: baseline dtbo vẫn cho system mount tại `/` và không có `SwitchRoot`. Với `mnt_point=/`,
     system mount đè lên `/dev`; second-stage init không mở được `/dev/null` và `/dev/kmsg`,
     `LOG(FATAL)` gọi `InitFatalReboot` mặc định `bootloader` nên reboot im lặng.
  Fix ban đầu: dùng lại `android-usb.dtbo` baseline và bỏ `force_normal_boot`/`selinux=0` khỏi cmdline.
  Artifact: `work/m1-usb64-p1fix.img` (128 MiB, sha256
  `ded3917aa9d245d20bd618efbbd632ce6fd9c9fdce572d1630b8e955f1460b28`).
  2026-10-27 12:01: đã flash artifact vào `/dev/sda1` (SSD Hynix V2 55.9G). Readback 128 MiB
  khớp sha256; `cmdline.txt` không còn `force_normal_boot`/`selinux=0`; `android-usb.dtbo`
  khớp baseline (`7e0c83f9...fed3eb`); `fsck.fat -n` sạch. Capture UART vẫn chạy (PID 4490,
  log cũ 70384 bytes); chờ power-cycle Pi để lấy log boot mới từ offset 70384.
- 2026-10-27 12:04: boot lại với p1fix. Kernel cmdline đã đúng (không còn `force_normal_boot`),
  USB/partition vẫn tốt, `sda7` mount rồi remount, `sda5` mount ro, nhưng **không có**
  `Switching root to '/system'`; sau đó vẫn `reboot: Restarting system with command 'bootloader'`.
  Như vậy baseline dtbo (không có property `mnt_point`) là **không đủ** trong build init này:
  system vẫn bị coi là mount tại `/`, nên không có `SwitchRoot("/system")`.
  Kết luận: phải ghi rõ `mnt_point="/system"` trong DT fstab, không dựa vào default.
- Fix 2: patch `android-usb.dtbo` (từ bản M1) để node `system` có `mnt_point="/system"`.
  Artifact: `work/m1-usb64-p1system.img` (128 MiB, sha256
  `f8f5811785c1417ac3b7cc06078bb94d45dde1a63c8b30d07cccf52c9b0586f5`), dtbo sha256
  `8040dc977fdd61f3dd77e424d522e6e301b6ee85b58da3ad7c2de0bb23bd7ac7`.
  `cmdline.txt` giữ nguyên bản đã sửa; `fsck.fat -n` sạch, 391 files. Chưa flash vì SSD đang
  cắm ở Pi; khi cắm lại laptop sẽ ghi vào `/dev/sda1` rồi power-cycle.
  Log UART cũ hiện 124150 bytes; lần boot tới đọc từ offset 124151.
- Lưu ý layout: p5 **không phải system-as-root thuần**. Root p5 có `bin -> /system/bin`,
  `etc -> /system/etc`, `vendor/`, `product/`, ... và **có thư mục `/system` chứa system thật**.
  Vì vậy `mnt_point="/"` có thể là chủ ý; mount p5 tại `/system` rồi `SwitchRoot("/system")`
  có thể làm mất đường dẫn `/system/bin/init`. Cần test explicit `/system` để xác nhận log
  `Switching root`, rồi nếu execv fail thì mới xử lý tiếp (thêm symlink hoặc giữ `/dev`).
  Artifact p1system đã sẵn sàng; script flash: `work/flash-p1system.sh /dev/sda1`.
- Fix 3 (chuẩn bị): giữ `mnt_point="/"` đúng với rootfs p5, đổi system sang `rw` để `/dev`
  trên ext4 có thể ghi, và thêm các device node tĩnh vào `/dev` của p5:
  `null`, `zero`, `full`, `random`, `urandom`, `kmsg`, `console`, `tty`, `ptmx`.
  Mục tiêu: first-stage mount p5 tại `/` không còn làm second-stage init chết ở
  `open("/dev/null")`; log sẽ quay lại UART và ta thấy lỗi kế tiếp (nếu có).
  Artifacts: `work/m1-usb64-p1rootrw.img` (sha256
  `9e1221fabe8e66ff3d28353c635fb81ebb53079e0c02663e8a96ae3382eee309`) và
  `work/m1-p5-devnodes.img` (sha256
  `cfbf42473ec8afdf9fffc150f5e070cb51323e55477310680d1e27b539bd5a34`).
  Flash cả p1+p5: `work/flash-p1p5.sh /dev/sda1 /dev/sda5` (chỉ khi SSD đã cắm laptop).
  Đây là workaround chẩn đoán; nếu boot qua second stage sẽ thay bằng mount tmpfs `/dev` sạch.
- 2026-10-27 12:25: đã flash Fix 3 vào SSD Hynix V2 (`/dev/sda`): p1 128 MiB → `/dev/sda1`,
  p5 8 GiB → `/dev/sda5` bằng `work/flash-p1p5.sh`. Kết quả:
  - p1: `dd` 32 record × 4 MiB = 134217728 bytes (4.4 s, 30.4 MB/s); readback 128 MiB khớp
    sha256 `9e1221fabe8e66ff3d28353c635fb81ebb53079e0c02663e8a96ae3382eee309`;
    `fsck.fat -n` sạch (391 files, 144129/258078 clusters).
  - p5: `dd` 2048 record × 4 MiB = 8589934592 bytes (356.5 s, 24.1 MB/s), `conv=fsync` OK,
    sha256 nguồn `cfbf42473ec8afdf9fffc150f5e070cb51323e55477310680d1e27b539bd5a34`
    (chưa readback vì cần root; block device là `root:disk`, user chỉ thuộc `wheel,video,input`).
  - `lsblk` sau khi ghi: `sda1` vfat `boot` 128M, `sda5` ext4 label `/` 8G, `sda6` vendor 384M,
    `sda7` metadata 16M, `sda3` userdata 5.8G — layout không đổi.
  - UART capture vẫn chạy (`cat /dev/ttyUSB0`, PID 4490); `work/pi-uart.log` = 124150 bytes.
    Lần boot tới đọc log mới từ offset 124151 (`tail -c +124151 work/pi-uart.log`).
  Bước tiếp theo: tháo an toàn SSD khỏi laptop, cắm lại Pi 5, power-cycle và theo dõi log để xem
  second-stage init có sống qua `open("/dev/null")`/`open("/dev/kmsg")` hay không.
- 2026-10-27 12:27: boot lại với Fix 3 (`pi-uart.log` từ offset 124151, 48127 bytes) — **log dừng
  ở 0.950 s**, ngay tại `pcieport 0002:00:00.0: AER: enabled with IRQ 41` (probe RP1), kèm vài
  chục byte rác rồi im lặng hoàn toàn (không còn byte nào trong >2 phút). Không hề có `rp1
  0002:01:00.0: bar0 ...`/`chip_id`, không có USB/MSD, không có `Run /init as init process`.
  So sánh với các lần boot tốt trước đó (cùng file log): 578 dòng, `Run /init` lúc 4.9 s,
  `reboot: Restarting` lúc 5.13 s — tức lần này chết **sớm hơn ~4 s**, trước cả khi kernel đọc
  được bất kỳ phân vùng nào.
  Đã kiểm tra để loại trừ lỗi image: so sánh trực tiếp readback `/tmp/p1rootrw-readback.img`
  (chính là nội dung trên `/dev/sda1`, sha256 khớp) với baseline `/tmp/base-p1.img`:
  - danh sách file y hệt (15 entry root + `overlays/`);
  - `Image`, `bcm2712-rpi-5-b.dtb` và các dtb khác giống nhau;
  - `cmdline.txt` = `console=ttyAMA0,115200 androidboot.hardware=rpi5
    androidboot.selinux=permissive loglevel=7 ignore_loglevel` (khớp cmdline mà kernel in ra,
    giống hệt các lần boot 11:5x);
  - `config.txt` khác baseline chỉ ở các mục debug UART đã thêm từ trước (`enable_uart=1`,
    `uart_2ndstage=1`, `dtparam=uart0=on`, `dtparam=uart0_console`, `dtoverlay=disable-bt`,
    `usb_max_current_enable=1`) — những mục này đã có mặt ở lần boot 12:04 vẫn chạy tới init.
  Kết luận tạm thời: điểm chết 0.95 s nằm trước mọi thứ liên quan tới p5/fstab, nên thay đổi
  `mnt_point`/`rw`/devnode **không thể** là nguyên nhân; nghi vấn thuộc về RP1/UART (UART0 trên
  Pi 5 đi qua RP1, RP1 chết là mất luôn console) hoặc nguồn/dây UART bị xê dịch khi tháo-cắm SSD.
  Đã khởi động lại capture sạch: `cat /dev/ttyUSB0 > work/pi-uart2.log` (PID 9788) sau khi
  `stty 115200 cs8 -crtscts raw -echo`. Cần power-cycle Pi và xem log mới; nếu vẫn dừng ở 0.95 s
  thì kiểm tra dây UART/GND và nguồn 5V/5A trước khi nghĩ tới rollback p1.
- 2026-10-27 12:33: power-cycle lần nữa, capture mới `work/pi-uart2.log` (59109 bytes, 1 boot,
  703 dòng kernel). Lần này chạy xa hơn một chút nhưng vẫn chết cùng chỗ:
  - `rp1 0002:01:00.0: chip_id 0x20001927` **OK** (0.950 s) và
    `rp1-firmware rp1_firmware: RP1 Firmware version 23fca1cd…` **OK** (1.110 s) — tức RP1 sống,
    firmware đã nạp, khác với suy đoán "RP1 firmware load fail" ở entry trước;
  - `xhci-hcd.0/.1` đăng ký bus 1..4 OK (1.109 s);
  - log kết thúc bằng `[drm] Initialized v3d 1.0.0 for 1002000000.v3d on minor 0` + rác nhị phân,
    rồi im lặng hoàn toàn.
  Cấu trúc file cho thấy rõ: earlycon in live tới ~1.11 s, sau đó kernel đăng ký console thật và
  **dump lại toàn bộ log buffer từ 0.000 s**; bản dump này chết ở mốc nội dung ~0.96 s. Nghĩa là
  lần chết này xảy ra trong lúc handover console, không phải ở một driver cụ thể của p5/fstab.
  Thêm bằng chứng nghi phần cứng/đường serial: trong cùng file có 7 banner ROM Espressif
  (`ets Jul 29 2019 … rst:0x1 (POWERON_RESET)`), 3 cái ở đầu và **4 cái ở offset 47632–48848**,
  tức có thiết bị thứ hai (ESP32/bridge) reset giữa lúc Pi đang in log, rồi ~10 KB sau thì stream
  của Pi hỏng và tắt. Nhiều khả năng đây là sự cố nguồn/đường UART dùng chung chứ không phải image.
  Bước kiểm tra rẻ nhất: cắm HDMI để xem console `tty0` có chạy tiếp qua mốc ~1 s hay không —
  nếu HDMI vẫn scroll tiếp thì Pi boot bình thường, chỉ kênh UART chết, và ta có thể chẩn đoán
  qua HDMI thay vì serial.
- 2026-10-27 12:36: chuẩn bị sẵn artifact để test giả thuyết brownout khi USB cấp nguồn cho SSD:
  `work/m1-usb64-p1usbpwr.img` = `work/m1-usb64-p1rootrw.img` với **đúng một dòng** đổi
  `usb_max_current_enable=1` → `#usb_max_current_enable=1` (diff đã kiểm tra), `fsck.fat -n` sạch,
  391 files, sha256 `0cad97a6fca60772e6a377337ded7b42a0b4fd2dbb54df47d2f843c34af32e65`.
- 2026-10-27 13:30 — **UART vẫn chỉ có rác ESP32 (58 KB mới = 27 banner), 0 byte của Pi.**
  - `work/pi-uart2.log` 145 618 → 204 131 B, toàn bộ 58 513 B mới là
    `ets Jul 29 2019 … rst:0x1 (POWERON_RESET)` ×27 ⇒ **ESP32 đang brownout-loop ~2 s/lần** (được cấp nguồn
    từ 3V3 của mạch nạp CH340 nên không đủ dòng) và **TX của nó đang nằm trên chính node RXD của adapter**.
  - Phân tích toàn bộ log cũ: banner ESP luôn xuất hiện **ngay trước** `Linux version` mỗi lần cấp nguồn
    (offset 0/304/510 → Linux version 917), nghĩa là ESP32 chia sẻ đường RX với Pi từ đầu; lượt này có ESP
    mà **không có `Linux version`** ⇒ dây **Pi pin 8 (GPIO14/TXD) → RXD** không còn tiếp xúc (hoặc cắm nhầm
    TX→TX). Không phải lỗi phần mềm: cmdline vẫn `console=ttyAMA0,115200`.
  - Đã xác nhận từ cmdline trong log: không có `console=tty1`; MAC ethernet Pi = `XX:XX:XX:XX:XX:XX`
    (`smsc95xx.macaddr`) và **không thấy MAC này trong LAN PI_IP/24** ⇒ Pi chưa lên mạng.
  - Kernel trên p1 **có fbcon** (strings có `[drm] fb%d: %s frame buffer device`, `fbcon_rotate_hint`) ⇒ dự
    phòng được: `work/m1-usb64-p1-tty1.img` (128 MB, chỉ cần flash p1 ~10 s) đã tạo sẵn, cmdline thêm
    `console=tty1 fbcon=nodefer` để log kernel + kmsg của init hiện **trực tiếp lên HDMI**.
  - Tool mới `work/uart-loopback.py`: test adapter bằng cách nối tắt RXD↔TXD rồi ghi/đọc `LOOPBACK-TEST-12345`
    (phân biệt lỗi adapter với lỗi dây).
  - Ghi chú thêm: fstab trong `android-usb.dtbo` **không có entry `/data`** (chỉ boot/system/vendor/metadata)
    ⇒ nếu /data không được mount ở second stage (qua `/vendor/etc/fstab.rpi5`) thì `post-fs-data` không bao
    giờ chạy ⇒ treo ở boot animation — đây là nghi phạm số 1 cho hiện tượng "treo logo Google", cần log để
    xác nhận.
- 2026-10-27 13:25 — **ĐỘT PHÁ: boot lên tới boot animation (logo Google). UART thì lại câm.**
  - Báo cáo từ màn hình: Pi đã hiện **logo Google / boot animation** ⇒ đã qua `switch_root`, `Loading SELinux
    policy` **thành công** (nhãn relabel có tác dụng), init second stage + apexd + zygote + surfaceflinger +
    bootanim đều đã chạy. Đây là lần đầu tiên p5 đi qua được điểm chết 4.5 s.
  - Nhưng UART chỉ nhận **1 216 B** trong lượt này và **toàn bộ là rác ESP32**
    (`ets Jul 29 2019 … rst:0x1 (POWERON_RESET),boot:0x13` lặp ~5 lần) — **không có một byte nào của Pi**.
    Log đứng ở 145 618 B / 13:20:43. Nguyên nhân: sau khi re-enumerate, CH340 (`1a86:7523`) chỉ còn nhận
    TX của ESP32 trên node RX; dây TX của Pi (pin 8 / GPIO14) coi như không tới adapter (khả năng cao bị
    tuột khi tháo/cắm SSD hoặc khi cắm lại nguồn). Không phải lỗi phần mềm: kernel `console=ttyAMA0` không đổi.
  - Tool mới **`work/wait-pi.py`**: chỉ kích hoạt khi thấy `Linux version` / `NOTICE:  BL31` /
    `Kernel command line:` sau baseline (nên **không bị đánh lừa bởi rác ESP32**), chờ log lặng 15 s rồi cắt
    phần mới ra `<prefix>.log` + `<prefix>.txt`, kèm bảng marker: switch_root / init 2nd stage / selinux load /
    avc denied / enforcing / apex / zygote / surfaceflinger / bootanim / reboot-panic / `:unlabeled:`.
    Đang chạy nền: baseline 145 618 B, prefix `work/pi-uart5`, timeout 5400 s.
  - Kế tiếp: kiểm tra dây UART (GND ↔ pin 6, Pi pin 8 TXD ↔ adapter RXD, **không** nối 3V3/5V), power-cycle
    lại để `wait-pi.py` bắt trọn lượt boot và lấy log init/apexd/zygote.
- 2026-10-27 13:20 — **ĐÃ FLASH p5 (có nhãn) + verify sha256 khớp; chờ power-cycle.**
  - `work/flash-p5.sh work/m1-p5-labeled.img /dev/sda5`: ghi 8 589 934 592 B trong 306 s (28 MB/s, đuôi
    chậm vì `conv=fsync`), readback `dd | sha256sum` = `627be67dab5ec022151b9536440507ad32776dcad89319abe7d8aedbf8a973ed`
    **trùng** sha ảnh ⇒ p5 trên đĩa đúng là ảnh đã relabel.
  - Sự cố nhỏ: cắm lại SSD/USB-serial làm `/dev/ttyUSB0` re-enumerate (12:56) ⇒ **mất ACL**, user không
    đọc được nữa (`cat: Permission denied`; `stty` cũng fail) và tiến trình `cat` capture cũ đã chết.
    Đã cấp lại: `sudo setfacl -m u:"$(id -un)":rw /dev/ttyUSB0` rồi `stty -F /dev/ttyUSB0 115200 raw -echo -crtscts`
    + `cat /dev/ttyUSB0 >> work/pi-uart2.log` (PID 14136). Nếu adapter re-enumerate lần nữa thì phải làm lại
    (hoặc thêm udev rule).
  - `work/wait-boot.sh` nâng cấp: sau khi thấy log tăng thì **chờ log lặng 15 s** (hoặc tối đa 240 s) rồi mới
    cắt `tail -c +BASE+1` ⇒ không còn cảnh cắt giữa boot; chạy nền baseline 144 401 B, timeout 3600 s
    (PID 13732, kết quả ở `work/pi-uart4.log` / `work/pi-uart4.txt`).
  - Kế tiếp: rút SSD khỏi host → cắm lại Pi → power-cycle → đọc `work/pi-uart4.txt`.
- 2026-10-27 13:05 — **NGUYÊN NHÂN GỐC ĐÃ TÌM RA (Fix 4): `/system` trên p5 mất nhãn SELinux.**
  Log mới `work/pi-uart3.log` (85 292 B, cắt từ offset 59 110) cho thấy boot **đã qua `switch_root`**:
  `[3.480527] init: Opening SELinux policy` → `[4.501151] init: Loading SELinux policy` → kernel load
  policy OK (`policy capability …`), rồi:
  ```
  [4.557255] audit: type=1404 enforcing=1 old_enforcing=0 enabled=1 lsm=selinux
  [4.566973] avc: denied { read } for pid=1 comm="init" name="plat_file_contexts" dev="sda5"
            scontext=u:r:kernel:s0 tcontext=u:object_r:unlabeled:s0 tclass=file permissive=0
  [4.566990] avc: denied { read } … name="system_ext_file_contexts" … tcontext=unlabeled …
  ```
  ⇒ `selinux_android_restorecon("/system/bin/init")` (`selinux.cpp:822`) không đọc được file_contexts
  (file đó **unlabeled**) ⇒ `PLOG(FATAL)` ⇒ PID 1 chết ⇒ kernel panic (stack có `__arm64_sys_exit_group`,
  `SMP: stopping secondary CPUs`; khớp "Attempted to kill init").
  Vì sao vẫn enforcing dù cmdline có `androidboot.selinux=permissive`: `selinux.cpp:114` `IsEnforcing()`
  chỉ tôn trọng permissive khi build đặt `ALLOW_PERMISSIVE_SELINUX=1` (userdebug/eng). Build của
  Aluminium OS là **user** ⇒ luôn enforcing ⇒ **bắt buộc phải có nhãn đúng**.
  Đo trên ảnh p5: `/system/bin/sh`, `/system/lib64/libc.so`, `/system/etc/…` … **unlabeled**;
  chỉ `/system` (system_file) và `/system/bin/bootstrap/linker64` (system_linker_exec) có nhãn.
  Nguồn gốc: `work/m1-system.img` mang nhãn **của host Fedora** (`unconfined_u:object_r:user_home_t:s0`)
  ⇒ cây file được dựng bằng copy trên host nên nhãn AOSP bị mất/ghi đè.
  Cách sửa đã làm (offline, không cần mount/quyền SELinux của host):
  - Tool mới `work/relabel-ext4.py`: duyệt ảnh qua `fuse2fs -o ro`, khớp path với
    `plat/system_ext/product_file_contexts` có sẵn trong ảnh (kiểu libselinux: full-match + stem dài
    nhất thắng), rồi ghi `security.selinux` bằng `debugfs ea_set` (host đang Enforcing nên `setfattr`
    sẽ bị chặn — `debugfs` sửa thẳng trên ảnh nên không đụng kernel SELinux).
  - Kết quả trên `work/m1-p5-labeled.img`: 4 990/4 992 path được gán nhãn, chỉ 2 path không khớp
    (`/lost+found`, `/init.environ.rc`). Kiểm chứng mẫu: `/`→rootfs, `/system/bin/sh`→shell_exec,
    `/system/bin/init`→init_exec, `/system/etc/selinux/plat_file_contexts`→file_contexts_file,
    `/system/lib64/libc.so`→system_lib_file, `/system/bin/bootstrap/linker64`→system_linker_exec,
    `/system/lib64/bootstrap/libc.so`→system_bootstrap_lib_file, `/system/bin/servicemanager`→
    servicemanager_exec, `/bin`→rootfs (symlink OK).
  - `e2fsck -fn` sạch và **cùng số inode/block** với ảnh gốc (5002 files / 1 298 782 blocks) ⇒ chỉ
    xattr thay đổi, nội dung file nguyên vẹn.
  - Tool mới `work/flash-p5.sh <p5-image> [/dev/sda5]`: kiểm tra đúng 8 GiB, `dd conv=fsync`, rồi
    readback `dd | sha256sum` để so với sha của ảnh; gom mọi thao tác root vào **một** lần `sudo -A`
    (askpass zenity, chỉ hỏi mật khẩu 1 lần).
  - Đang chờ: cắm SSD sang host để flash `work/m1-p5-labeled.img` vào `/dev/sda5` (≈8 GiB), sau đó cắm
    lại Pi và boot. Kỳ vọng: init qua được `Loading SELinux policy`, vào `init second stage started!`
    và ta sẽ thấy lỗi kế tiếp (nếu có) thay vì panic im lặng.
- 2026-10-27 12:47 — **ĐỌC LẠI LOG 12:33: Pi KHÔNG hề chết ở 1 s. Kết luận trước đó của mình SAI.**
  File `work/pi-uart2.log` chứa cả lượt boot thật (in live qua earlycon, 0→5.17 s) ở **nửa đầu**
  (offset 837–47 587) và một bản replay/rác ở nửa sau. Trích đúng đoạn live thì thấy init đã chạy:
  - `[1.281400] Run /init as init process`, `[1.283000] init first stage started!`
  - `[1.283318] dt_fstab: Using a specified mount point / for system` → Fix 3 (`mnt_point="/"`) **có tác dụng**
  - `[1.301622] … waiting for their uevent(s): sda`; sda xuất hiện 2.81 s (Hynix V2, 60 GB)
  - `[2.851499] init: create_device_symlinks: device sda5`
  - `[2.863] sda7` mount r/w (metadata, kèm unmount → đó là `check_fs()`), `[3.007] sda5` check_fs,
    **`[3.124885] EXT4-fs (sda5): mounted … r/w`** (p5 mount **rw** đúng như Fix 2), `[3.130710] sda6` (vendor) ro
  - **`[3.203127] kvm: exiting hardware virtualization`** = reboot notifier, chạy do **PID 1 (T1) gọi
    `reboot()`** ngay 72 ms sau khi mount vendor. Kernel in `[5.175124] reboot: Restarting system with
    command 'bootloader'` (2 s là thời gian kernel shutdown, không phải init treo).
  - Không có log nào của init giữa 3.130 và 3.203, không `Switching root`, không `Opening SELinux policy`.
  Nguyên nhân mất log: **`mnt_point="/"` ⇒ KHÔNG có `SwitchRoot()`**. Init chỉ tạo tmpfs `/dev`
  (`first_stage_init.cpp:352`, kèm `/dev/kmsg` 1:11 dòng 371) rồi mount thẳng p5 lên `/`, nên tmpfs
  `/dev` bị **che** bởi `/dev` của p5. Từ đó mọi `LOG()` của init (kể cả `PLOG(FATAL)`, `InitFatalReboot:
  signal`, backtrace, `Reboot ending…`) đều mất — nên ta chỉ thấy "im lặng 2 s rồi reboot".
  Ngược lại, `TrySwitchSystemAsRoot()` → `SwitchRoot("/system")` (`switch_root.cpp:72`) **move** toàn bộ
  mount (/dev, /proc, /sys, /second_stage_resources…) vào root mới ⇒ `/dev/kmsg` giữ nguyên fd/inode ⇒
  log init sống tiếp. Đây là đường chuẩn của Android (system-as-root vẫn đúng: mount p5 vào `/system`,
  switch_root xong `/` = root của p5, `/system/bin/init` vẫn là file của p5).
- 2026-10-27 12:47 — Đã đổi fstab về `/system` và flash lại p1:
  - Tool mới: `work/fdt-fstab.py` (dump fstab trong .dtbo), `work/fdt-set-mnt.py` (sửa `mnt_point`/`mnt_flags`
    của 1 entry), `work/flash-p1.sh` (đã sửa `lsblk` để không chết vì `dirname /dev/sda1 = /dev`),
    `work/uart-summary.sh` (tóm tắt 1 lượt boot trong log UART).
  - `overlays/android-usb.dtbo`: `system.mnt_point` `/` → **`/system`** (`mnt_flags` giữ `rw,barrier=1`).
  - Ảnh mới `work/m1-usb64-p1sysroot.img`, sha256 `a200ac5ffd6314e45cb568796f31391049dbc245b0db1e4877523f9ddc9e2d5d`,
    `fsck.fat -n` sạch (391 files). Đã flash vào `/dev/sda1` bằng `sudo -A work/flash-p1.sh …`,
    readback sha256 **khớp**, fsck sạch. p5 (8 GiB) **không đổi**, không cần flash lại.
  - Bước kế: power-cycle, rồi đọc phần log mới: `tail -c +59110 work/pi-uart2.log > work/pi-uart3.log`
    (59 109 = kích thước log trước khi boot) và `work/uart-summary.sh work/pi-uart3.log`. Kỳ vọng:
    thấy `Switching root to '/system'` + `Opening SELinux policy` + lỗi thật (nếu có) của second stage.
- 2026-10-27 13:40 — **UART không hỏng**: log Pi vẫn về, watcher cũ bỏ sót vì đòi marker
  `Linux version` trong khi baseline đã nằm giữa lượt boot. `work/wait-pi.py` giờ nhận thêm mọi
  dòng printk (`[    0.825511][    T1] ...`) nên không bỏ sót nữa. 58 513 B log mới thực chất chứa
  389 dòng kernel/init: boot đã lên tới **system_server (pid 765)**, audioserver, gpuservice,
  servicemanager; `/data` (sda3) **mount r/w thành công 7.85 s** ⇒ nghi phạn "thiếu entry /data"
  trong fstab/`android-usb.dtbo` được **loại bỏ**.
- Lỗi chặn boot thật sự: `init: cannot execv('/system/bin/logd') … Permission denied` → logd chết
  (status 127, 4 lần) → `apexd: Native process 'logd' is crashing`, `sys.init.updatable_crashing=1`,
  và **mất toàn bộ logcat** (nên không thấy vì sao vold crash: `crash_dump64 denied {ptrace}
  tcontext=u:r:vold:s0`). Không hề có `avc: denied` cho logd ⇒ không phải SELinux.
- Nguyên nhân: cây p5 được copy từ host nên **uid/gid bị san phẳng về 0:0** (mode thì còn nguyên).
  `fs_config.cpp` yêu cầu `system/bin/logd` = `0550 AID_LOGD:AID_LOGD` (1036:1036); init `setuid/setgid`
  *trước* `execve`, nên uid 1036 rơi vào quyền `other = ---` ⇒ **EACCES**, không có avc.
  Kiểm chứng: ảnh cũ có `Mode: 0550` nhưng `User: 0 Group: 0`; policy CIL thì **có đủ** rule
  (`allow init logd_exec (file (read getattr map execute open))`, transition, entrypoint).
- Tool mới `work/fix-fsconfig.py`: tái lập `get_fs_config()` của libcutils (đọc
  `<partition>/etc/fs_config_{dirs,files}` trong ảnh trước, rồi bảng biên dịch `android_dirs`/
  `android_files`, cuối cùng mặc định 0:0 0755/0644) rồi ghi bằng `debugfs sif`. Kết quả trên ảnh:
  **261 đường dẫn sai gid, 2 sai uid, 0 sai mode** (logd → 1036:1036, `run-as` → 0:2000 0750).
- Bài học hạ tầng: **không ghi vào ảnh khi fuse2fs đang mount** — lần đầu vừa mount ro vừa chạy
  `debugfs ea_set` đã làm hỏng checksum superblock (`Checksum errors in superblock! Retrying...`,
  `e2fsck: Superblock checksum does not match`). Cả 2 tool giờ có `--plan FILE` để tách pha:
  mount → ghi plan → `fusermount -u` → `debugfs -w -f plan`. Ảnh `m1-p5-labeled.img` (hỏng superblock)
  **bỏ**, thay bằng `work/m1-p5-final.img` dựng lại từ `m1-p5-devnodes.img` theo quy trình 2 pha:
  4 990/4 992 nhãn, **0 sai khác uid/gid/mode**, `e2fsck -fn` sạch (5 002 inode / 1 298 782 block),
  sha256 `21b8393634eea6d0c582f005bb4542b66b4fac25d21fe1455309ef27ea04aa9a`.
- Bước kế: flash `work/m1-p5-final.img` vào `/dev/sda5` (`sudo -A work/flash-p5.sh`), boot lại.
  Kỳ vọng logd sống ⇒ logcat đổ ra `/dev/kmsg` ⇒ UART thấy lý do vold crash; nếu logo vẫn treo thì
  đọc `work/uart-summary.sh` trên log mới thay vì đoán.
- 2026-10-27 13:52 — **Đã flash p5**: `work/flash-p5.sh work/m1-p5-final.img /dev/sda5`, ghi 8 589 934 592 B
  (2048 records, 294.9 s, 29.1 MB/s do USB ~30 MB/s), readback sha256
  `21b83936…aa9a` **khớp tuyệt đối** với ảnh ⇒ nội dung p5 trên SSD = ảnh đã kiểm định
  (0 sai khác uid/gid/mode, 4 990 nhãn SELinux, `e2fsck -fn` sạch). Watcher đã armed với
  baseline 204 131 B: boot xong sẽ tự cắt ra `work/pi-uart6.log` (log này lần đầu tiên sẽ có cả
  logcat vì logd chạy được).
- 2026-10-27 14:10 — **BOOT ĐƯỢC.** Sau khi flash `m1-p5-final.img`, lượt boot mới (log `work/pi-uart6.log`,
  bản đã lọc rác ESP32: `work/pi-uart6b.log`) đi qua toàn bộ chỗ trước đây chết:
  - `[3.40] init: Opening SELinux policy` → `Compiling SELinux policy` → `Loading SELinux policy`
  - `[4.46] audit: type=1404 enforcing=1` (policy nạp sạch, chỉ warning `watch_mountns` không có trong policy)
  - `[4.48] init: init second stage started!`, load file_contexts từ đủ 5 nguồn
  - `[45.28] servicemanager: Caller(pid=751,uid=1000,sid=u:r:system_server:s0) …` ⇒ **system_server sống**
  - Trong vùng log của lượt này: `cannot execv` = **0**, `updatable_crashing` = **0**, `Permission denied` = **0**
    (2 dòng `cannot execv` còn trong log nằm ở byte ~2367/2403 = lượt boot 13:22 cũ).
  ⇒ Khẳng định: treo logo **không phải** SELinux, **không phải** `/data`; đúng là **uid/gid bị san phẳng**
  làm `logd` không exec được (0550 + gid sai ⇒ `other=---`). `work/fix-fsconfig.py` đã sửa đúng chỗ.
- Còn tồn (không chặn boot): 5 `avc: denied { set }` cho property từ `vendor_init` —
  `ro.boot.audio.tinyalsa.simulate_input`, `persist.bluetooth.a2dp_aac.vbr_supported`,
  `ro.lockscreen.disable.default`, `persist.device_config.mglru_native.lru_gen_config` ⇒ thêm
  `vendor_init` vào các `vendor_*_prop` đó nếu muốn audio/bluetooth sạch denial.
  Build là **user/release-keys** (`ro.debuggable=0`) nên không có `adb`, cũng không có shell console
  (`init.rc:1306 on init && property:ro.debuggable=1 → start console`) ⇒ muốn `logcat` phải đặt
  `ro.debuggable=1` trong `/system/build.prop` rồi flash lại p5.
- 2026-10-27 14:20 — **Boot được nhưng màn hình đen, không có UI.** system_server sống (pid 751 @45 s),
  DRM phía kernel tốt: `[drm] Initialized v3d 1.0.0 … on minor 0`, `vc4-drm axi:gpu: bound
  107c580000.hvs`, HDMI0/1 bound, `simple-framebuffer … fb0` ⇒ `/dev/dri/card0` có. Lưu ý build là
  `ro.build.flavor=desktop_system-user` (AOSP *desktop*/ARC-style, launcher = `NexusLauncherRelease`
  trong `system_ext/priv-app`, SystemUI = `SystemUITitan`, có `SetupWizardDesktopPrebuilt`) — rất khác
  một build điện thoại, nên "không có UI" có thể do home activity/desktop mode chứ không chỉ graphics.
  Không kết luận được gì thêm vì: (a) đoạn 4.5 s → 45 s của UART **bị mất** (kernel console drop +
  ESP32 reset chèn rác), (b) build `user`/`ro.debuggable=0` ⇒ **không adb, không shell console**.
- Đã sửa trong `work/m1-p5-final.img` (chưa flash), 2 thay đổi **chỉ để lấy log**:
  1. `/system/build.prop`: `ro.debuggable=0→1`, `ro.force.debuggable=0→1` (cùng độ dài 7546 B, ghi lại
     bằng debugfs, giữ `0644 root:root` + nhãn `system_file`) ⇒ `init.rc:1306 on init &&
     property:ro.debuggable=1 → start console` ⇒ **shell trên UART ttyAMA10**. Đã kiểm policy trong
     `plat_sepolicy.cil`: `(allow shell logd (unix_stream_socket (connectto)))` ⇒ `logcat` chạy được;
     `(allow shell servicemanager (service_manager (list)))` ⇒ `service list` được; shell ghi được
     `shell_data_file` ⇒ `/data/local/tmp`. Nhưng **không** có `allow shell system_server:*binder*`
     ⇒ `dumpsys`/`am`/`input` sẽ bị từ chối.
  2. `/system/etc/init/zzz-logcap.rc` (mới, 0644 root:root, `system_file`): service `logcap_early`
     (`on post-fs-data`) và `logcap_boot` (`on property:sys.boot_completed=1`, chờ 20 s) chạy bằng
     domain `shell`, ghi `logcat -b all -d` + `getprop` + `service list` + `dumpsys SurfaceFlinger/window/
     activity` ra `/data/local/tmp/{boot,boot-early}.log,{props,services,sf,window,acts}.txt` ⇒ đọc offline.
  `e2fsck -fn` sạch (5 003 inode / 1 298 783 block), sha256 mới
  `5716eb5da8e0d269d8d81f432c77594826ac70bdededa0fd64e1215fc94bb291`.
- Tool mới `work/pull-bootlogs.sh`: sau khi Pi chạy, tắt nguồn, cắm SSD về host rồi chạy script để hút
  các file log trên từ `/dev/sda3` bằng `debugfs` (không mount).
- Bước kế: flash lại p5 (sha trên), boot, chờ ~60 s; nếu vẫn đen thì (a) gõ `logcat -d -s SurfaceFlinger`
  trên UART shell, (b) tắt nguồn, cắm SSD về host, chạy `work/pull-bootlogs.sh` để lấy log đầy đủ.
- 2026-10-27 14:15 — Đã **flash** ảnh debug vào `/dev/sda5` (301 s ghi @28.5 MB/s, readback sha256
  `5716eb5d…b291` khớp tuyệt đối). Tìm hiểu thêm về stack đồ hoạ: Pi5 **không** đặt HAL đồ hoạ trong
  `/vendor/lib64/hw` mà trong **vendor APEX** (`/vendor/apex`), đúng như `device/brcm/rpi5/device.mk`:
  `com.android.hardware.graphics.composer.drm_hwcomposer.apex` (khai báo
  `android.hardware.graphics.composer3` **v4** `IComposer/default`), `…allocator.minigbm_gbm_mesa.apex`,
  `com.android.hardware.egl.mesa.apex`, `com.android.hardware.vulkan.broadcom.apex`. Matrix của p5 yêu cầu
  composer3 `4-5` + allocator `1-3` ⇒ **khớp version**. Vậy đen màn hình không phải do thiếu HAL
  version, mà do (a) apexd không active được vendor APEX, (b) SF/Mesa/minigbm lỗi runtime, hoặc
  (c) build desktop không có home activity. Cần logcat để phân biệt (xem `zzz-logcap.rc`).
- Tool mới `work/uart-console.py` (pyserial không có ⇒ dùng termios/select): console UART 2 chiều +
  ghi log; `Ctrl-]` để thoát. Có thể lái shell bằng cách `printf 'lệnh\n' > /dev/ttyUSB0` trong khi
  `cat /dev/ttyUSB0` vẫn ghi log.
