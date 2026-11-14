# SPDX-License-Identifier: MIT
"""Compact R6 integration. No production systems or earlier revision modified."""
from pathlib import Path
import hashlib,itertools,json,argparse,time
import cadquery as cq
from build import box,cylinder,merge,bbox
ROOT=Path(__file__).resolve().parents[1]

def build(include_power=True):
    from r6_frame import build_frame
    from r6_storage import build_storage
    from r6_mainboard import build_mainboard
    from r6_gpu import build_gpu
    p,h,refs,air,sv,res,fm=build_frame()
    dp,dh,heads,ds,dm=build_storage();p.update(dp);h.update(dh);sv.update(ds)
    mp,mh,hd,ms,mr,mm=build_mainboard();p.update(mp);h.update(mh);heads.update(hd);sv.update(ms);res.update(mr)
    gp,gh,gs,gr,gm=build_gpu();p.update(gp);h.update(gh);sv.update(gs);res.update(gr)
    m={'parts':p,'hardware':h,'refs':refs,'air':air,'service':sv,'reserves':res,'heads':heads,'wires':{},
      'frame_meta':fm,'drive_meta':dm,'mainboard_meta':mm,'gpu_meta':gm,
      'params':{'name':'kiwinest-r6','revision':'R6_COMPACT_5825U_CPU40_FLEX_THREE_BAY',
      'body_mm':[250,250,255],'target_overall_mm':[250,250,275],
      'printing_build_volume_mm':[256,256,256],'stage':'GEOMETRY_PROTOTYPE_NOT_MANUFACTURING_RELEASE',
      'source_qnas8_commit':'492cbcc55a5f0c1f36b2798a21b64ffed85c3c4a'},'geometry_source_hashes':{}}
    if (ROOT/'design/r6_psu.py').exists():
        from r6_psu import build_psu
        pp,ph,pa,pr,pm=build_psu();p.update(pp);h.update(ph);air.update(pa);res.update(pr);m['psu_meta']=pm
        integrate_psu(m)
    if (ROOT/'design/r6_riser.py').exists():
        from r6_riser import build_riser
        rp,rh,rw,rs,rr,rm=build_riser();p.update(rp);h.update(rh);m['wires'].update(rw);sv.update(rs);res.update(rr);m['riser_meta']=rm
        integrate_riser(m)
    from r6_controls import apply_controls
    apply_controls(m)
    # Hub backing touches the same fixed cage; re-open the PSU front joint
    # after the final union rather than filling its captured-nut cavity.
    cage='R6_STORAGE_COMMON_CAGE_open_floor_rear_skeleton'
    for x in (12.,101.):
        p[cage]=p[cage].cut(cylinder(1.7,5,(x,141.5,146.5))).cut(box((5.9,9.1,2),(x-2.95,137.5,148.7))).clean()
    if include_power and (ROOT/'design/r6_power.py').exists():
        from r6_power import apply_power
        apply_power(m);integrate_lacing(m)
        if (ROOT/'design/r6_atx_refine.py').exists():
            from r6_atx_refine import apply_atx_refine
            apply_atx_refine(m)
        if (ROOT/'design/r6_sata_refine.py').exists():
            from r6_sata_refine import apply_sata_refine
            apply_sata_refine(m)
        from r6_packing import apply_packing
        apply_packing(m)
    for f in ['build_r6.py','build.py','r6_frame.py','r6_storage.py','r6_mainboard.py','r6_gpu.py','r5_gpu.py','r6_psu.py','r6_riser.py','r6_controls.py','r6_power.py','r6_atx_refine.py','r6_sata_refine.py','r6_packing.py','r2_cables.py','r4_riser_route.py']:
        if (ROOT/'design'/f).exists():m['geometry_source_hashes']['design/'+f]=hashlib.sha256((ROOT/'design'/f).read_bytes()).hexdigest()
    for rel in ['references/original/gpu_body.step','references/original/GPU_R5_IO_ear_PLACEMENT_REFERENCE.step',
      'references/original/GPU_R6_CEM_correct1p57_notch1p90_REFERENCE.step',
      'references/private/R83SL_official_male_endpoint.step','references/private/R83SL_official_female_endpoint.step']:
        m['geometry_source_hashes'][rel]=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
    return m

