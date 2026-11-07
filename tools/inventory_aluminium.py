#!/usr/bin/env python3
"""Generate evidence-only Phase 0 inventories from an extracted image tree."""
import argparse
import csv
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def properties(root: Path):
    values = {}
    for area in (root / "extracted", root / "ramdisks"):
        paths = list(area.rglob("*.prop")) + list(area.rglob("build.prop"))
        for path in sorted(set(paths)):
            for line in read(path).splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values.setdefault(key.strip(), set()).add(value.strip())
    return values


def vintf_inventory(root: Path) -> str:
    lines = [
        "Static XML inventory only. No checkvintf, runtime HAL or kernel compatibility claim.",
        "Malformed XML and absent files are reported as evidence limitations.", ""]
    seen = set()
    for area in (root / "extracted", root / "ramdisks"):
        for path in sorted(area.rglob("*.xml")):
            if "/etc/vintf/" not in str(path):
                continue
            relative = rel(path, root)
            if relative in seen:
                continue
            seen.add(relative)
            lines.append(f"## {relative}")
            try:
                tree = ET.parse(path)
            except (ET.ParseError, OSError) as error:
                lines.append(f"ERROR: {error}\n")
                continue
            document = tree.getroot()
            lines.append(f"root={document.tag}; attributes={document.attrib}")
            for tag in ("version", "target-level", "kernel-target-level"):
                element = document.find(tag)
                if element is not None:
                    lines.append(f"{tag}={element.text or ''}")
            for hal in document.findall("hal"):
                name = hal.findtext("name", "UNKNOWN")
                lines.append(f"HAL format={hal.get('format', 'UNKNOWN')}")
                versions = [e.text or "" for e in hal.findall("version")]
                transport = hal.find("transport")
                transport_text = "" if transport is None else (
                    f"{transport.get('format', '')}:{transport.text or ''}")
                instances = [e.text or "" for e in hal.findall("fqname")]
                lines.append(f"HAL {name}; versions={versions}; transport={transport_text}; "
                             f"instances={instances}")
            for kernel in document.findall("kernel"):
                lines.append(f"kernel version={kernel.get('version', '')}; "
                             f"conditions={len(kernel.findall('condition'))}; "
                             f"configs={len(kernel.findall('config'))}")
            lines.append("")
    if not seen:
        lines.append("No VINTF XML was found in the extracted input.")
    return "\n".join(lines) + "\n"


