# SPDX-License-Identifier: MIT
"""R6 common three-drive cage, native bottom mounts and independent front service.

Millimeters. Only this new module is constructed. The HDD body and native-hole
pattern are dimensioned references; SATA cable heads remain planning proxies.
"""
from __future__ import annotations
import itertools
import math
import cadquery as cq
from build import box, cylinder, merge, bbox
from r4_drive_mount import native_screw_x, screw_z

SOURCE='https://www.seagate.com/files/www-content/product-content/ironwolf/en-us/docs/100844482f.pdf'
FRAME_POINTS=((7.,21.),(101.,21.),(7.,134.),(101.,134.))
DRIVE_X=(9.,40.1,71.2)
BODY_Y=32.; BODY_Z=12.; TOP=159.


def _one(s,name):
    s=s.clean()
    if not s.isValid() or len(s.Solids())!=1:
        raise ValueError(f'{name}: expected one valid solid, got {len(s.Solids())}')
    return s.Solids()[0]


def _square_nut(x,y,z):
    return _one(box((5.5,5.5,2.4),(x-2.75,y-2.75,z)).cut(
        cylinder(1.6,2.6,(x,y,z-.1))),'M3 square nut')


def _frame_flat_screw(x,y):
    # DIN7991 M3x8 envelope: 90deg Ø6 head, overall8 including flat head.
    top=8.4; hh=1.5
    s=merge(cq.Solid.makeCone(3,1.5,hh,cq.Vector(x,y,top),cq.Vector(0,0,-1)),
            cylinder(1.5,8-hh,(x,y,top-hh),(0,0,-1)))
    recess=cq.Workplane('XY').polygon(6,2/math.cos(math.pi/6)).extrude(.8).val().translate((x,y,top-.7))
    return _one(s.cut(recess),'M3x8 flathead frame screw reference')


def _lock_tool(x,y):
    # Analytic continuous60deg L-key arm, directed front/right away from
    # the left-front enclosure post. Hex leg enters the front lock from above.
    z=29.2; r=80.; a0=270.; a1=330.
    c=cq.Vector(x,y,z)
    a=c+cq.Vector(r*math.cos(math.radians(a0)),r*math.sin(math.radians(a0)),0)
    b=c+cq.Vector(r*math.cos(math.radians(a1)),r*math.sin(math.radians(a1)),0)
    arc=cq.Edge.makeCircle(r,c,cq.Vector(0,0,1),a0,a1)
    sec=cq.Wire.assembleEdges([cq.Edge.makeLine(c,a),arc,cq.Edge.makeLine(b,c)])
    wire=sec.offset2D(1.45,kind='arc')[0]
    arm=cq.Solid.extrudeLinear(wire,[],cq.Vector(0,0,2.9))
    return _one(merge(arm,cylinder(1.5,18,(x,y,13))), 'front L-key tool envelope')


def _box_sweep(size,origin,axis,travel):
    size=list(size); origin=list(origin)
    k=next(k for k,v in enumerate(axis) if v)
    size[k]+=travel
    if axis[k]<0:origin[k]-=travel
    return box(tuple(size),tuple(origin))


def _forward_projection(shapes,travel=300):
    # Component-box projection is an intentional superset for native screws
    # and holes. Preserve each skeletal rail's X/Z section, never fill the
    # entire carrier bounding box and thereby hide the rear undercut.
    sweeps=[]
    for s in shapes:
        b=s.BoundingBox()
        sweeps.append(box((b.xlen,b.ylen+travel,b.zlen),(b.xmin,b.ymin-travel,b.zmin)))
    return cq.Compound.makeCompound(sweeps)


