> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# UI/ANR follow-up — 2026-11-06

Live Vulkan hardware smoke test PASSED; see vulkan_validation.md.

Fresh boot log current-ui-anr-audit.log records Google Search interactor and
googleapp startup ANRs at10:45:01 and10:45:11. DropBox system_app_anr supplied
actual traces (anr-dropbox-review.txt): main thread state D while loading and
verifying APK dex, in adler32/DexFileVerifier/OpenFromZipEntry. CPU snapshots
show crosvm_security_vm at93–100% of one core and substantial I/O wait. These
are observed contributors, not proof that disabling the VM fixes the issue.
No security service disabled, no cache purge or format.

Applied targeted trial: cmd package compile -m verify -f
com.google.android.googlequicksearchbox. Success; package dump confirms
status=verify, reason=cmdline and /data/dalvik-cache output. This avoids
repeating unprepared APK verification where ART can reuse this cache.
No claim ANR solved: cold boot/restart validation remains. The Google Search
APK has no MAIN/LAUNCHER activity resolvable by the test intent, so attempting
that did not exercise application startup. No app data cleared.

RepairMode user0 crashed because vendor.google.desktop.serviceability was
only installed for user10. Ran install-existing --user0 for the same signed
package; installation/list check passed. Binding/no-crash on next boot still
needs verification; no APK replaced.

Launcher exit history returned no entries. lastanr returned none even though
logcat/DropBox contain startup ANRs; logcat/DropBox take precedence. No current
launcher crash/ANR was captured. Do not claim user's flicker is disproven.
Boot switched from system user0 to desktop10 around10:44:30. HOME resolution
user0 is SetupWizardActivity, user10 NexusLauncherActivity. This may explain
some visual transition but no screenshot/timing proof exists yet. Persistent
hsum_boot_strategy remains0. Do not disable system-user components blindly.

Full latest evidence: launcher-targeted-audit.txt, current-ui-anr-audit.log,
anr-dropbox-review.txt, search-dexopt-trial.log, search-dexopt-validation.log.
Need next cold boot and the exact flicker event's log/time for remaining UI
work. User permits considering reformat; no specific destructive scope was
chosen and none is justified by current evidence.
