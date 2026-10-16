"""Download the original BPIC-17 log and verify the publisher's file hashes."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
METADATA_URL = "https://api.figshare.com/v2/articles/12696884"
FILES = ("BPI Challenge 2017.xes.gz", "DATA.xml")


def checksums(path):
    md5 = hashlib.md5(usedforsecurity=False)
    sha256 = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            md5.update(chunk)
            sha256.update(chunk)
    return md5.hexdigest(), sha256.hexdigest()


def main():
    with urlopen(METADATA_URL, timeout=60) as response:
        metadata = json.load(response)
    available = {item["name"]: item for item in metadata["files"]}
    destination = ROOT / "data" / "raw"
    destination.mkdir(parents=True, exist_ok=True)
    verified = []

    for name in FILES:
        item = available[name]
        target = destination / name
        expected_md5 = item["computed_md5"]
        downloaded = not target.exists()
        if downloaded:
            print(f"Downloading {name} ({item['size']:,} bytes)...", flush=True)
            temporary = target.with_name(target.name + ".part")
            with urlopen(item["download_url"], timeout=60) as source:
                with temporary.open("wb") as output:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        output.write(chunk)
            md5, sha256 = checksums(temporary)
            if temporary.stat().st_size != item["size"] or md5 != expected_md5:
                raise ValueError(f"Download verification failed: {temporary}")
            temporary.replace(target)
        else:
            md5, sha256 = checksums(target)
            if target.stat().st_size != item["size"] or md5 != expected_md5:
                raise ValueError(f"Existing file differs from source: {target}")

        verified.append({
            "path": target.relative_to(ROOT).as_posix(),
            "file_id": item["id"],
            "download_url": item["download_url"],
            "bytes": target.stat().st_size,
            "publisher_md5": expected_md5,
            "sha256": sha256,
            "downloaded_this_run": downloaded,
        })
        print(f"Verified {name}: SHA-256 {sha256}", flush=True)

    manifest = {
        "title": metadata["title"],
        "doi": metadata["doi"],
        "authors": [item["full_name"] for item in metadata["authors"]],
        "landing_page": metadata["url_public_html"],
        "metadata_url": METADATA_URL,
        "license": metadata["license"],
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": verified,
    }
    (ROOT / "data" / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
