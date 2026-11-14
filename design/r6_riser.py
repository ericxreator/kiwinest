# SPDX-License-Identifier: MIT
"""R7 R23SR: physical x4 male in the original x8 socket, x16 GPU receptacle.

The existing board/CPU coordinates and 40mm protection remain unchanged.
The deliberate electrical link is PCIe 3.0 x4; physical/thermal acceptance is
separate from the CAD checks. Manufacturer STEP inputs remain local-only.
"""
from __future__ import annotations
from pathlib import Path
import math
import cadquery as cq
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from build import box,cylinder,merge,bbox
from r4_riser_route import rounded_wire
from r6_mainboard import photo_yz

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'references/private'
FEMALE='R7_R23SR_OFFICIAL_x16_FEMALE_ASSEMBLED'
MALE='R7_R23SR_OFFICIAL_x4_MALE_ASSEMBLED'
MALE_SUPPORT='R7_RISER_MALE_UPPER_REAR_FRAME_SUPPORT'
MALE_T=(228.478,180.225,209.)
FEMALE_T=(136.95,173.147226721,53.9)
STOCK_MM=300.
SPRING_INDICES=list(range(2,166))


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


def _ribbon(path):
    first=path.Edges()[0];start=first.startPoint();normal=first.tangentAt(0)
    profile=cq.Workplane(cq.Plane(origin=start,xDir=(0,1,0),normal=normal)).rect(13.2,1.4)
    aux=cq.Workplane().newObject([path.translate((0,20,0))])
    return _one(profile.sweep(cq.Workplane().newObject([path]),auxSpine=aux,isFrenet=False).val(),'R23SR ribbon')


def distance(a,b):
    d=BRepExtrema_DistShapeShape(a.wrapped,b.wrapped);d.Perform()
    if not d.IsDone():raise ValueError('OCC distance computation failed')
    return d.Value()


