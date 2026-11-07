> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# Host extraction toolchain

Cập nhật: 2026-10-24. Toolchain nằm trong `toolchain/` (bị `.gitignore` loại khỏi version control), chạy với user hiện tại, không cần root. Nạp PATH bằng:

```sh
source /path/to/hoshinoos/aluminium-rpi5/tools/env.sh
/path/to/hoshinoos/aluminium-rpi5/tools/extract_aluminium.sh --check
```

Các script extract/capture tự source `env.sh`. Không có full AOSP sync hoặc full AOSP build nào được thực hiện để cài toolchain.

## 1. Fedora package chính thức

`sudo` trên host yêu cầu xác thực tương tác, nên RPM chính thức được tải và giải nén user-local thay vì cài system-wide. Đây vẫn là binary do Fedora phân phối, không phải binary từ nguồn không rõ.

| Trường | Giá trị |
|---|---|
| Repository | Fedora 44 `updates` |
| RPM | `android-tools-37.0.0p1-1.fc44.x86_64.rpm` |
| Epoch/version/release | `1:37.0.0p1-1.fc44` |
| Vendor | Fedora Project |
| RPM SHA256 | `3eca6631a2720cfeb77d82fce99cfb0a31e34a296073911add748e33204cf159` |
| Extraction root | `toolchain/fedora-android-tools/` |

RPM này cung cấp đủ năm dependency được ưu tiên tìm từ distro:

- `adb` — đã chạy `adb --version`: Android Debug Bridge 1.0.41, `37.0.0p1-android-tools`.
- `simg2img` — đã chạy usage và chuyển sparse system/super thành raw trong test.
- `lpunpack` — đã extract dynamic super test.
- `avbtool` — `avbtool version` trả về 1.4.0.
- `unpack_bootimg` — đã unpack Android boot header v4 và vendor_boot header v4.

Các tiện ích bổ sung từ cùng RPM cũng được expose: `fastboot`, `mkbootimg`, `img2simg`, `lpmake`, `lpdump`. `lpmake` chỉ dùng tạo fixture test; chưa có repack Aluminium/Pi image thật.

`ldd` của `adb`, `simg2img`, `lpunpack` không có library `not found`; các dependency resolve bằng shared libraries đã có trên Fedora host.

## 2. `magiskboot` build từ upstream

Fedora repositories không có provider cho `magiskboot`. Binary được build từ Magisk upstream, không dùng prebuilt APK/release binary.

| Trường | Giá trị |
|---|---|
| Source | `https://github.com/topjohnwu/Magisk.git` |
| Tag | `v31.0` |
| Commit | `96221b69fae9910b1c0c75c2f92a4ebb2c2dc698` |
| Build command | `python3 build.py -r -c config.host.prop native magiskboot` |
| Target | chỉ `magiskboot`, `x86_64`; không build app/APK |
| Build toolchain | ONDK `r30.1`, do `build.py ndk` tải từ `topjohnwu/ondk` |
| Output | ELF x86-64 statically linked |
| Binary SHA256 | `83f9ec1e2946668f3eb63c50ba2b72c5339603457e0d656a740067fe3af4afb2` |

ONDK URL được build script xác định là:

```text
https://github.com/topjohnwu/ondk/releases/download/r30.1/ondk-r30.1-linux.tar.xz
```

Git submodule commits đã khóa theo superproject:

| Submodule | Commit |
|---|---|
| `crt0` | `49bbd472a250e75315a9183586fab1e0c0982618` |
| `cxx-rs` | `b09b91554b392523f633b9e3cbe0b43273528c71` |
| `libcxx` | `130833618a50ff724a637d54fcb888d170ff9818` |
| `lsplt` | `7d609ac3c2d8faa0c830b0904024ef5c81a98e6e` |
| `lz4` | `d44371841a2f1728a3f36839fd4b7e872d0927d3` |
| `selinux` | `be1b39a657fee7faacfae548b75cb53302043a01` |
| `system_properties` | `2bf706b2a72caaf105d45e5929bb246068be4edc` |

`magiskboot --help` trả usage nhưng exit 1 ở phiên bản này; đây là behavior của CLI, không phải build failure. Extractor đã dùng binary để decompress và extract `newc` ramdisk từ boot, vendor_boot và FAT fixtures.

## 3. Host utilities cho filesystem và full disk

Các package sau đã có sẵn từ Fedora và được giữ nguyên:

| Package | Version | Công cụ sử dụng |
|---|---|---|
| `util-linux` | `2.41.5-1.fc44` | `sfdisk`, `blkid` |
| `e2fsprogs` | `1.47.3-4.fc44` | `debugfs` |
| `mtools` | `4.0.49-3.fc44` | `mcopy`, FAT boot extraction |
| `file` | `5.46-10.fc44` | File type evidence |
| `python3` | `3.14.8-1.fc44` | Partition JSON, VINTF/static reports |

