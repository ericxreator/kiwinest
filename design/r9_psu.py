# SPDX-License-Identifier: MIT
"""R9 rolled ENP-7660B: original rear AC/fan, six complete lay-in sources.

Only this module is new. Manufacturer dimensions, original fixed cables and
native mounting axes are retained. The illustrated vented broad face is exposed
through a left-panel window; the opposite face, wire port, threads and seals
still require inspection of the received supply. No PSU opening or wire cutting.
"""
from __future__ import annotations
from pathlib import Path
import hashlib,json,math
import cadquery as cq
from build import box,cylinder,merge,bbox

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'references/private/enp7660b-official-spec-20251008.pdf'
NATIVE=ROOT/'references/original/native-mechanical.json'
BODY_MIN=(2.9,96.,145.)
BODY_SIZE=(40.5,150.,81.5)
NATIVE_XZ=((39.4,150.5),(7.4,150.5),(7.4,222.19))
FRAME_REAR_AXES=((50.,151.),(50.,215.))
FLOOR_AXES=((8.,104.),(40.,104.),(8.,230.),(42.,230.))
CHANNELS={
    'ATX':{'point':[28.4,96.,153.],'diameter':11.},
    'EPS':{'point':[25.4,96.,166.],'diameter':4.5},
    'GPU':{'point':[37.9,96.,155.],'diameter':6.5},
    'SATA_A':{'point':[37.4,96.,146.5],'diameter':5.5},
    'SATA_B':{'point':[19.4,96.,147.],'diameter':5.5},
    'MOLEX_FDD':{'point':[19.4,96.,157.],'diameter':5.5},
}
SPLIT_X=28.4
SHIFT=15.
Y0,Y1=82.,96.
BASE='PSU_R9_ROLLED_COLD_FRAME_AND_FIXED_GLAND'
CAP='PSU_R9_ALL_FACTORY_LOOMS_LEFT_LAY_IN_CAP'
PSU='PSU_R9_ENP7660B_ORIGINAL_ROLLED_BODY_REFERENCE'
FLANGE='PSU_R9_REPLACEABLE_1mm_METAL_REAR_FLANGE_NOT_PRINT'
AIR='AIR_PSU_R6_front_and_ALL_FACE_cold_sleeve'
EXHAUST='AIR_PSU_R6_straight_rear_exhaust'


def one(s,name):
    s=s.clean()
    if not s.isValid() or len(s.Solids())!=1:raise ValueError(f'{name}: expected one valid solid, got {len(s.Solids())}')
    return s


def pan(length,point,axis=(0,0,1),radius=1.5,head_radius=2.75,head_height=2.4):
    p=cq.Vector(*point);v=cq.Vector(*axis)
    return merge(cylinder(radius,length,point,axis),cylinder(head_radius,head_height,(p-v*head_height).toTuple(),axis))


def csk(length,point):
    p=cq.Vector(*point)
    return merge(cq.Solid.makeCone(3,1.5,1.5,p,cq.Vector(0,0,-1)),cylinder(1.5,length-1.5,(point[0],point[1],point[2]-1.5),(0,0,-1)))


def nut_x(x,y,z):
    return box((1.8,5.5,5.5),(x,y-2.75,z-2.75)).cut(cylinder(1.6,2,(x-.1,y,z),(1,0,0)))


def nut_y(x,y,z):
    return box((5.5,1.8,5.5),(x-2.75,y,z-2.75)).cut(cylinder(1.6,2,(x,y-.1,z),(0,1,0)))


def _source_shape(x,z,r,y0=Y0,y1=Y1):
    return cylinder(r,y1-y0,(x,y0,z),(0,1,0))


def _release_profile(x,z,r,y0=Y0,y1=Y1):
    pieces=[_source_shape(x,z,r,y0,y1)]
    if abs(x-SPLIT_X)>1e-7:pieces.append(box((abs(x-SPLIT_X),y1-y0,2*r),(min(x,SPLIT_X),y0,z-r)))
    return merge(*pieces) if len(pieces)>1 else pieces[0]


