# SPDX-License-Identifier: MIT
"""R8 genuine x8 riser, complete factory endpoints and an insulating clamp.

The original board/socket/CPU40 datum is preserved.  Gen3 x8 is the design
requirement; link negotiation and the modified clamp still need hardware tests.
Manufacturer geometry is a private input, never a public project asset.
"""
from __future__ import annotations
from pathlib import Path
import math
import cadquery as cq
from build import box,cylinder,merge,bbox
from r4_riser_route import rounded_wire
from r6_mainboard import photo_yz

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'references/private'
MODEL='K83UP_TL'
REFERENCE_FILES=('K83UP_TL_official_male_endpoint.step','K83UP_TL_official_female_endpoint.step')
FEMALE='R8_K83UP_TL_x16_FEMALE_FACTORY_LATCH_PARKED'
MALE='R8_K83UP_TL_OFFICIAL_x8_MALE_ASSEMBLED_MODIFIED_CLAMP'
MALE_SUPPORT='R8_RISER_MALE_UPPER_REAR_FRAME_SUPPORT'
FR4='R8_RISER_MALE_CUSTOM_FR4_LOWER_CLAMP_0p8'
PAD='R8_RISER_MALE_INSULATING_SILICONE_PAD_1p5_COMPRESSED_1p4'
MALE_T=(197.449,271.750000264971,209.)
FEMALE_T=(172.9722137,48.549996483118,53.668167800352236)
LATCH_PARK_OFFSET=(-13.,-16.,-19.)
NATIVE_M2_AXIAL_SETTING_MM=0.399997425079
STOCK_MM=500.
SLEEVE_ALLOWANCE_MM=36.
FREE_BUNDLE_MM=STOCK_MM-SLEEVE_ALLOWANCE_MM


def transform(s,t):
    return s.rotate((0,0,0),(0,0,1),-90).translate(t)


def _one(s,name):
    s=s.clean()
    if not s.isValid() or len(s.Solids())!=1:raise ValueError(name)
    return s.Solids()[0]


def _nut3(x,y,z):
    return cq.Workplane('XY').polygon(6,5.5/math.cos(math.pi/6)).extrude(2.4).val().translate((x,y,z)).cut(cylinder(1.6,2.6,(x,y,z-.1)))


def _pan_z(x,y,z,length,up=False):
    d=1 if up else -1
    return merge(cylinder(1.5,length,(x,y,z),(0,0,d)),cylinder(2.75,3,(x,y,z),(0,0,-d)))


def _overlap(a,b):
    aa=a.BoundingBox();bb=b.BoundingBox()
    return aa.xmin<bb.xmax and aa.xmax>bb.xmin and aa.ymin<bb.ymax and aa.ymax>bb.ymin and aa.zmin<bb.zmax and aa.zmax>bb.zmin


def _CPU_lower(q,cy,cz):
    b=q.BoundingBox()
    # Distance to the circle from the nearest point of its YZ rectangle is a
    # rigorous lower bound; it only skips components already farther away.
    yy=min(max(cy,b.ymin),b.ymax);zz=min(max(cz,b.zmin),b.zmax)
    radial=max(0.,math.hypot(yy-cy,zz-cz)-47.5)
    axial=max(188.3-b.xmax,b.xmin-228.3,0.)
    return math.hypot(radial,axial)


def _CPU_check(shapes,cpu,cy,cz):
    near=sorted((_CPU_lower(q,cy,cz),i,q) for i,q in enumerate(shapes))
    best=float('inf');commons=[]
    for lower,_,q in near:
        if lower<best:best=min(best,q.distance(cpu))
        if lower<1e-6:
            common=q.intersect(cpu)
            if common.Volume()>1e-6:commons.extend(common.Solids())
    return best,cq.Compound.makeCompound(commons)


