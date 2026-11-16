#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Publish current original geometry while removing vendor models and bytes.

Run after design/r9_export.py. Only the explicit original-part allowlist and
original hardware/cable proxies are distributed. This is not a CAD check.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import html
import json
from pathlib import Path
import shutil
import struct

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {
    'R6_R83SL_OFFICIAL_x16_FEMALE_ASSEMBLED',
    'R6_R83SL_OFFICIAL_x8_MALE_ASSEMBLED',
}
PRESSED_FOAM = 'R8_RISER_MALE_INSULATING_SILICONE_PAD_1p5_COMPRESSED_1p4'
PUBLIC_FABRICATION_KEYS={
    'R8_RISER_MALE_CUSTOM_FR4_LOWER_CLAMP_0p8',
    'MAINBOARD_MOUNT_R8_lower_2_FLUSH_OD9_STEEL_CSK_WASHER',
    'MAINBOARD_MOUNT_R8_lower_4_FLUSH_OD9_STEEL_CSK_WASHER',
    'PSU_R6_REPLACEABLE_1mm_METAL_FLANGE_NOT_PRINT',
    'PSU_R9_REPLACEABLE_1mm_METAL_REAR_FLANGE_NOT_PRINT',
    'PSU_R9_SPLIT_INSULATING_FOAM_LEFT_INSTALLED',
    'PSU_R9_SPLIT_INSULATING_FOAM_RIGHT_INSTALLED',
    'PSU_R9_LEFT_PANEL_SEAL_INSTALLED','PSU_R9_REAR_PANEL_SEAL_INSTALLED',
    'R9_HDD_right_boundary_03mm_PC_SHEET',
    'R9_HDD_chimney_right_boundary_03mm_PC_SHEET',
    'R9_HDD_TOP_DIFFUSER_05mm_FOAM_EDGE_SEAL',
    *[f'R9_HDD_HATCH_{i}_REMOVABLE_SLOT_FOAM_SEAL' for i in (1,2,3)],
    *[f'R9_HDD_split_silicone_wire_seal_{i}' for i in range(1,7)],
}


def publication_preflight(source: Path,report: dict) -> None:
    """Refuse failed/stale CAD or unreviewed fabrication before public writes."""
    assert report['geometric_checks_passed'] and not any(report['checks'].values()), 'CAD checks are not clear'
    assert report['step_roundtrip']['passed'] and report['all_prints_watertight'], 'Export integrity is not clear'
    assert report['manufacturing_release'] is False
    assert report['thermal_or_physical_acceptance_completed'] is False
    for relative,digest in report.get('geometry_source_hashes',{}).items():
        path=Path(relative)
        assert not path.is_absolute() and '..' not in path.parts
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest, 'Source/report mismatch: '+relative
    flange=report['psu_meta']['metal_flange']
    flange_key=flange['key'] if isinstance(flange,dict) else flange
    assert flange_key in PUBLIC_FABRICATION_KEYS, 'Unreviewed metal flange'
    riser=report['riser_meta']
    assert set(report['external_geometry_names'])=={riser['male_hardware'],riser['female_hardware']}
    for item in report.get('original_fabrication_assets',[]):
        key=item['hardware_key']
        assert key==PRESSED_FOAM or key in PUBLIC_FABRICATION_KEYS, 'Unreviewed fabrication: '+key
        if report.get('params',{}).get('release_revision')=='R9' and key!=PRESSED_FOAM:
            assert item.get('geometry_origin')=='ORIGINAL_PRIMITIVE_GEOMETRY', 'Unexpected fabrication provenance'
        for name,digest in item['files'].items():
            assert Path(name).name==name and Path(name).stem==key
            assert Path(name).suffix in ('.step','.dxf')
            assert hashlib.sha256((source/'fabrication'/name).read_bytes()).hexdigest()==digest
    if report.get('params',{}).get('release_revision')=='R9':
        for name,info in report['parts'].items():
            assert hashlib.sha256((source/'parts'/(name+'.step')).read_bytes()).hexdigest()==info['step_sha256']
            assert hashlib.sha256((source/'parts'/(name+'.stl')).read_bytes()).hexdigest()==info['mesh']['sha256']
        expected=report['local_asset_sha256']['assembly.glb']
        assert hashlib.sha256((source/'assembly.glb').read_bytes()).hexdigest()==expected
        expected=report['local_asset_sha256']['PSU-flange-1mm-REVIEW.dxf']
        assert hashlib.sha256((source/'PSU-flange-1mm-REVIEW.dxf').read_bytes()).hexdigest()==expected
        expected=report['envelopes'][flange_key]['step_sha256']
        assert hashlib.sha256((source/'envelopes'/(flange_key+'.step')).read_bytes()).hexdigest()==expected


