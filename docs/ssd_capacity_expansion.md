> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# SSD capacity expansion — pending offline inspection

User requests using the entire Hynix USB SSD for HoshinoOS.
Live check 2026-11-06 over SSH confirmed `/data` is ext4 on
`/dev/block/sda3`, 5.5 GiB total, 4.6 GiB used, 585 MiB available (90%).
System is on sda5 and vendor on sda6: this is an installed SSD boot,
not a volatile live system. Expected SSD serial YOUR_SSD_SERIAL,
USB transport, approximately 55.9 GiB. Currently attached to Pi.

Offline procedure after clean Pi shutdown and attachment to laptop:

1. Identify by USB transport AND exact serial; never use laptop NVMe.
2. Inspect `sfdisk --json`, `lsblk`, `blkid`, filesystem features and all
   mount/swap users. All SSD partitions must be unmounted and unused.
3. Save partition table dump and raw MBR to a new backup directory.
4. Verify partition 3 is userdata ext4, physically last, with contiguous
   unused space after it. Preserve its start sector, type and UUID.
   Abort and reassess if layout differs; do not move/delete partitions.
5. Run `e2fsck -p` on userdata and stop on errors beyond corrected status.
6. Extend ONLY partition 3's end to the last usable disk sector with
   sfdisk; preserve all other entries. Reread table and verify starts,
   sizes and other partition entries before continuing.
7. Run `resize2fs` on userdata, followed by `e2fsck -fn`; confirm new
   filesystem block count fits partition and available space grew.
8. Sync and flush before unplugging. On Pi verify `df -h /data`, desktop
   user, installed apps and personal files. Do not reflash or format.

Use GUI sudo askpass if privilege is required; never store passwords.
No whole-disk SHA verification. Partition-table backups are not a backup
of personal files and must not be described as such.

Expected data capacity is roughly SSD capacity minus existing boot,
system, vendor and metadata partitions; compute exact value from the
actual partition table before mutation.

## Applied 2026-11-06

Exact serial checked, all partitions unmounted. Partition 3 start preserved at
17874944 sectors; its size extended from 12125056 to 99356464 sectors.
Filesystem now 12419072 blocks of 4096 bytes (~47.37 GiB).
Other partition-table entries unchanged; e2fsck -fn passed after resize.
Backups and check logs: work/ssd-expand-20261106-171929/.
Runtime df and data/app validation still require booting Pi.