def _male_clamp(male_raw):
    """Replace exactly the removable front M2 and original lower bar."""
    solids=male_raw.Solids()
    if len(solids)!=143:raise ValueError('Unexpected official male endpoint')
    removed={138,139,140}
    vv=sorted(solids[i].Volume() for i in removed)
    if any(abs(a-b)>1e-3 for a,b in zip(vv,(39.546364,39.546364,825.156663))):raise ValueError('Factory clamp/fastener source order changed')
    # Factory M2 heads face downward. Raise each retained original screw
    # only along its own axis until its real annular bearing face meets the
    # new FR4 underside205.2. Preserve every slightly offset source instance.
    retained_screw_indices={136,137,141,142}
    head_seats=[]
    for i in sorted(retained_screw_indices):
        faces=[f for f in solids[i].Faces() if f.geomType()=='PLANE'
            and f.normalAt().z>.999999 and abs(f.Area()-3*math.pi)<1e-4]
        if len(faces)!=1:raise ValueError('Factory M2 annular bearing face changed')
        head_seats.append(faces[0].Center().z+MALE_T[2])
    if abs(max(head_seats)+NATIVE_M2_AXIAL_SETTING_MM-205.2)>1e-6:raise ValueError('Factory M2 head setting changed')
    kept=[transform(q,MALE_T).translate((0,0,NATIVE_M2_AXIAL_SETTING_MM))
          if i in retained_screw_indices else transform(q,MALE_T)
          for i,q in enumerate(solids) if i not in removed]
    hw={MALE:cq.Compound.makeCompound(kept)}
    axes=[(210.257468609922,164.199766826221),(210.257468609922,203.374815654346)]
    bar=box((7.6,60.427,.8),(206.457,145.5,205.2))
    pad=box((7.6,60.427,1.4),(206.457,145.5,206.))
    for i,(x,y) in enumerate(axes,1):
        bar=bar.cut(cylinder(1.2,1,(x,y,205.1)))
        pad=pad.cut(cylinder(1.2,1.6,(x,y,205.9)))
    candidates=[q for q in kept if _overlap(q,pad)]
    pad=pad.cut(cq.Compound.makeCompound(candidates),tol=.01).clean()
    hw[FR4]=_one(bar,'FR4 lower clamp');hw[PAD]=_one(pad,'silicone clamp pad')
    return hw,_male_carrier(axes),axes


def _male_carrier(axes):
    # FR4 bears directly on the retained downward-facing factory heads.
    # Carrier lands support its underside205.2; circular reliefs clear the
    # actual4mm heads. No added nuts overlap the factory fasteners.
    bits=[box((4,80,4),(216,156,199.6)),box((4,6,14.4),(216,230,199.6)),
          box((28,6,3),(216,230,211)),box((8,6,8),(236,230,211))]
    for x,y in axes:bits.append(box((13,6.4,5.6),(207,y-3.2,199.6)))
    holder=merge(*bits)
    for x,y in axes:
        holder=holder.cut(cylinder(1.3,6.6,(x,y,199.1)))
        holder=holder.cut(cylinder(2.3,2,(x,y,203.4)))
    holder=holder.cut(cylinder(1.7,8,(240,229,215),(0,1,0)))
    return _one(holder,'male carrier')


def _female_bridge():
    fx=167.54999696;fys=(85.,201.);pcb_z=FEMALE_T[2]-1.5999968
    bits=[box((3,152,4.4),(160,64,42))]
    for y in (68.,212.):
        bits.extend([box((17,8,5),(156,y-4,5)),box((3,8,32),(160,y-4,10))])
    for y in fys:bits.append(box((12.3,6.6,pcb_z-46.4),(160,y-3.3,46.4)))
    # Captive parking well retains the complete detached factory latch.
    # Its open front permits -Y withdrawal after removing one M2 cross pin.
    bits.extend([box((20.5,18.8,2),(143.5,65.5,36.45)),
        box((2.75,18.8,12.7),(143.5,65.5,38.45)),
        box((3.15,18.8,12.7),(160.85,65.5,38.45)),
        box((14.6,1.63,10.9),(146.25,82.67,38.45)),
        box((20.5,3,1.8),(143.5,75.5,49.35))])
    saddle=merge(*bits).cut(box((14.6,42.67,10.9),(146.25,40.,38.45)))
    saddle=saddle.cut(cylinder(1.2,22,(142.5,68.2,46.5),(1,0,0)))
    # M2 AF4 nut is captured in the right wall, with a 1.35mm bearing web.
    pocket=cq.Workplane('YZ').polygon(6,4.3/math.cos(math.pi/6)).extrude(2).val().translate((162.2,68.2,46.5))
    saddle=saddle.cut(pocket)
    hw={'R8_RISER_LATCH_PARK_M2x25_PAN':merge(cylinder(1,25,(143.5,68.2,46.5),(1,0,0)),cylinder(2,1.6,(143.5,68.2,46.5),(-1,0,0))),
        'R8_RISER_LATCH_PARK_M2_HEX':cq.Workplane('YZ').polygon(6,4/math.cos(math.pi/6)).extrude(1.6).val().translate((162.2,68.2,46.5)).cut(cylinder(1.05,1.8,(162.1,68.2,46.5),(1,0,0)))}
    for i,y in enumerate(fys,1):
        saddle=saddle.cut(cylinder(1.7,14,(fx,y,44)))
        hw[f'R6_RISER_FEMALE_M3x8_{i}']=_pan_z(fx,y,FEMALE_T[2],8)
        hw[f'R6_RISER_FEMALE_M3_hex_{i}']=_nut3(fx,y,46.4)
    for i,y in enumerate((68.,212.),1):
        saddle=saddle.cut(cylinder(1.7,8,(170,y,4)))
        hw[f'R6_RISER_FOOT_M3x10_{i}']=_pan_z(170,y,10,10)
        hw[f'R6_RISER_FOOT_M3_hex_{i}']=_nut3(170,y,1.2)
    return _one(saddle,'female saddle'),hw,fx,fys


