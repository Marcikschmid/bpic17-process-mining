"""Install the official Windows Graphviz ZIP inside this project only."""

import hashlib
import json
import sys
import zipfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
VERSION = "16.1.0"
FILENAME = f"windows_10_cmake_Release_Graphviz-{VERSION}-win64.zip"
URL = (
    "https://gitlab.com/api/v4/projects/4207231/packages/generic/"
    f"graphviz-releases/{VERSION}/{FILENAME}"
)


def main():
    if sys.platform != "win32":
        raise SystemExit("On Linux/macOS, install Graphviz with your package manager.")
    with urlopen(URL + ".sha256", timeout=60) as response:
        expected = response.read().decode().split()[0].lower()
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise ValueError("The publisher did not return a valid SHA-256 checksum.")
    cache = ROOT / "tmp" / "tools"
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / FILENAME
    print(f"Downloading official Graphviz {VERSION} ZIP...", flush=True)
    digest = hashlib.sha256()
    with urlopen(URL, timeout=60) as source, archive.open("wb") as output:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            output.write(chunk)
            digest.update(chunk)
    if digest.hexdigest() != expected:
        raise ValueError("Graphviz archive checksum mismatch; refusing to extract.")
    destination = (ROOT / ".tools" / "graphviz").resolve()
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            if not (destination / entry.filename).resolve().is_relative_to(destination):
                raise ValueError(f"Unsafe archive path: {entry.filename}")
        bundle.extractall(destination)
    executables = list(destination.rglob("dot.exe"))
    if len(executables) != 1:
        raise ValueError(f"Expected one dot.exe, found {len(executables)}")
    manifest = {
        "version": VERSION,
        "source": "https://graphviz.org/download/",
        "archive_url": URL,
        "publisher_sha256": expected,
        "dot_path": executables[0].relative_to(ROOT).as_posix(),
    }
    (ROOT / "docs" / "graphviz_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Verified and extracted to {destination}", flush=True)


if __name__ == "__main__":
    main()
