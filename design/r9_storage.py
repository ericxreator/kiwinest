# SPDX-License-Identifier: MIT
"""R9 front-fed three-HDD bank; independent native-mount front service.

Original geometry in millimetres. HDDs and connectors are engineering reference
envelopes; airflow volumes are protected passages, not thermal simulation.
"""
from __future__ import annotations
import itertools
import math
import cadquery as cq
from build import box, cylinder, merge, bbox
from r4_drive_mount import native_screw_x, screw_z
from r6_storage import _one, _square_nut, _frame_flat_screw, _lock_tool, _forward_projection
from r6_frame import pan, nut4, csk

DRIVE_X=(7.4,40.5,73.6)
BODY_Y=60.; BODY_Z=12.; BODY_TOP=113.85; BODY_REAR=207.
FRAME_POINTS=((7.,51.),(101.,51.),(7.,215.),(101.,215.))
GAPS=((2.4,7.4),(33.5,40.5),(66.6,73.6),(99.7,104.7))
HDD_SOURCE='https://www.seagate.com/files/www-content/product-content/ironwolf/en-us/docs/100844482f.pdf'
FAN_SOURCE='https://www.noctua.at/en/products/nf-a9-pwm/specifications'


def _withdraw(size,origin,travel=15.):
    return box((size[0],size[1]+travel,size[2]),origin)


