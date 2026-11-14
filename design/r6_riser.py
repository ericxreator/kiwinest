# SPDX-License-Identifier: MIT
"""R6 R83SL actual ends and four400mm planning ribbons.

BLOCKED: the actual short male end intersects the required CPU guard. This
module is an interference prototype, not a manufacturing/purchase release.
"""
from __future__ import annotations
from pathlib import Path
import math
import cadquery as cq
from build import box,cylinder,merge,bbox
from r4_riser_route import rounded_wire

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'references/private'
FEMALE='R6_R83SL_OFFICIAL_x16_FEMALE_ASSEMBLED'
MALE='R6_R83SL_OFFICIAL_x8_MALE_ASSEMBLED'
MALE_T=(193.55-209.61599731445,185.2-138.62550354003,207.4)
FEMALE_T=(166.55-274.24844233,176.45-141.76887537,52.400001124270634)


def transform(s,t):
    return s.rotate((0,0,0),(1,1,0),180).translate(t)


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
    # Auxiliary translated spine fixes the width toward projected globalY,
    # preventing accumulated Frenet twist at the3D low-window offset.
    profile=cq.Workplane(cq.Plane(origin=start,xDir=(0,1,0),normal=normal)).rect(13.2,1.4)
    aux=cq.Workplane().newObject([path.translate((0,20,0))])
    return _one(profile.sweep(cq.Workplane().newObject([path]),auxSpine=aux,isFrenet=False).val(),'R83SL ribbon')