def _spring_domain(female,reference):
    """Only the actual 164 spring-tip intersections, never a CEM sweep."""
    source_solids=female.Solids();hits={}
    for i,q in enumerate(source_solids):
        if not _overlap(q,reference):continue
        hit=q.intersect(reference,tol=1e-6)
        if hit.Volume()>1e-7:hits[i]=hit
    caps=cq.Compound.makeCompound([q for hit in hits.values() for q in hit.Solids()])
    solids=caps.Solids()
    if len(solids)!=164:raise ValueError(f'Female key/contact mismatch: {len(solids)} local contacts')
    rows=[];banks=[[],[]]
    for q in solids:
        b=q.BoundingBox();x=(b.xmin+b.xmax)/2;y=(b.ymin+b.ymax)/2
        if not (.34<b.ylen<.37 and 6.8<b.zmin-FEMALE_T[2]<7.2 and 8.3<b.zmax-FEMALE_T[2]<8.7):raise ValueError('Unexpected contact-tip size')
        if b.ymax>175.5 and b.ymin<177.4:raise ValueError('Contact intersects GPU key')
        bank=0 if x<166.55 else 1;banks[bank].append(y)
        rows.append({'bank':bank,'volume_mm3':q.Volume(),'bbox_mm':bbox(q)})
    for ys in banks:
        ys.sort()
        if len(ys)!=82 or any(min(abs(b-a-1),abs(b-a-3))>1e-3 for a,b in zip(ys,ys[1:])):raise ValueError('Not two actual 82-position, 1mm-pitch spring rows')
    # Each tiny removed solid is itself the proven local domain. All PCB,
    # keys, endwalls, latches and the rest of the fused socket remain checked.
    # This is the STATIC installed card, never its withdrawal sweep.  The
    # preceding per-tip proof establishes its complete intersection is only
    # these caps. A simple static tool avoids a 164-tool Boolean over 10k
    # socket faces; the root independently audits removed material outside
    # the actual 164-cap domain and keeps every key/endwall in the check.
    if set(hits)!={4}:raise ValueError('Unexpected source part intersects the GPU CEM')
    checked=[q.cut(reference,tol=1e-6) if i in hits else q for i,q in enumerate(source_solids)]
    check=cq.Compound.makeCompound(checked)
    before=sum(q.Volume() for q in source_solids);after=sum(q.Volume() for q in checked)
    cap_volume=sum(q.Volume() for q in solids)
    if abs(before-after-cap_volume)>.01:raise ValueError('Non-contact female material changed')
    return caps,check,{'source_fused_socket_index':4,'only_modified_source_indices':[4],
        'unchanged_source_solid_count':218,'before_sum_solid_volume_mm3':before,
        'after_sum_solid_volume_mm3':after,'cap_sum_solid_volume_mm3':cap_volume,
        'volume_conservation_error_mm3':before-after-cap_volume,'contact_count':164,'row_counts':[82,82],'pitch_mm':1.,'normal_contact_common_mm3':caps.Volume(),'contacts':rows}


