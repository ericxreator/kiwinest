#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Audit exact public GLB accessor bytes against the local CAD export.

Manufacturer endpoint nodes and every accessor used exclusively by them must
be absent. Unaddressed public binary bytes must be alignment zeros only.
This audit does not validate physical fit or manufacturing readiness.
"""
import hashlib
import json
import argparse
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]


def read_glb(path):
    data = path.read_bytes()
    magic, version, total = struct.unpack_from('<4sII', data)
    assert magic == b'glTF' and version == 2 and total == len(data)
    size, kind = struct.unpack_from('<II', data, 12)
    assert kind == 0x4E4F534A
    doc = json.loads(data[20:20 + size])
    length, kind = struct.unpack_from('<II', data, 20 + size)
    assert kind == 0x004E4942
    assert 28 + size + length == len(data), 'Unexpected trailing GLB content'
    assert set(doc) <= {'asset', 'scene', 'scenes', 'nodes', 'meshes', 'accessors',
                        'bufferViews', 'buffers', 'materials'}
    assert len(doc['buffers']) == 1 and set(doc['buffers'][0]) == {'byteLength'}
    forbidden = {'uri', 'extras', 'extensions', 'extensionsUsed', 'extensionsRequired'}
    def inspect(value):
        if isinstance(value, dict):
            assert not set(value) & forbidden, 'Unexpected GLB metadata or external payload'
            for child in value.values():
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)
    inspect(doc)
    blob=data[28 + size:28 + size + length]
    assert 0<=len(blob)-doc['buffers'][0]['byteLength']<=3
    return doc, blob


def accessor(doc, blob, index):
    a = doc['accessors'][index]
    v = doc['bufferViews'][a['bufferView']]
    assert 'sparse' not in a
    width = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[a['type']]
    width *= {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}[a['componentType']]
    start = v.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = v.get('byteStride', width)
    assert stride>=width and a['count']>=0
    end=start+(a['count']-1)*stride+width if a['count'] else start
    assert v.get('byteOffset',0)<=start<=end<=v.get('byteOffset',0)+v['byteLength']
    assert end<=len(blob)
    ranges = [(start + row * stride, width) for row in range(a['count'])]
    return b''.join(blob[offset:offset + size] for offset, size in ranges), ranges


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'out-r9')
    args = parser.parse_args()
    raw = args.input / 'assembly.glb'
    public = ROOT / 'cad/kiwinest-public.glb'
    source, sb = read_glb(raw)
    target, tb = read_glb(public)
    report_file = args.input / 'report.json'
    report = json.loads(report_file.read_text())
    review = json.loads((ROOT / 'evidence/current-review.json').read_text())
    report_sha = hashlib.sha256(report_file.read_bytes()).hexdigest()
    assert review['source_report_sha256'] == report_sha
    assert review['public_geometry']['sha256'] == hashlib.sha256(public.read_bytes()).hexdigest()
    excluded = set(report['external_geometry_names'])
    assert len(excluded) == 2
    pressed_foam = 'R8_RISER_MALE_INSULATING_SILICONE_PAD_1p5_COMPRESSED_1p4'
    if pressed_foam in report['envelopes']:
        excluded.add(pressed_foam)
    assert excluded == set(review['public_geometry']['excluded_vendor_nodes'])
    sn = {n['name']: n for n in source['nodes'] if 'mesh' in n}
    tn = {n['name']: n for n in target['nodes'] if 'mesh' in n}
    assert len(sn)==sum('mesh' in n for n in source['nodes']), 'Duplicate local node name'
    assert len(tn)==sum('mesh' in n for n in target['nodes']), 'Duplicate public node name'
    assert set(tn) == set(sn) - excluded
    transforms=('matrix','translation','rotation','scale')
    for key in transforms:
        assert source['nodes'][0].get(key)==target['nodes'][0].get(key), 'Changed assembly transform'
    for name,node in tn.items():
        for key in transforms:
            assert sn[name].get(key)==node.get(key), (name,'Changed retained transform')
    selected_accessors, vendor_accessors = set(), set()
    for name, node in sn.items():
        for primitive in source['meshes'][node['mesh']]['primitives']:
            (vendor_accessors if name in excluded else selected_accessors).update(
                [primitive['indices'], *primitive['attributes'].values()])
    assert not selected_accessors & vendor_accessors
    def spans(indices):
        ranges = []
        for index in indices:
            a = source['accessors'][index]
            view = source['bufferViews'][a['bufferView']]
            _, addressed = accessor(source, sb, index)
            # Keep actual addressed intervals: bufferViews may share storage.
            ranges.extend((start, start + size) for start, size in addressed)
        merged = []
        for start, end in sorted(ranges):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
            else:
                merged.append((start, end))
        return merged
    own_spans, vendor_spans = spans(selected_accessors), spans(vendor_accessors)
    i = j = 0
    while i < len(own_spans) and j < len(vendor_spans):
        a, b = own_spans[i], vendor_spans[j]
        assert a[1] <= b[0] or b[1] <= a[0], 'Manufacturer and selected byte ranges overlap'
        if a[1] <= b[1]:
            i += 1
        else:
            j += 1
    covered = bytearray(len(tb))
    matched = set()
    for name, node in tn.items():
        old = source['meshes'][sn[name]['mesh']]['primitives']
        new = target['meshes'][node['mesh']]['primitives']
        assert len(old) == len(new)
        for before, after in zip(old, new):
            assert before.get('mode', 4) == after.get('mode', 4)
            assert set(before['attributes']) == set(after['attributes'])
            old_material=source.get('materials',[])[before['material']] if 'material' in before else None
            new_material=target.get('materials',[])[after['material']] if 'material' in after else None
            assert old_material==new_material, (name,'Changed retained material')
            pairs = [(before['indices'], after['indices'])]
            pairs += [(before['attributes'][key], after['attributes'][key]) for key in before['attributes']]
            for oi, ni in pairs:
                for key in ('count', 'type', 'componentType', 'normalized'):
                    assert source['accessors'][oi].get(key) == target['accessors'][ni].get(key)
                old_bytes, _ = accessor(source, sb, oi)
                new_bytes, ranges = accessor(target, tb, ni)
                assert old_bytes == new_bytes, (name, oi, ni)
                matched.add((oi, ni))
                for offset, size in ranges:
                    covered[offset:offset + size] = b'\1' * size
    assert len(matched) == len(target['accessors'])
    assert {ni for _, ni in matched} == set(range(len(target['accessors'])))
    assert all(byte == 0 for i, byte in enumerate(tb) if not covered[i])
    result = {'source_report_sha256': report_sha,
        'raw_glb_sha256': hashlib.sha256(raw.read_bytes()).hexdigest(),
        'public_glb_sha256': hashlib.sha256(public.read_bytes()).hexdigest(),
        'public_nodes': len(tn), 'excluded_vendor_nodes': sorted(excluded),
        'selected_accessors_byte_matched': len(matched), 'vendor_accessor_overlap': 0,
        'unused_binary_bytes_zero_only': True,'retained_node_transforms_matched':True,
        'assembly_root_transform_matched':True,'retained_material_properties_matched':True,
        'geometry_is_physical_acceptance': False}
    (ROOT / 'evidence/public-geometry-audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
