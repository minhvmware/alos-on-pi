> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# Original setup and performance — 2026-11-06

User chose original Google/Aluminium Setup Wizard and performance tweaks.

## Applied

Global window_animation_scale=0.5, transition_animation_scale=0.5,
animator_duration_scale=0.5. Readback confirmed. Original values were 1.0,
1.0 and absent respectively. This shortens UI animation duration; it does
not establish increased GPU throughput. Rollback via shell:

    settings put global window_animation_scale 1.0
    settings put global transition_animation_scale 1.0
    settings delete global animator_duration_scale

## Setup findings and blocker

Original APKs exist and are installed for user10:
com.google.android.desktop.setupwizard and com.google.android.setupwizard.
Original com.google.android.setupwizard.SetupWizardActivity is disabled
for user10. Desktop BootCompletedReceiver is also disabled. An attempt
to enable the latter from shell was rejected by PackageManager's component
state protection. No permission bypass was applied.

Desktop WELCOME_USER action starts but immediately routes to WizardManager
and finishes without a working setup session. Temporary user_setup_complete=0
was restored to 1. device_provisioned remains 1. No app data cleared.

Next maintenance requires root/offline SSD access to inspect the actual
user10 package restriction state and restore the original setup entry.
Preserve existing users and data; do not factory reset or clear global
provisioning blindly. Save restrictions/settings and prepare rollback before
changing them. Validate full setup flow, not merely am start Status:ok.

Evidence: work/setup-current-package.txt, setup-google-package.txt,
setup-replay-attempt.txt, setup-original-entry.txt, setup-replay-log.txt.

## Performance evidence

One top sample showed near-full CPU use while TikTok and Lightroom were
running/starting. crosvm_security_vm used ~55% of one core. This is a sample,
not an idle benchmark or proof of a particular performance regression.
Repeated gscd TPM-not-found aborts still occur. No security VM/TPM services
have been disabled. RAM cached ~4.4GiB is reclaimable and not by itself a leak.
No forced cache flushing, CPU overclock or thermal limit changes applied.
See work/setup-start-performance-before.txt and setup-performance-after.txt.

## Bluetooth next fault

After boot configuration repair, adapter address is present and BLE_ON is
reached, but Bluetooth aborts at FetchAudioProvider:
IBluetoothAudioProvidersFactory::openProvider(A2DP_SOFTWARE_ENCODING_DATAPATH)
failed 3 times. Concurrent hal_audio_default denials: write tmpfs:file on
memfd:MessageQueue. Investigate shared-memory policy/kernel compatibility
and provider creation before patching. This is a new failure beyond missing
HCI; Bluetooth is not yet working fully. Logs: work/boot-after-bt-restore.log.

## Capacity runtime validation

After reboot, df shows /data filesystem 46G total, 13G used, 30G available,
31% used. sys.boot_completed=1. Userdata expansion works at runtime.