def _bundle():
    first=(170.75327763324424,110.346318897128,43.87137293917623)
    last=(195.23006373431763,228.094469162773,217.4664906488225)
    def vertices(u):return [first,(first[0],95,first[2]),(186,95,38),
        (233,178,38),(233,208,38),(233,208,125),(230.5,241.2,125),
        (230.5,241.2,190),(230.5,u,190),(213,u,190),
        (213,241.2,190),(213,241.2,last[2]),(last[0],241.2,last[2]),last]
    lo=190.;hi=225.199;minimum_parameter=hi;radius=8.
    minimum=rounded_wire(vertices(hi),radius).Length()
    maximum=rounded_wire(vertices(lo),radius).Length()
    if not minimum<=FREE_BUNDLE_MM<=maximum:raise ValueError('Full riser stock length does not fit routed envelope')
    for _ in range(40):
        mid=(lo+hi)/2
        if rounded_wire(vertices(mid),radius).Length()>FREE_BUNDLE_MM:lo=mid
        else:hi=mid
    v=vertices((lo+hi)/2);path=rounded_wire(v,radius)
    start=path.Edges()[0].startPoint();normal=path.Edges()[0].tangentAt(0)
    profile=cq.Workplane(cq.Plane(origin=start,normal=normal)).circle(4.7)
    envelope=_one(profile.sweep(cq.Workplane().newObject([path]),isFrenet=False).val(),'K83 single bundle')
    return envelope,{'vertices_mm':v,'centerline_mm':path.Length(),'wire_only_nominal_mm':STOCK_MM,
        'factory_sleeve_allowance_mm':SLEEVE_ALLOWANCE_MM,'free_bundle_nominal_mm':FREE_BUNDLE_MM,
        'minimum_routed_centerline_mm':minimum,
        'geometric_service_loop_allocation_mm':FREE_BUNDLE_MM-minimum,
        'compact_reference_vertices_mm':vertices(minimum_parameter),'tuning_parameter_bounds_mm':[190.,225.199],
        'length_definition_source_image':'https://img.alicdn.com/imgextra/i1/3004660323/O1CN01vQVioa1EFz0Y3fWij_!!3004660323.jpg',
        'bundle_count':1,'outer_envelope_diameter_mm':9.4,'centerline_radius_mm':radius,
        'source_core_cross_section_mm2':21.47795,'source_braid_cross_section_mm2':3.17106,
        'source_section_slice_thickness_mm':.01,'source_core_envelope_section_mm':[6.88238,4.10938],
        'model_kind':'CONSERVATIVE_OUTER_BUNDLE_ENVELOPE_RETAINS_FULL_LENGTH_AND_CROSS_SECTION',
        'length_definition':'500mm nominal cable: 464mm free bundle plus two retained 18mm factory sleeves; factory PCB/fanout is separately retained. Confirm supplier measurement and tolerance before purchase',
        'manufacturer_minimum_bend_radius_confirmed':False,'installation_qualified':False}


