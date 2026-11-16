# SPDX-License-Identifier: MIT
"""R9 traceable review export; full original endpoints remain local.

Failed checks remain failed in every artifact.
"""
from pathlib import Path
import argparse,hashlib,json,time,shutil
import cadquery as cq
from build import bbox,export_mesh
from build_r9 import build,check
ROOT=Path(__file__).resolve().parents[1]
PRESSED_FOAM='R8_RISER_MALE_INSULATING_SILICONE_PAD_1p5_COMPRESSED_1p4'
OWN_FABRICATION_KEYS={
    'R8_RISER_MALE_CUSTOM_FR4_LOWER_CLAMP_0p8',PRESSED_FOAM,
    'MAINBOARD_MOUNT_R8_lower_2_FLUSH_OD9_STEEL_CSK_WASHER',
    'MAINBOARD_MOUNT_R8_lower_4_FLUSH_OD9_STEEL_CSK_WASHER',
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


def fabrication_declarations(model):
    """Finite owned-geometry allowlist; supplier endpoints cannot qualify."""
    declared=[];seen=set()
    for group in ('riser_meta','mainboard_meta','psu_meta'):
        declared.extend(model.get(group,{}).get('original_fabrication_parts',[]))
    declared.extend(dict(info,hardware_key=name) for name,info in
                    model.get('drive_meta',{}).get('own_fabrication_parts',{}).items())
    for item in declared:
        name=item['hardware_key']
        if name not in OWN_FABRICATION_KEYS:
            raise ValueError('Unreviewed fabrication geometry: '+name)
        if name in seen:raise ValueError('Duplicate fabrication geometry: '+name)
        if name not in model['hardware']:raise ValueError('Missing fabrication solid: '+name)
        seen.add(name)
    return declared


def fabrication_flat_shape(shape,item):
    """Return a local planar view, inferred only for uniform thin prisms.

    Stepped washers with an explicit axis retain a face-outline DXF; their
    STEP remains authoritative for countersinks. Installed foam is never
    relabelled as an accepted raw-stock thickness.
    """
    axis=item.get('flat_axis');inferred=False
    if axis is None:
        bb=shape.BoundingBox();sizes={'X':bb.xlen,'Y':bb.ylen,'Z':bb.zlen}
        candidate=min(sizes,key=sizes.get)
        thickness=item.get('thickness_mm',sizes[candidate])
        if abs(sizes[candidate]-thickness)>1e-5:return None,{}
        axis=candidate;inferred=True
    if axis not in ('X','Y','Z'):raise ValueError('Unknown fabrication flat axis '+str(axis))
    flat=shape
    if axis=='X':flat=flat.rotate((0,0,0),(0,1,0),90)
    elif axis=='Y':flat=flat.rotate((0,0,0),(1,0,0),90)
    bb=flat.BoundingBox();flat=flat.translate((-bb.xmin,-bb.ymin,-bb.zmin))
    thickness=bb.zlen
    top_area=sum(face.Area() for face in cq.Workplane('XY').newObject([flat]).faces('>Z').vals())
    uniform=abs(top_area*thickness-shape.Volume())<=max(1e-4,shape.Volume()*1e-7)
    if inferred and not uniform:return None,{}
    return flat,{'export_flat_axis':axis,'flat_axis_inferred_from_uniform_prism':inferred,
      'nominal_geometry_thickness_mm':thickness,'uniform_prismatic_outline':uniform,
      'DXF_scope':'Nominal planar face outline only; STEP and material metadata remain authoritative for thickness, steps, compression and fit.'}


def export_fabrication(model,directory):
    """Export only declared originals; the pressed supplier imprint stays local."""
    directory.mkdir(parents=True,exist_ok=True);assets=[]
    for item in fabrication_declarations(model):
        name=item['hardware_key'];shape=model['hardware'][name]
        if not shape.isValid() or not shape.Solids():raise ValueError('Invalid fabrication geometry: '+name)
        filename=name+'.step';cq.exporters.export(shape,str(directory/filename));files=[filename]
        flat,scope=fabrication_flat_shape(shape,item)
        if flat is not None:
            filename=name+'.dxf'
            cq.exporters.export(cq.Workplane('XY').newObject([flat]).faces('>Z').wires(),str(directory/filename))
            files.append(filename)
        assets.append(dict(item,**scope,files={
            f:hashlib.sha256((directory/f).read_bytes()).hexdigest() for f in files},
            geometry_origin='LOCAL_SUPPLIER_DERIVED_CONTACT_ONLY' if name==PRESSED_FOAM else 'ORIGINAL_PRIMITIVE_GEOMETRY',
            manufacturing_release=False))
    return assets

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir',type=Path,default=ROOT/'out-r9')
    parser.add_argument('--checks-only',action='store_true',help='Write actual checks without STEP/STL export')
    args=parser.parse_args()
    import r6_riser
    reference_files = getattr(r6_riser, 'REFERENCE_FILES',
      ('R23SR_official_male_endpoint.step', 'R23SR_official_female_endpoint.step'))
    required = [ROOT/'references/private'/name for name in (*reference_files, 'enp7660b-official-spec-20251008.pdf')]
    if any(not path.is_file() for path in required):
        raise SystemExit('Missing local manufacturer references. Run: python scripts/prepare_references.py')
    t=time.time();print('Building complete chassis including local manufacturer endpoints',flush=True)
    m=build();print('Checking complete chassis, service sweeps and protected clearances',flush=True)
    checks=check(m);out=args.out_dir;out.mkdir(parents=True,exist_ok=True)
    geometry_passed=not any(checks.values())
    failures={name:len(values) for name,values in checks.items() if values}
    print('built; exporting review with actual issues '+json.dumps({k:len(v) for k,v in checks.items() if v}),flush=True)
    for rel,sha in m['geometry_source_hashes'].items():assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==sha,rel
    report={k:v for k,v in m.items() if k.endswith('_meta') or k in ('params','geometry_source_hashes')}
    riser=m.get('riser_meta',{})
    external=sorted(set([riser[key] for key in ('female_hardware','male_hardware') if key in riser]
      +riser.get('external_hardware_names',[])))
    report.update({'stage':'CAD_CHECKS_PASSED_PHYSICAL_VALIDATION_PENDING' if geometry_passed else 'GEOMETRY_REVIEW_BLOCKED_NOT_MANUFACTURING_RELEASE',
      'checks':checks,'body_mm':m['params']['body_mm'],'overall_target_mm':m['params']['target_overall_mm'],
      'thermal_or_physical_acceptance_completed':False,'geometric_checks_passed':geometry_passed,
      'manufacturing_release':False,'external_geometry_names':external,
      'known_blocker':'; '.join(f'{name}: {count}' for name,count in failures.items()) if failures else None,
      'remaining_physical_gates':['Photo-derived board/socket dimensions and revision require measured fit-up',
        'Factory cable exit, usable lengths, bend behavior, surplus packing and pin grouping require received-hardware verification',
        'Printed strength, creep, vibration, electrical insulation, thermal and noise tests remain incomplete']})
    if args.checks_only:
        (out/'checks-only.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'seconds':round(time.time()-t,1),'geometry_passed':geometry_passed,'issues':failures}),flush=True)
        if not geometry_passed:raise SystemExit(2)
        return report
    if not geometry_passed:
        # A previous successful export in the same directory must not remain
        # the apparent current result after a failed source rebuild.
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print('CAD checks failed; no assembly or fabrication export was attempted',flush=True)
        raise SystemExit(2)
    groups=(('parts',m['parts']),('envelopes',m['hardware']|m['refs']),('cables',m['heads']|m['wires']),('inspection',m['air']|m['reserves']|m['service']))
    a=cq.Assembly(name=m['params']['name']);physical=[]
    for folder,group in groups:
        (out/folder).mkdir(exist_ok=True);report[folder]={}
        for n,s in group.items():
            info={'valid':s.isValid(),'solids':len(s.Solids()),'bbox_mm':bbox(s),'volume_mm3':s.Volume()}
            cq.exporters.export(s,str(out/folder/(n+'.step')))
            info['step_sha256']=hashlib.sha256((out/folder/(n+'.step')).read_bytes()).hexdigest()
            if folder=='parts':
                info['mesh']=export_mesh(s,out/folder/(n+'.stl'))
                info['mesh']['sha256']=hashlib.sha256((out/folder/(n+'.stl')).read_bytes()).hexdigest()
            report[folder][n]=info
            if folder=='inspection':continue
            physical.append(s)
            color=(.78,.64,.39) if n.startswith('SKIN') else (.14,.45,.37) if n.startswith('GPU') or 'riser' in n.lower() else (.27,.42,.39) if n.startswith(('CPU','RAM','SSD','mini_itx','SATA_DS')) else (.53,.56,.61)
            if folder=='cables':color=(.18,.21,.27)
            a.add(s,name=n,color=cq.Color(*color))
    a.export(str(out/'assembly.step'))
    a.export(str(out/'assembly.glb'),tolerance=.4,angularTolerance=.28)
    report['original_fabrication_assets']=export_fabrication(m,out/'fabrication')
    # Meshing may inflate OCC's later bounding box by its tessellation gap.
    # Use the recorded pre-mesh BRep bounds for authoritative CAD dimensions.
    b=[v['bbox_mm'] for f in ('parts','envelopes','cables') for v in report[f].values()]
    mn=[min(v['min'][i] for v in b) for i in range(3)];mx=[max(v['max'][i] for v in b) for i in range(3)]
    report['measured_physical_bbox_mm']={'min':mn,'max':mx,'size':[mx[i]-mn[i] for i in range(3)]}
    report['measured_litres']=__import__('math').prod(mx[i]-mn[i] for i in range(3))/1e6
    for n,s in groups[-1][1].items():
        color=(1.,.1,.08,.75) if 'COLLISION' in n.upper() else (.1,.75,.8,.14) if n.startswith('AIR_') else (.9,.2,.5,.12)
        a.add(s,name=n,color=cq.Color(*color))
    a.export(str(out/'inspection.glb'),tolerance=.4,angularTolerance=.28)
    rb=cq.importers.importStep(str(out/'assembly.step')).solids().vals();expected=sum(len(s.Solids()) for s in physical)
    report['step_roundtrip']={'valid':all(s.isValid() for s in rb),'solids':len(rb),'expected':expected,'passed':len(rb)==expected and all(s.isValid() for s in rb)}
    report['all_prints_watertight']=all(v.get('mesh',{}).get('watertight') and v['solids']==1 for v in report['parts'].values())
    report['all_print_meshes_winding_consistent']=all(v.get('mesh',{}).get('winding_consistent') for v in report['parts'].values())
    export_failures=[]
    if not report['step_roundtrip']['passed']:export_failures.append('STEP roundtrip validity or solid count failed')
    if not report['all_prints_watertight']:export_failures.append('A printable mesh is open or its source is disconnected')
    if not report['all_print_meshes_winding_consistent']:export_failures.append('A printable mesh has inconsistent winding')
    report['checks']['export_integrity']=export_failures
    report['geometric_checks_passed']=not any(report['checks'].values())
    report['stage']='CAD_CHECKS_PASSED_PHYSICAL_VALIDATION_PENDING' if report['geometric_checks_passed'] else 'GEOMETRY_REVIEW_BLOCKED_NOT_MANUFACTURING_RELEASE'
    report['known_blocker']='; '.join(export_failures) or None
    for rel,sha in m['geometry_source_hashes'].items():
        if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=sha:
            raise ValueError('Source changed during export: '+rel)
    flange_key=m['psu_meta']['metal_flange']['key']
    flange_dxf=out/'fabrication'/(flange_key+'.dxf')
    if not flange_dxf.is_file():raise ValueError('The declared metal flange has no flat fabrication DXF')
    shutil.copyfile(flange_dxf,out/'PSU-flange-1mm-REVIEW.dxf')
    report['local_asset_sha256']={name:hashlib.sha256((out/name).read_bytes()).hexdigest()
      for name in ('assembly.step','assembly.glb','inspection.glb','PSU-flange-1mm-REVIEW.dxf')}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (out/'params-used.json').write_text(json.dumps(m['params'],ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'seconds':round(time.time()-t,1),'counts':{f:len(g) for f,g in groups},'roundtrip':report['step_roundtrip'],'bbox':report['measured_physical_bbox_mm'],'geometry_passed':report['geometric_checks_passed']},ensure_ascii=False),flush=True)
    if export_failures:raise SystemExit(2)
if __name__=='__main__':main()
