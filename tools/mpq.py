#!/usr/bin/env python3
"""Read .SC2Map / .SC2Mod MPQ archives.

mpyq is read-only, so this tool is for inspection and for pulling the editor's
own build products (MapScript.galaxy, Triggers, GameStrings) back out of a map.

    python3 tools/mpq.py ls  <archive>
    python3 tools/mpq.py cat <archive> <name> [outfile]
    python3 tools/mpq.py x   <archive> <outdir>
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

from mpyq import MPQArchive  # noqa: E402


def _name(raw):
    # mpyq 0.2.5 hands back raw bytes from the (listfile)
    return raw.decode("latin-1") if isinstance(raw, bytes) else raw


def list_files(path):
    archive = MPQArchive(path)
    try:
        return [_name(n) for n in archive.files]
    finally:
        archive.file.close()


def read_file(path, name):
    archive = MPQArchive(path)
    try:
        data = archive.read_file(name)
        if data is None:
            data = archive.read_file(name.encode("latin-1"))
        return data
    finally:
        archive.file.close()


def extract(path, outdir):
    written = []
    archive = MPQArchive(path)
    try:
        names = [_name(n) for n in archive.files]
    finally:
        archive.file.close()

    for name in names:
        data = read_file(path, name)
        if data is None:
            continue

        dest = os.path.join(outdir, name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        with open(dest, "wb") as fh:
            fh.write(data)

        written.append(dest)

    return written


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["ls", "cat", "x"])
    ap.add_argument("archive")
    ap.add_argument("arg", nargs="?", help="file name (cat) or output dir (x)")
    ap.add_argument("outfile", nargs="?", help="cat: optional output file")

    args = ap.parse_args()

    if args.cmd == "ls":
        for name in list_files(args.archive):
            print(name)

    elif args.cmd == "cat":
        if not args.arg:
            ap.error("cat needs a file name")

        data = read_file(args.archive, args.arg)
        if data is None:
            print(f"not found: {args.arg}", file=sys.stderr)
            return 1

        if args.outfile:
            with open(args.outfile, "wb") as fh:
                fh.write(data)
            print(f"{args.outfile}: {len(data)} bytes")
        else:
            sys.stdout.write(data.decode("utf-8", errors="replace"))

    elif args.cmd == "x":
        if not args.arg:
            ap.error("x needs an output directory")

        for path in extract(args.archive, args.arg):
            print(path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
