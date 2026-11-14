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
        assert not Path(name).parts[0].startswith('out-r')
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
    review_path = ROOT / 'evidence/current-review.json'
    review = json.loads(review_path.read_text())
    assert isinstance(review['geometric_checks_passed'], bool)
    assert review['geometric_checks_passed'] == (not any(review['checks'].values()))
    assert review['manufacturing_release'] is False
    assert review['thermal_or_physical_acceptance_completed'] is False
    part_count = len(review['parts'])
    assert len(list((ROOT / 'cad/parts').glob('*.step'))) == part_count
    assert len(list((ROOT / 'cad/parts').glob('*.stl'))) == part_count
    fabrication_names=set()
    for item in review.get('original_fabrication_assets', []):
        for name, expected in item['files'].items():
            fabrication_names.add(name)
            assert hashlib.sha256((ROOT/'cad/fabrication'/name).read_bytes()).hexdigest() == expected
    actual_fabrication={p.name for p in (ROOT/'cad/fabrication').glob('*') if p.suffix in ('.step','.dxf')}
    assert actual_fabrication==fabrication_names
    assert not (ROOT/'cad/fabrication/R8_RISER_MALE_INSULATING_SILICONE_PAD_1p5_COMPRESSED_1p4.step').exists()
    data = (ROOT / 'cad/kiwinest-public.glb').read_bytes()
    length = struct.unpack_from('<I', data, 12)[0]
    document = json.loads(data[20:20 + length])
    names = {node.get('name') for node in document['nodes']}
    assert not (names & set(review['public_geometry']['excluded_vendor_nodes']))
    assert not any(name and '_OFFICIAL_' in name for name in names)
    html = (ROOT / 'docs/preview.html').read_text()
    encoded = re.search(r"atob\('([A-Za-z0-9+/=]+)'\)", html)
    assert encoded and base64.b64decode(encoded.group(1)) == data
    print(json.dumps({'tracked_files': len(tracked), 'sha256_files': len(manifest['files']),
                      'original_parts': part_count, 'public_model_nodes': len(names) - 1,
                      'geometry_passed': review['geometric_checks_passed'], 'publication_checks_passed': True}))


if __name__ == '__main__':
    main()