def _gland():
    """Two rigid halves, stationary split foam, and actual full-diameter stubs.

    Each release cavity reaches the split plane. On the removable left side
    its cross-section is monotone toward+X, so translating the cap toward-X
    opens it without feeding any finished connector through a closed bore.
    """
    inner_bits=[];outer_bits=[];outer_sweeps=[];wires={};paths={}
    for label,info in CHANNELS.items():
        x,_,z=info['point'];r=info['diameter']/2;ri=r+.5;ro=ri+1.
        inner_bits.append(_release_profile(x,z,ri));outer_bits.append(_release_profile(x,z,ro))
        # Exact-X Minkowski sweep of each cylindrical/rectangular primitive.
        if x<=SPLIT_X:
            outer_sweeps.extend([_source_shape(x,z,ro),_source_shape(x-SHIFT,z,ro),
                box((SHIFT,Y1-Y0,2*ro),(x-SHIFT,Y0,z-ro))])
            if x<SPLIT_X:
                outer_sweeps.append(box((SPLIT_X-x+SHIFT,Y1-Y0,2*ro),(x-SHIFT,Y0,z-ro)))
        key=f'CABLE_R9_PSU_FACTORY_SOURCE_{label}_COMPLETE_14mm'
        wires[key]=_source_shape(x,z,r)
        paths[label]={'key':key,'source_xyz_mm':[x,Y1,z],'exit_xyz_mm':[x,Y0,z],
            'diameter_mm':info['diameter'],'centerline_mm':14.,'source_coordinates_received_hardware_verified':False}
    # Two narrow webs join the EPS collar without replacing the actual bores.
    boxes=[((31.5,14,6),(14,Y0,170)),((1.5,14,20),(21,Y0,156)),((1.6,14,18),(28.4,Y0,158))]
    for size,origin in boxes:
        outer_bits.append(box(size,origin))
        if origin[0]<SPLIT_X:
            outer_sweeps.append(box((min(size[0],SPLIT_X-origin[0])+SHIFT,size[1],size[2]),(origin[0]-SHIFT,origin[1],origin[2])))
    outer=merge(*outer_bits);inner=merge(*inner_bits)
    left=box((228.4,100,200),(-200,50,100));right=box((200,100,200),(SPLIT_X,50,100))
    wall=outer.cut(inner);fixed=wall.intersect(right);cap=wall.intersect(left)
    bolts=[];hw={};holes=[]
    for i,y in enumerate((85.5,92.5),1):
        hole=cylinder(1.7,60,(-10,y,173),(1,0,0));holes.append(hole)
        fixed=fixed.cut(hole);cap=cap.cut(hole)
        fixed=fixed.cut(box((2,5.9,6.1),(30.2,y-2.95,170.05)))
        n=f'PSU_R9_GLAND_M3x20_{i}';hw[n]=pan(20,(14,y,173),(1,0,0));bolts.append(n)
        hw[f'PSU_R9_GLAND_DIN562_M3_{i}']=nut_x(30.3,y,173)
    sweep=merge(*outer_sweeps).intersect(left).cut(inner)
    for hole in holes:sweep=sweep.cut(hole)
    # The foam fills only the released-slot space. Actual wire cylinders are
    # retained, not replaced by a narrow placeholder or removed from the air.
    seal=inner.intersect(box((80,4,80),(-10,Y0,120))).cut(cq.Compound.makeCompound(list(wires.values())))
    hw['PSU_R9_SPLIT_INSULATING_FOAM_LEFT_INSTALLED']=seal.intersect(left)
    hw['PSU_R9_SPLIT_INSULATING_FOAM_RIGHT_INSTALLED']=seal.intersect(right)
    return fixed,cap,outer,inner,sweep,hw,wires,paths,bolts