def build_storage():
    """Return parts, hardware, heads, air, service, metadata for root assembly."""
    p={};h={};heads={};air={};sv={}
    meta={
      'revision':'R9_FOUR_PASSAGE_FRONT_FORCED_AIR',
      'reference_sku':'ST8000VN004','source_url':HDD_SOURCE,
      'body_size_mm':[26.1,147.,101.85],'body_x_min_mm':list(DRIVE_X),
      'body_y_mm':[60.,207.],'body_z_mm':[12.,113.85],
      'body_gap_mm':7.,'outer_gap_mm':[5.,5.],
      'orientation':'R8 reference rotated -90deg around X; PCB/native mount face -X; SATA mates toward +Y',
      'native_mount_surface':'PCB/bottom broad face -X; four native6-32, no backplane',
      'native_pattern_mm':{'hole_y_mm':[89.525,165.725],'hole_z_mm':[15.3,110.55]},
      'native_fastener':{'reference':'McMaster99926A106','url':'https://www.mcmaster.com/99926A106/',
        'thread':'6-32UNC','length_including_head_mm':6.35,'head_diameter_mm':7.7978,
        'head_height_mm':1.6764,'countersink_degrees':100,'driver_AF_mm':1.984375,
        'carrier_mount_wall_mm':2.8,'spacer_mm':.8,'penetration_mm':2.75,
        'manufacturer_max_penetration_mm':3.56,'manufacturer_max_torque_in_lb':6},
      'native_mounts':[],'moving_parts':{},'moving_hardware':{},
      'fan_wire_exit_xyz_mm':[11.5,28.,106.],
      'front_lock_hardware':{},'service':{},'connectors':{},
      'frame_attachment':{'points_xy_mm':[list(v) for v in FRAME_POINTS],
        'cage_bottom_z_mm':5.,'screw':'M3x8 90deg flathead reference,seatZ8.4',
        'root_bottom_frame_through_holes_diameter_mm':3.4,
        'root_square_nut_pockets':{'size_mm':[5.9,5.9,2.6],'z_mm':[1.1,3.7]},
        'nut_z_mm':[1.2,3.6],'bottom_frame_assumed_z_mm':[0,5],
        'note':'R9 frame must provide bearing beams at Y46..56 and211..221 plus matching holes; no suspended joints'},
      'fan':{'model':'Noctua NF-A9 PWM','source_url':FAN_SOURCE,
        'nominal_size_mm':[92,92,25],'with_antivibration_pads_mm':[93,93,27],
        'engineering_proxy_bbox_mm':[[11.5,16.5,14.5],[104.5,43.5,107.5]],
        'bare_frame_bbox_mm':[[12,17.5,15],[104,42.5,107]],
        'axis':[0,1,0],'center_xz_mm':[58.,61.],
        'hole_pitch_mm':82.5,'power_max_W':1.2,'current_max_A':.1,
        'stock_lead_mm':200.,'included_NA_EC1_mm':300.,
        'published_max_airflow_m3_h':78.9,'published_max_static_pressure_mmH2O':2.28,
        'fan_curve_and_installed_flow_verified':False,
        'proxy_includes_pad_extent_but_not_exact_molded_shape':True},
      'airflow':{'physical_gap_widths_mm':[5.,7.,7.,5.],
        'continuous_height_z_mm':[22.,104.],'continuous_height_mm':82.,
        'unobstructed_main_gap_area_mm2':1968.,
        'protected_core_edge_clearance_mm':.2,
        'mount_bands_z_mm':[[10.3,20.3],[105.55,115.55]],
        'rear_data_head_top_mm':93.85,
        'rear_under_roof_header_z_mm':[95.6,103.8],
        'rear_collector_y_mm':[207.,233.6],
        'chimney_inner_bbox_mm':[[47.,208.2,105.4],[104.7,233.6,192.7]],
        'top_diffuser_inner_bbox_mm':[[47.2,135.,192.5],[104.7,233.6,222.5]],
        'forced_flow_sequence':['front grille','NF-A9 axial +Y','sealed distribution plenum',
          'four independent passages between HDD broad faces','rear header above SATA heads',
          'upward chimney right of vertical PSU','root top exhaust connection'],
        'sealing':'front mask seals projected drive fronts; removable plenum; four gap floors/ceilings; left skin and0.3mm right sheet form side boundaries',
        'root_interfaces':['left skin must be solid Y42..236/Z20.8..135.2',
          'front panel must expose fan inlet R43 at X58/Z61 and permit removable fan module',
          'no packing basket/hub/power/data cable inside independent protected HDD air',
          'final top fan center146.55/125, R96 frame opening and R94 conservative rotor disk; diffuser outlet meets inlet side atZ223'],
        'thermal_test_completed':False,'CFD_completed':False,
        'flow_split_pressure_drop_dust_and_noise_verified':False},
      'own_fabrication_parts':{},'checks':[],
      'limits':['Printed mount strength/creep/vibration and sheet retention untested',
        'HDD model is dimensional reference; actual drive dimensions/power/SMART temperature require sample validation',
        'Connector heads are engineering proxies, not certified mating geometry',
        'Protected passages prove space only, not equal airflow or acceptable HDD temperature',
        'Root must route and retain complete power/data stock outside protected passages',
        'Final retained-geometry assembly checks remain root integration gate']}

    # Low fixed bearings: the moving soles stay under each drive footprint.
    cage_bits=[box((102.6,13,4.4),(2.4,46,5)),box((102.6,10,4.4),(2.4,211,5))]
    for x in DRIVE_X:
        for xx in (x+1.,x+22.7):
            cage_bits.append(box((2.4,165.,4.8),(xx,55,5)))
    cage=merge(*cage_bits)
    for i,x in enumerate(DRIVE_X,1):
        cx=x+13.05;ylock=55.
        # Upper/lower rails leave the entire Z22..104 broad-face passage clear.
        # Front vertical member is inside the projected disk thickness at Y<60.
        bones=[box((2.8,119.,10.),(x-3.6,55,z)) for z in (10.3,105.55)]
        bones += [box((7.6,3.,10.),(x-3.6,55,z)) for z in (10.3,105.55)]
        bones += [box((3.,3.,105.25),(x+1.,55,10.3))]
        bones += [box((2.4,156.,2.2),(xx,55,9.8)) for xx in (x+1.,x+22.7)]
        bones += [box((24.1,6.,3.2),(x+1.,53,9.8))]
        # Flush tongues close the manifold's rear-open service slots. They
        # travel with this carrier and permit removing the common front mask.
        bones += [box((7.6,5.,5.8),(x-3.6,55,14.5)),box((3.,5.,1.2),(x+1.,55,104.))]
        carrier=merge(*bones)
        body=box((26.1,147.,101.85),(x,60,12))
        carrier=carrier.cut(cylinder(1.7,5,(cx,ylock,9)))
        carrier=carrier.cut(cq.Solid.makeCone(3.2,1.7,1.5,cq.Vector(cx,ylock,13),cq.Vector(0,0,-1)))
        cage=cage.cut(cylinder(1.7,8,(cx,ylock,4.9)))
        cage=cage.cut(box((5.9,11.95,2.6),(cx-2.95,46,5.5)))
        lock=f'R9_STORAGE_LOCK_{i}_M3x8_CSK';nut=f'R9_STORAGE_LOCK_{i}_M3_square'
        h[lock]=_frame_flat_screw(cx,ylock).translate((0,0,4.6));h[nut]=_square_nut(cx,ylock,5.6)
        meta['front_lock_hardware'][str(i)]=[lock]
        native=[]
        for j,(y,z) in enumerate(itertools.product((89.525,165.725),(15.3,110.55)),1):
            body=body.cut(cylinder(1.8,3.56,(x,y,z),(1,0,0)))
            carrier=carrier.cut(cylinder(1.9,3.,(x-3.7,y,z),(1,0,0)))
            hh=(4.02-1.9)/math.tan(math.radians(50))
            carrier=carrier.cut(cq.Solid.makeCone(4.02,1.9,hh,cq.Vector(x-3.6,y,z),cq.Vector(1,0,0)))
            sn=f'R9_STORAGE_NATIVE_{i}_6_32_{j}';sp=f'R9_STORAGE_NATIVE_{i}_spacer08_{j}'
            h[sn]=native_screw_x(x-3.6,y,z)
            h[sp]=_one(cylinder(3,.8,(x-.8,y,z),(1,0,0)).cut(cylinder(1.9,.8,(x-.8,y,z),(1,0,0))),sp)
            native += [sn,sp]
            meta['native_mounts'].append({'drive':i,'axis':[1,0,0],'hole_center':[x,y,z],
              'screw':sn,'spacer':sp,'penetration_mm':2.75,'max_penetration_mm':3.56})
        pn=f'R9_STORAGE_TRAY_{i}_native4_edge_bands';dn=f'R9_drive_{i}'
        p[pn]=_one(carrier,pn);h[dn]=_one(body,dn)
        meta['moving_parts'][str(i)]=[pn];meta['moving_hardware'][str(i)]=[dn]+native
        tool=f'SERVICE_R9_STORAGE_{i}_front_lock_Lkey_60deg';sv[tool]=_lock_tool(cx,ylock)
        draw=f'SERVICE_R9_STORAGE_{i}_front_draw_300'
        sv[draw]=_forward_projection([h[dn]]+bones+[h[n] for n in native])
        connectors=[]
        # Exact rigid rotation of the R8 head proxy: old +Z becomes new +Y.
        for kind,zc,size in (('data',84.85,(10.,18.,18.)),('power',51.85,(12.,20.,28.))):
            hx=x+.138*25.4;origin=(hx-size[0]/2,207.,zc-size[2]/2)
            hn=f'R9_SATA_{kind}_{i}_HDD_HEAD_ENGINEERING_PROXY';heads[hn]=box(size,origin)
            sw=f'SERVICE_R9_SATA_{kind}_{i}_withdraw_plusY15';park=f'SERVICE_R9_SATA_{kind}_{i}_PARKED_after_plusY15'
            sv[sw]=_withdraw(size,origin);sv[park]=heads[hn].translate((0,15,0))
            meta['connectors'][hn]={'drive':i,'kind':kind,'origin_mm':list(origin),'size_mm':list(size),
              'withdrawal_axis':[0,1,0],'withdrawal_mm':15.,'withdrawal_service':sw,'parked_head_service':park,
              'exit_xyz_mm':[hx,207.+size[1],zc],'axis':[0,1,0],
              'status':'ENGINEERING_HEAD_ENVELOPE_NOT_CERTIFIED_CONNECTOR_CAD'}
            connectors.append(hn)
        meta['service'][str(i)]={'front_draw':draw,'tool':tool,'connectors':connectors,
          'remove_before_draw':[lock],
          'prerequisites':['power_down_wait_spindown','remove_front_skin','remove_complete_front_fan_plenum_module',
            'unplug_only_target_data_power_plusY15','restrain_target_loose_heads_and_wire_outside_draw',
            'remove_front_left_lower_post_for_drive1_only','remove_target_rear_connector_hatch'],
          'retained':'other2HDD/native hardware/duct floors and ceilings/GPU/MB/PSU/front-left upper post/hub/stock basket; own native hardware moves with target',
          'front_left_lower_post_required':i==1,
          'parking_limit':'rigid heads only; flexible attached route and target parking depend on root integration'}
    for j,(x,y) in enumerate(FRAME_POINTS,1):
        cage=cage.cut(cylinder(1.7,5,(x,y,4.9))).cut(cylinder(3.2,1.1,(x,y,8.4)))
        cage=cage.cut(cq.Solid.makeCone(3.2,1.7,1.5,cq.Vector(x,y,8.4),cq.Vector(0,0,-1)))
        h[f'R9_STORAGE_FRAME_M3x8_flat_{j}']=_frame_flat_screw(x,y)
        h[f'R9_STORAGE_FRAME_M3_square_{j}']=_square_nut(x,y,1.2)
    cage_key='R9_STORAGE_COMMON_CAGE_low_bearings';p[cage_key]=_one(cage,cage_key)

    # Rear-supported four-channel comb. No vertical member crosses a gap inlet.
    # Above the heads, air rises through the open former body columns between
    # the roof fingers; the low header joins all four passages before rising.
    duct_bits=[box((102.3,1.2,114.4),(2.4,233.6,20.8)),
      box((102.3,26.6,1.2),(2.4,207,94.4)),
      box((43.4,26.6,1.2),(2.4,207,134)),
      box((57.7,1.2,85.9),(47.,207,105.4)),
      box((1.2,26.6,57.3),(45.8,207.,134.))]
    for lo,hi in GAPS:
        duct_bits += [box((hi-lo,173.6,1.2),(lo,60,20.8)),box((hi-lo,173.6,1.2),(lo,60,104.))]
    # Join the rear wall to the chimney upstand without blocking the interior.
    duct_bits.append(box((58.9,1.2,88.5),(45.8,233.6,134.)))
    # Forward-spreading top diffuser, entirely above the GPU fixed lead.
    # Its floor stops at the rear chimney mouth; the roof closes only the
    # area outside the conservative R94 rotor disk, so there is a large outlet.
    duct_bits += [box((59.,73.2,1.2),(46.,135.,191.3)),
      box((1.2,101.,31.2),(46.,133.8,191.3)),
      box((59.,1.2,31.2),(46.,133.8,191.3))]
    # Lower the non-rotor roof below the left-rear M4x35 tip219.6/nut219.8.
    # A real annular collar rises to the fan rim instead of hiding either
    # fastener inside the protected diffuser air.
    cover=box((59.,101.,1.4),(46.,133.8,217.2)).cut(cylinder(94.,1.6,(146.55,125.,217.1)))
    duct_bits.append(cover)
    collar=cylinder(97.2,3.9,(146.55,125.,218.6)).cut(cylinder(96.,4.1,(146.55,125.,218.5)))
    collar=collar.intersect(box((59.,101.,3.9),(46.,133.8,218.6)))
    duct_bits.append(collar)
    duct_key='R9_HDD_rear_collector_and_four_passage_comb';p[duct_key]=_one(merge(*duct_bits),duct_key)
    # Six independently removable shutters preserve the normal complete
    # looms. Each shallow panel releases its open cable key, rises in the
    # rear service layer, then leaves through one clear common corridor.
    meta['rear_connector_hatches']={}
    for i,x in enumerate(DRIVE_X,1):
        hx=x+.138*25.4;cx=x+13.25;shutters={};slot_seals=[]
        seal=f'R9_HDD_HATCH_{i}_REMOVABLE_SLOT_FOAM_SEAL'
        for kind,z0,z1,zz,cz in (('power',37.5,66.2,51.85,61.5),
                                  ('data',75.5,94.2,84.85,89.5)):
            height=z1-z0
            hole=box((19.3,1.4,height),(x-2.8,233.5,z0))
            p[duct_key]=p[duct_key].cut(hole)
            # Start beyond the complete power head's X+ face. The tab
            # joins the fixed right jamb and retains its own square nut.
            tab=box((8.,3.3,8.),(x+10.,230.3,cz-4.))
            p[duct_key]=p[duct_key].fuse(tab)
            pocket=box((5.9,2.6,5.9),(cx-2.95,230.2,cz-2.95))
            p[duct_key]=p[duct_key].cut(pocket).cut(cylinder(1.7,6,(cx,229.7,cz),(0,1,0)))
            countersink=cq.Solid.makeCone(3.1,1.6,1.5,cq.Vector(cx,234.8,cz),cq.Vector(0,-1,0))
            p[duct_key]=p[duct_key].cut(countersink)
            hatch=f'R9_HDD_rear_connector_hatch_{i}_{kind}'
            shape=box((19.3,1.2,height),(x-2.8,233.6,z0)).cut(cylinder(1.7,1.4,(cx,233.5,cz),(0,1,0)))
            # The finished plug never threads through a closed hole. The
            # removable slot foam and split annulus release this one key.
            slot=box((hx-(x-2.8),1.2,6.5),(x-2.8,233.6,zz-3.25))
            bore=cylinder(3.25,1.4,(hx,233.5,zz),(0,1,0))
            shape=shape.cut(slot.fuse(bore)).cut(countersink);slot_seals.append(slot.cut(bore))
            p[hatch]=_one(shape,hatch)
            bn=f'R9_HDD_HATCH_{i}_{kind}_M3x6_CSK';nn=f'R9_HDD_HATCH_{i}_{kind}_M3_square'
            h[bn]=csk(6.,(cx,234.8,cz),(0,-1,0),3)
            h[nn]=box((5.5,2.4,5.5),(cx-2.75,230.3,cz-2.75)).cut(cylinder(1.6,2.6,(cx,230.2,cz),(0,1,0)))
            prefix=f'SERVICE_R9_HDD_rear_hatch_{i}_{kind}'
            lift=prefix+'_release_plusY1p5';shift=prefix+'_release_plusX10_afterY1p5'
            rise=prefix+'_raise_minZ90_afterY1p5_X10'
            align=prefix+'_align_leftX66p8_after_raise'
            draw=prefix+'_draw_plusY50_after_raise_align'
            # Fill only the removed screw bore before the exact +Y sweep.
            moving=box((19.3,1.2,height),(x-2.8,233.6,z0)).cut(slot.fuse(bore)).clean()
            bits=[moving]
            for face in cq.Workplane('XY').newObject([moving]).faces('>Y').vals():
                if face.geomType()!='PLANE':raise ValueError('Shutter requires a planar leading face')
                bits.append(cq.Solid.extrudeLinear(face.outerWire(),face.innerWires(),cq.Vector(0,1.5,0)))
            sv[lift]=cq.Compound.makeCompound(bits)
            shifted=moving.translate((0,1.5,0))
            sv[shift]=cq.Compound.makeCompound([shifted,box((10.,1.2,height),(x+16.5,235.1,z0))])
            # Once the key is clear, conservative full material boxes cover
            # every intermediate rigid pose, including the cable-key void.
            startx=x+7.2;dz=90.-z0;dx=66.8-startx
            sv[rise]=box((19.3,1.2,height+dz),(startx,235.1,z0))
            sv[align]=box((19.3+abs(dx),1.2,height),(min(startx,66.8),235.1,90.))
            sv[draw]=box((19.3,51.2,height),(66.8,235.1,90.))
            stages=[lift,shift,rise,align,draw]
            sweep=prefix+'_STAGED_removal';sv[sweep]=cq.Compound.makeCompound([sv[n] for n in stages])
            shutters[kind]={'part':hatch,'bolt':bn,'nut':nn,'sweep_key':sweep,
              'staged_service_keys':stages,'stages_mm':[[0,1.5,0],[10,0,0],[0,0,dz],[dx,0,0],[0,50,0]],
              'body_z_mm':[z0,z1],'fastener':'M3x6 90deg CSK, length including head',
              'countersink_depth_mm':1.5,'countersink_continues_into_fixed_tab_mm':.3,'normal_wire_slot_center_xz_mm':[hx,zz],
              'slot_seal_solid_index':0 if kind=='power' else 1,
              'root_annulus_index':2*i-1 if kind=='power' else 2*i,
              'remove_before_motion':[hatch,bn],
              'remove_target_slot_foam_and_annulus_before_motion':True,
              'all_other_shutters_and_complete_normal_wires_remain_installed':True,
              'common_extraction_corridor_x_mm':[66.8,86.1],'common_extraction_min_z_mm':90.,
              'sweep_proxy_scope':'Exact keyed profile +Y; exact monotone-key +X domain; conservative full material boxes after key release'}
        h[seal]=cq.Compound.makeCompound(slot_seals)
        for kind,info in shutters.items():
            other=f'CHECK_R9_HDD_HATCH_{i}_{kind}_OTHER_SLOT_FOAM_RETAINED'
            sv[other]=slot_seals[1-info['slot_seal_solid_index']]
            info['retained_other_slot_foam_service']=other
        meta['own_fabrication_parts'][seal]={'material':'split insulating silicone foam engineering candidate',
          'thickness_mm':1.2,'flat_axis':'Y','function':'two separately removable strips close power/data shutter keys outside split wire annuli',
          'remove_before_hatch_motion':True,'compression_and_leakage_verified':False}
        parts=[v['part'] for v in shutters.values()];bolts=[v['bolt'] for v in shutters.values()];nuts=[v['nut'] for v in shutters.values()]
        combined=f'SERVICE_R9_HDD_rear_connector_hatch_{i}_STAGED_removal'
        allstages=[n for v in shutters.values() for n in v['staged_service_keys']]
        sv[combined]=cq.Compound.makeCompound([sv[n] for n in allstages])
        meta['rear_connector_hatches'][str(i)]={'parts':parts,'bolts':bolts,'nuts':nuts,'shutters':shutters,
          'part':parts[0],'bolt':bolts[0],'nut':nuts[0],'sweep_key':combined,
          'slot_seal':seal,'staged_service_keys':allstages,
          'wire_slot_centers_xz_mm':[[hx,51.85],[hx,84.85]],'wire_slot_width_mm':6.5,
          'remove_before_head_withdrawal':parts+bolts+[seal],
          'prerequisites':['remove_back_skin','remove only target shutter slot foam and split wire annulus',
            'remove only target shutter M3x6','move one shutter at a time; other five remain installed'],
          'finished_connector_threading_required':False,
          'retained':'all other drive shutters, fixed nuts, complete normal heads and wires during shutter motion',
          'perimeter_air_seal_physical_acceptance':False}
    p[duct_key]=_one(p[duct_key],duct_key)
    # Two positive duct-to-cage joints below the protected passage floor.
    # Native edge bands endY174 and the soles are farther to each side, so
    # these small feet do not intercept any independent forward disk draw.
    # Keeping all metal atZ<=22/Y<=210 also clears root rear cable galleries.
    meta['duct_cage_joints']=[]
    for j,cx in enumerate((37.,70.1),1):
        post=box((5.8,6.,11.6),(cx-2.9,204.,10.4))
        boss=box((8.,11.,5.4),(cx-4,204.,5.))
        pocket=box((5.9,6.05,2.6),(cx-2.95,203.9,6.4))
        post=post.cut(cylinder(1.7,11.8,(cx,207.,10.3)))
        post=post.cut(cq.Solid.makeCone(3.2,1.7,1.5,cq.Vector(cx,207.,22.),cq.Vector(0,0,-1)))
        boss=boss.cut(pocket).cut(cylinder(1.7,5.6,(cx,207.,4.9)))
        p[duct_key]=_one(p[duct_key].fuse(post),duct_key)
        p[duct_key]=p[duct_key].cut(cylinder(1.7,1.4,(cx,207.,20.7)))
        p[duct_key]=_one(p[duct_key].cut(cq.Solid.makeCone(3.2,1.7,1.5,cq.Vector(cx,207.,22.),cq.Vector(0,0,-1))),duct_key)
        p[cage_key]=_one(p[cage_key].fuse(boss),cage_key)
        bn=f'R9_HDD_DUCT_mount_M3x16_CSK_{j}';nn=f'R9_HDD_DUCT_mount_M3_square_{j}'
        h[bn]=csk(16.,(cx,207.,22.),(0,0,-1),3)
        h[nn]=_square_nut(cx,207.,6.5)
        meta['duct_cage_joints'].append({'bolt':bn,'nut':nn,'axis':[0,0,-1],
          'screw_seat_xyz_mm':[cx,207.,22.],'nut_z_mm':[6.5,8.9],
          'nominal_thread_beyond_nut_mm':.5,
          'assembly_before_drives_installation':True,
          'load_vibration_creep_and_torque_acceptance':False})
    # A 0.3mm sheet is explicit fabrication, not a fictitious printed thin wall.
    sheet='R9_HDD_right_boundary_03mm_PC_SHEET'
    h[sheet]=box((.3,174.8,114.4),(104.7,60,20.8))
    sheet_top='R9_HDD_chimney_right_boundary_03mm_PC_SHEET'
    h[sheet_top]=merge(box((.3,26.6,87.3),(104.7,208.2,135.2)),
      box((.3,73.2,31.2),(104.7,135.,191.3)))
    # The sheet ends at the printed diffuser's inner right boundary. Cut its
    # exact occupied seat from the print, retaining a face-contact interface.
    p[duct_key]=_one(p[duct_key].cut(h[sheet_top]),duct_key)
    meta['own_fabrication_parts'][sheet]={'material':'0.3mm PC sheet engineering candidate','thickness_mm':.3,
      'flat_size_mm':[174.8,114.4],'retention':'captured by front plenum/rear collector; stiffness and perimeter seal pending'}
    meta['own_fabrication_parts'][sheet_top]={'material':'0.3mm PC sheet engineering candidate','thickness_mm':.3,
      'flat_outline':'L shape,26.6x87.3 rear rise plus73.2x31.2 forward wing',
      'retention':'captured chimney/diffuser edge; stiffness and seal pending'}
    seal='R9_HDD_TOP_DIFFUSER_05mm_FOAM_EDGE_SEAL'
    # Only the frame-facing circular arc is gasketed. The inner straight
    # outlet edge meets the shared fan inlet, not a fictitious solid rotor
    # face. The enclosed diffuser roof already closes the other regions.
    foam_arc=cylinder(97.2,.5,(146.55,125.,222.5)).cut(cylinder(96.,.7,(146.55,125.,222.4)))
    h[seal]=foam_arc.intersect(box((59.,101.,.5),(46.,133.8,222.5))).clean()
    meta['own_fabrication_parts'][seal]={'material':'0.5mm closed-cell foam engineering candidate',
      'thickness_mm':.5,'function':'circular edge seal on R96 frame opening only; inner outlet edge remains open to shared fan inlet',
      'compression_and_air_leakage_verified':False}

    # Removable fan/plenum: four slit mask matches only the real gap mouths.
    face=box((102.6,1.2,92.5),(2.4,43.5,14.5)).cut(cylinder(43,1.4,(58,43.4,61),(0,1,0)))
    mask=box((102.6,1.2,89.5),(2.4,58.8,15.7))
    for lo,hi in GAPS:mask=mask.cut(box((hi-lo,1.4,82.),(lo,58.7,22.)))
    plenum=merge(face,mask,box((102.6,16.5,1.2),(2.4,43.5,14.5)),
      box((102.6,15.3,1.2),(2.4,43.5,104.)),box((.3,16.5,90.7),(104.7,43.5,14.5)))
    for x in DRIVE_X:
        plenum=plenum.cut(box((3.,5.1,91.),(x+1.,55.,14.4)))
        plenum=plenum.cut(box((7.6,5.1,5.9),(x-3.6,55.,14.4)))
    fan=box((93.,27.,93.),(11.5,16.5,14.5))
    fan_mounts=[]
    for j,(x,z) in enumerate(itertools.product((16.75,99.25),(19.75,102.25)),1):
        hole=cylinder(2.4,36,(x,15.5,z),(0,1,0));fan=fan.cut(hole);plenum=plenum.cut(hole)
        bolt=f'R9_HDD_FAN_M4x35_{j}';nut=f'R9_HDD_FAN_M4_hex_{j}'
        h[bolt]=pan(35,(x,16.5,z),(0,1,0),4)
        h[nut]=nut4(0,0,0).rotate((0,0,0),(1,0,0),-90).translate((x,44.9,z))
        # Pockets retain the nut through the upper/lower plenum lip.
        plenum=plenum.cut(h[nut].scale(1.025).translate((-.025*x,-.025*44.9,-.025*z)))
        fan_mounts += [bolt,nut]
    fan_key='R9_HDD_NF_A9_PWM_WITH_PADS_ENGINEERING_PROXY';h[fan_key]=_one(fan,fan_key)
    plenum_key='R9_HDD_removable_front_fan_distribution_plenum';p[plenum_key]=_one(plenum,plenum_key)
    # Two M3 joints tie the removable plenum to the low cage/front mask.
    # They sit inside masked body columns and below all airflow passages.
    module_nodes=[fan_key,plenum_key]+fan_mounts
    for j,x in enumerate((25.5,82.5),1):
        tab=box((10.,8.5,6.3),(x-5,43.5,9.4))
        p[plenum_key]=_one(p[plenum_key].fuse(tab),plenum_key)
        p[plenum_key]=p[plenum_key].cut(cylinder(1.7,7,(x,49,8.9))).clean()
        p[cage_key]=p[cage_key].cut(cylinder(1.7,5,(x,49,4.9))).cut(box((5.9,5.9,2.6),(x-2.95,46.05,5.5))).clean()
        bn=f'R9_HDD_PLENUM_M3x10_{j}';nn=f'R9_HDD_PLENUM_M3_square_{j}'
        h[bn]=screw_z(10,(x,49,15.7));h[nn]=_square_nut(x,49,5.6)
        module_nodes += [bn]
    meta['front_fan_module_nodes']=module_nodes
    meta['front_fan_attached_route_keys']=['PWM_R9_HDD_factory200']
    meta['front_fan_module_fixed_nuts']=[f'R9_HDD_PLENUM_M3_square_{j}' for j in (1,2)]
    module_sweep='SERVICE_R9_HDD_front_fan_plenum_STAGED_removal'
    # Fan first shifts right of the fixed corner column, then leaves forward.
    # Removing the plenum separately permits a6mm release from the carrier
    # slots before its own rightward shift. The hub/front column stay in place.
    fan_shift='SERVICE_R9_HDD_fan_shift_plusX3'
    fan_draw='SERVICE_R9_HDD_fan_draw_minusY100_afterX3'
    sv[fan_shift]=box((96.,27.,93.),(11.5,16.5,14.5))
    sv[fan_draw]=box((93.,127.,93.),(14.5,-83.5,14.5))
    # Y-facing material projections retain all rear-open carrier-spine slots.
    projections=[p[plenum_key]]
    for face in p[plenum_key].Faces():
        if face.geomType()=='PLANE' and abs(face.normalAt().y)>.999:
            projections.append(cq.Solid.extrudeLinear(face.outerWire(),face.innerWires(),cq.Vector(0,-6,0)))
    nut_keys=[n for n in fan_mounts if '_hex_' in n]
    projections += [_forward_projection([h[n] for n in nut_keys],6)]
    release='SERVICE_R9_HDD_plenum_release_minusY6';sv[release]=cq.Compound.makeCompound(projections)
    shift='SERVICE_R9_HDD_plenum_shift_plusX12p1_afterY6'
    draw='SERVICE_R9_HDD_plenum_draw_minusY100_afterY6_X12p1'
    # Component boxes are conservative here. All low tabs already endY46;
    # all other material staysZ>=14.5, above the retained tray locking lips.
    shift_bits=[box((114.7,16.5,92.5),(2.4,37.5,14.5))]
    draw_bits=[box((102.6,116.5,92.5),(14.5,-62.5,14.5))]
    for x in (25.5,82.5):
        shift_bits.append(box((22.1,8.5,6.3),(x-5,37.5,9.4)))
        draw_bits.append(box((10.,108.5,6.3),(x+7.1,-62.5,9.4)))
    sv[shift]=cq.Compound.makeCompound(shift_bits);sv[draw]=cq.Compound.makeCompound(draw_bits)
    stage_keys=[fan_shift,fan_draw,release,shift,draw]
    sv[module_sweep]=cq.Compound.makeCompound([sv[n] for n in stage_keys])
    meta['front_fan_service']={'sweep_key':module_sweep,'staged_service_keys':stage_keys,
      'fan_stages_mm':[[3,0,0],[0,-100,0]],'plenum_stages_mm':[[0,-6,0],[12.1,0,0],[0,-100,0]],
      'removed_nodes':module_nodes,'fan_first_stage_retained_keys':[plenum_key]+nut_keys,
      'prerequisites':['power_down','remove_front_skin','unplug_front_fan_PWM',
        'remove_four_fan_M4x35','shift_and_remove_fan_first','remove_two_plenum_M3x10'],
      'retain':'all3HDDs and native mounts/front corner column/NA-FH1/GPU/MB/PSU; fan removed before moving plenum',
      'flexible_lead_motion_and_hand_access_physically_verified':False}

    # Protect actual designed passages without carving arbitrary obstacles out.
    air['AIR_R9_HDD_front_inlet']=cylinder(42.8,14.1,(58,2.4,61),(0,1,0))
    air['AIR_R9_HDD_fan_rotor']=cylinder(42.8,27.,(58,16.5,61),(0,1,0))
    air['AIR_R9_HDD_plenum_round_outlet']=cylinder(42.8,8.5,(58,43.5,61),(0,1,0))
    air['AIR_R9_HDD_plenum_common']=box((101.9,3.1,81.6),(2.6,51.7,22.2))
    for j,(lo,hi) in enumerate(GAPS,1):
        air[f'AIR_R9_HDD_passage_{j}']=box((hi-lo-.4,152.2,81.6),(lo+.2,54.8,22.2))
    air['AIR_R9_HDD_rear_low_header']=box((101.9,26.6,8.2),(2.6,207,95.6))
    for j,x in enumerate(DRIVE_X,1):
        air[f'AIR_R9_HDD_rear_rise_{j}']=box((25.7,25.2,38.2),(x+.2,208.2,95.6))
    air['AIR_R9_HDD_rear_upper_header']=box((101.9,25.2,28.4),(2.6,208.2,105.4))
    air['AIR_R9_HDD_chimney']=box((57.3,25.2,87.6),(47.2,208.2,105.4))
    air['AIR_R9_HDD_top_diffuser']=box((57.1,98.2,24.5),(47.4,135.2,192.7))
    mouth=box((57.1,98.2,5.8),(47.4,135.2,217.2)).intersect(cylinder(93.8,5.8,(146.55,125.,217.2)))
    air['AIR_R9_HDD_top_rotor_mouth']=mouth
    physical_mouth=box((57.5,98.6,1.),(47.2,135.,217.2)).intersect(cylinder(94.,1.,(146.55,125.,217.2)))
    # A scalar lower bound from a separate private supplier-frame projection
    # proof. No supplier surface, projected polygon or BRep enters this model.
    # The R94 throat itself is original circle/rectangle geometry.
    clear_lower_bound=2192.5090661881513
    meta['airflow']['top_rotor_mouth_gross_area_mm2']=physical_mouth.Volume()
    meta['airflow']['top_rotor_mouth_net_area_mm2']=clear_lower_bound
    meta['airflow']['top_rotor_mouth_minimum_area_mm2']=1968.
    meta['airflow']['top_outlet_projection_proof']={
      'source':'Noctua NF-A20_Public-CAD.stp, fixed frame solid0 only; dynamic rotor blades excluded',
      'source_sha256':'4dba51c63094d461351024ba1314afb87714d43e6bee220bdab2d93a21563498',
      'nominal_frame_opening_radius_mm':96.,'conservative_rotor_disk_radius_mm':94.,
      'mouth_rectangle_xy_mm':[[47.2,135.],[104.7,233.6]],
      'frame_tessellation_linear_deflection_mm':.05,'frame_tessellation_angular_deflection_radians':.1,
      'projected_frame_expansion_mm':.1,
      'inscribed_throat_polygon_gross_area_mm2':2620.2738580731975,
      'conservatively_projected_stationary_frame_obstruction_mm2':427.76479188504686,
      'net_clear_area_lower_bound_mm2':clear_lower_bound,
      'derived_supplier_geometry_published':False,'installed_airflow_or_pressure_drop_verified':False}
    meta['airflow']['top_fixed_fastener_requirement']='M4x35 seat254.6 tip219.6; nut219.8..223; outside lowered cover217.2..218.6, nominal tip clearance1.0mm'
    meta['airflow']['top_outlet_seal_scope']='Circular R96 frame arc only; inner outlet edge opens into the shared top-fan inlet. No gasket is assumed to touch rotating blades.'
    if physical_mouth.Volume()<clear_lower_bound or clear_lower_bound<1968.:
        raise ValueError('HDD diffuser clear mouth below full four-channel area')
    meta['protected_air_keys']=list(air)
    network=merge(*air.values())
    meta['airflow']['protected_network_valid']=network.isValid()
    meta['airflow']['protected_network_solid_count']=len(network.Solids())
    meta['airflow']['protected_network_volume_mm3']=network.Volume()
    if not network.isValid() or len(network.Solids())!=1:
        raise ValueError('Independent HDD airflow network must be one connected valid solid')
    meta['air_obstacle_exclusions']={'AIR_R9_HDD_fan_rotor':[fan_key]}
    meta['fixed_parts']=[cage_key,duct_key]
    meta['fixed_hardware']=[n for n in h if n.startswith(('R9_STORAGE_FRAME_','R9_HDD_DUCT_mount_')) or '_M3_square' in n]+[sheet,sheet_top]
    for info in meta['service'].values():info['remove_before_draw'] += module_nodes
    meta['part_count']=len(p);meta['hardware_count']=len(h);meta['head_count']=len(heads);meta['service_count']=len(sv)
    return p,h,heads,air,sv,meta
