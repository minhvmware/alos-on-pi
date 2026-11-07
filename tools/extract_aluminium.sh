#!/usr/bin/env bash
# Read-only Android image extraction. Never mounts or modifies input images.
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"

usage() {
    cat <<'EOF'
Usage: extract_aluminium.sh --input IMAGE_OR_DIRECTORY --output NEW_OUTPUT_DIR
       extract_aluminium.sh --check

Input may be a directory of .img files, one partition image, an Android
boot/vendor_boot/init_boot image, a sparse/raw super.img, or an MBR/GPT disk.
The output path must not exist. No root, loop device or mount is used.
EOF
}

check_only=0
input=
output=
while (($#)); do
    case "$1" in
        -i|--input) input=${2:?missing value for $1}; shift 2 ;;
        -o|--output) output=${2:?missing value for $1}; shift 2 ;;
        --check) check_only=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
done

missing=()
for tool in debugfs fsck.erofs lpunpack lpdump simg2img avbtool unpack_bootimg magiskboot \
            sha256sum file od strings blkid sfdisk python3 mcopy; do
    command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
done
if ((${#missing[@]})); then
    printf 'Missing tools: %s\n' "${missing[*]}" >&2
    printf 'Run: source %q\n' "$SCRIPT_DIR/env.sh" >&2
    exit 1
fi
if ((check_only)); then
    printf 'All extraction tools are available.\n'
    adb --version | head -3
    avbtool version
    magiskboot 2>&1 | head -2 || true
    exit 0
fi
[[ -n $input && -n $output ]] || { usage >&2; exit 2; }
[[ -f $input || -d $input ]] || { printf 'Not a file/directory: %s\n' "$input" >&2; exit 1; }
[[ ! -e $output ]] || { printf 'Refusing existing output path: %s\n' "$output" >&2; exit 1; }
input=$(realpath "$input")
output=$(realpath -m "$output")

images=()
if [[ -d $input ]]; then
    mapfile -t images < <(find "$input" -maxdepth 1 -type f -name '*.img' -print | sort)
    ((${#images[@]})) || { printf 'No .img files found in %s\n' "$input" >&2; exit 1; }
else
    images=("$input")
fi
mkdir -p "$output"/{raw,extracted,ramdisks,metadata,reports}
: >"$output/metadata/input-images.sha256"
: >"$output/metadata/file-types.txt"
printf 'input\traw\tclass\tfilesystem\textracted\n' >"$output/metadata/image-inventory.tsv"
for src in "${images[@]}"; do
    sha256sum "$src" >>"$output/metadata/input-images.sha256"
done

materialize() {
    local src=$1 dst=$2 magic
    magic=$(od -An -tx1 -N4 "$src" | tr -d ' \n')
    if [[ $magic == 3aff26ed ]]; then
        simg2img "$src" "$dst"
    else
        cp --reflink=auto --sparse=always "$src" "$dst"
    fi
}

record() {
    printf '%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "$5" \
        >>"$output/metadata/image-inventory.tsv"
}

avb_info() {
    avbtool info_image --image "$1" >"$2" 2>&1 || true
}

unpack_ramdisk() {
    local src=$1 label=$2 cpio="$output/raw/${label}.cpio"
    local dst="$output/ramdisks/$label"
    if [[ ! -s $src ]]; then
        printf '%s\tEMPTY\n' "$label" >>"$output/metadata/ramdisks.txt"
        return 0
    fi
    mkdir -p "$dst"
    if ! magiskboot decompress "$src" "$cpio" \
            >"$output/metadata/${label}.decompress.txt" 2>&1; then
        cp --reflink=auto "$src" "$cpio"
    fi
    if (cd "$dst" && magiskboot cpio "$cpio" extract) \
            >"$output/metadata/${label}.cpio.txt" 2>&1; then
        printf '%s\t%s\n' "$label" "${src#"$output/"}" >>"$output/metadata/ramdisks.txt"
    else
        printf 'Could not unpack ramdisk %s; see %s.cpio.txt\n' "$label" "$label" >&2
        return 1
    fi
}

inspect_kernel() {
    local src=$1 base=$2 raw="$output/raw/${base}.kernel"
    [[ -s $src ]] || return 0
    if ! magiskboot decompress "$src" "$raw" \
            >"$output/metadata/${base}.kernel-decompress.txt" 2>&1; then
        cp --reflink=auto "$src" "$raw"
    fi
    {
        file "$src"
        file "$raw"
        strings "$raw" | grep -m3 -E 'Linux version [0-9]' || true
    } >"$output/metadata/${base}.kernel-info.txt"
    python3 "$SCRIPT_DIR/ikconfig.py" --input "$raw" \
        --output "$output/metadata/${base}.kernel.config" \
        >"$output/metadata/${base}.ikconfig.txt" 2>&1 || true
}

unpack_boot() {
    local src=$1 base=$2 dst="$output/extracted/$base"
    mkdir -p "$dst"
    unpack_bootimg --boot_img "$src" --out "$dst" \
        >"$output/metadata/${base}.boot-info.txt" 2>&1
    inspect_kernel "$dst/kernel" "$base"
    local ramdisk relative label
    while IFS= read -r -d '' ramdisk; do
        relative=${ramdisk#"$dst/"}
        label="${base}_$(printf '%s' "$relative" | tr '/ ' '__')"
        unpack_ramdisk "$ramdisk" "$label"
    done < <(find "$dst" -type f \( -name ramdisk -o -name ramdisk.img -o -name 'vendor_ramdisk*' \) -print0)
}

extract_fat() {
    local src=$1 base=$2 dst="$output/extracted/$base"
    mkdir -p "$dst"
    mcopy -s -i "$src" :: "$dst" >"$output/metadata/${base}.mcopy.txt" 2>&1
    local ramdisk relative label
    while IFS= read -r -d '' ramdisk; do
        relative=${ramdisk#"$dst/"}
        label="${base}_$(printf '%s' "$relative" | tr '/ ' '__')"
        unpack_ramdisk "$ramdisk" "$label"
    done < <(find "$dst" -type f -name 'ramdisk*.img' -print0)
}

extract_ext() {
    local src=$1 dst=$2 label=$3
    mkdir -p "$dst"
    debugfs -R stats "$src" >"$output/metadata/${label}.filesystem.txt" 2>&1
    debugfs -R "rdump / \"$dst\"" "$src" >"$output/metadata/${label}.debugfs.txt" 2>&1
}

process_raw() {
    local raw=$1 base=$2 origin=$3 magic fs_type logical
    printf 'Processing %s\n' "${raw#"$output/"}"
    file "$raw" >>"$output/metadata/file-types.txt"
    avb_info "$raw" "$output/metadata/${base}.avb.txt"
    magic=$(od -An -tx1 -N8 "$raw" | tr -d ' \n')
    if [[ $magic == 414e44524f494421 || $magic == 564e4452424f4f54 ]]; then
        unpack_boot "$raw" "$base"
        record "$origin" "${raw#"$output/"}" android-boot '' "extracted/$base"
        return
    fi
    logical=${base%_a}
    logical=${logical%_b}
    fs_type=$(blkid -p -o value -s TYPE "$raw" 2>/dev/null || true)
    local is_super=0
    if [[ $logical == super ]]; then
        is_super=1
        lpdump "$raw" >"$output/metadata/${base}.lpdump.txt" 2>&1 || true
    elif [[ -z $fs_type ]] && \
            lpdump "$raw" >"$output/metadata/${base}.lpdump.txt" 2>&1; then
        is_super=1
    fi
    if ((is_super)); then
        mkdir -p "$output/raw/${base}_super"
        lpunpack "$raw" "$output/raw/${base}_super" \
            >"$output/metadata/${base}.lpunpack.txt" 2>&1
        record "$origin" "${raw#"$output/"}" dynamic-super '' "raw/${base}_super"
        local child child_name
        for child in "$output/raw/${base}_super"/*.img; do
            [[ -f $child ]] || continue
            child_name=${child##*/}
            process_raw "$child" "${base}_super_${child_name%.img}" "${child#"$output/"}"
        done
        return
    fi
    case "$fs_type" in
        ext2|ext3|ext4)
            extract_ext "$raw" "$output/extracted/$base" "$base"
            record "$origin" "${raw#"$output/"}" filesystem "$fs_type" "extracted/$base"
            ;;
        vfat|msdos)
            extract_fat "$raw" "$base"
            record "$origin" "${raw#"$output/"}" filesystem "$fs_type" "extracted/$base"
            ;;
        erofs)
            mkdir -p "$output/extracted/$base"
            fsck.erofs --extract="$output/extracted/$base" \
                --no-preserve-owner --preserve-perms "$raw" \
                >"$output/metadata/${base}.erofs.txt" 2>&1
            record "$origin" "${raw#"$output/"}" filesystem "$fs_type" "extracted/$base"
            ;;
        f2fs)
            printf 'Unsupported filesystem %s in %s; raw image preserved.\n' \
                "$fs_type" "$raw" >&2
            record "$origin" "${raw#"$output/"}" unsupported-filesystem "$fs_type" ''
            return 1
            ;;
        *)
            record "$origin" "${raw#"$output/"}" raw "$fs_type" ''
            ;;
    esac
}

process_disk() {
    local raw=$1 base=$2 origin=$3 dir="$output/raw/${base}_disk"
    python3 "$SCRIPT_DIR/extract_disk.py" --image "$raw" --output "$dir" \
        --metadata-prefix "$output/metadata/${base}.disk"
    record "$origin" "${raw#"$output/"}" full-disk '' "raw/${base}_disk"
    local child child_name
    for child in "$dir"/p*.img; do
        [[ -f $child ]] || continue
        child_name=${child##*/}
        process_raw "$child" "${base}_${child_name%.img}" "${child#"$output/"}"
    done
}

: >"$output/metadata/ramdisks.txt"
for src in "${images[@]}"; do
    name=${src##*/}
    base=${name%.img}
    raw=$output/raw/$name
    file "$src" >>"$output/metadata/file-types.txt"
    materialize "$src" "$raw"
    origin=${src#"$input"}
    [[ -n $origin ]] || origin=$name
    if sfdisk --json "$raw" 2>/dev/null | python3 -c \
            'import json,os,sys; t=json.load(sys.stdin).get("partitiontable", {}); p=t.get("partitions", []); s=int(t.get("sectorSize",512)); z=os.path.getsize(sys.argv[1]); ok=t.get("label") in ("dos","gpt") and s>0 and bool(p) and all(int(x["start"])>=0 and int(x["size"])>0 and (int(x["start"])+int(x["size"]))*s<=z for x in p); sys.exit(not ok)' "$raw" \
            2>/dev/null; then
        process_disk "$raw" "$base" "$origin"
    else
        process_raw "$raw" "$base" "$origin"
    fi
done

roots=("$output/extracted" "$output/ramdisks")
: >"$output/metadata/aluminium-properties.txt"
: >"$output/metadata/aluminium-build-properties.txt"
while IFS= read -r -d '' prop; do
    relative=${prop#"$output/"}
    printf '\n# %s\n' "$relative" >>"$output/metadata/aluminium-properties.txt"
    grep -E '^[[:space:]]*[A-Za-z0-9._-]+=' "$prop" \
        >>"$output/metadata/aluminium-properties.txt" || true
    grep -E '^(ro\.(build\.|product\.|hardware|board\.|boot\.)|ro\.product\.|ro\.vendor\.|ro\.odm\.|persist\.sys\.)' \
        "$prop" >>"$output/metadata/aluminium-build-properties.txt" || true
done < <(find "${roots[@]}" -type f \( -name build.prop -o -name '*.prop' \) -print0)
find "${roots[@]}" -type f -name '*.apex' -printf '%P\n' | sort -u >"$output/metadata/apex-list.txt"
find "${roots[@]}" -type f -path '*/apex/*' \( -name 'apex_manifest*' -o -name 'apex_pubkey' \) \
    -printf '%P\n' | sort -u >"$output/metadata/apex-manifest-files.txt"
find "${roots[@]}" -type f -path '*/etc/vintf/*' -printf '%P\n' | sort -u >"$output/metadata/vintf-files.txt"
find "${roots[@]}" -type f \( -name 'android.hardware*' -o -name 'android.hidl*' \) \
    -printf '%P\n' | sort -u >"$output/metadata/hal-files.txt"
find "${roots[@]}" -type f -name '*.rc' -print0 | sort -z | \
    xargs -0 -r grep -HnE '^[[:space:]]*service[[:space:]]+' \
    >"$output/metadata/init-services.txt" || true
find "${roots[@]}" -type f \( -name '*.rc' -o -name '*.xml' \) -printf '%P\n' | \
    sort -u >"$output/metadata/init-and-xml-files.txt"
find "${roots[@]}" -type f \( -name '*sepolicy*' -o -name '*_contexts' -o -name '*.cil' \) \
    -printf '%P\n' | sort -u >"$output/metadata/sepolicy-files.txt"
find "${roots[@]}" -type f \( -name 'fstab*' -o -name 'modules.load*' -o \
    -name 'modules.block*' -o -name '*modprobe*' -o -name 'ueventd*.rc' \) \
    -printf '%P\n' | sort -u >"$output/metadata/kernel-expectations-files.txt"

if command -v seinfo >/dev/null 2>&1; then
    while IFS= read -r -d '' policy; do
        label=$(printf '%s' "${policy#"$output/"}" | tr '/ ' '__')
        seinfo "$policy" >"$output/metadata/${label}.seinfo.txt" 2>&1 || true
        seinfo --permissive "$policy" \
            >"$output/metadata/${label}.permissive.txt" 2>&1 || true
    done < <(find "${roots[@]}" -type f \( -name sepolicy -o -name precompiled_sepolicy \) -print0)
fi

if [[ -d $PROJECT_ROOT/upstream/android_device_brcm_rpi5 ]]; then
    python3 "$SCRIPT_DIR/compare_vintf.py" --root "$output" \
        --pi-device "$PROJECT_ROOT/upstream/android_device_brcm_rpi5" \
        --output "$output/metadata/vintf-static-comparison.md" || true
fi
python3 "$SCRIPT_DIR/inventory_aluminium.py" --root "$output"
printf '\nExtraction complete: %s\n' "$output" >&2
printf 'Static inventory only; runtime/SELinux/VINTF validation still requires device evidence.\n' >&2
