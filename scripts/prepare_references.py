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
        'filename': 'ADT_R23_3D.zip',
        'url': 'https://www.adtlink.cn/Uploads/download/ADT_R23_3D.zip',
        'sha256': '227d64324a5d49b440ffbe7c01bea4c7cc162d9b05a6b5b20bc370cf0c083be8',
        'bytes': 21188109,
    },
    'psu': {
        'filename': 'enp7660b-official-spec-20251008.pdf',
        'url': 'https://www.enhanceusa.com/upload/DM/202510080638420.pdf',
        'sha256': '8df699a26d42f0849d06c9cd043733581196acea124f6a97b5c515b07cce7c4e',
        'bytes': 325319,
    },
}
STEP_MEMBER = 'R23SR 20230514.step'
STEP_SHA256 = 'daea4402f8c8652474d4e57de4ae1d59c219e5d86f5db2b2c6fc56857e8fb018'


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
            raise ValueError('Unexpected vendor archive: R23SR STEP member is missing, duplicated, or oversized')
        raw_data = bundle.read(matching[0])
    if hashlib.sha256(raw_data).hexdigest() != STEP_SHA256:
        raise ValueError('Unexpected R23SR source STEP checksum')
    raw_step = PRIVATE / STEP_MEMBER
    raw_step.write_bytes(raw_data)
    shape = cq.importers.importStep(str(raw_step)).val()
    solids = shape.Solids()
    if len(solids) != 263:
        raise ValueError('Unexpected R23SR solid decomposition; stop and inspect vendor geometry')
    result = {'source_step_sha256': hashlib.sha256(raw_data).hexdigest(), 'endpoints': {}}
    for name, pcb_lo, pcb_hi, lo, hi in (
        ('male', -100, -21.70125, -100, -10),
        ('female', 21.29875, 100, 10, 100),
    ):
        pieces = []
        source_indices = []
        for index, solid in enumerate(solids):
            bounds = solid.BoundingBox()
            if index == 0:
                pieces += solid.intersect(box((400, pcb_hi - pcb_lo, 100), (-200, pcb_lo, -50))).Solids()
                source_indices.append(index)
            elif bounds.ymin >= lo - .001 and bounds.ymax <= hi + .001:
                pieces.append(solid)
                source_indices.append(index)
        endpoint = cq.Compound.makeCompound(pieces)
        expected = {'male': 47, 'female': 215}
        if not endpoint.isValid() or len(pieces) != expected[name]:
            raise ValueError(f'Unexpected {name} endpoint: {len(pieces)} solids; stop and inspect vendor geometry')
        output = PRIVATE / f'R23SR_official_{name}_endpoint.step'
        cq.exporters.export(endpoint, str(output))
        result['endpoints'][name] = {
            'filename': output.name,
            'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
            'valid': True,
            'solids': len(pieces),
            'source_indices': source_indices,
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
    print('Next: python design/r6_export.py. CAD export does not establish physical/manufacturing acceptance.')


if __name__ == '__main__':
    main()
