# Capture, sanitize and package a public image

Use the source at the release tag, Linux host tools listed in DEVELOPMENT.md,
at least24GiB free work space plus room for compressed assets, and a cleanly
shut down Pi SSD. The source USB disk must be entirely unmounted and identified
by exact serial. No source partition is written by the capture tool.

```bash
lsblk -o NAME,SIZE,MODEL,SERIAL,TRAN,MOUNTPOINTS
sudo python3 tools/capture_release.py /dev/sdX \
  /absolute/path/work/HoshinoOS-Pi5-YYYYMMDD.img --serial YOUR_SSD_SERIAL
python3 tools/package_release.py /absolute/path/work/HoshinoOS-Pi5-YYYYMMDD.img \
  /absolute/path/new-release-assets
```

## What capture does

1. Check USB identity, all mounts/swap, MBR/512-byte geometry and the tested
   p1/p5/p6/p7 sizes; run read-only source ext4 checks.
2. Rebuild FAT from current boot files with empty free space. Remove static
   serial/MAC cmdline tokens and explicitly request SELinux enforcing in the
   COPY. The Aluminium user init already enforced despite an obsolete
   permissive bring-up token on the tested source.
3. Copy allocated system/vendor blocks. Remove the preconfigured portssh
   endpoint, authorization and host key on the copy, then recopy allocated
   blocks so freed key blocks are not distributed.
4. Create new userdata and metadata; **never read/copy source userdata files**.
   Preserve Android-required ext4 features, including userdata casefold/quota/
   verity, while giving the new filesystems new UUIDs.
5. Check filesystem consistency, reset-safe Task Manager provider, HSUM boot
   default, CPU profile and Bluetooth boot configuration.
6. Scan private-key material. Known key-shaped resources inside two pristine
   input APKs are accepted only when their exact bytes match the locked SHA256
   in manifests/stock-apks.json. Unknown or changed files stop publication.
   APK signatures/resources are not rewritten to hide such matches.
7. Generate fresh MBR/EBRs and a compact15,360,000,000-byte disk image. Source
   gaps, old data/metadata, unallocated blocks and deleted files are not copied.
8. Write a public capture manifest without the workstation's identity or serial.

This is a targeted privacy cleanup of this project layout, not a general
forensic sanitization tool for arbitrary OS images. No image is uploaded by
capture. Temporary partition images are kept private and removed on completion.

## Package and validation levels

The packager streams zstd and splits at1900MiB when needed so every asset is
below GitHub's2GiB limit. SHA256SUMS covers compressed downloads; it does not
trigger an extra full raw SSD readback. Upload assets.json, capture manifest,
SHA256SUMS and all compressed parts together.
Fresh filesystem UUIDs/timestamps make this a repeatable assembly workflow,
not a bit-for-bit reproducible build. Published compressed digests identify
the exact downloadable artifacts.

Before release, validate archive decompression and the partition/filesystem
layout, confirm the Git tag matches the packaging scripts, and record whether
the assembled image itself has booted on hardware. A test of its underlying
components does not count as a fresh-image boot test. If that boot test is
pending, publish as a development prerelease and say so in the notes.

The first snapshot keeps the original Setup Wizard; data-held preferences and
app updates from the maintainer's installation are absent. Include concrete
install/decompress steps and known app/Vulkan/ANR limitations in release notes.
