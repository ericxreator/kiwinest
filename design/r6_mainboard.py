# SPDX-License-Identifier: MIT
"""DS_2501 photo-derived Mini-ITX reference and removable mounting tray, mm.

User photograph is the only board-specific mechanical reference. Four holes use
Mini-ITX reference dimensions; socket placement/shape is a scaled photo estimate,
not manufacturer CAD. No R1--R5 file is changed by this module.
"""
from __future__ import annotations
import math
import cadquery as cq
from build import box, cylinder, merge, bbox

PHOTO='private-board-front-photo-NOT-REDISTRIBUTED.jpg'
SPEC_PHOTO='private-board-back-photo-NOT-REDISTRIBUTED.jpg'
TRAY='MAINBOARD_MOUNT_R6_DS2501_open_tray'
PCB='mini_itx_pcb'
# Same asymmetric C-datum Mini-ITX reference used in R4; not guessed corners.
HOLES_C=((0.,0.),(157.48,22.86),(0.,154.94),(157.48,154.94))
HOLES_YZ=tuple((242-(v+10.16),259-(45+u+6.35)) for u,v in HOLES_C)
PCB_X=(186.7,188.3)
FRAME_POINTS=((180.,68.),(180.,244.))
TOP_FRAME_POINTS=((180.,42.),(180.,244.))

def photo_yz(px,py):
    """Front photo board edge box: x88..504, y336..746 = 170 x 170 mm."""
    return (242-(px-88)*170/416,44+(py-336)*170/410)


def _hex_x(af,length,x,y,z):
    return cq.Workplane(cq.Plane(origin=(x,y,z),xDir=(0,1,0),normal=(1,0,0))).polygon(6,af/math.cos(math.pi/6)).extrude(length).val()


def _one(s,name):
    s=s.clean()
    if not s.isValid() or len(s.Solids()) != 1:
        raise ValueError(f'{name}: expected one valid solid, got {len(s.Solids())}')
    return s.Solids()[0]


def _washer(x,y,z,outer=3.5,thick=.5):
    return cylinder(outer,thick,(x,y,z),(1,0,0)).cut(cylinder(1.6,thick+.2,(x-.1,y,z),(1,0,0)))


def _sweep(s,axis,travel):
    b=s.BoundingBox(); v=(b.xlen,b.ylen,b.zlen); o=(b.xmin,b.ymin,b.zmin)
    return box(tuple(v[k]+abs(axis[k]*travel) for k in range(3)),tuple(o[k]+min(0,axis[k]*travel) for k in range(3)))


