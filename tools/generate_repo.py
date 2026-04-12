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
    for f in ["addons.xml", "addons.xml.md5", "index.html"]:
        p = ROOT / f
        if p.exists():
            p.unlink()
    for p in ROOT.glob("repository.*.zip"):
        p.unlink()

def addon_dirs():
    for path in ROOT.iterdir():
        if not path.is_dir():
            continue
        if path.name in IGNORE or path.name.startswith("."):
            continue
        if (path / "addon.xml").exists():
            yield path

def parse_addon(addon_xml: Path):
    tree = ET.parse(addon_xml)
    root = tree.getroot()
    return root, root.attrib["id"], root.attrib["version"]

def zip_addon(folder: Path, addon_id: str, version: str):
    zip_dir = ZIPS / addon_id
    zip_dir.mkdir(parents=True, exist_ok=True)
    zip_path = zip_dir / f"{addon_id}-{version}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in folder.rglob("*"):
            if file.is_dir() or file.suffix == ".zip":
                continue
            rel = file.relative_to(folder)
            zf.write(file, f"{addon_id}/{rel.as_posix()}")
    for asset in ["icon.png", "fanart.jpg"]:
        src = folder / asset
        if not src.exists():
            src = folder / "resources" / asset
        if src.exists():
            shutil.copy2(src, zip_dir / asset)
            res_dir = zip_dir / "resources"
            res_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, res_dir / asset)
    tree = ET.parse(folder / "addon.xml")
    for ss in tree.iter("screenshot"):
        ss_path = ss.text.strip() if ss.text else ""
        src = folder / ss_path
        if src.is_file():
            dst_dir = zip_dir / str(Path(ss_path).parent)
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst_dir / src.name)
    return zip_path

def build_addons_xml(entries):
    xml_parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', "<addons>"]
    for root in entries:
        xml_parts.append(ET.tostring(root, encoding="unicode"))
    xml_parts.append("</addons>")
    raw = ("\n".join(xml_parts) + "\n").encode("utf-8")
    (ROOT / "addons.xml").write_bytes(raw)
    (ROOT / "addons.xml.md5").write_bytes(hashlib.md5(raw).hexdigest().encode("utf-8"))

def copy_repo_zip(repo_id: str, repo_version: str):
    shutil.copy2(ZIPS / repo_id / f"{repo_id}-{repo_version}.zip",
                 ROOT / f"{repo_id}-{repo_version}.zip")
    (ROOT / "index.html").write_text(
        '<html><head><title>Index of /</title></head><body>'
        '<h1>Index of /</h1><hr><pre>'
        '<a href="{0}-{1}.zip">{0}-{1}.zip</a>'
        '</pre><hr></body></html>'.format(repo_id, repo_version),
        encoding="utf-8",
    )

def main():
    clean()
    addon_roots = []
    repo_id = None
    repo_version = None
    for folder in sorted(addon_dirs(), key=lambda p: p.name):
        root, addon_id, version = parse_addon(folder / "addon.xml")
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