def build_riser():
    parts={};hw={};wires={};service={};res={}
    male_raw=cq.importers.importStep(str(REF/f'{MODEL}_official_male_endpoint.step')).val()
    female_raw=cq.importers.importStep(str(REF/f'{MODEL}_official_female_endpoint.step')).val()
    if len(female_raw.Solids())!=219:raise ValueError('Unexpected official female endpoint')
    mh,support,axes=_male_clamp(male_raw);hw.update(mh);parts[MALE_SUPPORT]=support
    female_solids=[transform(q,FEMALE_T) for q in female_raw.Solids()]
    if abs(female_raw.Solids()[2].Volume()-356.232414535509)>1e-3:raise ValueError('Factory detachable latch source order changed')
    female_solids[2]=female_solids[2].translate(LATCH_PARK_OFFSET)
    hw[FEMALE]=cq.Compound.makeCompound(female_solids)
    saddle,fh,fx,fys=_female_bridge();hw.update(fh);parts['R6_RISER_FEMALE_LOW_BRIDGE_FRAME_FEET']=saddle
    reference=cq.importers.importStep(str(ROOT/'references/original/GPU_R6_CEM_correct1p57_notch1p90_REFERENCE.step')).val()
    caps,noncontact,contact_meta=_spring_domain(hw[FEMALE],reference)
    cap_key='CHECK_R8_FEMALE_164_LOCAL_SPRING_TIP_CONTACT_DOMAINS'
    check_key='CHECK_R8_FEMALE_ENTIRE_ENDPOINT_EXCEPT_LOCAL_SPRING_TIPS'
    res[cap_key]=caps;res[check_key]=noncontact
    pad_domain='CHECK_R8_SILICONE_PAD_LOCAL_ELASTIC_CONTACT_DOMAIN'
    res[pad_domain]=box((7.6,60.427,1.4),(206.457,145.5,206.))
    # The PCB starts at207.4000032, above this domain. Both M2 bores have
    # 0.2mm radial clearance; only the soft grooved fanout pad can preload.
    latch=female_solids[2]
    female_without_latch='CHECK_R8_FEMALE_OTHER_218_FACTORY_SOLIDS_FOR_LATCH_SERVICE'
    res[female_without_latch]=cq.Compound.makeCompound([q for i,q in enumerate(female_solids) if i!=2])
    service['SERVICE_R8_DETACHED_FACTORY_LATCH_WITHDRAW_MINUSY25']=cq.Compound.makeCompound([
        box((q.BoundingBox().xlen,q.BoundingBox().ylen+25,q.BoundingBox().zlen),
            (q.BoundingBox().xmin,q.BoundingBox().ymin-25,q.BoundingBox().zmin)) for q in latch.Solids()])
    pin=hw['R8_RISER_LATCH_PARK_M2x25_PAN'];pb=pin.BoundingBox()
    service['SERVICE_R8_LATCH_PARK_PIN_WITHDRAW_MINUSX25']=merge(cylinder(1,50,(118.5,68.2,46.5),(1,0,0)),cylinder(2,26.6,(116.9,68.2,46.5),(1,0,0)))
    wire_key='CABLE_R8_K83_x8_SINGLE_BUNDLE_500mm_D9p4_PLANNING'
    wires[wire_key],wire_meta=_bundle()
    # The actual tiny braid termination source39 protrudes0.375mm beyond
    # its sleeve. Keep that factory material in MALE and remove only the
    # duplicate envelope material it already occupies. The complete union
    # (factory braid + outer free-bundle envelope) is unchanged.
    braid_end=transform(male_raw.Solids()[2],MALE_T)
    if abs(braid_end.Volume()-.045291097554)>1e-6:raise ValueError('Braid termination source order changed')
    shared_braid=wires[wire_key].intersect(braid_end,tol=1e-6)
    wires[wire_key]=_one(wires[wire_key].cut(braid_end,tol=1e-6),'free bundle with retained native braid transition')
    wire_meta['native_braid_transition']={'original_source_index':39,'retained_endpoint_index':2,
        'volume_represented_by_factory_part_instead_of_duplicate_envelope_mm3':shared_braid.Volume(),
        'factory_material_preserved_in_male':True,'complete_union_envelope_unchanged':True}
    cy,cz=photo_yz(380,618);cpu=cylinder(47.5,40,(188.3,cy,cz),(1,0,0))
    male_min,collision=_CPU_check(hw[MALE].Solids(),cpu,cy,cz)
    cpu_keys=[MALE,FR4,PAD,*[n for n in hw if n.startswith('R8_RISER_MALE_M2_hex_')],MALE_SUPPORT]
    distances={n:(_CPU_check(hw[n].Solids(),cpu,cy,cz)[0] if n==MALE else (hw.get(n) or parts[n]).distance(cpu)) for n in cpu_keys}
    if min(distances.values())<2:raise ValueError('Male clamp/carrier has less than 2mm CPU40 clearance')
    conflict_name='CONFLICT_R8_x8_MALE_CPU_HARD_GUARD_RED'
    if collision.Volume()>1e-4:res[conflict_name]=collision
    service['SERVICE_R8_x8_MALE_WITHDRAW_PLUSX15_REFERENCE']=cq.Compound.makeCompound([
        box((q.BoundingBox().xlen+15,q.BoundingBox().ylen,q.BoundingBox().zlen),
            (q.BoundingBox().xmin,q.BoundingBox().ymin,q.BoundingBox().zmin)) for q in hw[MALE].Solids()])
    meta={'model':'ADT-Link K83UP-TL 50cm custom, custom insulating lower clamp','selected_model':'K83UP-TL',
      'electrical_lanes':8,'link_generation':3,'electrical_requirement':'Gen3 x8 target/minimum design; actual negotiated speed and lane count unverified',
      'release_status':'CAD_CANDIDATE_NOT_PHYSICALLY_OR_THERMALLY_ACCEPTED',
      'release_note_zh':'原始x8 PCB及全部触点保留，原厂锁扣拆下停放；目标Gen3 x8，真实协商/拆扣/绝缘压条待实物验收',
      'actual_male_CPU_guard_intersection_mm3':collision.Volume(),
      'actual_male_CPU_guard_intersection_bbox':bbox(collision) if collision.Volume()>1e-4 else None,
      'actual_male_CPU40_minimum_clearance_mm':male_min,'male_mount_CPU40_minimum_clearances_mm':distances,
      'CPU_clearance_component_keys':cpu_keys,'conflict_reserve':conflict_name,'male_support_part':MALE_SUPPORT,
      'female_source':str(REF/f'{MODEL}_official_female_endpoint.step'),'male_source':str(REF/f'{MODEL}_official_male_endpoint.step'),
      'female_raw_to_case':{'rotation_Z_deg':-90,'translation':list(FEMALE_T)},
      'male_raw_to_case':{'rotation_Z_deg':-90,'translation':list(MALE_T)},
      'female_solid_count':219,'male_solid_count':len(hw[MALE].Solids()),
      'female_spring_contact_indices':[],'female_source_contact_classification':'Single fused socket: classify only 164 actual spring-tip intersections; full housing/key/endwalls/PCB remain checked',
      'spring_contact_domain_key':cap_key,
      'mechanical_local_contacts':[{'a':PAD,'b':MALE,'domain_key':pad_domain,'maximum_overlap_mm3':.5,
          'contact_kind':'bounded soft insulating pad preload; rigid PCB is above domain and fastener bores are clear',
          'physical_preload_verified':False}],
      'female_latch_pose':{'original_source_index':2,'complete_factory_part_retained':True,
          'mode':'DETACHED_AND_CAPTIVELY_PARKED_IN_INTEGRAL_BRIDGE_WELL',
          'pin_hardware_key':'R8_RISER_LATCH_PARK_M2x25_PAN',
          'pin_service_sweep_key':'SERVICE_R8_LATCH_PARK_PIN_WITHDRAW_MINUSX25',
          'latch_service_sweep_key':'SERVICE_R8_DETACHED_FACTORY_LATCH_WITHDRAW_MINUSY25',
          'retained_female_without_latch_check_key':female_without_latch,
          'service_prerequisites':'Open left/front access panel; tool-access clearance remains physically unverified',
          'case_translation_from_stock_mm':list(LATCH_PARK_OFFSET),'is_actual_detachability_verified':False,
          'actual_hardware_modified':False,'retention':'M2x25 cross pin and captive AF4x1.6 nut, integral well/floor/roof',
          'GPU_retention':'existing GPU IO ears/guide rails/top clamp; factory connector latch is parked',
          'service':['remove M2 cross pin toward -X25','withdraw complete parked latch -Y25'],
          'requires_physical_validation':'Confirm reversible snap-latch detachment, parking fit and retention before build'},'non_spring_material_check_shape':check_key,'spring_contact_proof':contact_meta,
      'female_hardware':FEMALE,'male_hardware':MALE,'wire_keys':[wire_key],'wire_paths':{wire_key:wire_meta},
      'electrical_mating_pairs':[],
      'GPU_CEM_reference':{'source':'references/original/GPU_R6_CEM_correct1p57_notch1p90_REFERENCE.step',
        'PCB_center_x_mm':166.55,'key_y_mm':176.45,'blade_z_mm':[59.25,65],'is_vendor_Zotac_CAD':False,
        'nominal_socket_metal_shoulder_z_mm':65.,'nominal_socket_polymer_mouth_z_mm':64.75,
        'nominal_card_insertion_below_polymer_mouth_mm':5.5,'GPU_placement_reference_unchanged':True,
        'root_mating_pair':[FEMALE,'GPU_R6_CEM_keyed_edge_PLACEMENT_REFERENCE']},
      'motherboard_mating_pair':[MALE,'PCIE_DS2501_PHYSICAL_X8_OPEN_END_UNVERIFIED_PHOTO_PROXY'],
      'motherboard_mating_datum':{'insertion_axis':[-1,0,0],'blade_tip_x_mm':193.55,'insertion_depth_CEM_REFERENCE_mm':5.75,
        'key_y_mm':185.2,'PCB_center_z_mm':208.2,'photo_scaled_not_manufacturer_millimeter_CAD':True,'physical_x8_male_in_x8_socket':True},
      'female_mounts':{'selected_slot_mount_pitch_mm':116,'source_slot_width_mm':3.5,
        'axes':[[fx,y,FEMALE_T[2],0,0,-1] for y in fys],'bolts':'M3x8','nuts':'M3DIN934hex2.4mm','nut_pocket_z_min_mm':46.2},
      'male_mounts':{'axes':[[x,y,205.2,0,0,1] for x,y in axes],'bolts':'Retained original M2x8 middle/rear screws, factory heads downward',
        'added_nuts':False,'original_fastener_source_indices':[993,996,1006,1009],
        'axial_setting_plusZ_mm':NATIVE_M2_AXIAL_SETTING_MM,
        'actual_head_bearing_z_mm':205.2,'head_diameter_mm':4.,
        'carrier_head_relief_diameter_mm':4.6,'carrier_head_relief_floor_z_mm':203.4,
        'driver_relief_diameter_mm':2.6,'in_place_tool_access_verified':False,
        'factory_shank_length_mm':8.,'shank_overlap_with_original_upper_clamp_mm':2.8,
        'tip_above_upper_clamp_mm':.399997655884,
        'CAD_upper_clamp_bore_diameter_mm':2.2,
        'actual_thread_retention_and_engagement_verified':False,
        'retention_note':'Retain the factory upper-clamp fastening method; CAD omits threads and shows2.2mm clearance bores. Confirm actual retention and0.4mm added insertion on received hardware',
        'status':'CPU40_CLEARANCE_VERIFIED_NOT_LOAD_QUALIFIED'},
      'modified_factory_parts':{'female_latch_detached_and_fully_parked_source_index':2,'removed_exact_endpoint_indices':[138,139,140],'removed_original_source_indices':[999,1002,1003],
        'removed_parts':['removable lower aluminum clamp','front removable M2 fastener (both slightly offset CAD representations)'],
        'retained':'Full x8 PCB/gold fingers, all factory fanout/coax/sleeves/core stub/braid end, upper clamp and all slightly offset representations of middle/rear M2 fasteners',
        'replacement_parts':[FR4,PAD,MALE_SUPPORT],'retained_middle_rear_fastener_axial_setting_mm':NATIVE_M2_AXIAL_SETTING_MM,
        'pad_stock_mm':1.5,'pad_installed_nominal_mm':1.4,'pad_preload_and_pullout_qualified':False},
      'original_fabrication_parts':[{'hardware_key':FR4,'material':'FR4 insulating laminate','thickness_mm':.8,'flat_axis':'Z'},
        {'hardware_key':PAD,'material':'electrically insulating silicone foam','stock_thickness_mm':1.5,'installed_thickness_mm':1.4,'flat_axis':'Z',
        'manufacturing_note':'Cut the1.5mm foam blank outline and bores; STEP shows nominal installed compression/conformation, not a milled groove specification. Supplier compression curve and preload unverified'}],
      'frame_mount_axes':[{'point':[170,y,10],'axis':[0,0,-1],'through_d_mm':3.4,'bolt':'M3x10','root_nut_center_z_mm':2.4} for y in (68.,212.)]+[
        {'point':[240,230,215],'axis':[0,1,0],'through_d_mm':3.4,'status':'ROOT_CLOSES_FRAME_BOLT_AND_NUT'}],
      'prerequisites_for_male_service':['Assemble the complete factory clamp and carrier on the bench before motherboard insertion',
        'For service release the rear frame joint and cable restraints first',
        'Withdraw the complete rigid male/carrier assembly from the socket before moving it outside the case',
        'Operate downward-facing factory M2 heads only after removal; no in-place driver access is claimed',
        'Flexible bundle must reconfigure; complete extraction, tools and actual clamp retention need physical validation'],
      'source_product_url':'https://adtlink.cn/cn/product/K83UX-FG.html',
      'limits':['Board-specific socket datum remains photo-derived with 1–2mm uncertainty; physical measurements required',
        'R8 bend radius is an engineering candidate, not a manufacturer minimum certification',
        'Custom FR4/silicone clamp requires preload, pullout, insulation, continuity and PCIe signal tests',
        'Verify board PCIe power capacity and GPU slot power draw; no unknown auxiliary power pinout assumed',
        'Physical fit, negotiated Gen3 x8, stability, printed load and thermal/noise acceptance incomplete']}
    return parts,hw,wires,service,res,meta