def integrate_lacing(m):
    from r6_frame import pan
    p,h=m['parts'],m['hardware'];base=p['FRAME_R6_base']
    # Independent posts leave the front floor crossing open for theATX lead.
    # A continuous39mm-high rail would cut straight through that wire route.
    base=merge(base,box((8,8,40),(101,6,5)),box((8,8,40),(221,6,5)))
    for i,x in enumerate((105.,225.),1):
        base=base.cut(cylinder(1.7,10,(x,5,39),(0,1,0))).cut(cylinder(3.1,5,(x,5,39),(0,1,0)))
        h[f'R6_LACING_M3x10_pan_{i}']=pan(10,(x,10,39),(0,1,0))
        h[f'R6_LACING_M3_square_{i}']=box((5.5,2.4,5.5),(x-2.75,15.4,36.25)).cut(cylinder(1.6,2.6,(x,15.3,39),(0,1,0)))
    for n in m['power_meta']['lacing_interfaces']['parts']:
        x=p[n].BoundingBox().center.x
        p[n]=p[n].cut(box((9.1,2.6,5.9),(x-6.1,15.3,36.05))).clean()
    p['FRAME_R6_base']=base.clean()
    m['power_meta']['lacing_interfaces']['root_integration']='two independent8x8frontposts,toolcounterbores,M3x10pan and2.4square nuts;frontfloorcrossingopen'

def integrate_riser(m):
    from r6_frame import pan
    p,h=m['parts'],m['hardware'];base=p['FRAME_R6_base']
    saddle='R6_RISER_FEMALE_LOW_BRIDGE_FRAME_FEET'
    for i,y in enumerate((68.,212.),1):
        # Narrow the front/rear feet and move their bolt centres left2.5mm,
        # leaving a0.5mm gap to the separate motherboard tray feet atX172.
        p[saddle]=p[saddle].cut(box((18,8,5.1),(155,y-4,4.9)))
        foot=box((15.5,8,5),(156,y-4,5)).cut(cylinder(1.7,7,(167.5,y,4)))
        p[saddle]=merge(p[saddle],foot)
        for suffix in ('M3x10','M3_hex'):
            n=f'R6_RISER_FOOT_{suffix}_{i}';h[n]=h[n].translate((-2.5,0,0))
        base=merge(base,box((14,14,5),(163,y-7,0)))
        base=base.cut(cylinder(1.7,7,(167.5,y,-1))).cut(box((7,7,2.6),(164,y-3.5,1.1)))
    for axis in m['riser_meta']['female_mounts']['axes']:
        x,y=axis[:2]
        p[saddle]=p[saddle].cut(box((7,7,2.6),(x-3.5,y-3.5,46.3))).clean()
    p['FRAME_R6_base']=base.clean()
    support='R6_RISER_MALE_UPPER_REAR_FRAME_SUPPORT_BLOCKED'
    p[support]=p[support].cut(box((7.3,2.8,5.9),(237.05,230.9,212.05))).clean()
    post='FRAME_R6_corner_240_240'
    p[post]=p[post].cut(cylinder(1.7,16,(240,229,215),(0,1,0))).clean()
    h['R6_RISER_FRAME_REAR_M3x16_pan']=pan(16,(240,245,215),(0,-1,0))
    h['R6_RISER_FRAME_REAR_M3_square_2p4']=box((5.5,2.4,5.5),(237.25,231.1,212.25)).cut(cylinder(1.6,2.6,(240,231,215),(0,1,0)))
    m['riser_meta']['root_integration']={'female_base_lands':'14x14x5,through3.4 and7x7x2.6 nut pockets at167.5/68,167.5/212;feet narrowed toX171.5',
      'male_rear_joint':'M3x16pan seatY245,direction-Y,nutY231.1..233.5 in existing holder;post240/240 drilled3.4'}
    rm=m['riser_meta'];guard=m['reserves']['KEEP_DS2501_CPU_40mm_FROM_COMPONENT_FACE_HARD_LIMIT']
    conflict=h[rm['male_hardware']].intersect(guard)
    rm['module_rounded_CPU_center_intersection_mm3']=rm['actual_male_CPU_guard_intersection_mm3']
    rm['actual_male_CPU_guard_intersection_mm3']=conflict.Volume()
    rm['actual_male_CPU_guard_intersection_bbox']=bbox(conflict)
    m['reserves'][rm['conflict_reserve']]=conflict
    solids=h[rm['female_hardware']].Solids();assert len(solids)==252
    # Vendor end extraction order: PCB0,FFCclamp1,plastic2,164springcontacts
    #3..166,thenFFCsheet/fixings/FFCcontacts. Retain every rigid object while
    #allowing only spring contacts to mate with the nominal card-edge proxy.
    noncontact=cq.Compound.makeCompound([s for i,s in enumerate(solids) if not 3<=i<=166])
    nk='CHECK_R6_R83SL_FEMALE_NON_SPRING_MATERIAL'
    m['reserves'][nk]=noncontact;rm['non_spring_material_check_shape']=nk
    rm['spring_contact_indices_excluded_only_for_edge_mating']=[3,166]
    m['mainboard_meta']['PCIe']['required_fieldgate']='Confirm actual shortx8 key/socket/5.75mm insertion,roundcooler andR83SL ear/clamp clearance with40mm userreserve;no x16male assumed'