Extractor không mount, không tạo loop device và không mở input ở chế độ ghi. Full disk được đọc bằng `sfdisk --json`; partition bytes được copy theo offset. Extended MBR partition chỉ là container nên không được extract như filesystem.

Filesystem hiện hỗ trợ extract: ext2/3/4 bằng `debugfs`, FAT bằng `mcopy`, EROFS bằng `fsck.erofs --extract`. F2FS được giữ raw và extractor dừng với lỗi rõ ràng thay vì báo “complete” thiếu dữ liệu. Nếu Aluminium image thật dùng F2FS, phải bổ sung extractor tương ứng trước khi hoàn tất Phase 0.

## 4. Reproduce toolchain

Biến `ROOT` dưới đây phải là đường dẫn tuyệt đối của project:

```sh
ROOT=/path/to/hoshinoos/aluminium-rpi5
mkdir -p "$ROOT/toolchain"/{rpms,bin,src,fedora-android-tools}
dnf --disablerepo='*' --enablerepo=updates download \
  --destdir "$ROOT/toolchain/rpms" android-tools
RPM="$ROOT/toolchain/rpms/android-tools-37.0.0p1-1.fc44.x86_64.rpm"
(cd "$ROOT/toolchain/fedora-android-tools" && rpm2cpio "$RPM" | cpio -idmu)
for tool in adb fastboot simg2img lpunpack lpdump lpmake avbtool \
            unpack_bootimg mkbootimg img2simg; do
  ln -sfn "../fedora-android-tools/usr/bin/$tool" "$ROOT/toolchain/bin/$tool"
done

git clone --branch v31.0 --depth 1 --recurse-submodules \
  https://github.com/topjohnwu/Magisk.git "$ROOT/toolchain/src/Magisk"
git -C "$ROOT/toolchain/src/Magisk" checkout \
  96221b69fae9910b1c0c75c2f92a4ebb2c2dc698
git -C "$ROOT/toolchain/src/Magisk" submodule update --init --recursive
```

`config.host.prop` dùng cho build:

```ini
version=31.0-host
versionCode=31000
outdir=out-host
abiList=x86_64
```

Sau đó:

```sh
cd "$ROOT/toolchain/src/Magisk"
export ANDROID_HOME="$ROOT/toolchain/android-sdk"
python3 build.py ndk
python3 build.py -r -c config.host.prop native magiskboot
cp native/out/x86_64/magiskboot "$ROOT/toolchain/bin/magiskboot"
```

## 5. Validation đã chạy

Synthetic fixtures nằm ngoài repository và không được dùng làm Aluminium evidence. Test bao phủ:

- thư mục nhiều `.img`; một image riêng với tên không theo chuẩn;
- Android sparse system, dynamic sparse/raw super;
- `super` nằm trong GPT full disk, không dựa vào filename;
- Android boot v4, vendor_boot v4 và nhiều tên ramdisk fragment;
- FAT32 boot có `ramdisk.img`;
- MBR có primary + extended/logical p1/p3/p5/p6/p7 và GPT;
- properties, VINTF XML/HAL, init services, APEX, SELinux file inventory;
- generated static Phase 0 reports và hardware compatibility triage;
- SHA256 input trước/sau extraction không đổi; output cũ bị từ chối ghi đè.

Đây là test công cụ, không phải kết quả reverse-engineer AluminiumOS. Pi boot/runtime log, semantic `checkvintf`, SELinux denial audit và hardware validation vẫn chưa có.

## 6. OTA payload dumper

Sau khi nhận OTA `91b269229318b3dae45e08966e69e2991e52c039.zip`, Fedora vẫn không có provider cho `payload-dumper-go`; công cụ được build từ source:

| Trường | Giá trị |
|---|---|
| Source | `https://github.com/ssut/payload-dumper-go.git` |
| Branch/revision | `main`, commit `c3a50ba8d784764c06143c1f82971cd81a77f9d6` |
| Build metadata | `vcs.modified=false`; `go version -m` xác nhận cùng commit |
| Bootstrap | Fedora `golang-1.26.10-1.fc44`, `golang-bin`, `golang-src`, `go-filesystem` |
| Build toolchain | Go `1.27.0` theo `go.mod`, tải bằng `GOTOOLCHAIN=go1.27.0` |
| Binary SHA256 | `d35e9d2037b47d41844c71735eb567bf0a3074ae8a37ac7eeebeaf82468dedd5` |
| Runtime libraries | `liblzma.so.5`, `libresolv.so.2`, `libc.so.6`; tất cả resolve trên host |

Build command:

```sh
cd /path/to/hoshinoos/aluminium-rpi5/toolchain/src/payload-dumper-go
export GOROOT=/path/to/hoshinoos/aluminium-rpi5/toolchain/fedora-golang/usr/lib/golang
export PATH="$GOROOT/bin:/usr/bin:/bin"
export GOTOOLCHAIN=go1.27.0
export GOMODCACHE=/path/to/hoshinoos/aluminium-rpi5/toolchain/go-mod-cache
export GOCACHE=/path/to/hoshinoos/aluminium-rpi5/toolchain/go-build-cache
go build -trimpath -ldflags='-s -w' \
  -o /path/to/hoshinoos/aluminium-rpi5/toolchain/bin/payload-dumper-go .
```

