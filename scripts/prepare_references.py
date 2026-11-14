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
from io import BytesIO
import json
from pathlib import Path
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'references/private'
INPUTS = {
    'adt': {
        'filename': 'ADT_K83UP-TL_3D.zip',
        'url': 'https://www.adtlink.cn/download/ADT_K83UP-TL_3D.zip',
        'sha256': '1971eca32a1d68b7ef9b86890fe03d989d0ddb1659a6031c6fe1f2e425eb2c56',
        'bytes': 36635266,
    },
    'psu': {
        'filename': 'enp7660b-official-spec-20251008.pdf',
        'url': 'https://www.enhanceusa.com/upload/DM/202510080638420.pdf',
        'sha256': '8df699a26d42f0849d06c9cd043733581196acea124f6a97b5c515b07cce7c4e',
        'bytes': 325319,
    },
}
STEP_MEMBER = 'K83UP-TL 5.0 20260707.step'
STEP_SHA256 = 'e156ba5c03c742bebcb18983eb98ac41141be0d495ccd572c6015d496692b309'


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
        if len(matching) != 1 or matching[0].is_dir() or matching[0].file_size != 96_869_926:
            raise ValueError('Unexpected vendor archive: K83UP-TL STEP member is missing, duplicated, or changed')
        raw_data = bundle.read(matching[0])
    if hashlib.sha256(raw_data).hexdigest() != STEP_SHA256:
        raise ValueError('Unexpected K83UP-TL source STEP checksum')
    raw_step = PRIVATE / STEP_MEMBER
    raw_step.write_bytes(raw_data)
    shape = cq.importers.importStep(str(raw_step)).val()
    solids = shape.Solids()
    if len(solids) != 1012:
        raise ValueError('Unexpected K83UP-TL solid decomposition; stop and inspect vendor geometry')
    serialized = []
    for solid in solids:
        stream = BytesIO(); solid.exportBrep(stream)
        serialized.append(hashlib.sha256(stream.getvalue()).hexdigest())
    # These are exact repeated source instances, not equal-volume guesses.
    assert serialized[33] == serialized[34] == serialized[35], 'Changed coax core instances'
    result = {'step_sha256': STEP_SHA256, 'source_solids': 1012,
              'source_core_index': 33, 'source_wrapper_index': 36,
              'method': 'Exact serialized BREP SHA-256 identity only; natural PCB split; retain coax core stubs inside both complete factory sleeves',
              'endpoints': {}}
    for name, pcb_lo, pcb_hi, core_lo, core_hi in (
        ('male', 65.143, 200., 43.655531002198, 200.),
        ('female', -200., -16.143, -200., -61.79632251401),
    ):
        pieces = solids[0].intersect(box((pcb_hi-pcb_lo,100,100),(pcb_lo,-50,-50))).Solids()
        source_indices = [0]; indices = {'0':0}; duplicates = []; seen = {}
        assert len(pieces) == 1
        for index, solid in enumerate(solids[1:],1):
            bounds = solid.BoundingBox()
            if index in (33,34,35):
                if index != 33:
                    if name == 'male': duplicates.append([index,33])
                    continue
                stub = solid.intersect(box((core_hi-core_lo,100,100),(core_lo,-50,-50))).Solids()
                if stub:
                    assert len(stub) == 1
                    indices[str(index)] = len(pieces); pieces.extend(stub); source_indices.append(index)
                continue
            # Only the free demo braid is replaced by the routed harness.
            if index in (36,37,38): continue
            # Natural gap separates endpoints. Keep even the tiny braid-end
            # fragments just outside the sleeve rather than clipping them.
            selected = bounds.xmin > 0 if name == 'male' else bounds.xmax < 0
            if not selected: continue
            digest = serialized[index]
            if digest in seen:
                duplicates.append([index,seen[digest]]); continue
            seen[digest] = index; indices[str(index)] = len(pieces)
            pieces.append(solid); source_indices.append(index)
        endpoint = cq.Compound.makeCompound(pieces)
        expected = {'male': 143, 'female': 219}
        if not endpoint.isValid() or len(pieces) != expected[name]:
            raise ValueError(f'Unexpected {name} endpoint: {len(pieces)} solids; stop and inspect vendor geometry')
        output = PRIVATE / f'K83UP_TL_official_{name}_endpoint.step'
        cq.exporters.export(endpoint, str(output))
        brep = output.with_suffix('.brep'); endpoint.exportBrep(str(brep))
        result['endpoints'][name] = {
            'filename': output.name,
            'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
            'brep_sha256': hashlib.sha256(brep.read_bytes()).hexdigest(),
            'valid': True,
            'solids': len(pieces),
            'unique_source_indices': source_indices,
            'endpoint_indices_by_source': indices,
            'duplicates_exact_brep_pairs': duplicates,
            'selected_before_dedup': len(pieces)+len(duplicates),
            'bbox_mm': bbox(endpoint),
        }
    assert sum(v['selected_before_dedup'] for v in result['endpoints'].values())-1+3 == 1012, 'Source solid attribution is incomplete'
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