def integrate_psu(m):
    p,h=m['parts'],m['hardware'];changes=[]
    # These load lands belong to the fixed cage, never the removable carriers.
    n='R6_STORAGE_COMMON_CAGE_open_floor_rear_skeleton';cage=p[n]
    for x in (12.,101.):
        boss=box((8,11.85,3.7),(x-4,134.65,147.3))
        boss=boss.cut(cylinder(1.7,5,(x,141.5,146.5))).cut(box((5.9,9.1,2),(x-2.95,137.5,148.7)))
        cage=merge(cage,boss)
    p[n]=cage
    top=p['FRAME_R6_top']
    for x in (22.,93.):
        top=top.cut(cylinder(1.7,6,(x,242,246))).cut(cq.Solid.makeCone(3,1.5,1.5,cq.Vector(x,242,251),cq.Vector(0,0,-1)))
    # Cover screws on the left margin stop at247.4, below the lid. Relief in
    # the top ring leaves them accessible when the lid is removed.
    for n,s in h.items():
        if n.startswith('PSU_R6_') and '_COVER_M3x8_' in n:
            b=s.BoundingBox();top=top.cut(cylinder(3.25,3,(b.center.x,b.center.y,246.8)))
    p['FRAME_R6_top']=top.clean()
    # Printed sleeves wrap around the case skeleton with explicit 0.4mm
    # assembly gaps. Thin foam seals are required at these new interfaces.
    obstacles={n:s for n,s in p.items() if n.startswith('FRAME_R6_corner_10_')}
    obstacles.update({n:s for n,s in h.items() if n.startswith(('FRAME_R6_10_10','FRAME_R6_10_240','TOP_R6_lid_M3x12_CSK_1','TOP_R6_lid_M3x12_CSK_2','PANEL_R6_'))})
    for pn in [n for n in p if n.startswith('PSU_R6_')]:
        s=p[pn]
        for on,o in obstacles.items():
            b=o.BoundingBox();clear=box((b.xlen+.8,b.ylen+.8,b.zlen+.8),(b.xmin-.4,b.ymin-.4,b.zmin-.4))
            # AABB culling avoids dozens of unnecessary expensive BRep cuts.
            if overlap(s,clear)>1e-5:s=s.cut(clear);changes.append([pn,on])
        if pn=='PSU_R6_isolated_cold_sleeve_and_wire_gutter_BASE':
            # Clear the entire corner termination, including the unusable
            #0.6mm front-wall sliver left beyond the post clearance box.
            s=s.cut(box((3.6,10,50),(10.8,4.8,195.2)))
        p[pn]=s.clean()
    flange='PSU_R6_REPLACEABLE_1mm_METAL_FLANGE_NOT_PRINT'
    for on,o in h.copy().items():
        if on.startswith('PANEL_R6_'):
            b=o.BoundingBox();clear=box((b.xlen+.6,b.ylen+.6,b.zlen+.6),(b.xmin-.3,b.ymin-.3,b.zmin-.3))
            if overlap(h[flange],clear)>1e-5:h[flange]=h[flange].cut(clear).clean();changes.append([flange,on])
    p['SKIN_R6_back']=p['SKIN_R6_back'].cut(box((86,6,51),(14,246,198))).clean()
    m['psu_meta']['root_integration']={'modified_fixed_cage_bosses':'X8..16/97..105,Y134.65..146.5,Z147.3..151,load on fixed rear beams',
      'clearance_notches':changes,'corner_and_fastener_gap_mm':.4,'sealing':'add fitted thin closed-cell foam around corner/stand penetrations;airtightness not accepted'}

