#!/usr/bin/env python3
"""Static VINTF requirement/provider comparison. Never claims checkvintf."""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

REQUIREMENT_FILES = (
    "system/system/etc/vintf/compatibility_matrix.device.xml",
    "product/etc/vintf/compatibility_matrix.xml",
    "system_ext/etc/vintf/compatibility_matrix.toscana.xml",
    "vendor/etc/vintf/compatibility_matrix.xml",
)
PI_PROVIDER_FILES = ("manifest.xml", "product_manifest.xml")


def hal_key(hal, name, versions, instances):
    return (hal.get("format", "unknown"), name,
            ",".join(versions), ",".join(instances))


def parse_matrix(path: Path):
    requirements = []
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return requirements
    for hal in root.iter("hal"):
        if str(hal.get("optional", "")).lower() == "true":
            continue
        name = hal.findtext("name", "")
        versions = [element.text or "" for element in hal.findall("version")]
        instances = []
        for interface in hal.findall("interface"):
            interface_name = interface.findtext("name", "")
            for instance in interface.findall("instance"):
                instances.append(f"{interface_name}/{instance.text or ''}")
        for fqname in hal.findall("fqname"):
            instances.append(fqname.text or "")
        requirements.append((hal_key(hal, name, versions, instances),
                             hal.get("format", "unknown"), name,
                             versions, instances))
    return requirements


def parse_providers(path: Path):
    providers = set()
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return providers
    for hal in root.iter("hal"):
        name = hal.findtext("name", "")
        providers.add(name)
    return providers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True,
                        help="extracted Aluminium output directory")
    parser.add_argument("--pi-device", required=True,
                        help="device/brcm/rpi5 source directory")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    pi = Path(args.pi_device).resolve()
    extracted = root / "extracted"
    requirements = []
    for relative in REQUIREMENT_FILES:
        path = extracted / relative
        if not path.exists():
            requirements.append((relative, None, "missing", "", [], []))
            continue
        for item in parse_matrix(path):
            requirements.append((relative, *item))
    pi_providers = set()
    for name in PI_PROVIDER_FILES:
        pi_providers |= parse_providers(pi / name)
    aluminium_providers = set()
    for path in extracted.rglob("manifest*.xml"):
        if "/etc/vintf/" in str(path):
            aluminium_providers |= parse_providers(path)
    package_hints = set()
    device_mk = pi / "device.mk"
    if device_mk.exists():
        for line in device_mk.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("com.android.hardware.") or line.startswith("com.google.android.hardware."):
                package_hints.add(line.rstrip("\\").strip())
    lines = [
        "# Static VINTF requirement/provider comparison", "",
        "This parses extracted XML and Pi device source. It is not `checkvintf`, does not",
        "evaluate version ranges/instances semantically and does not prove runtime registration.", "",
        "Pi manifests in this source tree are known to be incomplete because APEX service",
        "metadata can add VINTF fragments at build time. A `NOT-DECLARED` row is therefore a",
        "review item, not proof of incompatibility.", "",
        "| Matrix source | Format | Required HAL | Versions | Instances | Static status |",
        "|---|---|---|---|---|---|",
    ]
    seen = set()
    for item in requirements:
        source, fmt, name, versions, instances = item[0], item[2], item[3], item[4], item[5]
        if fmt == "missing":
            lines.append(f"| {source} | — | — | — | — | FILE-MISSING |")
            continue
        if name in pi_providers:
            status = "PI-SOURCE-DECLARES"
        elif name in aluminium_providers:
            status = "ALUMINIUM-VENDOR-DECLARES"
        else:
            status = "NOT-DECLARED-IN-PI-SOURCE"
        key = (fmt, name, tuple(versions), tuple(instances))
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"| {source} | {fmt} | {name} | "
                     f"{', '.join(versions) or '—'} | {', '.join(instances) or '—'} | {status} |")
    lines += ["", "## Pi `com.android.hardware.*` package hints", "",
              "```", "\n".join(sorted(package_hints)), "```"]
    Path(args.output).write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