def write_phase_reports(root: Path, props, inventory, vintf):
    reports = root / "reports"
    reports.mkdir(exist_ok=True)
    metadata = root / "metadata"
    def values(key):
        return ", ".join(sorted(props.get(key, []))) or "UNKNOWN — not present in extracted properties"

    rows = ["| Input | Raw image | Class | FS | Extracted |", "|---|---|---|---|---|"]
    for item in inventory:
        rows.append("| " + " | ".join(item.get(key, "") or "—" for key in
                    ("input", "raw", "class", "filesystem", "extracted")) + " |")
    (reports / "aluminium_partition_layout.md").write_text(
        "# Aluminium image layout — static extraction evidence\n\n" +
        "Generated only from the supplied image. This is not a Pi 5 target layout.\n\n" +
        "\n".join(rows) + "\n\nFull disk JSON/sfdisk dumps, when detected, are in `metadata/*.disk.*`.\n",
        encoding="utf-8")

    boot_files = sorted(metadata.glob("*.boot-info.txt"))
    boot_lines = ["# Aluminium boot evidence", "",
                  "Only detected headers, unpacked artifacts and cmdlines are evidence; no bootloader chain is inferred.", ""]
    boot_lines += [f"- `{rel(path, root)}`" for path in boot_files] or [
        "- No Android boot header information was extracted. This does not prove boot is absent."]
    boot_lines += ["", "## Kernel evidence", ""]
    boot_lines += [f"- `{rel(path, root)}`" for path in sorted(metadata.glob("*.kernel-info.txt"))] or [
        "- No kernel binary was extracted."]
    boot_lines += ["", "## Unpacked ramdisks", "", "```", read(metadata / "ramdisks.txt").rstrip(), "```"]
    (reports / "aluminium_bootflow.md").write_text("\n".join(boot_lines) + "\n", encoding="utf-8")

    comparison = read(metadata / "vintf-static-comparison.md")
    hal = ["# Aluminium HAL inventory", "",
           "Static files and declared VINTF HALs only; service registration and runtime operation are unverified.", "",
           "## VINTF declarations", "", "```", vintf.rstrip(), "```", "",
           "## HAL-named files", "", "```", read(metadata / "hal-files.txt").rstrip(), "```", "",
           "## Init service declarations", "", "```", read(metadata / "init-services.txt").rstrip(), "```"]
    if comparison:
        hal += ["", "## Static requirement comparison", "", comparison]
    (reports / "aluminium_hal_list.md").write_text("\n".join(hal) + "\n", encoding="utf-8")
    (reports / "aluminium_vintf.md").write_text(
        "# Aluminium VINTF static inspection\n\n```\n" + vintf +
        "```\n## Static requirement comparison\n\n" + comparison +
        "\nNo semantic `checkvintf` or runtime compatibility result is claimed.\n", encoding="utf-8")

    sepolicy = ["# Aluminium SELinux inventory", "",
                "Policy files are inventoried, not decompiled or runtime-audited. Enforcing/permissive state remains unverified without boot evidence.", "",
                f"- `ro.build.selinux`: {values('ro.build.selinux')}", "",
                "## Policy/context files", "", "```", read(metadata / "sepolicy-files.txt").rstrip(), "```"]
    (reports / "aluminium_sepolicy.md").write_text("\n".join(sepolicy) + "\n", encoding="utf-8")

    extras = ["# Aluminium APEX, init và kernel expectations", "",
              "Static inventories only; APEX signatures/activation and kernel runtime compatibility are not verified.", "",
              "## APEX packages", "```", read(metadata / "apex-list.txt").rstrip(), "```", "",
              "## Flattened APEX manifests/pubkeys", "```",
              read(metadata / "apex-manifest-files.txt").rstrip(), "```", "",
              "## Init services", "```", read(metadata / "init-services.txt").rstrip(), "```", "",
              "## fstab/modules/ueventd evidence", "```",
              read(metadata / "kernel-expectations-files.txt").rstrip(), "```"]
    (reports / "aluminium_apex_init_kernel.md").write_text("\n".join(extras) + "\n", encoding="utf-8")

    classes = {item["class"] for item in inventory}
    def comparison(key, expected):
        actual = props.get(key, set())
        if not actual:
            return "UNKNOWN", values(key)
        return ("SOURCE-MATCH" if actual == {expected} else "REVIEW/MISMATCH"), ", ".join(sorted(actual))
    release_status, release = comparison("ro.build.version.release", "17")
    sdk_status, sdk = comparison("ro.build.version.sdk", "37")
    abi_status, abi = comparison("ro.product.cpu.abi", "arm64-v8a")
    dynamic_prop = any(value.lower() == "true"
                       for value in props.get("ro.boot.dynamic_partitions", set()))
    virtual_ab = any(value.lower() == "true"
                     for value in props.get("ro.virtual_ab.enabled", set()))
    if dynamic_prop or "dynamic-super" in classes:
        layout_status = "NO-DIRECT-DD"
        layout_evidence = (f"dynamic_partitions={dynamic_prop}; virtual_ab={virtual_ab}; "
                           "logical partitions/slots must be mapped to a Pi-compatible scheme")
    elif "filesystem" in classes:
        layout_status = "REVIEW"
        layout_evidence = "Standalone filesystem images detected; slot, size and contents still require mapping"
    else:
        layout_status = "UNKNOWN"
        layout_evidence = "No usable filesystem layout evidence extracted"
    boot_status = "REPLACE/REVIEW" if "android-boot" in classes else "UNKNOWN"
    kernel_text = "\n".join(read(path) for path in metadata.glob("*.kernel-info.txt"))
    kernel_version = re.search(r"Linux version (\S+)", kernel_text)
    kernel_page = re.search(r"(\d+)K pages", kernel_text)
    kernel_evidence = (f"{kernel_version.group(1) if kernel_version else 'UNKNOWN'}; "
                       f"{kernel_page.group(1) + 'K pages' if kernel_page else 'page size UNKNOWN'}")
    avb_text = "\n".join(read(path) for path in metadata.glob("*.avb.txt"))
    avb_evidence = "Detected AVB metadata" if ("Footer version:" in avb_text or
                   "Minimum libavb version:" in avb_text) else "Not detected in supplied images; absence not proven"
    matrix = ["# Aluminium ↔ Raspberry Vanilla Pi 5 compatibility matrix", "",
              "Static triage generated from the supplied image. It is not a boot or runtime validation result.", "",
              "| Area | Aluminium evidence | Raspberry Vanilla source baseline | Triage |", "|---|---|---|---|",
              f"| Android release | {release} | AOSP 17 | {release_status} |",
              f"| SDK | {sdk} | Shipping API 37 | {sdk_status} |",
              f"| Primary ABI | {abi} | arm64 / armv8-a | {abi_status} |",
              f"| Partition scheme | {layout_evidence} | Static MBR; system=p5, vendor=p6; no super in source flow | {layout_status} |",
              f"| Boot container | Android boot={('android-boot' in classes)}; FAT={any(i['filesystem'] in ('vfat', 'msdos') for i in inventory)} | FAT32 firmware boot.img | {boot_status} |",
              f"| AVB | {avb_evidence} | No AVB/vbmeta flow found in device source | REVIEW |",
              f"| Kernel/modules | {kernel_evidence} | Pi baseline kernel 6.18, 16 KiB pages | "
              "CANNOT-REUSE-ALUMINIUM-KERNEL/MODULES |",
              "| Userspace page alignment | Audit ELF LOAD alignment; APEX payloads are separate | Pi kernel 16 KiB | REVIEW/RUNTIME REQUIRED |",
              "| VINTF/HAL | See static comparison and HAL reports | Pi source manifest incomplete; APEX adds fragments | CHECKVINTF + RUNTIME REQUIRED |",
              "| SELinux | Compiled policy inspected if seinfo ran | Pi cmdline source is permissive for bring-up | DENIAL/RUNTIME AUDIT REQUIRED |",
              "", "A `SOURCE-MATCH` only compares two static values. It never proves hardware or userspace compatibility."]
    (reports / "hardware_compatibility_matrix.md").write_text("\n".join(matrix) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    metadata = root / "metadata"
    with (metadata / "image-inventory.tsv").open(encoding="utf-8") as stream:
        inventory = list(csv.DictReader(stream, delimiter="\t"))
    props = properties(root)
    vintf = vintf_inventory(root)
    (metadata / "vintf-summary.txt").write_text(vintf, encoding="utf-8")
    keys = ("ro.build.version.release", "ro.build.version.sdk", "ro.build.fingerprint",
            "ro.product.cpu.abi", "ro.hardware", "ro.board.platform",
            "ro.boot.slot_suffix", "ro.boot.dynamic_partitions",
            "ro.boot.verifiedbootstate", "ro.boot.veritymode", "ro.build.selinux")
    summary = [f"{key}={', '.join(sorted(props[key])) if props.get(key) else 'UNKNOWN'}"
               for key in keys]
    (metadata / "aluminium-build-summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    write_phase_reports(root, props, inventory, vintf)


if __name__ == "__main__":
    main()
