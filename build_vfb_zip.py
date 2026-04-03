#!/usr/bin/env python3
"""Build VFB_instance_manager.zip for Blender (v1.0+).

Output is **Extensions-style** by default: includes blender_manifest.toml next to
__init__.py under VFB_instance_manager/ inside the zip (Blender 4.2+ Install from Disk
and extensions.blender.org publishing). __pycache__ / .pyc are always omitted.
Use --legacy for a zip without the manifest if needed.

"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

API = Path(__file__).resolve().parent
ADDON_DIR = API / "VFB_instance_manager"
OUT_ZIP = API / "VFB_instance_manager.zip"
ARCHIVE_PREFIX = "VFB_instance_manager"


def _skip(path: Path, *, include_manifest: bool) -> bool:
    parts = path.parts
    if "__pycache__" in parts:
        return True
    if path.suffix.lower() == ".pyc":
        return True
    if not include_manifest and path.name == "blender_manifest.toml":
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Exclude blender_manifest.toml (legacy-style zip only)",
    )
    args = parser.parse_args()
    include_manifest = not args.legacy

    if not ADDON_DIR.is_dir():
        raise SystemExit(f"Missing addon folder: {ADDON_DIR}")
    OUT_ZIP.unlink(missing_ok=True)
    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in ADDON_DIR.rglob("*"):
            if not f.is_file() or _skip(f, include_manifest=include_manifest):
                continue
            arc = Path(ARCHIVE_PREFIX) / f.relative_to(ADDON_DIR)
            zf.write(f, arc.as_posix())
    with zipfile.ZipFile(OUT_ZIP, "r") as zr:
        n = len(zr.namelist())
    print(f"Wrote {OUT_ZIP} ({n} files)")


if __name__ == "__main__":
    main()
