"""Fetch the official prebuilt bpmn-js modeler, verify npm integrity, keep local.

No global installation, no CDN calls when viewing a diagram. npm's published
SHA-512 integrity is checked before selected regular package files are copied.
"""
import base64
import hashlib
import io
import json
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / '.tools/bpmn-js'


def main():
    manifest_path=ROOT/'docs/bpmn_viewer_manifest.json'
    pinned=json.loads(manifest_path.read_text())['version'] if manifest_path.exists() else 'latest'
    metadata = json.load(urllib.request.urlopen('https://registry.npmjs.org/bpmn-js/'+pinned, timeout=60))
    data = urllib.request.urlopen(metadata['dist']['tarball'], timeout=120).read()
    algorithm, expected = metadata['dist']['integrity'].split('-', 1)
    assert algorithm == 'sha512'
    assert base64.b64encode(hashlib.sha512(data).digest()).decode() == expected
    hashes = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        for member in archive.getmembers():
            name = member.name.removeprefix('package/')
            if not member.isfile() or not (name.startswith('dist/assets/') or name in (
                'dist/bpmn-modeler.production.min.js', 'LICENSE', 'package.json')):
                continue
            target = (TARGET / name).resolve()
            if not target.is_relative_to(TARGET.resolve()): raise ValueError('Invalid archive path')
            content = archive.extractfile(member).read()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            hashes[name] = hashlib.sha256(content).hexdigest()
    manifest = {'package': 'bpmn-js', 'version': metadata['version'],
        'source': metadata['dist']['tarball'], 'integrity': metadata['dist']['integrity'],
        'license': metadata.get('license'), 'artifacts_sha256': hashes}
    (ROOT / 'docs/bpmn_viewer_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f"Installed local bpmn-js {metadata['version']}; {len(hashes)} files; SHA-512 verified")


if __name__ == '__main__': main()
