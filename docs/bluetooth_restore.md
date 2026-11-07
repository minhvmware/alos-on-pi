> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# Bluetooth boot configuration repair — 2026-11-06

Live Bluetooth enable failed in BLE_TURNING_ON. HAL could see WiFi rfkill0
but no Bluetooth rfkill entry; no HCI adapter appeared.

Actual SSD config.txt contained dtoverlay=disable-bt under the misleading
comment "Free UART0 from Bluetooth for serial console". Its overlay_map.dtb
maps this name on BCM2712 to disable-bt-pi5, which disables the bluetooth node.
Actual SSD DTB places Bluetooth under /soc@107c000000/serial@7d50c000;
GPIO UART console is /axi/pcie@1000120000/rp1/serial@30000. Separate UARTs.

Applied minimum change: removed active disable-bt overlay. Kept uart0=on,
uart0_console, firmware, kernel, HAL and policies unchanged.
Readback matched exact expected config. Backups:
work/bluetooth-restore-20261106-171958/config.txt.before and config.txt.after.

Initial FAT check reported an existing dirty bit and backup boot-sector
byte65 discrepancy. fsck.fat -a cleared the dirty state; subsequent
fsck.fat -n reported no errors. No reformat was performed.

Runtime pending: boot Pi, confirm HCI/rfkill device, enable Bluetooth,
check Bluetooth ON and scan, then pair Pixel7 Android16 with user action.
Do not claim pairing or complete Bluetooth success from offline edits.
