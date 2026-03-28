#!/usr/bin/env python3
import hashlib
import shutil
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ZIPS = ROOT / "zips"

IGNORE = {".git", ".github", "zips", "tools", "__pycache__"}

def clean():
    if ZIPS.exists():
        shutil.rmtree(ZIPS)
    ZIPS.mkdir(parents=True, exist_ok=True)
    # Remove old generated files from root
    for f in ["addons.xml", "addons.xml.md5"]:
        p = ROOT / f
        if p.exists():
            p.unlink()
    # Remove old repository zip files from root
    for p in ROOT.glob("repository.*.zip"):
        p.unlink()

def addon_dirs():
    for path in ROOT.iterdir():
        if not path.is_dir():
            continue
        if path.name in IGNORE or path.name.startswith("."):
            continue
        addon_xml = path / "addon.xml"
        if addon_xml.exists():
            yield path

def parse_addon(addon_xml: Path):
    tree = ET.parse(addon_xml)
    root = tree.getroot()
    addon_id = root.attrib["id"]
    version = root.attrib["version"]
    return root, addon_id, version

def zip_addon(folder: Path, addon_id: str, version: str):
    zip_dir = ZIPS / addon_id
    zip_dir.mkdir(parents=True, exist_ok=True)
    zip_path = zip_dir / f"{addon_id}-{version}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in folder.rglob("*"):
            if file.is_dir():
                continue
            if file.suffix == ".zip":
                continue
            # Files inside the zip should be under addon_id/ folder
            rel = file.relative_to(folder)
            zf.write(file, f"{addon_id}/{rel.as_posix()}")
    # Copy icon.png and fanart.jpg next to the zip so Kodi can display them
    for asset in ["icon.png", "fanart.jpg"]:
        src = folder / asset
        if not src.exists():
            src = folder / "resources" / asset
        if src.exists():
            shutil.copy2(src, zip_dir / asset)
            # Also copy to resources/ subfolder to match addons.xml asset paths
            res_dir = zip_dir / "resources"
            res_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, res_dir / asset)
    return zip_path

def build_addons_xml(entries):
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        "<addons>",
    ]

    for root in entries:
        xml_parts.append(ET.tostring(root, encoding="unicode"))

    xml_parts.append("</addons>")
    content = "\n".join(xml_parts) + "\n"

    # Write in binary mode so the bytes on disk match what we hash
    raw = content.encode("utf-8")
    (ROOT / "addons.xml").write_bytes(raw)
    md5 = hashlib.md5(raw).hexdigest()
    (ROOT / "addons.xml.md5").write_bytes(md5.encode("utf-8"))

def copy_repo_zip(repo_id: str, repo_version: str):
    # Copy the repository zip to the root for easy user install
    repo_zip_src = ZIPS / repo_id / f"{repo_id}-{repo_version}.zip"
    repo_zip_dst = ROOT / f"{repo_id}-{repo_version}.zip"
    shutil.copy2(repo_zip_src, repo_zip_dst)

def main():
    clean()
    addon_roots = []
    repo_id = None
    repo_version = None
    for folder in sorted(addon_dirs(), key=lambda p: p.name):
        addon_xml = folder / "addon.xml"
        root, addon_id, version = parse_addon(addon_xml)
        addon_roots.append(root)
        zip_addon(folder, addon_id, version)
        if addon_id.startswith("repository."):
            repo_id = addon_id
            repo_version = version
    build_addons_xml(addon_roots)
    if repo_id and repo_version:
        copy_repo_zip(repo_id, repo_version)
    else:
        raise SystemExit("No repository.* addon found")

if __name__ == "__main__":
    main()
