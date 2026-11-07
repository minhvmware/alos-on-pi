> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# Đọc log sơ bộ — 2026-11-03

Phạm vi: log có sẵn; chưa boot lại, chưa sửa image hoặc flash thiết bị.
Không gộp các lần boot thành một timeline: UART có log cũ/replay và các image khác nhau.

## Bằng chứng hiện có

- `work/pi-uart6b.log:239`: init second stage đã chạy. Dòng 254–255 có lời gọi từ
  `system_server` pid 751 tại khoảng 45 giây, tìm `android.system.suspend.ISystemSuspend/default`
  và servicemanager không khởi động lazy service được. Điều này chứng minh process đã chạy,
  chưa chứng minh boot hoàn tất hoặc process tiếp tục sống ổn định.
- `work/bootlogs/boot-early.log:988`: ghi nhận `apexd.status=activated`.
  Các dòng 1008–1023 liệt kê EGL Mesa,
  allocator minigbm, composer và Vulkan Broadcom; dòng 1287 ghi `Marking APEXd as ready`.
  Giả thuyết toàn bộ vendor graphics APEX không kích hoạt được không được log này ủng hộ.
  Chưa có bằng chứng composer đăng ký Binder hay EGL render thành công.
- `work/bootlogs/boot-early.log:906`: KeyMint đăng ký IKeyMintDevice/default;
  dòng 936 đăng ký Keystore 2.0, dòng 1280 odsign xác nhận artifacts VALID.
  Lỗi đọc boot patchlevel trước đó chưa đủ để kết luận KeyMint chặn boot.
- GSC/TPM: có wait /dev/tpm0 10 giây, retry và SELinux denial; đây là phụ thuộc phần cứng
  desktop gốc còn sót lại. Có chi phí khởi động thấy được, chưa chứng minh là nguyên nhân màn hình đen.

## Giới hạn của capture

`boot-early.log` kết thúc khoảng 00:59:32.739, ngay sau odsign/APEX ready.
Không có log runtime SurfaceFlinger/composer, zygote hoặc launcher trong capture này.
Dòng monitoring sys.boot_completed=1 chỉ là đăng ký theo dõi, không phải boot completed.
Vì vậy chưa thể xác định màn hình đen do graphics HAL, framework hay desktop UI.

## Ưu tiên điều tra tiếp

1. SystemSuspend: kiểm tra service `system_suspend` có chạy/crash, Binder registration,
   linker và SELinux denial trong cùng một lượt boot. File rc Aluminium có khai báo service;
   không được suy ra binary bị thiếu chỉ từ lỗi lazy-start.
   Source AOSP tham chiếu `frameworks/base/services/core/jni/com_android_server_power_PowerManagerService.cpp:133`
   gọi `AServiceManager_waitForService` để lấy suspend HAL. Vì thế thiếu service có khả năng
   làm framework chờ; cần stack hoặc log mới để xác nhận trên binary Aluminium.
2. Capture liên tục sau APEX ready: init service state, logcat all buffers, SurfaceFlinger,
   composer, system_server và sys.boot_completed. Phân biệt HAL được mount và HAL thực sự chạy.
3. Chỉ điều tra launcher/SystemUI sau khi xác nhận SurfaceFlinger và display hoạt động.

README và bringup_status còn mô tả trạng thái cũ; dùng log trực tiếp và lịch sử
`docs/m1_port_plan.md` khi đối chiếu. Những kết luận ở đây là sơ bộ, không phải bản sửa đã kiểm thử.