Dumper đọc trực tiếp OTA ZIP/payload, hỗ trợ list partitions, verify operation/source/output SHA256 và tái tạo dm-verity FEC. Extraction thật giữ verification/FEC mặc định, không dùng `-no-verify` hoặc `-no-fec`.

## 7. Công cụ phân tích filesystem/APEX/SELinux/protobuf

Các package chính thức bổ sung khi image thật dùng EROFS và cần phân tích policy/APEX:

| Package | Version | RPM SHA256 | Dùng cho |
|---|---|---|---|
| `erofs-utils` | `1.9.4-1.fc44` | `1a1b0df0d95c91b97d6ccebbb809e0d7c54f67105445850c41b411cb82c7908f` | `fsck.erofs --extract`, `dump.erofs` |
| `intel-qpl` | `1.9.0-3.fc44` | `bc10e5c4fb6b014dd047a9e5182190bbdb8d56fea47afa6879d1662067bb5771` | `libqpl.so.1` cho erofs-utils |
| `setools-console` | `4.6.0-6.fc44` | `4914209d53c5f061b4d176a176761ab5f6949d4e67f052057cc27988ec290066` | `seinfo`, `sesearch` |
| `protobuf-compiler` | `3.19.6-20.fc44` | `4129d67d4270d6c1f64908625628836fc6385d890992d6925b1fc4cfe8df1caa` | decode OTA/APEX protobuf |
| `protobuf` | `3.19.6-20.fc44` | — | `libprotoc.so.30` |

- Fedora 1.9.4 không ship `extract.erofs`; extractor dùng `fsck.erofs --extract=DIR --no-preserve-owner --preserve-perms`.
- `python3-setools` 4.6.0 đã có trên host, nên `seinfo` console dùng Python/setools host; `tools/env.sh` thêm `LD_LIBRARY_PATH` cho `libqpl` và `libprotoc` user-local.
- Protobuf schema lấy trực tiếp từ AOSP `android-17.0.0_r1`:
  - `system/update_engine/update_metadata.proto`, commit peeled `4591637f51644f5429f9e2fe589ab22b92f61842`, dùng decode `apex_info.pb`/payload manifest.
  - `system/apex/proto/apex_manifest.proto` và `apex_build_info.proto`, commit peeled `ce2bb9f710183c864040401d859874b5723e44d8`, dùng decode APEX manifest.
- `tools/ikconfig.py` đọc marker `IKCFG_ST`/`IKCFG_ED` và giải nén kernel config bằng Python standard library.
- APEX payload được extract bằng `unzip -p ... apex_payload.img` + `fsck.erofs`/`debugfs`; 46/46 APEX thật thành công.

## 8. Validation trên OTA thật

- `tools/extract_aluminium.sh` rc=0 trên 15 partition: 6 EROFS, 1 ext4, 2 FAT, 4 Android boot/vendor_boot/pvmfw, 2 raw (`dtbo`, `vbmeta`).
- Kernel LZ4 decompress và IKCONFIG pass; `seinfo` chạy trên normal precompiled policy và recovery policy; VINTF static comparison chạy với Pi device source.
- 2,432 ELF parse được (1,749 partition + 683 APEX) có alignment 16K; APEX manifest 46/46 decode.
- SHA256 mọi input không đổi; các output cũ bị từ chối ghi đè; synthetic regression đã pass trước đó và extractor phiên bản cuối chạy end-to-end rc=0 trên OTA thật.

## 9. AOSP build tooling cho Pi baseline

- `repo` launcher 2.69 tải từ `https://storage.googleapis.com/git-repo-downloads/repo`, SHA256 `6ed2f6325705b6ea0af99466d6ebd04adec387a5b6a906cd77bc8c6da65123e5`, đặt tại `toolchain/bin/repo`.
- Dependency build user-local từ Fedora: `bison 3.8.2`, `flex 2.6.4`, `gperf 3.2.1`, `lz4 1.10.0`, `ccache 4.12.3`, `ncurses-devel 6.6`, `openssl-devel 3.5.9`, giải nén tại `toolchain/fedora-builddeps`.
- `tools/aosp_env.sh` nạp PATH/CPATH/LIBRARY_PATH/PKG_CONFIG_PATH cho workspace AOSP; JDK dùng prebuilt của AOSP.
- Filen CLI 0.2.9 được thử cho prebuilt cộng đồng nhưng không hỗ trợ public-link download anonymous; không dùng trong workflow.
- Chi tiết workspace, giới hạn RAM/disk, lệnh build, flash và M0 checklist nằm trong `docs/rpi5_build_plan.md`.
