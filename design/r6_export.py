# SPDX-License-Identifier: MIT
"""Traceable review export. Failed checks remain failed in every artifact."""
from pathlib import Path
import argparse,hashlib,json,time
import cadquery as cq
from build import bbox,export_mesh
from build_r6 import build,check
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir',type=Path,default=ROOT/'out-r8')
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
        return report
    groups=(('parts',m['parts']),('envelopes',m['hardware']|m['refs']),('cables',m['heads']|m['wires']),('inspection',m['air']|m['reserves']|m['service']))
    a=cq.Assembly(name=m['params']['name']);physical=[]
    for folder,group in groups:
        (out/folder).mkdir(exist_ok=True);report[folder]={}
        for n,s in group.items():
            info={'valid':s.isValid(),'solids':len(s.Solids()),'bbox_mm':bbox(s),'volume_mm3':s.Volume()}
            cq.exporters.export(s,str(out/folder/(n+'.step')))
            if folder=='parts':info['mesh']=export_mesh(s,out/folder/(n+'.stl'))
            report[folder][n]=info
            if folder=='inspection':continue
            physical.append(s)
            color=(.78,.64,.39) if n.startswith('SKIN') else (.14,.45,.37) if n.startswith('GPU') or 'riser' in n.lower() else (.27,.42,.39) if n.startswith(('CPU','RAM','SSD','mini_itx','SATA_DS')) else (.53,.56,.61)
            if folder=='cables':color=(.18,.21,.27)
            a.add(s,name=n,color=cq.Color(*color))
    a.export(str(out/'assembly.step'))
    a.export(str(out/'assembly.glb'),tolerance=.4,angularTolerance=.28)
    # Original machined/laminated parts are fabrication assets, not prints.
    # Keep the allowlist explicit so vendor endpoint geometry cannot enter it.
    fabrication=out/'fabrication';fabrication.mkdir(exist_ok=True)
    report['original_fabrication_assets']=[]
    own_fabrication={'R8_RISER_MALE_CUSTOM_FR4_LOWER_CLAMP_0p8',
      'R8_RISER_MALE_INSULATING_SILICONE_PAD_1p5_COMPRESSED_1p4',
      'MAINBOARD_MOUNT_R8_lower_2_FLUSH_OD9_STEEL_CSK_WASHER',
      'MAINBOARD_MOUNT_R8_lower_4_FLUSH_OD9_STEEL_CSK_WASHER'}
    for item in riser.get('original_fabrication_parts',[])+m['mainboard_meta'].get('original_fabrication_parts',[]):
        name=item['hardware_key'];assert name in own_fabrication
        shape=m['hardware'][name];filename=name+'.step'
        cq.exporters.export(shape,str(fabrication/filename))
        files=[filename]
        if item.get('thickness_mm')==.8 and item.get('flat_axis')=='Z':
            dxf=name+'.dxf'
            cq.exporters.export(cq.Workplane('XY').newObject([shape]).faces('>Z').wires(),str(fabrication/dxf))
            files.append(dxf)
        report['original_fabrication_assets'].append(dict(item,files={
          f:hashlib.sha256((fabrication/f).read_bytes()).hexdigest() for f in files},
          manufacturing_release=False))
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
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (out/'params-used.json').write_text(json.dumps(m['params'],ensure_ascii=False,indent=2)+'\n')
    flange=m['hardware'].get('PSU_R6_REPLACEABLE_1mm_METAL_FLANGE_NOT_PRINT')
    if flange:
        flat=flange.rotate((0,0,0),(1,0,0),90)
        cq.exporters.export(cq.Workplane('XY').newObject([flat]).faces('>Z').wires(),str(out/'PSU-flange-1mm-REVIEW.dxf'))
    print(json.dumps({'seconds':round(time.time()-t,1),'counts':{f:len(g) for f,g in groups},'roundtrip':report['step_roundtrip'],'bbox':report['measured_physical_bbox_mm'],'geometry_passed':geometry_passed},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