def build_riser():
    parts={};hw={};wires={};service={};res={}
    female_raw=cq.importers.importStep(str(REF/'R83SL_official_female_endpoint.step')).val()
    male_raw=cq.importers.importStep(str(REF/'R83SL_official_male_endpoint.step')).val()
    hw[FEMALE]=transform(female_raw,FEMALE_T);hw[MALE]=transform(male_raw,MALE_T)
    cpu=cylinder(47.5,40,(188.3,122.7,160.9),(1,0,0))
    collision=hw[MALE].intersect(cpu)
    res['CONFLICT_R6_R83SL_MALE_CPU_HARD_GUARD_RED']=collision
    # Actual108mm femalePCB holes. A low bridge straddles the bottom fan;
    # two mounting axes coincide with existing frame struts, not fan blades.
    fx=272.047444+FEMALE_T[0]
    fys=[57.849265+FEMALE_T[1],165.849264+FEMALE_T[1]]
    female_bits=[box((3,152,6.8),(160,64,42))]
    for y in (68.,212.):
        female_bits += [box((17,8,5),(156,y-4,5)),box((3,8,32),(160,y-4,10))]
    for y in fys:female_bits.append(box((7.65,6.6,3.6),(160,y-3.3,48.8)))
    saddle=merge(*female_bits)
    for j,y in enumerate(fys,1):
        saddle=saddle.cut(cylinder(1.7,12,(fx,y,44)))
        hw[f'R6_RISER_FEMALE_M3x8_{j}']=_pan_z(fx,y,54.00000046,8)
        hw[f'R6_RISER_FEMALE_M3_hex_{j}']=_nut3(fx,y,46.4)
    for j,y in enumerate((68.,212.),1):
        saddle=saddle.cut(cylinder(1.7,8,(170,y,4)))
        hw[f'R6_RISER_FOOT_M3x10_{j}']=_pan_z(170,y,10,10)
        hw[f'R6_RISER_FOOT_M3_hex_{j}']=_nut3(170,y,1.2)
    parts['R6_RISER_FEMALE_LOW_BRIDGE_FRAME_FEET']=_one(saddle,'female saddle')
    # Male upper support bears the two actual75.45mm ear holes. Its front
    # screw/CPU clearance remains blocked along with the actual male itself.
    mx=221.544421+MALE_T[0]
    mys=[87.425489+MALE_T[1],162.875491+MALE_T[1]]
    male_bits=[box((4,106,3),(211,130,211)),box((33,6,3),(211,230,211)),
               box((8,6,8),(236,230,211))]
    for y in mys:male_bits.append(box((14.4,6.6,4),(mx-3.3,y-3.3,209)))
    holder=merge(*male_bits)
    for j,y in enumerate(mys,1):
        holder=holder.cut(cylinder(1.7,8,(mx,y,207)))
        hw[f'R6_RISER_MALE_M3x8_UP_{j}']=_pan_z(mx,y,207.4,8,True)
        hw[f'R6_RISER_MALE_M3_hex_{j}']=_nut3(mx,y,213)
    holder=holder.cut(cylinder(1.7,8,(240,229,215),(0,1,0)))
    parts['R6_RISER_MALE_UPPER_REAR_FRAME_SUPPORT_BLOCKED']=_one(holder,'male frame support')
    # Source cable planes:4bands13.2wide at13.3pitch. Nominal400mm excludes
    # both rigidends. Solve a right-side hairpin to represent all stock length.
    raw_centers=(105.200601,118.500596,131.800599,145.100602)
    wire_meta={};wire_keys=[];mates=[]
    for i,rawx in enumerate(raw_centers,1):
        yf=rawx+FEMALE_T[1];ym=rawx+MALE_T[1]
        first=(265.879395778+FEMALE_T[0],yf,FEMALE_T[2]-.7)
        last=(222.879394523+MALE_T[0],ym,MALE_T[2]-.7)
        def vertices(u):return [first,(106,yf,first[2]),(106,yf,37.2),
            (178,ym,37.2),(178,ym,218),(u,ym,218),(u,ym,last[2]),last]
        lo=last[0]+10.001;hi=246.7
        minL=rounded_wire(vertices(lo),5).Length();maxL=rounded_wire(vertices(hi),5).Length()
        if not minL<=400<=maxL:
            raise ValueError(f'400mm stock cannot fit boundedR6 route:band{i},min{minL},max{maxL}')
        for _ in range(35):
            mid=(lo+hi)/2
            if rounded_wire(vertices(mid),5).Length()<400:lo=mid
            else:hi=mid
        u=(lo+hi)/2;vs=vertices(u);path=rounded_wire(vs,5)
        name=f'CABLE_R6_R83SL_band_{i}_400mm_13p2x1p4_PLANNING'
        wires[name]=_ribbon(path);wire_keys.append(name)
        mates.extend([[name,FEMALE],[name,MALE]])
        wire_meta[name]={'vertices_mm':vs,'centerline_mm':path.Length(),'wire_only_nominal_mm':400,
          'cross_section_mm':[13.2,1.4],'centerline_radius_mm':5,'auxiliary_spine_offset_mm':[0,20,0],
          'manufacturer_minimum_bend_radius_confirmed':False,'installation_qualified':False}
    service['SERVICE_R6_R83SL_MALE_WITHDRAW_PLUSX15_REFERENCE']=cq.Compound.makeCompound([
        box((q.BoundingBox().xlen+15,q.BoundingBox().ylen,q.BoundingBox().zlen),
            (q.BoundingBox().xmin,q.BoundingBox().ymin,q.BoundingBox().zmin)) for q in hw[MALE].Solids()])
    meta={'model':'ADT-Link R83SL40cm','release_status':'BLOCKED_DO_NOT_MANUFACTURE_OR_PURCHASE_RISER',
      'release_note_zh':'不可制造放行；转接线暂不采购',
      'actual_male_CPU_guard_intersection_mm3':collision.Volume(),
      'actual_male_CPU_guard_intersection_bbox':bbox(collision),
      'conflict_reserve':'CONFLICT_R6_R83SL_MALE_CPU_HARD_GUARD_RED',
      'measurement_only_slot_minimum_upshift_mm':1.17445,
      'measurement_only_note':'Not an authorized coordinate change;touching is not installable clearance;add real tolerance margin after measurement',
      'female_source':str(REF/'R83SL_official_female_endpoint.step'),
      'male_source':str(REF/'R83SL_official_male_endpoint.step'),
      'female_raw_to_case':{'rotation_180_axis':[1,1,0],'translation':list(FEMALE_T)},
      'male_raw_to_case':{'rotation_180_axis':[1,1,0],'translation':list(MALE_T)},
      'female_hardware':FEMALE,'male_hardware':MALE,'wire_keys':wire_keys,'wire_paths':wire_meta,
      'electrical_mating_pairs':mates,
      'GPU_CEM_reference':{'source':'references/original/GPU_R5_CEM_keyed_edge_PLACEMENT_REFERENCE.step','translation':[20,-32.5,0],
         'PCB_center_x_mm':166.55,'key_y_mm':176.45,'blade_z_mm':[59.25,65],
         'is_vendor_Zotac_CAD':False,'root_mating_pair':[FEMALE,'GPU_R6_CEM_keyed_edge_PLACEMENT_REFERENCE']},
      'motherboard_mating_pair':[MALE,'PCIE_DS2501_PHYSICAL_X8_OPEN_END_UNVERIFIED_PHOTO_PROXY'],
      'motherboard_mating_datum':{'insertion_axis':[-1,0,0],'blade_tip_x_mm':193.55,'insertion_depth_CEM_REFERENCE_mm':5.75,'key_y_mm':185.2,'PCB_center_z_mm':208.2,
        'photo_scaled_not_manufacturer_millimeter_CAD':True},
      'female_mounts':{'hole_pitch_mm':108,'source_hole_diameters_mm':[3.6,3.5],
        'axes':[[fx,y,54.00000046,0,0,-1] for y in fys],'bolts':'M3x8','nuts':'M3DIN934 hex2.4mm'},
      'male_mounts':{'hole_pitch_mm':75.45,'source_hole_diameters_mm':[3.6,3.6],
        'axes':[[mx,y,207.4,0,0,1] for y in mys],'bolts':'M3x8','nuts':'M3DIN934 hex2.4mm',
        'status':'HARD_CPU_CONFLICT_PROTOTYPE_NOT_LOAD_QUALIFIED'},
      'frame_mount_axes':[{'point':[170,y,10],'axis':[0,0,-1],'through_d_mm':3.4,'bolt':'M3x10',
        'root_nut_center_z_mm':2.4} for y in (68.,212.)]+[
        {'point':[240,230,215],'axis':[0,1,0],'through_d_mm':3.4,
         'status':'ROOT_MUST_CLOSE_POST_ATTACHMENT;framebolt/nut not yet modeled at root cornerpost'}],
      'prerequisites_for_male_service':['unthread2native_ear_M3','release2framewireties','disengage+X15',
        'flexible_ribbons_must_reconfigure;thecurrentserviceonlysweepsrigidmale'],
      'limits':['Nochange toCPU40mmhardcylinder or photo-scaledslotcoordinates',
        'Actualshortmalecollision persists;alternativesSF/K83candidateevidence retained butnotselected',
        'R5CEM/GPUreference is placementonly,not ZotacPCB/CAD;mustfitupphysicalcard',
        'R5radius is an engineering candidate only,not manufacturer minimum bend certification',
        'Root framehole cuts/retention hardware,flexible unplug reconfiguration and printing load tests remain necessary']}
    return parts,hw,wires,service,res,meta