def build_mainboard():
    """Return parts, hardware, heads, service, reserves, JSON-safe metadata."""
    parts={};hw={};heads={};service={};reserves={}
    pcb=box((1.6,170,170),(186.7,72,44))
    # Thin perimeter plus four individually connected mount lands. Bottom
    # female-riser volume stays open; no full crossbar across Y85..205/Z42..68.
    tray=merge(box((3,4,213),(173.2,66,5)),box((3,4,213),(173.2,242,5)),
      box((3,180,4),(173.2,66,36)),box((3,180,4),(173.2,66,214)),
      box((3,30,4),(173.2,42,214)),box((3,8,28),(173.2,38,214)),
      box((3,7.4,28),(173.2,240,214)))
    for i,(y,z) in enumerate(HOLES_YZ,1):
        land=cylinder(6.5,3,(173.2,y,z),(1,0,0))
        yy=66 if y<160 else y
        reach=(y+6.5-66) if y<160 else (246-y)
        land=merge(land,box((3,reach,8),(173.2,yy,z-4)))
        tray=merge(tray,land)
        pcb=pcb.cut(cylinder(1.98,2,(186.5,y,z),(1,0,0)))
    # Also open the low return turn at Z38: an intact lower rail here would
    # force the flexible riser through plastic. Two end legs and upper bridge
    # still form one connected tray; the four lower lands retain side ribs.
    tray=tray.cut(box((5,120.4,33),(172.2,84.9,35)))
    # Circular 5.4 clearance permits +/-1 mm radial adjustment of M3 hardware;
    # washers cover slot. This is not +/-1 in both axes simultaneously.
    for i,(y,z) in enumerate(HOLES_YZ,1):
        tray=tray.cut(cylinder(2.7,5,(172.2,y,z),(1,0,0)))
        hw[f'MAINBOARD_MOUNT_R6_M3_FF_10mm_standoff_{i}']=_one(_hex_x(5.5,10,176.7,y,z).cut(cylinder(1.45,10.2,(176.6,y,z),(1,0,0))), 'standoff')
        hw[f'MAINBOARD_MOUNT_R6_front_spacer_M3_0p5mm_{i}']=_one(_washer(176.2,y,z),'front spacer')
        hw[f'MAINBOARD_MOUNT_R6_rear_loadwasher_M3_9mm_{i}']=_one(_washer(172.7,y,z,4.5),'rear washer')
        rear=merge(cylinder(1.45,6,(172.7,y,z),(1,0,0)),cylinder(2.75,2.4,(170.3,y,z),(1,0,0)))
        front=merge(cylinder(1.45,5,(188.3,y,z),(-1,0,0)),cylinder(2.75,2.4,(188.3,y,z),(1,0,0)))
        hw[f'MAINBOARD_MOUNT_R6_rear_M3x6_pan_{i}']=rear
        hw[f'MAINBOARD_MOUNT_R6_PCB_M3x5_pan_{i}']=front
        service[f'SERVICE_MAINBOARD_R6_front_screw_{i}_unthread_plusX8']=_sweep(front,(1,0,0),8)
        service[f'SERVICE_MAINBOARD_R6_rear_screw_{i}_unthread_minusX8']=_sweep(rear,(-1,0,0),8)
        service[f'SERVICE_MAINBOARD_R6_front_tool_{i}_RIGHT_SKIN_REMOVED']=cylinder(2.75,55,(190.7,y,z),(1,0,0))
        service[f'SERVICE_MAINBOARD_R6_rear_tool_{i}_TRAY_OUTSIDE_CASE']=cylinder(2.75,40,(170.3,y,z),(-1,0,0))
    # Preserve the complete x8 female PCB, including its small +X tabs.
    # Its measured maximum is X173.5572. Open a shallow rear-face relief,
    # and recess both lower rear fasteners without moving the board datum.
    tray=tray.cut(box((.9,152,2.4),(173.1,64,51.9)))
    flush_joints=[];fabrication=[]
    for i in (2,4):
        y,z=HOLES_YZ[i-1]
        washer_key=f'MAINBOARD_MOUNT_R8_lower_{i}_FLUSH_OD9_STEEL_CSK_WASHER'
        screw_key=f'MAINBOARD_MOUNT_R8_rear_M3x8_CSK_{i}'
        # D11.2 pocket retains +/-1mm radial adjustment with an OD9 washer.
        # The continuous 0.9mm floor and perimeter ribs need load/creep tests.
        tray=tray.cut(cylinder(5.6,2.2,(173.1,y,z),(1,0,0)))
        washer=cylinder(4.5,1.5,(173.8,y,z),(1,0,0))
        washer=washer.cut(cylinder(1.6,1.7,(173.7,y,z),(1,0,0)))
        washer=washer.cut(cq.Solid.makeCone(3.,1.6,1.4,cq.Vector(173.8,y,z),cq.Vector(1,0,0)))
        hw.pop(f'MAINBOARD_MOUNT_R6_rear_loadwasher_M3_9mm_{i}')
        hw.pop(f'MAINBOARD_MOUNT_R6_rear_M3x6_pan_{i}')
        hw[washer_key]=_one(washer,washer_key)
        hw[screw_key]=_one(merge(
          cq.Solid.makeCone(3.,1.5,1.5,cq.Vector(173.8,y,z),cq.Vector(1,0,0)),
          cylinder(1.45,6.5,(175.3,y,z),(1,0,0))),screw_key)
        service[f'SERVICE_MAINBOARD_R6_rear_screw_{i}_unthread_minusX8']=_sweep(hw[screw_key],(-1,0,0),8)
        service[f'SERVICE_MAINBOARD_R6_rear_tool_{i}_TRAY_OUTSIDE_CASE']=cylinder(3.,40,(173.8,y,z),(-1,0,0))
        flush_joints.append({'mount_index':i,'axis_yz_mm':[y,z],
          'washer':washer_key,'screw':screw_key,'flush_face_x_mm':173.8,
          'custom_steel_washer_OD_mm':9.,'washer_thickness_mm':1.5,
          'washer_bore_mm':3.2,'washer_90deg_countersink_major_D_mm':6.,
          'tray_recess_diameter_mm':11.2,'tray_recess_floor_x_mm':175.3,
          'remaining_tray_bearing_thickness_mm':.9,'radial_adjustment_mm':1.,
          'screw_nominal_length_including_head_mm':8.,'nominal_standoff_engagement_mm':5.1,
          'factory_female_PCB_max_x_mm':173.5572137,'nominal_PCB_face_clearance_mm':.2427863,
          'physical_fit_torque_creep_and_bearing_load_verified':False})
        fabrication.append({'hardware_key':washer_key,'material':'steel load washer',
          'thickness_mm':1.5,'flat_axis':'X','manufacturing_notes':'Custom OD9 / bore3.2 / 90deg D6 countersink; STEP is the authoritative stepped profile. Verify material, tolerances, bearing and clamp load before manufacture.'})
    # Four real tray feet and M3x10/nut references. Root must cut its bottom/top
    # frames at these points; bolts are removed before tray extraction.
    frame_screws=[];frame_nuts=[]
    for j in (1,2):
        for top,z in ((False,5.),(True,242.)):
            x,y=(TOP_FRAME_POINTS if top else FRAME_POINTS)[j-1]
            label='top' if top else 'bottom'
            fy=8 if top else 10
            fy0=y-fy/2; fy1=min(y+fy/2,247.4)
            foot=box((12,fy1-fy0,5),(172,fy0,z))
            foot=foot.cut(cylinder(1.7,6,(x,y,z-.5)))
            nz=243.2 if top else z+1.3
            nt=1.8 if top else 2.4
            foot=foot.cut(box((5.9,fy1-fy0+.2,nt+.4),(x-2.95,fy0-.1,nz-.2)))
            tray=merge(tray,foot)
            nn=f'MAINBOARD_MOUNT_R6_frame_{label}_M3_square_nut_{j}'
            nut=box((5.5,5.5,nt),(x-2.75,y-2.75,nz)).cut(cylinder(1.45,nt+.2,(x,y,nz-.1)))
            hw[nn]=_one(nut,nn);frame_nuts.append(nn)
            if top:
                # Front point Y42 and rear point Y244 avoid top fan Y50..190.
                seat=251.;sgn=-1
            else:
                seat=0.;sgn=1
            sn=f'MAINBOARD_MOUNT_R6_frame_{label}_M3x10_{j}'
            if top:
                # Flush 90deg head: no protrusion into the top fan starting
                # at Z220. Root must countersink its matching upper bridge.
                screw=merge(cylinder(1.45,8.5,(x,y,241)),cq.Solid.makeCone(1.5,3,1.5,cq.Vector(x,y,249.5),cq.Vector(0,0,1)))
            else:
                screw=merge(cylinder(1.45,10,(x,y,seat),(0,0,sgn)),cylinder(2.75,2.4,(x,y,seat),(0,0,-sgn)))
            hw[sn]=screw;frame_screws.append(sn)
            service[f'SERVICE_{sn}_unthread_12mm']=_sweep(screw,(0,0,-sgn),12)
            service[f'SERVICE_{sn}_tool_TOP_FAN_OR_BOTTOM_OPEN']=cylinder(2.75,40,(x,y,seat-2.4 if not top else seat+2.4),(0,0,-sgn))
    parts[TRAY]=_one(tray,TRAY);hw[PCB]=_one(pcb,PCB)

    # Original round copper heatsink: photo outline, overall photographed
    # assembly 25 mm including PCB; no invented cooler clamp/Intel bracket.
    cy,cz=photo_yz(380,618);cr=47.5
    hw['CPU_DS2501_stock_round_copper_25mm_TOTAL_PHOTO_PROXY']=cylinder(cr,23.4,(188.3,cy,cz),(1,0,0))
    reserves['KEEP_DS2501_CPU_40mm_FROM_COMPONENT_FACE_HARD_LIMIT']=cylinder(cr,40,(188.3,cy,cz),(1,0,0))
    # DDR4 laptop modules are staggered planes. Their exact seat height and
    # overlap are not measured; keep compact generic JEDEC-style dimensions.
    for k,(xx,zz) in enumerate(((190.3,79.),(194.3,82.)),1):
        hw[f'RAM_DS2501_DDR4_SODIMM_EXISTING_{k}_PHOTO_PROXY']=box((1.0,67.6,30),(xx,87,zz))
    # Two face M.2 and one rear M.2; lane labels conflict in seller images.
    for k,yy in enumerate((195.,171.5),1):
        hw[f'SSD_DS2501_front_M2_2280_{k}_PHOTO_PROXY']=box((3,22,80),(190.3,yy,89))
    hw['SSD_DS2501_back_M2_2280_3_PHOTO_PROXY']=box((3,22,80),(181.7,188,102))
    hw['CPU_DS2501_back_retention_plate_PHOTO_PROXY']=box((2.5,80,80),(184.2,82.7,120.9))
    reserves['KEEP_DS2501_BACK_M2_SOLDER_SERVICE_UNMEASURED']=box((7,28,86),(179.7,185,99))
    # Photo scaled eight top-entry SATA ports; choose 2 blue native and one
    # rightmost ASM1166 black port. Contacts all face +X in enlarged photo.
    selected=[];sata=[]
    for row,py in enumerate((347.,370.),1):
        for col,px in enumerate((330.,374.,418.,463.),1):
            yy,zz=photo_yz(px,py)
            tag=f'SATA_DS2501_{"native_blue" if col==4 else "ASM1166_black"}_r{row}_c{col}_PHOTO_PROXY'
            hw[tag]=box((8,15.5,7.4),(188.3,yy-7.75,zz-3.7))
            sata.append({'socket':tag,'row':row,'column':col,'center_yz_mm':[yy,zz], 'exit_axis':[1,0,0]})
            if (row,col) in ((1,4),(2,4),(1,3)):
                number={(1,4):1,(2,4):2,(1,3):3}[(row,col)]
                hn=f'SATA_DATA_{number}_MB_DS2501_MATING_HEAD_PROXY'
                heads[hn]=box((20,14.5,6.4),(196.3,yy-7.25,zz-3.2))
                selected.append({'drive':number,'socket':tag,'head':hn,'exit_axis':[1,0,0],
                    'cable_exit_xyz_mm':[216.3,yy,zz], 'socket_bbox_mm':bbox(hw[tag]),'head_bbox_mm':bbox(heads[hn])})
                service[f'SERVICE_{hn}_WITHDRAW_PLUSX15']=_sweep(heads[hn],(1,0,0),15)
    # Main power ports: photo exact pin counts, bodies/plug lengths engineering
    # proxies until actual ENP7660B cable and board sample are checked.
    power=[]
    for kind,y,z,wy,wz,sh,hh in (('ATX24',178.65,48.5,52,9.5,13,24),('ATX4_CPU',219.0,48.5,9.5,9.5,11,20)):
        sn=f'POWER_DS2501_{kind}_SOCKET_PHOTO_PROXY';hn=f'POWER_DS2501_{kind}_MATING_HEAD_PROXY'
        hw[sn]=box((sh,wy,wz),(188.3,y-wy/2,z-wz/2))
        heads[hn]=box((hh,wy,wz),(188.3+sh,y-wy/2,z-wz/2))
        service[f'SERVICE_{hn}_WITHDRAW_PLUSX15']=_sweep(heads[hn],(1,0,0),15)
        power.append({'kind':kind,'socket':sn,'head':hn,'exit_axis':[1,0,0],
            'cable_exit_xyz_mm':[188.3+sh+hh,y,z],'socket_bbox_mm':bbox(hw[sn]),'head_bbox_mm':bbox(heads[hn])})
    # Physical x8-length socket; front end intentionally shown open ONLY as an
    # engineering installation hypothesis. This must not certify x16 insertion.
    slot=box((11,56.8,8.3),(188.3,142.7,204.0))
    cavity=box((11.2,56.3,2.4),(188.2,142.6,207.0)).cut(box((11.4,1.8,2.6),(188.1,184.3,206.9)))
    hw['PCIE_DS2501_PHYSICAL_X8_OPEN_END_UNVERIFIED_PHOTO_PROXY']=_one(slot.cut(cavity),'PCIe socket')
    # Rear I/O individual port envelopes, shortened at rear panel datum Y246.
    for tag,z,sz,sx in (('HDMI_PAIR',64,18,14),('USB3_PAIR',85,16,15),('RJ45_1',119,17,16),('RJ45_2',141,17,16),('USB2_PAIR',158,16,15),('AUDIO_PAIR',180,18,13)):
        hw[f'IO_DS2501_{tag}_PHOTO_PROXY']=box((sx,10,sz),(188.3,236,z))
    all_moving=[TRAY]+[k for k in hw if k not in frame_screws]+list(heads)
    # Heads remain named in metadata as unplug-before-extract, not an assertion
    # that the connected board/tray can be pulled through the side wall.
    meta={
      'board':'DS_2501 Ryzen7 5825U user-owned reference',
      'evidence':{'front_photo':PHOTO,'spec_photo':SPEC_PHOTO,'front_version':'Ver1.2','back_version':'Ver1.3',
        'manufacturer_mechanical_CAD_available':False,'photo_board_px':[88,504,336,746],
        'photo_mapping':'Y=242-(px-88)*170/416; Z=44+(py-336)*170/410; front +X',
        'coordinate_uncertainty_mm':'approximately 1–2; version and perspective errors not measured'},
      'seller_spec_not_independently_certified':{'pcb_mm':[170,170],'overall_with_stock_cooler_mm':25,'CPU':'Ryzen7 5825U,8C16T,15W nominal','memory':'2 DDR4 SODIMM; reuse existing',
        'SATA':'2 native +6 ASM1166, total8','power':'ATX24 plus ATX4 CPU, not EPS8',
        'PCIe':'PCIe3.0 electrically x8; visible physical length ~56.8mm; open-end unconfirmed',
        'M2':'seller table 1xPCIe3x4+2xPCIe3x1; front silk appears x4 on both: conflict unresolved'},
      'pcb_x_mm':list(PCB_X),'pcb_yz_mm':[[72,242],[44,214]],
      'r5_to_r6_transform':'(x,y,z)->(442.3-x,y+12,259-z)',
      'mount':{'standard_source':'analysis/r4-mainboard/reference/dfi-cs100.pdf official DFI reference,not DS2501 mechanical CAD',
        'holes_C_datum_mm':[list(v) for v in HOLES_C],'holes_yz_mm':[list(v) for v in HOLES_YZ],
        'PCB_hole_diameter_mm':3.96,'tray_clearance_diameter_mm':5.4,'radial_adjustment_mm':1,
        'standoff':'M3 F/F 10mm AF5.5 reference,thread teeth not modeled; procurement SKU not locked',
        'tray_x_mm':[173.2,176.2],'nylon_washer_x_mm':[176.2,176.7],'standoff_x_mm':[176.7,186.7],
        'rear_loadwasher_x_mm':[172.7,173.2],'rear_gap_mm':10.5,'rear_M2_reserve_depth_mm':7,
        'lower_flush_joints':flush_joints,
        'female_PCB_rear_face_relief_mm':{'X':[173.1,174.0],'Y':[64,216],'Z':[51.9,54.3]},
        'frame_points_xy_mm':[list(p) for p in FRAME_POINTS],
        'top_frame_points_xy_mm':[list(p) for p in TOP_FRAME_POINTS],
        'frame_required_cuts':{'bottom_through_D_mm':3.4,'bottom_frame_z_mm':[0,5], 'upper_bridge_z_mm':[247,251],
          'top_through_D_mm':3.4,'top_countersink_mm':{'diameter':6,'depth':1.5,'z':[249.5,251]},
          'top_fastener':'M3x10 90deg countersunk,overall including head; top flushZ251',
          'top_square_nut':'DIN562 thin M3,5.5 square x1.8,z243.2..245',
          'bottom_fastener':'M3x10 pan,10mm from under head,head belowZ0',
          'warning':'root must provide matching upper/lower bridge and clearance; these are not floating frame feet'},
        'frame_screws':frame_screws,'frame_nuts':frame_nuts,
        'female_riser_window_mm':{'Y':[84.9,205.3],'Z':[35,68]},'tray_part':TRAY},
      'CPU':{'photo_center_yz_mm':[cy,cz],'photo_outline_diameter_mm':95,'stock_total_assembly_height_mm':25,
        'stock_front_height_mm':23.4,'user_hard_clearance_from_component_face_mm':40,
        'hard_clearance_x_mm':[188.3,228.3],'hard_guard_diameter_mm':95,
        'guard':'reserve,not exact fin/rotor geometry; stock cooler mounting not invented'},
      'PCIe':{'socket':'PCIE_DS2501_PHYSICAL_X8_OPEN_END_UNVERIFIED_PHOTO_PROXY','socket_y_mm':[142.7,199.5],
        'socket_z_mm':[204,212.3],'reference_mating_center_z_mm':208.2,'photo_key_center_y_mm':185.2,
        'key_axis':'short contact segment toward rear +Y/I-O','head_insertion_axis':[-1,0,0],
        'x16_riser_into_x8_socket_accepted':False,'required_fieldgate':'check end wall and full x16 male clearance against round CPU guard before buying/cutting anything'},
      'SATA':{'ports':sata,'selected_ports':sorted(selected,key=lambda v:v['drive']),'direct_to_HDD':True,'backplane':False,
        'axis_evidence':'enlarged photo shows complete L-shaped cavities on component face; +X top entry',
        'head_body_dimensions_engineering_assumption_mm':[20,14.5,6.4],'unplug_before_HDD_draw':True},
      'original_fabrication_parts':fabrication,
      'power':power,'new_parts':list(parts),'new_hardware':list(hw),'new_heads':list(heads),
      'service_names':list(service),'reserve_names':list(reserves),'tray_moving_nodes_after_unplug':all_moving,
      'service_conditions':['Remove right skin and unplug SATA/ATX24/ATX4/PCIe riser/fan/front I-O before tray removal',
        'Remove four frame M3 fasteners before side extraction; complete side extraction sweep remains root integration work',
        'Rear tray screws are serviced after removing tray,not by reaching a driver through GPU'],
      'limits':['All board-specific geometry is seller-photo-scaled reference,not manufacturer CAD or measured sample',
        'PCB hole pattern,connector variants,board version,back SSD/plate heights need user sample verification',
        'CPU 40mm hard reserve is authoritative; photographed 25mm stock proxy does not relax it',
        'Fan connector pin count,front I-O header pinout and RAM/M2 electrical compatibility not certified',
        'No cooler retainer screw/clamp invented from stock Intel115x label; reuse complete original cooler',
        'Mount stiffness,print creep,torque,electrical clearances and thermal/noise acceptance require real assembly']}
    return parts,hw,heads,service,reserves,meta