def publish_foam_stock(fabrication: Path, report: dict) -> dict:
    """Publish only an independently drawn flat blank, never OEM imprint faces."""
    import cadquery as cq
    info = report['envelopes'][PRESSED_FOAM]
    origin = info['bbox_mm']['min']
    width, length = info['bbox_mm']['size'][:2]
    raw = next(item for item in report['riser_meta']['original_fabrication_parts']
               if item['hardware_key'] == PRESSED_FOAM)
    thickness = raw['stock_thickness_mm']
    stock = cq.Solid.makeBox(width, length, thickness)
    holes = [[axis[0]-origin[0], axis[1]-origin[1]]
             for axis in report['riser_meta']['male_mounts']['axes']]
    for x, y in holes:
        stock = stock.cut(cq.Solid.makeCylinder(1.2, thickness+.2,
                          cq.Vector(x, y, -.1)))
    assert stock.isValid() and len(stock.Solids()) == 1
    stem = 'R8_RISER_MALE_SILICONE_FOAM_FLAT_STOCK_1p5'
    step, dxf = stem+'.step', stem+'.dxf'
    cq.exporters.export(stock, str(fabrication/step))
    cq.exporters.export(cq.Workplane('XY').newObject([stock]).faces('>Z').wires(),
                        str(fabrication/dxf))
    return dict(raw, asset_role='FLAT_RAW_STOCK_NOT_INSTALLED_CONTACT_ENVELOPE',
        stock_outline_mm=[width, length], stock_hole_centers_xy_mm=holes,
        stock_hole_diameter_mm=2.4, coordinate_frame='Local stock XY, Z0..1.5',
        scope='Original rectangle and two round holes only. Manufacturer-derived compressed contact surfaces are not distributed.',
        files={name:hashlib.sha256((fabrication/name).read_bytes()).hexdigest()
               for name in (step, dxf)}, manufacturing_release=False)


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
    assert len(selected)==len(allowed), 'Duplicate public node name'
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
        assert stride>=width and accessor['count']>=0
        end=offset+(accessor['count']-1)*stride+width if accessor['count'] else offset
        assert 0<=offset<=end<=len(binary)
        assert end<=view.get('byteOffset',0)+view['byteLength']
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
    assert 'mesh' not in root, 'Expected an assembly transform root'
    root['name'] = 'KiwiNest-original-geometry'
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
    parser.add_argument('--input', type=Path, default=ROOT / 'out-r9')
    args = parser.parse_args()
    source = args.input
    report_data = (source / 'report.json').read_bytes()
    report = json.loads(report_data)
    publication_preflight(source,report)
    excluded = EXCLUDED | set(report.get('external_geometry_names', []))
    riser = report.get('riser_meta', {})
    excluded |= {riser[key] for key in ('female_hardware', 'male_hardware') if key in riser}
    derived_excluded = {PRESSED_FOAM} & set(report['envelopes'])
    excluded |= derived_excluded
    allowed = set(report['parts']) | set(report['envelopes']) | set(report['cables'])
    excluded &= allowed
    allowed -= excluded
    assert not any('_OFFICIAL_' in name for name in allowed), 'Unexpected manufacturer geometry remains public'
    revision = report.get('params', {}).get('release_revision', 'R6')
    cad = ROOT / 'cad'
    (cad / 'parts').mkdir(parents=True, exist_ok=True)
    for old in (cad / 'parts').iterdir():
        if old.suffix in ('.step', '.stl') and old.stem not in report['parts']:
            old.unlink()
    for name in report['parts']:
        for suffix in ('.step', '.stl'):
            shutil.copyfile(source / 'parts' / (name + suffix), cad / 'parts' / (name + suffix))
    shutil.copyfile(source / 'PSU-flange-1mm-REVIEW.dxf', cad / 'PSU-flange-1mm-REVIEW.dxf')
    flange_meta=report['psu_meta']['metal_flange']
    flange_key = flange_meta['key'] if isinstance(flange_meta,dict) else flange_meta
    assert flange_key in PUBLIC_FABRICATION_KEYS
    flange = flange_key+'.step'
    shutil.copyfile(source / 'envelopes' / flange, cad / flange)
    for old in cad.glob('PSU_R*_REPLACEABLE_1mm_METAL*step'):
        if old.name != flange:old.unlink()
    fabrication = cad / 'fabrication'
    fabrication.mkdir(exist_ok=True)
    public_fabrication_assets = []
    # Remove only the previously generated, unpublished compressed envelope.
    for suffix in ('.step', '.dxf'):
        (fabrication/(PRESSED_FOAM+suffix)).unlink(missing_ok=True)
    for item in report.get('original_fabrication_assets', []):
        if item['hardware_key'] == PRESSED_FOAM:
            public_fabrication_assets.append(publish_foam_stock(fabrication, report))
            continue
        for name, digest in item['files'].items():
            assert Path(name).name == name and Path(name).suffix in ('.step', '.dxf')
            assert Path(name).stem==item['hardware_key']
            data = (source / 'fabrication' / name).read_bytes()
            assert hashlib.sha256(data).hexdigest() == digest
            (fabrication / name).write_bytes(data)
        public_fabrication_assets.append(item)
    expected_fabrication={name for item in public_fabrication_assets for name in item['files']}
    for old in fabrication.iterdir():
        if old.suffix in ('.step','.dxf') and old.name not in expected_fabrication:old.unlink()
    glb, document = prune_glb((source / 'assembly.glb').read_bytes(), allowed)
    (cad / 'kiwinest-public.glb').write_bytes(glb)
    evidence = {
        'revision': revision,
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
            'excluded_vendor_nodes': sorted(excluded),
            'vendor_endpoint_nodes': sorted(set(report['external_geometry_names'])),
            'vendor_derived_contact_nodes': sorted(derived_excluded),
            'sha256': hashlib.sha256(glb).hexdigest(),
            'scope': 'Original chassis, hardware and cable planning proxies. Vendor endpoint geometry omitted. Not a new collision or manufacturing acceptance.',
        },
        'remaining_physical_gates': report.get('remaining_physical_gates', [
            'Board socket and mounting coordinates are photo-derived; physical fit-up remains required.',
            'Factory usable cable lengths, actual packing, bend radii, thermal and noise acceptance remain unverified.',
        ]),
    }
    if report.get('atx_refine_meta', {}).get('EPS_complete_length_budgets'):
        evidence['EPS_complete_length_budgets'] = report['atx_refine_meta']['EPS_complete_length_budgets']
        evidence['EPS_isolated_factory_exit_transition'] = report['atx_refine_meta']['EPS_isolated_factory_exit_transition']
    boundaries = report.get('psu_meta', {}).get('root_integration', {}).get('actual_cold_air_boundaries')
    if boundaries:
        evidence['PSU_structural_air_boundaries'] = boundaries
    evidence['complete_length_budgets'] = {
        name: route['complete_length_budget']
        for name, route in report.get('power_meta', {}).get('routes', {}).items()
        if 'complete_length_budget' in route
    }
    if report.get('gpu_power_meta', {}).get('complete_length_budget'):
        route_key = report.get('gpu_power_meta', {}).get('route_key', 'GPU_standard_extension')
        evidence['complete_length_budgets'][route_key] = report['gpu_power_meta']['complete_length_budget']
    gpu_channel = report.get('psu_meta', {}).get('GPU_isolated_factory_exit_transition')
    if gpu_channel:
        evidence['GPU_isolated_factory_exit_transition'] = gpu_channel
    evidence['GPU_factory_bottom_open_arch'] = report.get('psu_meta', {}).get('GPU_factory_bottom_open_arch')
    evidence['wire_bay_floor_open_edges'] = report.get('psu_meta', {}).get('wire_bay_floor_open_edges')
    evidence['PSU_final_cold_air_domain'] = report.get('psu_meta', {}).get('final_cold_air_domain')
    evidence['ATX_isolated_factory_exit_transition'] = report.get('psu_meta', {}).get('ATX_isolated_factory_exit_transition')
    evidence['ATX_GPU_shared_factory_exit_gland'] = report.get('psu_meta', {}).get('ATX_GPU_shared_factory_exit_gland')
    evidence['GPU_factory_service_parking'] = report.get('power_meta', {}).get('GPU_factory_service_parking')
    evidence['GPU_extension_service_parking'] = {key: report.get('gpu_power_meta', {}).get(key) for key in (
        'normal_paths', 'modeled_wire_centerline_mm', 'free_tail_mm', 'parked_tail_mm',
        'fixed_anchor_mm', 'park_path_mm', 'wire_diameter_mm', 'engineering_radius_mm',
        'cap_interface_intersections_mm3', 'physical_flexible_deformation_verified')}
    evidence['EPS_standard_extension'] = report.get('atx_refine_meta', {}).get('EPS_standard_extension')
    evidence['SATA_hub_extension'] = report.get('power_meta', {}).get('SATA_hub_extension')
    evidence['controls_complete_length_budgets'] = report.get('controls_meta', {}).get('complete_length_budgets')
    evidence['retained_stock_packing'] = report.get('power_meta', {}).get('surplus_packing')
    evidence['original_fabrication_assets'] = public_fabrication_assets
    evidence['factory_exit_engineering_assumptions'] = {
        'source_points_mm': report.get('power_meta', {}).get('native_factory_exit_points_engineering'),
        'gland_status': report.get('atx_refine_meta', {}).get('gland_y_status'),
        'received_hardware_verified': False,
    }
    evidence['measured_physical_bbox_mm'] = report.get('measured_physical_bbox_mm')
    evidence['measured_litres'] = report.get('measured_litres')
    hashes = report.get('geometry_source_hashes', {})
    for relative, digest in hashes.items():
        assert not Path(relative).is_absolute() and '..' not in Path(relative).parts
        assert len(digest) == 64 and all(c in '0123456789abcdef' for c in digest)
    evidence['geometry_source_hashes'] = hashes
    evidence['service_procedures'] = {
        'wire_roof': (gpu_channel or {}).get('service'),
        'GPU_card_only': report.get('gpu_meta', {}).get('gpu_card_only'),
    }
    evidence['riser_selection'] = {key: riser[key] for key in (
        'model', 'catalog_length_source', 'catalog_option_not_inventory_or_delivery_confirmation',
        'electrical_lanes', 'link_generation', 'bandwidth_tradeoff', 'release_status',
        'actual_male_CPU_guard_minimum_distance_mm', 'actual_male_CPU40_minimum_clearance_mm', 'male_mount_CPU40_minimum_clearances_mm',
        'modified_factory_parts','spring_contact_proof','validated_local_mechanical_contacts',
        'CPU_clearance_component_keys','selected_model','wire_paths','female_latch_pose',
        'native_braid_transition','male_mounts','limits') if key in riser}
    evidence['HDD_airflow_layout'] = report.get('drive_meta', {}).get('airflow')
    evidence['HDD_front_fan'] = report.get('drive_meta', {}).get('fan')
    evidence['HDD_drive_service'] = report.get('drive_meta', {}).get('service')
    evidence['HDD_front_fan_service'] = report.get('drive_meta', {}).get('front_fan_service')
    evidence['HDD_rear_hatches'] = report.get('drive_meta', {}).get('rear_connector_hatches')
    evidence['HDD_rear_data_cable_reliefs'] = report.get('frame_meta', {}).get('rear_data_cable_reliefs')
    evidence['HDD_complete_tail_parking'] = report.get('power_meta', {}).get('HDD_service_tail_parking')
    if report.get('incremental_validation_meta'):
        evidence['incremental_validation_meta'] = report['incremental_validation_meta']
    evidence['PSU_rolled_original_supply'] = {key:report.get('psu_meta', {}).get(key) for key in ('body_bbox_mm','body_axes','intake_face_scope','fixed_frame_support_implemented','complete_factory_source_material_proof','limits')}
    evidence['independent_feet_and_filter'] = {key:report.get('frame_meta', {}).get(key) for key in ('feet_mm','filter','front_left_split_column','front_left_lower_post_service')}
    evidence['mainboard_lower_flush_joints'] = report.get('mainboard_meta', {}).get('mount', {}).get('lower_flush_joints')
    evidence_dir = ROOT / 'evidence'
    evidence_dir.mkdir(exist_ok=True)
    (evidence_dir / 'current-review.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    docs = ROOT / 'docs'
    docs.mkdir(exist_ok=True)
    template = (ROOT / 'scripts' / 'preview-template.html').read_text()
    failed = report['checks']
    limits = []
    if failed.get('CPU40_hard_clearance'):
        limits.append('转接端头/固定件与CPU40mm保护空间仍有干涉')
    if failed.get('stock_length_or_storage_volume'):
        limits.append('线长或余线空间检查未通过')
    if failed.get('protected_air'):
        limits.append('保护风路仍有占用')
    if not limits and not report['geometric_checks_passed']:
        limits.append('整机检查仍有失败项，详见仓库报告')
    limits.append('实物接口、线缆安装、承载、热和噪声尚待验证')
    template = template.replace('__REVISION__', html.escape(revision))
    lanes = riser.get('electrical_lanes', 'unknown')
    generation = report.get('params', {}).get('target_pcie_generation', 3)
    template = template.replace('__PCIE_LINK__', html.escape(f'PCIe {generation}.0 x{lanes}（设计目标）'))
    template = template.replace('__CAD_RESULT__', 'CAD检查通过 · 待实物验证' if report['geometric_checks_passed'] else '未制造放行')
    template = template.replace('__CURRENT_LIMITS__', html.escape('；'.join(limits) + '。公开预览省略第三方端头、原厂锁扣及泡棉压接曲面。'))
    (docs / 'preview.html').write_text(template.replace('__MODEL_BASE64__', base64.b64encode(glb).decode()))
    print(json.dumps({'original_parts': len(report['parts']), 'public_nodes': len(allowed),
                      'vendor_endpoints_removed': len(report['external_geometry_names']),
                      'derived_contact_nodes_removed': len(derived_excluded), 'public_glb_bytes': len(glb),
                      'geometry_passed': report['geometric_checks_passed']}))


if __name__ == '__main__':
    main()
