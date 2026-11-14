#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify the committed publication boundary and checksums, not CAD acceptance."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    tracked = [name for name in tracked if name]
    assert tracked, 'No tracked publication files'
    for name in tracked:
        assert not name.startswith(('references/private/', 'out-r6/', 'analysis/', '.venv/'))
        assert Path(name).suffix.lower() not in ('.pdf', '.zip', '.jpg', '.jpeg', '.webp')
        content = (ROOT / name).read_bytes()
        markers = (b'/' + b'home/' + b'eric/', b'/' + b'tmp/' + b'codex',
                   b'192.' + b'168.' + b'168.', b'famlab' + b'.app',
                   b'-----BEGIN ' + b'PRIVATE KEY-----', b'-----BEGIN ' + b'OPENSSH PRIVATE KEY-----')
        for marker in markers:
            assert marker not in content, f'Private marker in {name}'
        if Path(name).suffix in ('.py', '.md', '.json', '.csv', '.txt', '.html'):
            text = content.decode('utf-8-sig')
            assert not re.search(r'(?i)(?:gh[pousr]_[a-z0-9]{25,}|github_pat_[a-z0-9_]{30,})', text), name
    manifest = json.loads((ROOT / 'MANIFEST.json').read_text())
    for name, expected in manifest['files'].items():
        actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        assert actual == expected, f'Changed publication file: {name}'
    assert set(manifest['files']) == set(tracked) - {'MANIFEST.json'}
    review = json.loads((ROOT / 'evidence/r6-review.json').read_text())
    assert review['geometric_checks_passed'] is False and review['manufacturing_release'] is False
    assert len(list((ROOT / 'cad/parts').glob('*.step'))) == 40
    assert len(list((ROOT / 'cad/parts').glob('*.stl'))) == 40
    data = (ROOT / 'cad/kiwinest-r6-public.glb').read_bytes()
    length = struct.unpack_from('<I', data, 12)[0]
    document = json.loads(data[20:20 + length])
    names = {node.get('name') for node in document['nodes']}
    assert not any(name and name.startswith('R6_R83SL_OFFICIAL_') for name in names)
    html = (ROOT / 'docs/preview.html').read_text()
    encoded = re.search(r"atob\('([A-Za-z0-9+/=]+)'\)", html)
    assert encoded and base64.b64decode(encoded.group(1)) == data
    print(json.dumps({'tracked_files': len(tracked), 'sha256_files': len(manifest['files']),
                      'original_parts': 40, 'public_model_nodes': len(names) - 1,
                      'geometry_passed': False, 'publication_checks_passed': True}))


if __name__ == '__main__':
    main()