def build_storage():
    parts={};hardware={};heads={};service={}
    meta={'reference_sku':'ST8000VN004','source_url':SOURCE,
      'manual':'100844482RevF,printed21–22,Fig4/5;3.4mounting',
      'requested_mechanical_box_mm':{'X':[4,104],'Y':[18,138],'Z':[5,175]},
      'body_size_mm':[26.1,101.85,147.0], 'body_x_min_mm':list(DRIVE_X),
      'body_y_mm':[32,133.85],'body_z_mm':[12,159], 'body_gap_mm':5.,
      'native_mount_surface':'PCB/bottom broad face -X;not narrow side holes',
      'native_pattern_mm':{'width_pitch':95.25,'from_connector_end':[41.275,117.475]},
      'native_fastener':{'reference':'McMaster99926A106','url':'https://www.mcmaster.com/99926A106/',
        'thread':'6-32UNC','length_including_head_mm':6.35,'head_diameter_mm':7.7978,
        'head_height_mm':1.6764,'countersink_degrees':100,'driver_AF_mm':1.984375,
        'carrier_mount_wall_mm':2.8,'spacer_mm':.8,'penetration_mm':2.75,
        'manufacturer_max_penetration_mm':3.56,'manufacturer_max_torque_in_lb':6},
      'native_mounts':[],'moving_parts':{},'moving_hardware':{},
      'front_lock_hardware':{},'service':{},'connectors':{},
      'frame_attachment':{'points_xy_mm':[list(v) for v in FRAME_POINTS],
        'cage_bottom_z_mm':5,'screw':'M3x8 90deg flathead reference,seatZ8.4',
        'root_bottom_frame_through_holes_diameter_mm':3.4,
        'root_square_nut_pockets':{'size_mm':[5.9,5.9,2.6],'z_mm':[1.1,3.7]},
        'nut_z_mm':[1.2,3.6],'bottom_frame_assumed_z_mm':[0,5],
        'note':'root must provide cut bottom-frame holes/nut pockets; cage is not floating'},
      'checks':[],
      'limits':['Neutral mounting holes,not modeled thread teeth;printed strength/creep/vibration not accepted',
        'Head body dimensions and cable bends remain engineering proxies;not exact connector CAD',
        'R6 power/data flexible routes and retained parking clips must be supplied by the root assembly',
        'Lock-tool envelope is a2.5mm L-key,not a fat straight driver handle',
        'Bottom-frame M3 screws/nuts are complete references but depend on root frame holes and material'],
      'head_source_note':'XconnectorCL=PCBface+.138in fromSeagateFig4;Ydata/power center offsets29/62mm inherited engineering estimates,not certified mating coordinates'}

    # Shared open floor: two narrow longitudinal bearing strips per drive,
    # joined only by front/rear edge beams. Nothing spans the main bottom fan.
    cage_bits=[box((100,12,4.4),(4,18,5)),box((100,8,4.4),(4,130,5))]
    for x in DRIVE_X:
        for xx in (x-3.6,x+23.7):
            cage_bits.append(box((2.4,104.3,4.8),(xx,30,5)))
    # Low lateral guides terminate below HDD metal; no thick C/T extrusion.
    for x,w in ((4,1.1),(35.4,.8),(66.5,.8),(97.6,2.4)):
        cage_bits.append(box((w,104,6.5),(x,30,5)))
    # A common rear skeleton supports upper anti-sway fingers. The lower
    # rear wall sits beyond the moving sole; four upright posts start above it.
    cage_bits.append(box((100,1.2,5.6),(4,136.8,9.4)))
    for x in (10.,41.1,72.2,100.):
        cage_bits.append(box((4,3.35,136),(x,134.65,15)))
    cage_bits.append(box((100,3.35,3),(4,134.65,148)))
    for x in DRIVE_X:
        # Rear foot undercut: only the right sole is caught, never the PCB rail.
        cage_bits.append(box((5.0,3.35,2.6),(x+22.1,134.65,12.4)))
        # Upper lateral fingers have0.8mm metal clearance and stay above all
        # native mounting rails (rail top122.725); no HDD top-cover clamp.
        for xx in (x-2,x+26.9):
            cage_bits.append(box((1.2,9,6),(xx,129,145)))
        # Bridge each pair of upper fingers to the common rear top member.
        cage_bits.append(box((30.1,3.35,3),(x-2,134.65,148)))
    cage=merge(*cage_bits)

    for i,x in enumerate(DRIVE_X,1):
        cx=x+13.05; ylock=24.
        # The front screw is removed before drawing. Fixed bosses are below
        # all moving feet except the front lip that already departs forward.
        cage=cage.cut(cylinder(1.7,8,(cx,ylock,4.9)))
        cage=cage.cut(box((5.9,5.9,2.6),(cx-2.95,ylock-2.95,5.5)))
        cage=cage.cut(box((5.9,ylock-18+2.95,2.6),(cx-2.95,18,5.5)))
        lock=f'R6_STORAGE_LOCK_{i}_M3x8'
        nut=f'R6_STORAGE_LOCK_{i}_M3_square'
        hardware[lock]=screw_z(8,(cx,ylock,13))
        hardware[nut]=_square_nut(cx,ylock,5.6)
        meta['front_lock_hardware'][str(i)]=[lock]

        body=box((26.1,101.85,147),(x,BODY_Y,BODY_Z))
        hole_ys=(BODY_Y+3.3,BODY_Y+98.55)
        hole_zs=(TOP-117.475,TOP-41.275)
        # A narrow U-frame occupies only local PCB edge bands. Broad planar
        # cover/PCB areas remain exposed; its top is below all SATA heads.
        bones=[box((2.8,10,112.925),(x-3.6,y-5,9.8)) for y in hole_ys]
        bones.append(box((2.8,105.25,4.2),(x-3.6,30.3,9.8)))
        for xx in (x-3.6,x+23.7):
            bones.append(box((2.4,116.4,2.2),(xx,20,9.8)))
        for yy in (28.,130.4):
            bones.append(box((29.7,6,2.2),(x-3.6,yy,9.8)))
        bones.append(box((29.7,8,3.6),(x-3.6,20,9.4)))
        carrier=merge(*bones)
        carrier=carrier.cut(cylinder(1.7,5,(cx,ylock,9)))
        native_keys=[]
        for j,(y,z) in enumerate(itertools.product(hole_ys,hole_zs),1):
            body=body.cut(cylinder(1.8,3.56,(x,y,z),(1,0,0)))
            carrier=carrier.cut(cylinder(1.9,3,(x-3.7,y,z),(1,0,0)))
            hh=(4.02-1.9)/math.tan(math.radians(50))
            carrier=carrier.cut(cq.Solid.makeCone(4.02,1.9,hh,cq.Vector(x-3.6,y,z),cq.Vector(1,0,0)))
            sn=f'R6_STORAGE_NATIVE_{i}_6_32_{j}';sp=f'R6_STORAGE_NATIVE_{i}_spacer08_{j}'
            hardware[sn]=native_screw_x(x-3.6,y,z)
            hardware[sp]=_one(cylinder(3,.8,(x-.8,y,z),(1,0,0)).cut(
                cylinder(1.9,.8,(x-.8,y,z),(1,0,0))),sp)
            native_keys += [sn,sp]
            meta['native_mounts'].append({'drive':i,'axis':[1,0,0],'hole_center':[x,y,z],
                'screw':sn,'spacer':sp,'penetration_mm':2.75,'max_penetration_mm':3.56})
        pn=f'R6_STORAGE_TRAY_{i}_native4_open_U'; dn=f'R6_drive_{i}'
        parts[pn]=_one(carrier,pn);hardware[dn]=_one(body,dn)
        meta['moving_parts'][str(i)]=[pn]
        meta['moving_hardware'][str(i)]=[dn]+native_keys
        tool=f'SERVICE_R6_STORAGE_{i}_front_lock_Lkey_60deg'
        service[tool]=_lock_tool(cx,ylock)
        # Include body, precise skeletal projection and all retained native
        # metal. Removed M3 lock does not disappear without a prerequisite.
        moving=[box((26.1,101.85,147),(x,BODY_Y,BODY_Z))]+bones+[hardware[n] for n in native_keys]
        draw=f'SERVICE_R6_STORAGE_{i}_front_draw_300'
        service[draw]=_forward_projection(moving)
        connectors=[]
        for kind,dy,size in (('data',29.,(10.,18.,18.)),('power',62.,(12.,28.,20.))):
            hx=x+.138*25.4;hy=BODY_Y+dy
            hn=f'R6_SATA_{kind}_{i}_HDD_HEAD_ENGINEERING_PROXY'
            origin=(hx-size[0]/2,hy-size[1]/2,TOP)
            heads[hn]=box(size,origin)
            sw=f'SERVICE_R6_SATA_{kind}_{i}_withdraw_plusZ15'
            park=f'SERVICE_R6_SATA_{kind}_{i}_PARKED_after_plusZ15'
            service[sw]=_box_sweep(size,origin,(0,0,1),15)
            service[park]=heads[hn].translate((0,0,15))
            meta['connectors'][hn]={'drive':i,'kind':kind,'origin_mm':list(origin),'size_mm':list(size),
              'withdrawal_axis':[0,0,1],'withdrawal_mm':15,'withdrawal_service':sw,'parked_head_service':park,
              'status':'ENGINEERING_HEAD_ENVELOPE_NOT_CERTIFIED_CONNECTOR_CAD'}
            connectors.append(hn)
        meta['service'][str(i)]={'front_draw':draw,'tool':tool,'connectors':connectors,
          'remove_before_draw':[lock],
          'prerequisites':['remove_front_panel','open_top_access','power_down_and_wait_spindown',
            'unplug_only_target_data_and_power','park_target_heads_plusZ15_and_release_target_data_clamp'],
          'retained':'other2HDDs/PSU/GPU/MB and all native6-32/spacers;native hardware moves with target',
          'parking_limit':'head solids modeled at+Z15;root must route/restrain the attached flexible cables and park unused4thpowerhead'}

    # Four explicit cage-to-bottom-frame joints. All heads are recessed below
    # moving feet; nuts live in root's0..5mm bottom frame, not inside HDD paths.
    for j,(x,y) in enumerate(FRAME_POINTS,1):
        cage=cage.cut(cylinder(1.7,5,(x,y,4.9)))
        cage=cage.cut(cylinder(3.2,1.1,(x,y,8.4)))
        cage=cage.cut(cq.Solid.makeCone(3.2,1.7,1.5,cq.Vector(x,y,8.4),cq.Vector(0,0,-1)))
        hardware[f'R6_STORAGE_FRAME_M3x8_flat_{j}']=_frame_flat_screw(x,y)
        hardware[f'R6_STORAGE_FRAME_M3_square_{j}']=_square_nut(x,y,1.2)
    parts['R6_STORAGE_COMMON_CAGE_open_floor_rear_skeleton']=_one(cage,'commoncage')
    meta['fixed_parts']=['R6_STORAGE_COMMON_CAGE_open_floor_rear_skeleton']
    meta['fixed_hardware']=[n for n in hardware if n.startswith('R6_STORAGE_FRAME_') or '_M3_square' in n]
    meta['part_count']=len(parts);meta['hardware_count']=len(hardware);meta['head_count']=len(heads)
    meta['service_count']=len(service)
    return parts,hardware,heads,service,meta
