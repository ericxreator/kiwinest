#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Download checksum-pinned vendor inputs for local use, never redistribution.

All downloaded and extracted files stay under the gitignored references/private/
folder. Original manufacturer terms apply. No license to vendor material is
implied by KiwiNest's source-code or original-design licenses.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'references/private'
INPUTS = {
    'adt': {
        'filename': 'ADT_R83_3D.zip',
        'url': 'https://www.adtlink.cn/Uploads/download/ADT_R83_3D.zip',
        'sha256': '10d914c2fd31f081c9dc8c8d6bb5b5b48d283d560bfc82932b4a4a48363e5065',
        'bytes': 8470296,
    },
    'psu': {
        'filename': 'enp7660b-official-spec-20251008.pdf',
        'url': 'https://www.enhanceusa.com/upload/DM/202510080638420.pdf',
        'sha256': '8df699a26d42f0849d06c9cd043733581196acea124f6a97b5c515b07cce7c4e',
        'bytes': 325319,
    },
}
STEP_MEMBER = 'R83SL 20190922.step'


def verified_input(spec: dict, supplied: Path | None) -> Path:
    target = PRIVATE / spec['filename']
    if supplied is not None:
        data = supplied.read_bytes()
    elif target.exists():
        data = target.read_bytes()
    else:
        request = urllib.request.Request(spec['url'], headers={'User-Agent': 'KiwiNest-reference-preparation/1'})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(spec['bytes'] + 1)
    if len(data) != spec['bytes'] or hashlib.sha256(data).hexdigest() != spec['sha256']:
        raise ValueError(f"Reference changed or incomplete: {spec['filename']}; stop and review the manufacturer source")
    target.write_bytes(data)
    return target


def extract_endpoints(archive: Path) -> dict:
    import cadquery as cq
    sys.path.insert(0, str(ROOT / 'design'))
    from build import box, bbox

    # Select one exact regular ZIP member, with no archive-wide extraction.
    with zipfile.ZipFile(archive) as bundle:
        matching = [item for item in bundle.infolist() if item.filename == STEP_MEMBER]
        if len(matching) != 1 or matching[0].is_dir() or matching[0].file_size > 80_000_000:
            raise ValueError('Unexpected vendor archive: R83SL STEP member is missing, duplicated, or oversized')
        raw_data = bundle.read(matching[0])
    raw_step = PRIVATE / STEP_MEMBER
    raw_step.write_bytes(raw_data)
    shape = cq.importers.importStep(str(raw_step)).val()
    solids = shape.Solids()
    result = {'source_step_sha256': hashlib.sha256(raw_data).hexdigest(), 'endpoints': {}}
    for name, pcb_lo, pcb_hi, lo, hi in (
        ('male', 200, 222.879394523, 200, 226),
        ('female', 265.879395778, 300, 262, 300),
    ):
        pieces = []
        for index, solid in enumerate(solids):
            bounds = solid.BoundingBox()
            if index == 0:
                pieces += solid.intersect(box((300, pcb_hi - pcb_lo, 100), (0, pcb_lo, -50))).Solids()
            elif bounds.ymin >= lo - .001 and bounds.ymax <= hi + .001:
                pieces.append(solid)
        endpoint = cq.Compound.makeCompound(pieces)
        expected = {'male': 88, 'female': 252}
        if not endpoint.isValid() or len(pieces) != expected[name]:
            raise ValueError(f'Unexpected {name} endpoint: {len(pieces)} solids; stop and inspect vendor geometry')
        output = PRIVATE / f'R83SL_official_{name}_endpoint.step'
        cq.exporters.export(endpoint, str(output))
        result['endpoints'][name] = {
            'filename': output.name,
            'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
            'valid': True,
            'solids': len(pieces),
            'bbox_mm': bbox(endpoint),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adt-archive', type=Path, help='Use an existing official archive after the same exact checksum verification')
    parser.add_argument('--psu-pdf', type=Path, help='Use an existing official PDF after the same exact checksum verification')
    args = parser.parse_args()
    PRIVATE.mkdir(parents=True, exist_ok=True)
    archive = verified_input(INPUTS['adt'], args.adt_archive)
    verified_input(INPUTS['psu'], args.psu_pdf)
    receipt = extract_endpoints(archive)
    receipt['inputs'] = INPUTS
    receipt['redistribution'] = 'VENDOR_INPUTS_LOCAL_ONLY_NOT_COVERED_BY_PROJECT_LICENSES'
    (PRIVATE / 'preparation-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('Verified manufacturer inputs prepared in references/private/ (gitignored).')
    print('Next: python design/r6_export.py. R6 remains an unresolved geometry prototype.')


if __name__ == '__main__':
    main()
