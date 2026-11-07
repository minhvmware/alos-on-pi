#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
workspace=$(dirname -- "$project")
sdk="$workspace/aosp-rpi5/prebuilts/sdk"
source_dir="$project/patches/graphics/compact-desktop-overlay"
output="$project/work/compact-desktop-overlay"
original="$workspace/aluminium-analysis/91b269229318b3dae45e08966e69e2991e52c039/extracted/extracted"
target="$original/system_ext/priv-app/NexusLauncherRelease/NexusLauncherRelease.apk"
keys="$workspace/aosp-rpi5/build/make/target/product/security"
mkdir -p "$output"
"$sdk/tools/linux/bin/aapt2" compile --dir "$source_dir/res" -o "$output/resources.zip"
"$sdk/tools/linux/bin/aapt2" link -o "$output/unsigned.apk" \
    --package-id 0x7e --allow-reserved-package-id \
    --manifest "$source_dir/AndroidManifest.xml" \
    -I "$sdk/37.0/public/android.jar" -I "$target" \
    "$output/resources.zip"
java -jar "$sdk/tools/linux/lib/apksigner.jar" sign \
    --key "$keys/testkey.pk8" --cert "$keys/testkey.x509.pem" \
    --out "$output/CompactDesktopGrid.apk" "$output/unsigned.apk"
java -jar "$sdk/tools/linux/lib/apksigner.jar" verify "$output/CompactDesktopGrid.apk"
"$sdk/tools/linux/bin/aapt2" dump xmltree \
    --file res/xml/spec_landscape_optimized_desktop_workspace.xml \
    "$output/CompactDesktopGrid.apk" > "$output/xml-readback.txt"
printf 'Built and signature-checked: %s\n' "$output/CompactDesktopGrid.apk"
printf 'Requires preinstalled product overlay placement and a physical boot check.\n'