def build_psu():
    """Return parts,hardware,source_wires,air,service,reserves,JSON metadata."""
    p={};h={};a={};sv={};res={}
    body=box(BODY_SIZE,BODY_MIN)
    for x,z in NATIVE_XZ:body=body.cut(cylinder(1.9,4.1,(x,246,z),(0,-1,0)))
    h[PSU]=one(body,'original PSU rigid-body roll')
    # Unaltered three manufacturer mounting axes; custom metal carrier ring.
    flange=box((42.5,1,90),(2.5,246,141)).cut(box((39.7,3,80.7),(3.3,245,145.4)))
    for x,z in NATIVE_XZ:
        island=cylinder(4,1,(x,246,z),(0,1,0))
        neck=box((max(1.,x-2.5),1,3),(2.5,246,z-1.5)) if x<20 else box((45-x,1,3),(x,246,z-1.5))
        flange=merge(flange,island,neck).cut(cylinder(2,3,(x,245,z),(0,1,0)))
    native=[]
    for i,(x,z) in enumerate(NATIVE_XZ,1):
        key=f'PSU_R9_NATIVE_6_32_x3_16_LENGTH_UNVERIFIED_REFERENCE_{i}'
        h[key]=pan(4.7625,(x,247,z),(0,-1,0),1.7526,3.25,2.2);native.append(key)
    for i,(x,z) in enumerate(FRAME_REAR_AXES,1):
        flange=merge(flange,box((9,1,7),(45,246,z-3.5))).cut(cylinder(1.7,3,(x,245,z),(0,1,0)))
        h[f'PSU_R9_REAR_FRAME_M3x10_{i}']=pan(10,(x,247,z),(0,-1,0))
        h[f'PSU_R9_REAR_FRAME_DIN562_M3_{i}']=nut_y(x,239,z)
        h[f'PSU_R9_REAR_FRAME_SPACER2mm_{i}']=cylinder(3.3,2,(x,244,z),(0,1,0)).cut(cylinder(1.6,2.2,(x,243.9,z),(0,1,0)))
    h[FLANGE]=one(flange,'1mm metal rear flange')
    # Independent fixed support below the blank narrow face; never a moving
    # HDD tray. Root supplies the four stated fixed-frame bearing lands.
    floor=box((42.6,164,1.5),(2.9,82,143))
    for x in (4.,38.3):
        for y in (120.,200.):floor=merge(floor,box((4,10,.5),(x,y,144.5)))
    for i,(x,y) in enumerate(FLOOR_AXES,1):
        floor=merge(floor,box((min(x+4,45.5)-(x-4),10,4),(x-4,y-5,139)))
        floor=floor.cut(cylinder(1.7,11,(x,y,135)))
        floor=floor.cut(cq.Solid.makeCone(3,1.5,1.5,cq.Vector(x,y,144.5),cq.Vector(0,0,-1)))
        h[f'PSU_R9_FIXED_SUPPORT_M3x8_CSK_{i}']=csk(8,(x,y,144.5))
        h[f'PSU_R9_FIXED_SUPPORT_DIN562_M3_{i}']=box((5.5,5.5,1.8),(x-2.75,y-2.75,137.)).cut(cylinder(1.6,2,(x,y,136.9)))
    # Rear remains open to the original external AC/fan face. Left is an
    # intentional directly-exposed side window, not a0.5mm lateral duct.
    fixed,cap,outer,inner,sweep,gh,wires,paths,cap_bolts=_gland();h.update(gh)
    # The left front wall travels with the split cap. Leaving this boundary
    # fixed would require threading finished connectors despite an open gland.
    # A0.1mm join and0.55mm front-port radial gap avoid coincident OCC seams;
    # the six actual wire diameters and source coordinates remain unchanged.
    front_ports=merge(*[_release_profile(q['point'][0],q['point'][2],q['diameter']/2+.55,80.2,82.3)
        for q in CHANNELS.values()])
    front_wall=box((41.5,1.6,84.6),(2.5,80.5,144.5)).cut(front_ports)
    left_half=box((228.4,100,200),(-200,50,100))
    front_cap=front_wall.intersect(left_half)
    front_fixed=front_wall.cut(front_cap)
    cap=one(cap.fuse(front_cap),'left lay-in cap with released front boundary')
    # Every cutout in this flat wall opens toward+X. Its exact-X sweep is
    # its original material plus the15mm strip extending its solid left edge.
    sweep=merge(sweep,front_cap,box((SHIFT,1.6,84.6),(2.5-SHIFT,80.5,144.5)))
    shell=merge(floor,box((1.5,164,88),(44,82,143)),
        box((43,164,1.5),(2.5,82,229.5)),front_fixed)
    # The full real cap motion opens the first14mm of the support floor.
    # Front fixing lands are behind that opening, not under the moving cap.
    shell=shell.cut(outer).fuse(fixed).cut(sweep).clean()
    # Re-open every fastener seat after the side wall has joined the floor;
    # the right rear fixing atX42 locally enters that wall's lower edge.
    for x,y in FLOOR_AXES:
        shell=shell.cut(cylinder(1.7,11,(x,y,135)))
        shell=shell.cut(cq.Solid.makeCone(3,1.5,1.5,cq.Vector(x,y,144.5),cq.Vector(0,0,-1)))
    shell=shell.clean()
    p[BASE]=one(shell,'fixed PSU cold frame and lay-in half')
    p[CAP]=one(cap,'all finished factory loom removable half')
    sk='SERVICE_PSU_R9_ALL_LOOM_CAP_MINUSX15';sv[sk]=sweep
    service={'sweep_key':sk,'translation_mm':[-SHIFT,0,0],
        'removed_parts_for_access':['SKIN_R6_left','PSU_R9_LEFT_PANEL_SEAL_INSTALLED'],
        'remove_bolts_and_captured_nuts':cap_bolts,
        'retained_captured_nut_keys':[f'PSU_R9_GLAND_DIN562_M3_{i}' for i in (1,2)],
        'method':'Exact-X sweep of primitives clipped at split plane; original release cavities are monotone toward opening',
        'assembly_order':'Place right/deep GPU and SATA_A looms first, then left-side SATAB/MOLEX/EPS, ATX last; fit loose split foam and cap. No finished connector passes a closed bore.',
        'service_order':'ACoff/unplug; remove left skin and its seal; remove two M3x20 cap screws; slide rigid cap-X15, retain soft foam until cap is clear; peel split foam and free ATX/left looms before deep GPU/SATA_A.',
        'support_floor_opened_by_actual_cap_sweep':True,
        'front_fixing_axes_moved_behind_source_cap_Y_mm':104.,
        'soft_seal_and_wire_deformation_qualified':False,'opens_without_PSU_disassembly_or_cable_cutting':True}
    # Nominal installed foam sheets are separate owned fabricated components.
    lseal=box((.5,163.9,88),(2.4,82.1,141.5)).cut(box((.7,160,84),(2.3,84,143.5)))
    h['PSU_R9_LEFT_PANEL_SEAL_INSTALLED']=lseal
    rseal=box((42.5,.6,90),(2.5,247,141)).cut(box((39.7,.8,80.7),(3.3,246.9,145.4)))
    h['PSU_R9_REAR_PANEL_SEAL_INSTALLED']=rseal
    # Protected cold volume includes the real external side opening and end
    # plenum. Only actual walls/seals and the enclosed source collar displace it.
    # Native screw bores are inside the original PSU, not fresh-air ducts.
    # Re-derive from the raised support floor's actual upper surface144.5.
    # Its underside is a separate cable bay, not part of the PSU cold cavity.
    cavity=box((41.6,164,85),(2.4,82,144.5)).cut(box(BODY_SIZE,BODY_MIN))
    side=box((22.9,160,84),(-20,84,143.5))
    cold=merge(cavity,side).cut(outer)
    for q in list(p.values())+[lseal,rseal]:cold=cold.cut(q)
    for key,q in h.items():
        if key.startswith(('PSU_R9_GLAND_','PSU_R9_FIXED_SUPPORT_','PSU_R9_REAR_FRAME_')):cold=cold.cut(q)
    a[AIR]=cold.clean()
    # Drawing shows the fan in the lower40.5mm of the81.5mm rear face. The
    # upper IEC region has its own external cable approach and is not a duct.
    hot=box((40.5,29,40.5),(2.9,246,145))
    for q in h.values():hot=hot.cut(q)
    a[EXHAUST]=hot.clean()
    res['RESERVE_PSU_R9_NATIVE_FRONT_TONGUE_SIDE_PLANE_UNKNOWN']=box((40.5,10,81.5),(2.9,86,145))
    res['RESERVE_PSU_R9_UNMEASURED_FACTORY_WIRE_PORT']=box((31,18,30),(14,80,141.5))
    # Full conservative commercial C13 reference, not truncated to recess depth.
    # No rewirable connector is a purchase instruction; use an intact cord.
    sv['SERVICE_PSU_R9_EXTERNAL_C13_APPROACH_REFERENCE']=box((28.7,87.5+40,21),(12.05,246,201.5))
    for i,y in enumerate((85.5,92.5),1):
        sv[f'SERVICE_PSU_R9_GLAND_SCREW_{i}_MINUSX20']=merge(cylinder(1.5,40,(-6,y,173),(1,0,0)),cylinder(2.75,22.4,(-8.4,y,173),(1,0,0)))
    meta={'model':'Enhance ENP-7660B original fixed-wire, rolled90deg with native rear AC',
        'body_bbox_mm':bbox(h[PSU]),'body_axes':'40.5X x150Y x81.5Z; AC/fan+Y246, intact fixed cables/intake Y96',
        'R8_rigid_body_transform':{'rotation_Y_deg':-90,'translation_mm':[243.4,0,129]},
        'manufacturer_airflow_global':[0,1,0],'native_hole_axes_xz_mm':[list(q) for q in NATIVE_XZ],
        'native_screw_hardware':native,'native_screw_length_reference_mm':4.7625,
        'native_screw_intrusion_reference_mm':3.7625,'native_screw_length_and_penetration_verified':False,
        'source_file':str(SOURCE.relative_to(ROOT)),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'native_transcription_file':str(NATIVE.relative_to(ROOT)),'native_transcription_sha256':hashlib.sha256(NATIVE.read_bytes()).hexdigest(),
        'metal_flange':{'key':FLANGE,'material':'1mm steel/aluminium, deburr; notFDM','Y_mm':[246,247],'native_holes':'original three UNC6-32 axes','outer_bbox_mm':bbox(h[FLANGE])},
        'frame_interfaces':{'rear':{'axes_xyz_mm':[[x,247,z] for x,z in FRAME_REAR_AXES],
            'axis':[0,-1,0],'bolt':'M3x10pan, tipY237','post':'shifted rearleft upper column X46..54/Y236..244',
            'nuts_bbox_mm':[[[x-2.75,239,z-2.75],[x+2.75,240.8,z+2.75]] for x,z in FRAME_REAR_AXES]},
          'fixed_bottom':[{'point_mm':[x,y,144.5],'axis':[0,0,-1],'root_land_bbox_mm':[[x-4,y-5,135.5 if y>200 else 136],[min(x+4,45.5),y+5,139]],
              'root_through_D_mm':3.4,'root_nut_pocket_bbox_mm':[[x-2.95,y-2.95,136.9],[x+2.95,y+2.95,139.1]]} for x,y in FLOOR_AXES]},
        'case_interfaces':{'left_opening_bbox_mm':[[0,84,143.5],[2.9,244,227.5]],
            'rear_opening_bbox_mm':[[2.9,247.1,145.],[43.4,250.1,226.5]],
            'rear_frame_head_clearances':[{'center_xz_mm':[x,z],'D_mm':6.0,'Y_mm':[247,251]} for x,z in FRAME_REAR_AXES]},
        'intake_face_scope':{'official_page':2,'visible_broad_face_vented':True,
            'mapped_visible_vent_face':'Left-X2.9 inferred from drawing orientation; confirm on received unit',
            'left_face_is_direct_exterior_window':True,'left_nominal_skin_gap_mm':.5,
            'unshown_opposite_broad_face_vent_status_verified':False,'right_gap_mm':.6,
            'right_opposite_face_and_pressure_drop_require_received_hardware':True,
            'cold_air_key':AIR,'key_retained_for_checker_compatibility_not_all_face_flow_certification':True,
            'cold_cavity_Z_mm':[144.5,229.5],
            'cold_cavity_lower_boundary':'Actual upper face of the raised floor; underside belongs to the separate cable bay',
            'air_boundary_is_derived_from_support_not_individual_wire_clearances':True},
        'fixed_wire_front_port':{'status':'UNMEASURED_ENGINEERING_SOURCE_POSITIONS','source_paths':paths,
            'source_point_scope':'Rigidly transformed R8 engineering positions, not manufacturer dimensions',
            'all_finished_looms_lay_in':True,'complete_source_segment_mm':14.,'cap_service':service,
            'source_release_profiles_open_through_front_wall_Y_mm':[80.5,82.1],
            'port_bore_radial_wire_clearance_mm':.5,
            'front_boundary_port_radial_clearance_mm':.55,
            'front_boundary_left_half_moves_with_lay_in_cap':True},
        'external_AC_approach':{'service_key':'SERVICE_PSU_R9_EXTERNAL_C13_APPROACH_REFERENCE',
            'engineering_bbox_mm':[[12.05,246.,201.5],[40.75,373.5,222.5]],
            'connector_size_and_wire_bend_are_engineering_reserves_not_vendor_CAD':True,
            'actual_intact_cord_fit_verified':False},
        'PSU_removal':'ACoff/unplug; release external cord, all loads and retained looms; remove left skin/cap/foam, support original PSU, remove3native screws, move body forward away from rear flange then lift with top module removed; full extraction/tool paths unqualified.',
        'native_harness':{'ATX24_mm':300,'EPS4plus4_mm':300,'PCIe6plus2_segments_mm':[300,150],'SATA_strings':2,'SATA_each_segments_mm':[300,150],'SATA_heads':4,'Molex3plusFDD_segments_mm':[300,150,150,150]},
        'original_fabrication_parts':[{'hardware_key':FLANGE,'material':'1mm steel/aluminium','thickness_mm':1.,'flat_axis':'Y'}]+[
            {'hardware_key':n,'material':'electrically insulating closed-cell silicone foam','nominal_installed_state':True,'cut_and_fit_received_hardware_required':True}
            for n in ('PSU_R9_SPLIT_INSULATING_FOAM_LEFT_INSTALLED','PSU_R9_SPLIT_INSULATING_FOAM_RIGHT_INSTALLED','PSU_R9_LEFT_PANEL_SEAL_INSTALLED','PSU_R9_REAR_PANEL_SEAL_INSTALLED')],
        'mating_pairs':[[PSU,n] for n in native],
        'checks':[],'limits':['Manufacturer input is2D reference; exact vent/IEC/native tongue/loom port need the received original unit',
            'At least one broadside is vented. Preserve direct external access; opposite face and narrow wrap gaps are not thermally qualified',
            'Source stubs retain actual engineering diameters ATX11/EPS4.5/GPU6.5/SATA5.5/Molex5.5; never shrink them for fit',
            'Foam is nominal installed geometry; radial cuts, compression, strain relief and airtightness require physical acceptance',
            'Bench assembly, creep/strength, native screw penetration and tool access are not accepted by CAD']}
    for label,path in paths.items():
        rec={'part':BASE,'removable_half_part':CAP,'service':service,
            'source_face_point_engineering_xyz_mm':path['source_xyz_mm'],'native_gland_point_engineering_xyz_mm':path['exit_xyz_mm'],
            'complete_source_segment_modeled':True,'wire_proxy_diameter_mm':path['diameter_mm'],'source_centerline_mm':14.,
            'source_wire_key':path['key'],'source_coordinates_received_hardware_verified':False,'thermal_or_physical_acceptance_completed':False}
        meta[label+'_isolated_factory_exit_transition']=rec
    for n in h:
        if n.startswith('PSU_R9_GLAND_M3x20_'):
            i=n.rsplit('_',1)[1];meta['mating_pairs'].append([n,f'PSU_R9_GLAND_DIN562_M3_{i}'])
    return p,h,wires,a,sv,res,meta


