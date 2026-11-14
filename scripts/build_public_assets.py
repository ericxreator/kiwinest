#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Publish original R6 geometry while removing vendor models and their bytes.

Run after design/r6_export.py. Only the explicit original-part allowlist and
original hardware/cable proxies are distributed. This is not a CAD check.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import shutil
import struct

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {
    'R6_R83SL_OFFICIAL_x16_FEMALE_ASSEMBLED',
    'R6_R83SL_OFFICIAL_x8_MALE_ASSEMBLED',
}


def prune_glb(data: bytes, allowed: set[str]) -> tuple[bytes, dict]:
    magic, version, total = struct.unpack_from('<4sII', data)
    assert magic == b'glTF' and version == 2 and total == len(data)
    length, kind = struct.unpack_from('<II', data, 12)
    assert kind == 0x4E4F534A
    source = json.loads(data[20:20 + length])
    binary_length, binary_type = struct.unpack_from('<II', data, 20 + length)
    assert binary_type == 0x004E4942
    binary = data[28 + length:28 + length + binary_length]
    assert not any(key in source for key in ('images', 'textures', 'skins', 'animations'))
    assert len(source['buffers']) == 1
    # The CAD exporter emits one named node per part under one rotated root.
    selected = [node for node in source['nodes'] if node.get('name') in allowed]
    assert {node['name'] for node in selected} == allowed
    meshes = sorted({node['mesh'] for node in selected})
    mesh_map = {old: new for new, old in enumerate(meshes)}
    accessors = set()
    for index in meshes:
        for primitive in source['meshes'][index]['primitives']:
            assert 'extensions' not in primitive and 'targets' not in primitive
            accessors.update(primitive['attributes'].values())
            accessors.add(primitive['indices'])
    accessor_map = {old: new for new, old in enumerate(sorted(accessors))}
    result = {
        'asset': {'version': '2.0', 'generator': 'KiwiNest original-geometry publisher'},
        'scene': 0, 'scenes': [{'nodes': [0]}],
        'nodes': [], 'meshes': [], 'accessors': [], 'bufferViews': [],
        'materials': copy.deepcopy(source.get('materials', [])),
    }
    output = bytearray()
    widths = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}
    sizes = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
    # Copy only bytes addressed by selected accessors. Copying whole shared
    # bufferViews would retain the removed vendor connectors in unused bytes.
    for old in sorted(accessors):
        accessor = copy.deepcopy(source['accessors'][old])
        assert 'sparse' not in accessor
        view = source['bufferViews'][accessor['bufferView']]
        width = widths[accessor['type']] * sizes[accessor['componentType']]
        stride = view.get('byteStride', width)
        offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
        output.extend(b'\0' * (-len(output) % 4))
        start = len(output)
        if stride == width:
            output.extend(binary[offset:offset + width * accessor['count']])
        else:
            for item in range(accessor['count']):
                output.extend(binary[offset + item * stride:offset + item * stride + width])
        new_view = {'buffer': 0, 'byteOffset': start, 'byteLength': len(output) - start}
        if 'target' in view:
            new_view['target'] = view['target']
        accessor['bufferView'] = len(result['bufferViews'])
        accessor['byteOffset'] = 0
        result['bufferViews'].append(new_view)
        result['accessors'].append(accessor)
    for old in meshes:
        mesh = copy.deepcopy(source['meshes'][old])
        for primitive in mesh['primitives']:
            primitive['attributes'] = {key: accessor_map[value] for key, value in primitive['attributes'].items()}
            primitive['indices'] = accessor_map[primitive['indices']]
        result['meshes'].append(mesh)
    root = copy.deepcopy(source['nodes'][0])
    root['name'] = 'KiwiNest-R6-original-geometry'
    root['children'] = list(range(1, len(selected) + 1))
    result['nodes'].append(root)
    for node in selected:
        node = copy.deepcopy(node)
        assert 'children' not in node
        node['mesh'] = mesh_map[node['mesh']]
        result['nodes'].append(node)
    result['buffers'] = [{'byteLength': len(output)}]
    encoded = json.dumps(result, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    output.extend(b'\0' * (-len(output) % 4))
    packed = struct.pack('<4sII', b'glTF', 2, 28 + len(encoded) + len(output))
    packed += struct.pack('<II', len(encoded), 0x4E4F534A) + encoded
    packed += struct.pack('<II', len(output), 0x004E4942) + output
    return packed, result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'out-r6')
    args = parser.parse_args()
    source = args.input
    report_data = (source / 'report.json').read_bytes()
    report = json.loads(report_data)
    allowed = set(report['parts']) | set(report['envelopes']) | set(report['cables'])
    allowed -= EXCLUDED
    cad = ROOT / 'cad'
    (cad / 'parts').mkdir(parents=True, exist_ok=True)
    for name in report['parts']:
        for suffix in ('.step', '.stl'):
            shutil.copyfile(source / 'parts' / (name + suffix), cad / 'parts' / (name + suffix))
    shutil.copyfile(source / 'PSU-flange-1mm-REVIEW.dxf', cad / 'PSU-flange-1mm-REVIEW.dxf')
    flange = 'PSU_R6_REPLACEABLE_1mm_METAL_FLANGE_NOT_PRINT.step'
    shutil.copyfile(source / 'envelopes' / flange, cad / flange)
    glb, document = prune_glb((source / 'assembly.glb').read_bytes(), allowed)
    (cad / 'kiwinest-r6-public.glb').write_bytes(glb)
    evidence = {
        'revision': 'R6',
        'source_report_sha256': hashlib.sha256(report_data).hexdigest(),
        'stage': report['stage'],
        'geometric_checks_passed': report['geometric_checks_passed'],
        'thermal_or_physical_acceptance_completed': report['thermal_or_physical_acceptance_completed'],
        'manufacturing_release': False,
        'body_mm': report['body_mm'], 'overall_target_mm': report['overall_target_mm'],
        'known_blocker': report['known_blocker'],
        'checks': report['checks'],
        'parts': report['parts'],
        'source_step_roundtrip': report['step_roundtrip'],
        'original_print_meshes_watertight': report['all_prints_watertight'],
        'public_geometry': {
            'nodes': len(document['nodes']) - 1, 'parts': len(report['parts']),
            'excluded_vendor_nodes': sorted(EXCLUDED),
            'sha256': hashlib.sha256(glb).hexdigest(),
            'scope': 'Original chassis, hardware and cable planning proxies. Vendor endpoint geometry omitted. Not a new collision or manufacturing acceptance.',
        },
        'additional_blockers': [
            'Factory EPS300mm not accepted: minimum complete route >=308.309mm before connector allowance; confirm >=350mm, preferably400mm, or reroute.',
            'Board socket and mounting coordinates are photo-derived; physical fit-up remains required.',
            'Lower riser bands intersect protected supply air; no CFD, thermal or noise acceptance.',
        ],
    }
    evidence_dir = ROOT / 'evidence'
    evidence_dir.mkdir(exist_ok=True)
    (evidence_dir / 'r6-review.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    docs = ROOT / 'docs'
    docs.mkdir(exist_ok=True)
    template = (ROOT / 'scripts' / 'preview-template.html').read_text()
    (docs / 'preview.html').write_text(template.replace('__MODEL_BASE64__', base64.b64encode(glb).decode()))
    print(json.dumps({'original_parts': len(report['parts']), 'public_nodes': len(allowed),
                      'vendor_nodes_removed': len(EXCLUDED), 'public_glb_bytes': len(glb),
                      'geometry_passed': report['geometric_checks_passed']}))


if __name__ == '__main__':
    main()