_bounds={}
def bounds(s):
    k=id(s)
    if k not in _bounds:_bounds[k]=(s,bbox(s))
    return _bounds[k][1]
def overlap(a,b):
    aa,bb=bounds(a),bounds(b)
    if any(aa['max'][i]<=bb['min'][i]+1e-6 or bb['max'][i]<=aa['min'][i]+1e-6 for i in range(3)):return 0.
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
    op=BRepAlgoAPI_Common(a.wrapped,b.wrapped);op.SetFuzzyValue(1e-5);op.Build()
    if not op.IsDone():raise ValueError('OCC common failed;not counted as clear')
    result=op.Shape()
    if result.IsNull():return 0.
    volume=cq.Shape.cast(result).Volume()
    if volume < -1e-5:raise ValueError('Negative OCC common volume;not counted as clear')
    return max(0.,volume)
def cross(a,b,same=False,allow=()):
    out=[];allow={frozenset(v) for v in allow}
    pairs=itertools.combinations(a.items(),2) if same else itertools.product(a.items(),b.items())
    for (an,x),(bn,y) in pairs:
        if an==bn or frozenset((an,bn)) in allow:continue
        v=overlap(x,y)
        if v>1e-4:out.append({'a':an,'b':bn,'volume_mm3':round(v,5)})
    return out