def integrate_psu(m):
    """Real fixed-frame lands, native rear flange, and direct skin openings.

    Both printed support beams join fixed corner posts. Neither the HDD
    carrier nor removable cable basket is used as a PSU bearing surface.
    """
    p=m['parts'];pm=m['psu_meta']
    front=merge(box((8,95,3),(3,14,136)),box((40,10,3),(4,99,136)))
    # The rear transverse connection crosses the HDD chimney's left wall
    # only behind its actual Y234.8 outer edge, never through that wall.
    rear=merge(box((41.5,11,3.5),(4,225,135.5)),box((50,11.6,4.5),(4,235.2,134.5)),
        box((9.5,11,3.5),(36,225,135.5)))
    # Three full-diameter HDD extension looms pass in real open saddles.
    # The front web is0.75mm at the saddle bottom; behind the HDD wall its
    # thickness increases to1.75mm. Neither is a strength qualification.
    rear_channels=[]
    for x in (15.,25.,35.):
        channel=cylinder(3.25,21,(x,224,139.5),(0,1,0))
        rear=rear.cut(channel)
        rear_channels.append({'center_xz_mm':[x,139.5],'bore_diameter_mm':6.5,
            'routed_wire_diameter_mm':5.5,'nominal_radial_gap_mm':.5})
    # The installed looms turn downward atY239.5. The horizontal bores alone
    # do not contain the full R3 bend; open the actual rear drop envelopes.
    # The continuous3.8mm stripY243..246.8 remains joined to the rear post.
    rear_drop_slots=[]
    for x in (15.,25.,35.):
        slot=box((6.5,8.,9),(x-3.25,235.,131.))
        rear=rear.cut(slot)
        rear_drop_slots.append({'bbox_mm':bbox(slot),'purpose':'Complete R3 downward loom bend plus0.5mm radial clearance'})
    rear=rear.clean()
    for beam_name,beam,points in (
        ('FRAME_R6_corner_10_10',front,FLOOR_AXES[:2]),
        ('FRAME_R6_corner_10_240',rear,FLOOR_AXES[2:])):
        q=merge(p[beam_name],beam)
        for x,y in points:
            q=q.cut(cylinder(1.7,5,(x,y,135))).cut(box((5.9,5.9,2.2),(x-2.95,y-2.95,136.9)))
        if beam_name.endswith('10_240'):q=q.cut(cylinder(1.7,115,(50,240,135)))
        p[beam_name]=one(q,beam_name+' fixed PSU support beam')
    p['SKIN_R6_left']=one(p['SKIN_R6_left'].cut(box((4,160,84),(-.5,84,143.5))),'left PSU direct vent opening')
    back=p['SKIN_R6_back'].cut(box((40.5,4,81.5),(2.9,247.1,145.)))
    for x,z in FRAME_REAR_AXES:
        back=back.cut(cylinder(3,5,(x,247,z),(0,1,0)))
    p['SKIN_R6_back']=one(back,'rear original PSU AC/fan opening')
    pm['fixed_frame_support_implemented']={'front_part':'FRAME_R6_corner_10_10','rear_part':'FRAME_R6_corner_10_240',
      'bearing_Z_mm':[136,139],'front_brace_bbox_mm':bbox(front),'rear_brace_bbox_mm':bbox(rear),
      'mounting_screw':'M3x8 CSK, head seat Z144.5, tip Z136.5, captured nut Z137..138.8',
      'independent_of_moving_HDD_and_cable_basket':True,'strength_and_creep_physically_verified':False,
      'rear_real_cable_saddles':rear_channels,'rear_real_cable_drop_slots':rear_drop_slots,'front_rear_brace_bottom_Z_mm':[136.,135.5],
      'rear_brace_deep_back_Z_mm':[134.5,139.],
      'rear_saddle_minimum_web_mm':.75,'rear_saddle_back_web_mm':1.75,'rear_drop_slot_back_strip_mm':3.8,
      'rear_left_wall_minimum_nominal_gap_mm':.3,'rear_back_wall_nominal_gap_mm':.4,
      'prototype_only_thin_web_and_tight_gaps_require_sample_validation':True}
