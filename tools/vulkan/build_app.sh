#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "$0")/../.." && pwd)
root=$(dirname -- "$project")
sdk="$root/aosp-rpi5/prebuilts/sdk"
native="$root/aosp-rpi5/prebuilts/runtime/mainline/runtime/sdk/android/arm64/lib"
cc="$root/aosp-rpi5/prebuilts/clang/host/linux-x86/clang-r596125/bin/clang"
source="$project/tools/vulkan/app"
out="$project/work/vulkan/app"
keys="$root/aosp-rpi5/build/make/target/product/security"
jdk="$root/aosp-rpi5/prebuilts/jdk/jdk25/linux-x86/bin"
mkdir -p "$out/classes" "$out/dex" "$out/lib/arm64-v8a"
"$cc" --target=aarch64-linux-android37 -ffreestanding -fPIC -shared -nostdlib -fuse-ld=lld -Wall -Wextra -Werror \
 -I "$root/aosp-rpi5/external/vulkan-headers/include" -I "$root/aosp-rpi5/libnativehelper/include_jni" \
 -Dmain=hoshino_probe_main "$native/crtbegin_so.o" "$project/tools/vulkan/v3dv_smoke.c" "$source/bridge.c" "$source/present.c" \
 -L "$native" -lc -ldl "$native/crtend_so.o" -o "$out/lib/arm64-v8a/libhoshinoprobe.so"
"$jdk/javac" --release 8 -classpath "$sdk/37.0/public/android.jar" -d "$out/classes" "$source/src/org/hoshino/diagnostics/GpuProbe.java"
"$jdk/java" -cp "$sdk/tools/linux/lib/d8.jar" com.android.tools.r8.D8 --min-api 36 --lib "$sdk/37.0/public/android.jar" --output "$out/dex" "$out/classes/org/hoshino/diagnostics/"*.class
"$sdk/tools/linux/bin/aapt2" link --manifest "$source/AndroidManifest.xml" -I "$sdk/37.0/public/android.jar" -o "$out/unsigned.apk"
cp "$out/dex/classes.dex" "$out/classes.dex"
(cd "$out" && zip -q -0 unsigned.apk classes.dex lib/arm64-v8a/libhoshinoprobe.so)
"$jdk/java" -jar "$sdk/tools/linux/lib/apksigner.jar" sign --key "$keys/testkey.pk8" --cert "$keys/testkey.x509.pem" --out "$out/HoshinoDiagnostics.apk" "$out/unsigned.apk"
"$jdk/java" -jar "$sdk/tools/linux/lib/apksigner.jar" verify "$out/HoshinoDiagnostics.apk"
printf 'Built: %s\n' "$out/HoshinoDiagnostics.apk"