def check(m):
    p,h,hd,w,sv=m['parts'],m['hardware'],m['heads'],m['wires'],m['service'];allphys=p|h|hd|w
    rm=m.get('riser_meta',{});mates=m.get('controls_meta',{}).get('expected_mating_pairs',[])+rm.get('electrical_mating_pairs',[])+m.get('power_meta',{}).get('expected_mating_pairs',[])
    if rm:
        mates += [rm['GPU_CEM_reference']['root_mating_pair'],rm['motherboard_mating_pair']]
    c={'invalid_shapes':[n for n,s in allphys.items() if not s.isValid() or not s.Solids()],
       'disconnected_prints':[n for n,s in p.items() if len(s.Solids())!=1],
       'print_print':cross(p,p,True),'print_hardware':cross(p,h),
       'print_heads':cross(p,hd),'print_wires':cross(p,w),'hardware_hardware':cross(h,h,True,allow=mates),
       'hardware_heads':cross(h,hd,allow=mates),'hardware_wires':cross(h,w,allow=mates),'heads_heads':cross(hd,hd,True,allow=mates),'heads_wires':cross(hd,w,allow=mates),'wires_wires':cross(w,w,True,allow=mates)}
    # Permit only the measured local intersection inside a declared electrical
    #fork sphere. Any material outside that sphere remains a collision.
    for fork in m.get('power_meta',{}).get('exact_same_net_junction_spheres',[]):
        for q in list(c['wires_wires']):
            if {q['a'],q['b']}!={fork['a'],fork['b']}:continue
            common=w[q['a']].intersect(w[q['b']],tol=1e-5)
            sphere=cq.Solid.makeSphere(fork['radius_mm'],cq.Vector(*fork['center_mm']),angleDegrees1=-90,angleDegrees2=90)
            outside=common.cut(sphere).Volume()
            if outside<=1e-4:
                c['wires_wires'].remove(q)
                m['power_meta'].setdefault('validated_local_electrical_forks',[]).append({'pair':[q['a'],q['b']],'overlap_mm3':q['volume_mm3'],'outside_allowed_sphere_mm3':outside,'sphere':fork})
    c['stock_length_or_storage_volume']=m.get('power_meta',{}).get('checks',[])
    cpu=m['reserves']['KEEP_DS2501_CPU_40mm_FROM_COMPONENT_FACE_HARD_LIMIT']
    c['CPU40_hard_clearance']=cross({'CPU40':cpu},{n:s for n,s in allphys.items() if n!='CPU_DS2501_stock_round_copper_25mm_TOTAL_PHOTO_PROXY'})
    card=m['gpu_meta']['gpu_card_only']
    removed=set(m['frame_meta']['top_module_nodes'])|set(card['moving_hardware'])|{m['gpu_meta']['jaw']}|set(card['remove_hardware_before_service'])|{card['power_head'],card['free_wire']}
    # Fixed top-frame corner bolts remain if outside the extraction column.
    obs={n:s for n,s in allphys.items() if n not in removed}
    obs['PARKED_GPU8_head']=sv[card['parked_head_service']];obs['PARKED_GPU8_tail']=sv[card['parked_tail_service']]
    if rm:
        obs.pop(rm['female_hardware'],None)
        obs['FEMALE_NON_SPRING_MATERIAL']=m['reserves'][rm['non_spring_material_check_shape']]
    c['GPU_upward_removal']=cross({n:sv[n] for n in m['gpu_meta']['gpu_card_only']['stage_service_names']},obs)
    if rm:
        from r5_gpu import sweep_card_reference
        c['GPU_body_ear_vs_entire_socket']=cross({n:sweep_card_reference(h[n],312) for n in ('gpu_body','GPU_R6_IO_ear_PLACEMENT_REFERENCE')},{rm['female_hardware']:h[rm['female_hardware']]})
    c['protected_air']=[]
    for n in ('AIR_gpu_intake22','AIR_gpu_lower_supply'):
        c['protected_air']+=cross({n:m['air'][n]},allphys)
    # Independent frame column removal is a real disk1 service prerequisite.
    c['drive_forward_removal']=[]
    for i in ('1','2','3'):
        dm=m['drive_meta'];info=dm['service'][i]
        excluded=set(dm['moving_parts'][i]+dm['moving_hardware'][i]+dm['front_lock_hardware'][i])
        excluded|=set(info.get('connectors',[]))|{n for n in p if n.startswith(('SKIN_R6_front','SKIN_R6_left'))}
        excluded|={n for n in h if n.startswith(('PANEL_R6_front','PANEL_R6_left'))}
        if i=='1':excluded|={'FRAME_R6_corner_10_10','FRAME_R6_base_M3x12_CSK_10_10','TOP_R6_lid_M3x12_CSK_1'}|{n for n in h if n.startswith('FRAME_R6_10_10_')}
        c['drive_forward_removal']+=cross({info['front_draw']:sv[info['front_draw']]},{n:s for n,s in allphys.items() if n not in excluded})
    c['outside_target']=[{'name':n,'bbox':bounds(s)} for n,s in allphys.items() if any(bounds(s)['min'][i]<[0,0,-20][i]-1e-5 or bounds(s)['max'][i]>[250,250,255][i]+1e-5 for i in range(3))]
    return c

def main():
    t=time.time();m=build();c=check(m);out=ROOT/'analysis/r6-integration';out.mkdir(exist_ok=True)
    (out/'checks.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
    (out/'metadata.json').write_text(json.dumps({k:v for k,v in m.items() if k.endswith('_meta') or k in ('params','geometry_source_hashes')},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'seconds':round(time.time()-t,1),'counts':{g:len(m[g]) for g in ('parts','hardware','heads','wires','service')},'issues':{k:len(v) for k,v in c.items()}},ensure_ascii=False),flush=True)
    return m,c
if __name__=='__main__':main()
