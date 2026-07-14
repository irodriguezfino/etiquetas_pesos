from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def project_version() -> str:
    text = read_text(PYPROJECT)
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"\s*$', text)
    if not match:
        raise SystemExit("No se encontro project.version en pyproject.toml.")
    version = match.group(1).strip()
    if not SEMVER_RE.match(version):
        raise SystemExit(f"La version no cumple SemVer: {version}")
    return version


def version_tuple(version: str) -> tuple[int, int, int, int]:
    core = version.split("-", 1)[0].split("+", 1)[0]
    major, minor, patch = (int(part) for part in core.split("."))
    return major, minor, patch, 0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def generate_version_files() -> None:
    version = project_version()
    write_json(ROOT / "version_local.json", {"version": version})
    major, minor, patch, build = version_tuple(version)
    version_info = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, {build}),
    prodvers=({major}, {minor}, {patch}, {build}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'Rodriguez - Finura'),
          StringStruct('FileDescription', 'Etiquetado Pesos'),
          StringStruct('FileVersion', '{version}'),
          StringStruct('InternalName', 'Etiquetado Pesos'),
          StringStruct('OriginalFilename', 'Etiquetado_Pesos.exe'),
          StringStruct('ProductName', 'Etiquetado Pesos'),
          StringStruct('ProductVersion', '{version}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    build_dir = ROOT / "build"
    build_dir.mkdir(exist_ok=True)
    (build_dir / "version_info.txt").write_text(version_info, encoding="utf-8")


def write_update_manifest(update_zip: Path, output_dir: Path, notes: str) -> None:
    version = project_version()
    update_zip = update_zip.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    digest = sha256_file(update_zip)
    package_name = update_zip.name
    url = f"https://github.com/irodriguezfino/etiquetas_pesos/releases/download/v{version}/{package_name}"
    manifest = {
        "version": version,
        "notes": notes,
        "prerelease": "-" in version,
        "auto_update": {
            "type": "zip",
            "url": url,
            "file": package_name,
            "sha256": digest,
        },
    }
    write_json(output_dir / "update-manifest.json", manifest)
    write_json(output_dir / "version.json", manifest)
    (output_dir / f"{package_name}.sha256").write_text(f"{digest}  {package_name}\n", encoding="utf-8")


def validate_tag(tag: str) -> None:
    expected = f"v{project_version()}"
    if tag != expected:
        raise SystemExit(f"La etiqueta {tag!r} no coincide con la version declarada {expected!r}.")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("print-version")
    sub.add_parser("generate")
    tag_parser = sub.add_parser("validate-tag")
    tag_parser.add_argument("tag")
    manifest_parser = sub.add_parser("manifest")
    manifest_parser.add_argument("--zip", required=True)
    manifest_parser.add_argument("--out", required=True)
    manifest_parser.add_argument("--notes", default="")
    args = parser.parse_args()

    if args.command == "print-version":
        print(project_version())
    elif args.command == "generate":
        generate_version_files()
    elif args.command == "validate-tag":
        validate_tag(args.tag)
    elif args.command == "manifest":
        write_update_manifest(Path(args.zip), Path(args.out), args.notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
