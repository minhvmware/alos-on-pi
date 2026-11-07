#!/usr/bin/env python3
"""Read-only MBR/GPT partition extractor; no mount, loop device or root."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

CHUNK_SIZE = 8 * 1024 * 1024
EXTENDED_IDS = {0x05, 0x0F, 0x85}


def partition_number(node: str, image: str, fallback: int) -> int:
    suffix = node[len(image):] if node.startswith(image) else node
    match = re.search(r"(?:p)?(\d+)$", suffix)
    return int(match.group(1)) if match else fallback


def copy_range(source, destination, offset: int, size: int) -> None:
    source.seek(offset)
    remaining = size
    with destination.open("wb") as out:
        while remaining:
            chunk = source.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                raise RuntimeError("Unexpected EOF while copying partition")
            # Preserve empty filesystem space as holes in the output.
            if chunk.count(0) == len(chunk):
                out.seek(len(chunk), os.SEEK_CUR)
            else:
                out.write(chunk)
            remaining -= len(chunk)
        out.truncate(size)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", required=True,
                        help="new directory for raw pN.img partitions")
    parser.add_argument("--metadata-prefix", required=True,
                        help="path prefix for JSON, dump and TSV reports")
    args = parser.parse_args()
    image = Path(args.image).resolve()
    output = Path(args.output)
    prefix = Path(args.metadata_prefix)
    if not image.is_file():
        parser.error(f"not a regular file: {image}")
    if output.exists():
        parser.error(f"refusing existing output path: {output}")
    prefix.parent.mkdir(parents=True, exist_ok=True)

    probe = subprocess.run(["sfdisk", "--json", str(image)],
                           capture_output=True, text=True)
    Path(str(prefix) + ".sfdisk-diagnostics.txt").write_text(
        probe.stdout + probe.stderr, encoding="utf-8")
    if probe.returncode:
        raise RuntimeError(f"sfdisk failed; see {prefix}.sfdisk-diagnostics.txt")
    table = json.loads(probe.stdout)["partitiontable"]
    partitions = table.get("partitions", [])
    if not partitions:
        raise RuntimeError("partition table contains no partitions")
    sector_size = int(table.get("sectorSize", 512))
    if sector_size <= 0:
        raise RuntimeError("invalid logical sector size")
    Path(str(prefix) + ".partition-table.json").write_text(
        json.dumps(table, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    dump = subprocess.run(["sfdisk", "--dump", str(image)],
                          capture_output=True, text=True, check=True)
    Path(str(prefix) + ".sfdisk.dump").write_text(dump.stdout, encoding="utf-8")

    output.mkdir(parents=True)
    rows = ["number\tnode\tstart_sector\tsectors\toffset_bytes\tsize_bytes"
            "\ttype\tname\tbootable\toutput\tstatus"]
    with image.open("rb") as source:
        image_size = os.fstat(source.fileno()).st_size
        for index, part in enumerate(partitions, 1):
            number = partition_number(str(part.get("node", "")), str(image), index)
            start = int(part["start"])
            sectors = int(part["size"])
            offset, size = start * sector_size, sectors * sector_size
            if start < 0 or sectors <= 0 or offset + size > image_size:
                raise RuntimeError(f"partition {number} exceeds input bounds")
            type_id = str(part.get("id", part.get("type", "")))
            name = str(part.get("name", ""))
            bootable = str(part.get("bootable", False)).lower()
            try:
                numeric_type = int(type_id, 16)
            except ValueError:
                numeric_type = -1
            is_extended = numeric_type in EXTENDED_IDS
            filename = "" if is_extended else f"p{number}.img"
            status = "extended-container" if is_extended else "extracted"
            rows.append("\t".join(str(value) for value in (
                number, part.get("node", ""), start, sectors, offset, size,
                part.get("type", type_id), name, bootable, filename, status)))
            if not is_extended:
                copy_range(source, output / filename, offset, size)
                print(f"Extracted p{number}: {size} bytes", file=sys.stderr)
    Path(str(prefix) + ".partitions.tsv").write_text(
        "\n".join(rows) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"extract_disk.py: {error}", file=sys.stderr)
        sys.exit(1)