def build_riser():
    parts={};hw={};wires={};service={};res={}
    female_raw=cq.importers.importStep(str(REF/'R23SR_official_female_endpoint.step')).val()
    male_raw=cq.importers.importStep(str(REF/'R23SR_official_male_endpoint.step')).val()
    if len(female_raw.Solids())!=215 or len(male_raw.Solids())!=47:
        raise ValueError('Unexpected R23SR endpoint selection; run the checksum-pinned reference preparation')
    hw[FEMALE]=transform(female_raw,FEMALE_T);hw[MALE]=transform(male_raw,MALE_T)
    cy,cz=photo_yz(380,618)
    cpu=cylinder(47.5,40,(188.3,cy,cz),(1,0,0))
    collision=hw[MALE].intersect(cpu,tol=1e-5)
    conflict_name='CONFLICT_R7_R23SR_MALE_CPU_HARD_GUARD_RED'
    if collision.Volume()>1e-4:res[conflict_name]=collision
    # Original numerical bridge, not a copied manufacturer surface. Its
    # native hole axes follow the real R23SR 108mm PCB mounting pattern.
    fx=27.467+FEMALE_T[0]
    fys=sorted([-(-27.399)+FEMALE_T[1],-80.601+FEMALE_T[1]])
    female_bits=[box((3,152,6.8),(160,64,42))]
    for y in (68.,212.):
        female_bits += [box((17,8,5),(156,y-4,5)),box((3,8,32),(160,y-4,10))]
    for y in fys:female_bits.append(box((7.65,6.6,3.6),(160,y-3.3,48.7)))
    saddle=merge(*female_bits)
    for j,y in enumerate(fys,1):
        saddle=saddle.cut(cylinder(1.7,12,(fx,y,44)))
        hw[f'R6_RISER_FEMALE_M3x8_{j}']=_pan_z(fx,y,53.9,8)
        hw[f'R6_RISER_FEMALE_M3_hex_{j}']=_nut3(fx,y,46.3)
    for j,y in enumerate((68.,212.),1):
        saddle=saddle.cut(cylinder(1.7,8,(170,y,4)))
        hw[f'R6_RISER_FOOT_M3x10_{j}']=_pan_z(170,y,10,10)
        hw[f'R6_RISER_FOOT_M3_hex_{j}']=_nut3(170,y,1.2)
    parts['R6_RISER_FEMALE_LOW_BRIDGE_FRAME_FEET']=_one(saddle,'female saddle')
    mx=-23.036+MALE_T[0]
    mys=sorted([-(-23.648)+MALE_T[1],-23.649+MALE_T[1]])
    male_bits=[box((4,106,3),(211,130,211)),box((33,6,3),(211,230,211)),
               box((8,6,8),(236,230,211))]
    for y in mys:male_bits.append(box((215-(mx-3.3),6.6,4),(mx-3.3,y-3.3,209)))
    holder=merge(*male_bits)
    for j,y in enumerate(mys,1):
        holder=holder.cut(cylinder(1.7,8,(mx,y,207)))
        hw[f'R6_RISER_MALE_M3x8_UP_{j}']=_pan_z(mx,y,207.4,8,True)
        hw[f'R6_RISER_MALE_M3_hex_{j}']=_nut3(mx,y,213)
    holder=holder.cut(cylinder(1.7,8,(240,229,215),(0,1,0)))
    parts[MALE_SUPPORT]=_one(holder,'male frame support')
    raw_centers=(6.651176575512,-6.648811217457)
    wire_meta={};wire_keys=[];mates=[]
    # Source two ribbons are13.2wide x1.4 thick with visible43mm demo span.
    # Their endpoints and every rigid factory part remain unscaled.
    for i,rawx in enumerate(raw_centers,1):
        yf=-rawx+FEMALE_T[1];ym=-rawx+MALE_T[1]
        first=(21.29875+FEMALE_T[0],yf,FEMALE_T[2]-2.299985033715)
        last=(-21.70125+MALE_T[0],ym,MALE_T[2]-2.299985033715)
        def vertices(u):return [first,(152,yf,first[2]),(152,yf,37.8),
            (178,ym,37.8),(178,ym,218),(u,ym,218),(u,ym,last[2]),last]
        lo=last[0]+10.001;hi=246.7
        minL=rounded_wire(vertices(lo),5).Length();maxL=rounded_wire(vertices(hi),5).Length()
        if not minL<=STOCK_MM<=maxL:
            raise ValueError(f'{STOCK_MM}mm stock cannot fit boundedR7 route:band{i},min{minL},max{maxL}')
        for _ in range(35):
            mid=(lo+hi)/2
            if rounded_wire(vertices(mid),5).Length()<STOCK_MM:lo=mid
            else:hi=mid
        u=(lo+hi)/2;vs=vertices(u);path=rounded_wire(vs,5)
        name=f'CABLE_R7_R23SR_band_{i}_300mm_13p2x1p4_PLANNING'
        wires[name]=_ribbon(path);wire_keys.append(name)
        mates.extend([[name,FEMALE],[name,MALE]])
        wire_meta[name]={'vertices_mm':vs,'centerline_mm':path.Length(),'wire_only_nominal_mm':STOCK_MM,
          'cross_section_mm':[13.2,1.4],'centerline_radius_mm':5,'auxiliary_spine_offset_mm':[0,20,0],
          'manufacturer_minimum_bend_radius_confirmed':False,'installation_qualified':False}
    service['SERVICE_R7_R23SR_MALE_WITHDRAW_PLUSX15_REFERENCE']=cq.Compound.makeCompound([
        box((q.BoundingBox().xlen+15,q.BoundingBox().ylen,q.BoundingBox().zlen),
            (q.BoundingBox().xmin,q.BoundingBox().ymin,q.BoundingBox().zmin)) for q in hw[MALE].Solids()])
    cpu_bolt_distances={n:distance(s,cpu) for n,s in hw.items() if n.startswith('R6_RISER_MALE_')}
    if min(cpu_bolt_distances.values())<2:raise ValueError('Male mounting hardware has less than2mm CPU40 clearance')
    meta={'model':'ADT-Link R23SR30cm','selected_model':'R23SR','electrical_lanes':4,'link_generation':3,
      'bandwidth_tradeoff':'DeliberatePCIe3x4 link in original physicalx8 motherboard slot;notx8performance',
      'release_status':'CAD_CANDIDATE_NOT_PHYSICALLY_OR_THERMALLY_ACCEPTED',
      'release_note_zh':'保留原主板和CPU40保护，转接线为PCIe3.0x4；实物和负载尚待验收',
      'actual_male_CPU_guard_intersection_mm3':collision.Volume(),
      'actual_male_CPU_guard_intersection_bbox':bbox(collision) if collision.Volume()>1e-4 else None,
      'actual_male_CPU40_minimum_clearance_mm':distance(hw[MALE],cpu),
      'male_mount_CPU40_minimum_clearances_mm':cpu_bolt_distances,
      'conflict_reserve':conflict_name,'male_support_part':MALE_SUPPORT,
      'female_source':str(REF/'R23SR_official_female_endpoint.step'),
      'male_source':str(REF/'R23SR_official_male_endpoint.step'),
      'female_raw_to_case':{'rotation_Z_deg':-90,'translation':list(FEMALE_T)},
      'male_raw_to_case':{'rotation_Z_deg':-90,'translation':list(MALE_T)},
      'female_solid_count':215,'male_solid_count':47,
      'female_spring_contact_indices':SPRING_INDICES,
      'female_source_contact_classification':'Endpoint0PCB,1polymerhousing,2..165the164separate springcontacts;all latch/clamp/fasteners/FFCcontacts remain rigid non-spring material',
      'female_hardware':FEMALE,'male_hardware':MALE,'wire_keys':wire_keys,'wire_paths':wire_meta,
      'electrical_mating_pairs':[],
      'wire_endpoint_interference_proof':{'tolerance_mm':1e-5,'female_solids':215,'male_solids':47,
        'wire_endpoint_pairs_checked':4,'common_volume_mm3':0.0,
        'scope':'All factory material retained;no whole-endpoint wire collision exemptions'},
      'GPU_CEM_reference':{'source':'references/original/GPU_R6_CEM_correct1p57_notch1p90_REFERENCE.step',
         'PCB_center_x_mm':166.55,'key_y_mm':176.45,'blade_z_mm':[59.25,65],
         'is_vendor_Zotac_CAD':False,'root_mating_pair':[FEMALE,'GPU_R6_CEM_keyed_edge_PLACEMENT_REFERENCE']},
      'motherboard_mating_pair':[MALE,'PCIE_DS2501_PHYSICAL_X8_OPEN_END_UNVERIFIED_PHOTO_PROXY'],
      'motherboard_mating_datum':{'insertion_axis':[-1,0,0],'blade_tip_x_mm':193.55,'insertion_depth_CEM_REFERENCE_mm':5.75,'key_y_mm':185.2,'PCB_center_z_mm':208.2,
        'photo_scaled_not_manufacturer_millimeter_CAD':True,'physical_x4_male_in_x8_socket':True},
      'female_mounts':{'hole_pitch_mm':108,'source_hole_diameters_mm':[3.6,3.5],
        'axes':[[fx,y,53.9,0,0,-1] for y in fys],'bolts':'M3x8','nuts':'M3DIN934hex2.4mm','nut_pocket_z_min_mm':46.2},
      'male_mounts':{'hole_pitch_mm':47.297,'source_hole_diameters_mm':[3.5,3.5],
        'axes':[[mx,y,207.4,0,0,1] for y in mys],'bolts':'M3x8','nuts':'M3DIN934hex2.4mm',
        'status':'CPU40_CLEARANCE_VERIFIED_NOT_LOAD_QUALIFIED'},
      'frame_mount_axes':[{'point':[170,y,10],'axis':[0,0,-1],'through_d_mm':3.4,'bolt':'M3x10',
        'root_nut_center_z_mm':2.4} for y in (68.,212.)]+[
        {'point':[240,230,215],'axis':[0,1,0],'through_d_mm':3.4,
         'status':'ROOT_CLOSES_FRAME_BOLT_AND_NUT'}],
      'prerequisites_for_male_service':['unthread2native_ear_M3','releaseframewireties','disengage+X15',
        'flexible_ribbons_must_reconfigure;serviceonlysweepsrigidmale'],
      'limits':['Board-specificsocketdatumremainsphoto-derived1-2mmuncertainty;physicalmeasurementsrequired',
        'R5bendradiusisengineeringcandidate,notmanufacturerminimumcertification',
        'VerifyboardPCIepowercapacityandGPUslotpowerdraw;nofactoryPWvariantorunknownpinoutassumed',
        'Physicalfit,PCIelinkstability,printedloadandthermal/noiseacceptanceincomplete']}
    return parts,hw,wires,service,res,meta
