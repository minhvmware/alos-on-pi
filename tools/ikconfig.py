#!/usr/bin/env python3
"""Extract an embedded IKCONFIG gzip blob from a raw kernel image."""

import argparse
import sys
import zlib
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    raw = Path(args.input).read_bytes()
    start = raw.find(b"IKCFG_ST")
    end = raw.find(b"IKCFG_ED", start + 8)
    if start < 0 or end < 0:
        print("IKCONFIG markers not found")
        return 3
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    config = decompressor.decompress(raw[start + 8:end]) + decompressor.flush()
    Path(args.output).write_bytes(config)
    print(f"IKCONFIG extracted {len(config)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
