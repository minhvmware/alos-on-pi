# Install the Pi 5 development image

This is an experimental desktop port, not a stable daily-use release. Download
the image assets from [Releases](https://github.com/minhvmware/alos-on-pi/releases).
GitHub's automatic **Source code** ZIP contains scripts, not a bootable OS.

## Hardware and host requirements

- Raspberry Pi 5, adequate Pi5 power supply, HDMI screen, USB keyboard/mouse.
- USB SSD/enclosure with at least15,360,000,000bytes available;16GB or larger
  media normally meets this size. USB boot is the tested path. SD/NVMe support
  is not established by this release; do not change boot overlays at random.
- Linux host: Python3, util-linux (`lsblk`, `sfdisk`, `blockdev`), coreutils,
  e2fsprogs and zstd. mtools/dosfstools are needed for image development, not
  the normal unchanged-image flash command.

The image is about14.3GiB when decompressed. Allow enough free host space.
Flashing erases the selected target; identify it by model, size and serial.

## Download and decompress

Download **all image parts**, `SHA256SUMS`, `assets.json` and the
`*.release.json` manifest from the same release into one directory.
Each compressed asset is below GitHub's2GiB per-file limit.

```bash
# Optional check of downloaded compressed files, not a full SSD readback:
sha256sum -c SHA256SUMS

# A release with one compressed file:
zstd -d HoshinoOS-Pi5-20261107.img.zst

# OR a split release; concatenate parts in numerical order:
cat HoshinoOS-Pi5-20261107.img.zst.[0-9][0-9][0-9] \
  | zstd -d -o HoshinoOS-Pi5-20261107.img
```

Use the single-file or split command matching `assets.json`, not both.
On Windows, numbered parts can be joined using `copy /b part.001+part.002
joined.img.zst` with the actual complete part list, then decompressed with a
zstd-capable extractor. The supported guarded flash commands below use Linux.

## Flash, preview first

Clone this repo or unpack its source ZIP, then run from its root:

```bash
lsblk -o NAME,SIZE,TYPE,MODEL,SERIAL,TRAN,MOUNTPOINTS

# Unmount target partitions using your disk manager. Choose the actual disk;
# /dev/sdX below is a placeholder, never a device name to copy blindly.
python3 tools/flash_release.py /absolute/path/HoshinoOS-Pi5-20261107.img \
  /dev/sdX --serial YOUR_SSD_SERIAL

# Read the preview, then execute the write explicitly:
sudo python3 tools/flash_release.py /absolute/path/HoshinoOS-Pi5-20261107.img \
  /dev/sdX --serial YOUR_SSD_SERIAL --write
```

This writer checks exact USB identity, disk size, partitions, mount/swap state,
then writes and flushes with start/end readback. It does not patch the supplied
image or add a second full-disk hash pass. The older `flash_rpi5_sd.sh` is for
baseline development; use `flash_release.py` for this already-configured image.

## Use the rest of a larger SSD

The download has a compact data partition so it fits smaller media. It is a
persistent installation, not a volatile live session. To use the rest of your
SSD, while it is still attached to Linux and all partitions are unmounted:

```bash
sudo python3 tools/grow_userdata.py /dev/sdX --serial YOUR_SSD_SERIAL
sudo python3 tools/grow_userdata.py /dev/sdX --serial YOUR_SSD_SERIAL \
  --write --backup /absolute/path/new-partition-backup
```

The first command previews. The second backs up the partition table/MBR,
checks the filesystem, grows final partition3 without moving its start, runs
resize2fs and checks/flushes it. Existing other partitions are preserved.
The backup directory must not already exist. It is a table backup, not a
replacement for backing up personal files before later storage changes.

## First boot

Safely eject the SSD, attach it to Pi5, connect screen/input/network and power
on. The original Google/Aluminium setup is retained. Fresh data has no accounts,
Wi-Fi credentials, Chrome profile or personal app updates. Complete setup and
connect Wi-Fi/Ethernet. First-boot package compilation can be slow; record UART
if it never progresses instead of repeatedly cutting power.

The packaged image is derived from the boot-tested component installation;
the fresh reset, sanitization and compact disk assembly have **not** received
a separate physical boot test. See the validation level in the release notes.

Defaults retained: Pi kernel/vendor/Mesa, CPU schedutil without overclock,
Task Manager provider and desktop boot strategy. Density160, mouse preferences
and Chrome profile flags were user settings before reset and are not assumed
to survive. See [first-boot configuration](FIRST_BOOT.md).

## Diagnostics and recovery

The release has **no preconfigured SSH server/key**. UART shell diagnostics
remain available on this development build; see [developer guide](DEVELOPMENT.md).
Keep your previous known-good image separately. Reflashing the development
image resets data; do not use it as an in-place updater.

Known gaps include startup ANRs, incomplete Chrome ANGLE Vulkan compatibility,
incomplete Bluetooth/audio/video testing, and no production AVB/OTA workflow.
Read [STATUS.md](STATUS.md) before filing a regression.
