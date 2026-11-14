# SPDX-License-Identifier: MIT
"""Bounded ATX/EPS/native-GPU routing corrections; base r6_power untouched.

Named standard-end connectors and installed routes remain explicit geometry.
A shared split source gland and direct underfloor GPU route separate wires
from the PSU intake. Physical wire/fit and full-stock packing gates remain.
"""
from __future__ import annotations
import math
import cadquery as cq
from build import box,cylinder,bbox
from r6_power import _tube


def _apply_shared_factory_exit_channels(m):
    """Model the whole ATX source and a finished-loom lay-in split gland.

    The ATX/GPU insulated looms clear each other, but separate round tube
    walls would overlap. A connected lobed interior removes that internal
    wall physically. GPU is laid in first, then ATX through the upper opening;
    their finished connectors stay outside the gland. The thin moving divider
    guide fills its own release slot and preserves the cold-plenum boundary.
    All source coordinates remain engineering assumptions pending a sample.
    """
    BASE='PSU_R6_isolated_cold_sleeve_and_wire_gutter_BASE'
    ROOF='PSU_R6_fixed_wire_gutter_REMOVABLE_roof'
    AIR='AIR_PSU_R6_front_and_ALL_FACE_cold_sleeve'
    fixed=m['parts'][BASE]
    flat=m['parts'][ROOF].cut(box((50,10,4),(0,4.5,242))).clean()
    roof=flat
    # EPS original split tube and sliding upper guide.
    eo=cylinder(3.75,14,(37,82,218),(0,1,0));ei=cylinder(2.75,18,(37,79,218),(0,1,0))
    ew=eo.cut(ei)
    el=ew.intersect(box((9.5,18,4.75),(32.25,79,213.25)))
    eu=ew.intersect(box((9.5,18,4.75),(32.25,79,218)))
    en=box((2,4.2,23.5),(33.25,80,220)).cut(ei)
    eg=box((7.5,4,27),(33.25,82,218)).cut(ei)
    egs=box((7.5,4,34.5),(33.25,82,218)).cut(ei)
    eu=eu.fuse(eg).clean();fixed=fixed.cut(egs).fuse(el).cut(ei).cut(eu).clean();roof=roof.fuse(eu).fuse(en).clean()
    # ATX and GPU share one vertically connected, lobed channel. With the lid
    # removed both finished looms lay in from above (GPU first, ATX second).
    ao=cylinder(7,10.2,(24,85.8,215),(0,1,0));ai=cylinder(6,18,(24,79,215),(0,1,0))
    go=cylinder(4.75,10.2,(26,85.8,205.5),(0,1,0));gi=cylinder(3.75,18,(26,79,205.5),(0,1,0))
    bridge_outer=box((9.5,10.2,9.5),(21.25,85.8,205.5))
    bridge_inner=box((7.5,12,9.5),(22.25,85,205.5))
    outer=ao.fuse(go).fuse(bridge_outer).clean();inner=ai.fuse(gi).fuse(bridge_inner).clean()
    wall=outer.cut(inner).clean()
    low=wall.intersect(box((30,18,20),(10,79,195)))
    upper=wall.intersect(box((30,18,30),(10,79,215)))
    lower_anchor=box((7,5.8,3),(11,80,212)).cut(inner)
    neck=box((14,1,30),(17,85.8,215)).cut(inner).clean()
    fixed=fixed.cut(box((14,1,37.5),(17,85.8,215))).clean()
    fixed=fixed.fuse(low).fuse(lower_anchor).cut(inner).cut(upper).clean()
    roof=roof.fuse(upper).fuse(neck).clean()
    # Exact continuous +Z7.5 sweep of original roof leading faces, two upper
    # semicircles, their vertical guides and the new ATX neck.
    shift=7.5;sw=flat
    for f in flat.Faces():
        if f.geomType()=='PLANE' and f.normalAt().z>.999999:
            sw=sw.fuse(cq.Solid.extrudeLinear(f.outerWire(),f.innerWires(),cq.Vector(0,0,shift)))
    for x,z,r,y0,ins in ((37,218,3.75,82,ei),(24,215,7,85.8,inner)):
        o=cylinder(r,96-y0,(x,y0,z),(0,1,0))
        cap=o.fuse(o.translate((0,0,shift))).fuse(box((2*r,96-y0,shift),(x-r,y0,z)))
        sw=sw.fuse(cap.intersect(box((2*r+2,18,40),(x-r-1,79,z))).cut(ins))
    for org,size,ins in (((33.25,82,218),(7.5,4,27),ei),((33.25,80,220),(2,4.2,23.5),ei),((17,85.8,215),(14,1,30),inner)):
        sw=sw.fuse(box((size[0],size[1],size[2]+shift),org).cut(ins))
    sw=sw.clean();air0=m['air'][AIR];env=outer.fuse(eo).fuse(neck);air=air0.cut(env).clean()
    m['parts'][BASE]=fixed;m['parts'][ROOF]=roof;m['air'][AIR]=air
    m['parts']['PSU_R6_cold_sleeve_REMOVABLE_roof']=m['parts']['PSU_R6_cold_sleeve_REMOVABLE_roof'].cut(box((14,1,37.5),(17,85.8,215))).clean()
    m['service']['SERVICE_POWER_R8_SHARED_WIRE_ROOF_plusZ7p5']=sw
    cold_roof='PSU_R6_cold_sleeve_REMOVABLE_roof'
    cold_cap=m['parts'][cold_roof]
    for label,shape in ((BASE,fixed),(ROOF,roof),(cold_roof,cold_cap)):
        if not shape.isValid() or len(shape.Solids())!=1:
            raise ValueError(label+' must remain one attached valid solid')
    overlaps={'fixed_vs_wire_roof':fixed.intersect(roof).Volume(),
      'wire_vs_cold_roof':roof.intersect(cold_cap).Volume()}
    if any(volume>1e-4 for volume in overlaps.values()):
        raise ValueError('Shared source-gland parts overlap')
    if not air.isValid() or len(air.Solids())!=1:
        raise ValueError('Shared source gland must preserve one cold-air region')
    removed_air=air0.Volume()-air.Volume()
    exact_air=air0.intersect(env).Volume()
    if abs(removed_air-exact_air)>1e-4:
        raise ValueError('Air change exceeds physical gland outer envelope/guide')
    if not sw.isValid():
        raise ValueError('Invalid continuous shared-gland roof sweep')
    samples=23
    if any(roof.translate((0,0,shift*i/(samples-1))).cut(sw).Volume()>1e-4
           for i in range(samples)):
        raise ValueError('Continuous shared-gland sweep misses a roof pose')
    # The shared interior contains the complete vertical GPU lay-in capsule.
    # Its upper end fits the ATX opening: 6-(2+3.25)=0.75mm radial allowance.
    gpu_lift=cylinder(3.25,10.2,(26,85.8,205.5),(0,1,0))
    gpu_lift=gpu_lift.fuse(gpu_lift.translate((0,0,9.5))).fuse(
      box((6.5,10.2,9.5),(22.75,85.8,205.5))).clean()
    lay_in_outside=gpu_lift.cut(inner).Volume()
    if lay_in_outside>1e-4:
        raise ValueError('GPU loom cannot pass through the shared upper opening')
    service_key='SERVICE_POWER_R8_SHARED_WIRE_ROOF_plusZ7p5'
    service={'sweep_key':service_key,'translation_mm':[0,0,shift],
      'method':'Exact continuous leading-face and upper-semicircle construction',
      'pose_containment_samples':samples,
      'removed_parts_for_access':['TOP_R6_lid','SKIN_R6_left','top_fan_body','FRAME_R6_top'],
      'remove_bolts_and_captured_nuts':[
        'PSU_R6_WIRE_COVER_M3x8_9','PSU_R6_WIRE_COVER_M3x8_10',
        'PSU_R6_WIRE_COVER_DIN562_M3_9','PSU_R6_WIRE_COVER_DIN562_M3_10',
        'PSU_R6_TOP_M3x10_CSK_1','PSU_R6_TOP_M3x10_CSK_2',
        'PSU_R6_TOP_DIN562_M3_1','PSU_R6_TOP_DIN562_M3_2',
        'MAINBOARD_MOUNT_R6_frame_top_M3x10_1','MAINBOARD_MOUNT_R6_frame_top_M3x10_2',
        'MAINBOARD_MOUNT_R6_frame_top_M3_square_nut_1','MAINBOARD_MOUNT_R6_frame_top_M3_square_nut_2'],
      'remove_access_fastener_prefixes':['TOP_R6_lid_','PANEL_R6_left_'],
      'top_frame_may_remain_for_opening':False,
      'temporary_support_required':'Support PSU/mainboard; release GPU anchor and control leads before top-frame removal.',
      'assembly_order':'Lay finished GPU loom first in shared lower opening, then ATX, and EPS in its independent opening; fit one shared roof. Never thread finished connectors through bores.',
      'service_order':'AC off; support PSU/mainboard; remove access panels and top-frame attachments; remove top frame and two wire-roof fastener/nut pairs; lift roof +Z7.5. Lift ATX loom before GPU from shared opening.',
      'whole_top_frame_extraction_verified':False,
      'clip_strength_and_seal_verified':False,
      'opens_without_PSU_disassembly_or_cable_cutting':True}
    shared={'part':BASE,'removable_half_part':ROOF,
      'modified_cold_roof_part':cold_roof,'service':service,
      'channel_type':'Connected ATX/GPU lobed lay-in gland; separate EPS split bore',
      'shared_split_plane_Z_mm':215.,'channel_Y_mm':[85.8,96.],
      'ATX_bore_inner_outer_diameter_mm':[12.,14.],
      'GPU_bore_inner_outer_diameter_mm':[7.5,9.5],
      'vertical_connected_throat_inner_outer_width_mm':[7.5,9.5],
      'vertical_connected_throat_Z_mm':[205.5,215.],
      'nominal_wall_thickness_mm':1.,
      'ATX_nominal_radial_wire_clearance_mm':.5,
      'GPU_nominal_radial_wire_clearance_mm':.5,
      'actual_ATX_wire_to_channel_wall_distance_mm':m['wires']['CABLE_R6_ATX_FACTORY300'].distance(wall),
      'actual_GPU_wire_to_channel_wall_distance_mm':m['wires']['CABLE_R6_GPU_FACTORY300'].distance(wall),
      'GPU_lay_in_sweep_outside_shared_inner_mm3':lay_in_outside,
      'GPU_lay_in_upper_opening_allowance_mm':.75,
      'common_outer_cross_section_area_mm2':outer.intersect(box((50,1,50),(0,90,190))).Volume(),
      'common_inner_cross_section_area_mm2':inner.intersect(box((50,1,50),(0,90,190))).Volume(),
      'factory_face_reference_area_mm2':81.5*40.5,
      'divider_guide_nominal_origin_mm':[17.,85.8,215.],
      'divider_guide_nominal_size_mm':[14.,1.,30.],
      'cold_roof_front_notch_width_depth_mm':[14.,.8],
      'protected_air_removed_mm3':removed_air,
      'exact_physical_envelope_and_guide_air_overlap_mm3':exact_air,
      'divider_guide_air_overlap_mm3':air0.intersect(neck).Volume(),
      'air_change_scope':'Exact physical shared/EPS channel outer envelopes and roof-carried divider guide only; no cable shape excluded.',
      'attached_single_solid':True,'removable_roof_single_solid':True,
      'fixed_moving_parts_overlap_mm3':0.,
      'source_exit_coordinates_status':'Engineering XYZ only, not measured manufacturer wire-exit positions.',
      'thermal_or_physical_acceptance_completed':False}
    transitions={}
    for label,point,gland,key in (
      ('ATX',[24.,96.,215.],[24.,82.,215.],'CABLE_R6_ATX_FACTORY300'),
      ('GPU',[26.,96.,205.5],[26.,82.,205.5],'CABLE_R6_GPU_FACTORY300')):
        record=dict(shared,source_face_point_engineering_xyz_mm=point,
          native_gland_point_engineering_xyz_mm=gland,
          complete_source_segment_modeled=True,
          factory_face_transition_geometry_verified=True,
          source_coordinates_received_hardware_verified=False,
          wire_proxy_diameter_mm=m['power_meta']['routes'][key]['engineering_diameter_mm'])
        transitions[label]=record
        m['psu_meta'][label+'_isolated_factory_exit_transition']=record
    eps={'part':BASE,'removable_half_part':ROOF,'service':service,
      'centerline_xyz_mm':[[37.,82.,218.],[37.,96.,218.]],
      'outer_diameter_mm':7.5,'inner_diameter_mm':5.5,
      'wire_proxy_diameter_mm':4.5,'nominal_radial_clearance_mm':.5,
      'minimum_wire_to_wall_distance_mm':m['wires']['CABLE_R6_EPS_FACTORY300'].distance(ew.fuse(en)),
      'factory_face_reference_area_mm2':81.5*40.5,
      'isolated_outer_envelope_projected_area_mm2':math.pi*3.75**2,
      'cold_air_face_area_fraction_displaced':math.pi*3.75**2/(81.5*40.5),
      'source_exit_coordinates_status':'Engineering XYZ only; factory exit requires measurement.',
      'attached_single_solid':True,'removable_roof_single_solid':True,
      'fixed_moving_parts_overlap_mm3':0.,
      'complete_source_segment_modeled':True,
      'thermal_or_physical_acceptance_completed':False}
    transitions['EPS']=eps
    m['psu_meta']['EPS_isolated_factory_exit_transition']=eps
    m['psu_meta']['ATX_GPU_shared_factory_exit_gland']=shared
    return transitions

def apply_atx_refine(m):
    p=m['power_meta'];heads=m['heads'];wires=m['wires']
    changed_wires=[];changed_heads=[];checks=[];newroutes={}
    removed_wires=[];removed_heads=[]

    def replace(key,points,d,R,nominal=None):
        shape,L=_tube(points,d,R)
        wires[key]=shape;changed_wires.append(key)
        info={'keys':[key],'vertices_mm':[list(v) for v in points],
          'modeled_centerline_mm':L,'engineering_diameter_mm':d,
          'engineering_bend_R_mm':R,
          'full_length_installed_and_flex_verified':False}
        if nominal is not None:
            info.update(nominal_stock_mm=nominal,unmodeled_surplus_mm=nominal-L,
              surplus_insulated_material_mm3=max(0.,nominal-L)*math.pi*(d/2)**2)
        else:info['same_extension_terminal_branch_not_additional_stock']=True
        p['routes'][key]=info;newroutes[key]=info
        if nominal is not None and L>nominal+1e-4:checks.append({'route':key,'kind':'stock_length_short','required_mm':L,'available_mm':nominal})

    # Rotate the standard ATX pair toward the front. The native lead arrives
    # from the rear between the DATA2/3 heads; the extension exits directly
    # toward the front floor, without crossing through either connector.
    k='CABLE_R6_ATX_FACTORY300'
    replace(k,[[24,96,215],[24,82,215],[28.5,60,215],[24.5,60,202],[24.5,60,184.5],
      [24.5,74.5,184.5],[60,74.5,184.5],[60,74.5,172],[60,45.5,172]],11,6,300)
    for key,origin in (
      ('POWER_R6_ATX_FACTORY24_STANDARD_MALE_PROXY',(34,33.5,165)),
      ('POWER_R6_ATX_EXT24_STANDARD_FEMALE_PROXY',(34,21.5,165))):
        heads[key]=box((52,12,14),origin);changed_heads.append(key)
    a=next(v['cable_exit_xyz_mm'] for v in m['mainboard_meta']['power'] if v['kind']=='ATX24')
    replace('CABLE_R6_ATX_PHANTEKS_PH_CB24P_BK500',[[60,21.5,172],[60,8,172],
      [193,8,174.5],[220,20,110],[241,80,38],
      [241,118,38],[241,144,48.5],[241,a[1],a[2]],a],11,6,500)

    # The original 300mm factory lead now ends beside the PSU, not across the
    # chassis. Include the previously omitted faceY96-to-glandY82 transition.
    # Rise outside the GPU inlet, then enter the vertical 4pin pair from below.
    replace('CABLE_R6_EPS_FACTORY300',[[37,96,218],[37,78,218],[37,42,218],
      [22.5,42,218],[22.5,42,162],[98,24.75,162],
      [98,24.75,188],[108.55,24.75,188],[108.55,24.75,193.5]],4.5,4,300)
    for key,origin in (
      ('POWER_R6_GPU_FACTORY_UNUSED_SECOND6plus2_PARKED_PROXY',(106,110,198)),):
        old=heads[key].BoundingBox()
        heads[key]=box((old.xlen,old.ylen,old.zlen),origin)
        changed_heads.append(key)
    # One original4pin half mates with a standard4pin female extension. The
    # unused factory4pin half remains counted/parked; the new4pin extension has
    # no second4pin branch. No PSU modification or private pinout is involved.
    active='POWER_R6_EPS_FACTORY4plus4_STANDARD_PROXY'
    heads[active]=box((9.5,9.5,12),(103.8,20,193.5));changed_heads.append(active)
    female='POWER_R8_EPS_MODDIY_4PIN_FEMALE_PROXY'
    heads[female]=box((9.5,9.5,12),(103.8,20,205.5));changed_heads.append(female)
    for key in ('POWER_R6_EPS_EXT4plus4_STANDARD_PROXY',
                'POWER_R6_EPS_EXTENSION_UNUSED4_HALF_PARKED_PROXY'):
        heads.pop(key,None);removed_heads.append(key)
    for key in ('CABLE_R6_EPS_AK_CBPW08_40BK400',
                'CABLE_R6_EPS_UNUSED4_HALF_BRANCH_PROXY'):
        wires.pop(key,None);p['routes'].pop(key,None)
        changed_wires.append(key);removed_wires.append(key)
    e=next(v['cable_exit_xyz_mm'] for v in m['mainboard_meta']['power'] if v['kind']=='ATX4_CPU')
    extension='CABLE_R8_EPS_MODDIY_CO581_600'
    replace(extension,[[108.55,24.75,217.5],[108.55,24.75,225],
      [123,24.75,225],[123,9.8,225],[180,9.8,206],[215,9.8,206],
      [237,39,204],[243.8,39,195],[243.8,80,115],[243.8,e[1],e[2]],e],6.5,7,600)
    p['extensions']['EPS']='MODDIY CO581 configured60cm standard4pinmotherboardextension'
    p['standard_EPS_coupling_heads']=[active,female]
    p['EPS_native_half_plan']='Oneoriginal4pinhalf-to-standard4pinextension;retainunusedfactory4pinhalf.NoPSUinternalpinoutmodification.'
    eps_source='https://www.moddiy.com/products/2256/Premium-Custom-PSU-Extension-Cable-4-Pin-CPU-EPS-Power.html'
    budgets={}
    for key,connector_allowance,slack in (
      ('CABLE_R6_EPS_FACTORY300',24.,15.),(extension,48.,15.)):
        info=p['routes'][key];required=info['modeled_centerline_mm']+connector_allowance+slack
        budget={'modeled_complete_centerline_mm':info['modeled_centerline_mm'],
          'connector_allowance_mm':connector_allowance,'assembly_slack_mm':slack,
          'required_with_allowances_mm':required,'nominal_stock_mm':info['nominal_stock_mm'],
          'remaining_length_margin_mm':info['nominal_stock_mm']-required,
          'geometric_length_budget_passed':required<=info['nominal_stock_mm'],
          'factory_measurement_origin_and_installed_flex_verified':False,
          'connector_allowance_is_engineering_assumption':True}
        budgets[key]=budget;info['complete_length_budget']=budget
        if required>info['nominal_stock_mm']:
            checks.append({'route':key,'kind':'complete_stock_length_short',
              'required_mm':required,'available_mm':info['nominal_stock_mm']})
    p['EPS_complete_length_budgets']=budgets
    p['native_factory_exit_points_engineering']={'ATX':[24,96,215],'EPS':[37,96,218]}

    # Native GPU coupling stays left of the entire GPU lifting column. Both
    # original factory branches remain installed while the card is removed.
    gpu_native='POWER_R6_GPU_FACTORY6plus2_STANDARD_PROXY'
    heads[gpu_native]=box((14,18,18),(106,62,193.5));changed_heads.append(gpu_native)
    replace('CABLE_R6_GPU_FACTORY300',[[26, 96, 205.5], [26, 82, 205.5], [35, 73, 205.5], [35, 64, 190], [120, 64, 190], [109.5, 88, 190], [109.5, 88, 202.5], [109.5, 80, 202.5]],6.5,6,300)
    replace('CABLE_R6_GPU_FACTORY_SECOND150',[[116.5, 80, 202.5], [116.5, 96, 202.5], [116.5, 96, 190], [113, 119, 190], [113, 119, 198]],6.5,6,150)
    joint=p['GPU_factory_joint']
    joint.update(bbox_mm=bbox(heads[gpu_native]),nose_axis=[0,-1,0],root_extension_mating_plane_Y_mm=62.)
    joint.pop('root_extension_mating_plane_Z_mm',None)

    # One physical shared ATX/GPU channel keeps original engineering source
    # coordinates and opens for finished looms; EPS retains its separate bore.
    transitions=_apply_shared_factory_exit_channels(m)
    sleeve=transitions['EPS'];gpu_sleeve=transitions['GPU'];atx_sleeve=transitions['ATX']
    base=sleeve['part'];air_key='AIR_PSU_R6_front_and_ALL_FACE_cold_sleeve'

    # Direct Z190 underfloor route replaces the long front arch. The intact
    # cold-plenum floor now separates the loom from air; no arch air is cut.
    arch_meta={'active':False,'retired_in':'R8',
      'replacement':'Direct underfloor Z190 route; original lead remains left of GPU lift column.'}
    m['psu_meta']['GPU_factory_bottom_open_arch']=arch_meta
    ears=[]
    for x in (50.,90.):
        for y in (57.5,68.):
            ear=box((6,2.5,7),(x-3,y,190)).cut(box((4,3.5,2),(x-2,y-.5,192.5)))
            m['parts'][base]=m['parts'][base].fuse(ear).clean();ears.append(ear)
    m['psu_meta']['GPU_underfloor_retention']={'part':base,
      'wire_center_Z_mm':190.,'wire_center_Y_mm':64.,'wire_diameter_mm':6.5,
      'strap_pair_centers_X_mm':[50.,90.],
      'ear_bboxes_mm':[bbox(ear) for ear in ears],
      'nominal_lateral_wire_to_ear_gap_mm':.75,
      'installed_straps_and_strain_relief_verified':False,
      'retained_during_GPU_extraction':True}

    # Finished looms enter from the open left edge of the wire-bay floor.
    # These slots are outside the cold plenum and do not cut the GPU arch.
    floor_edges=[]
    for label,origin,size in (
      ('EPS',(10.5,39.25,195.3),(14.75,5.5,1.8)),
      ('ATX',(14.,54.,195.3),(16.5,12.,1.8)),
      ('GPU',(10.5,59.,195.3),(29.,18.,1.8))):
        opening=box(size,origin)
        air_overlap=m['air'][air_key].intersect(opening).Volume()
        if air_overlap>1e-4:
            raise ValueError('Wire-bay open edges must preserve protected cold air')
        before=m['parts'][base].Volume()
        m['parts'][base]=m['parts'][base].cut(opening).clean()
        floor_edges.append({'loom':label,'origin_mm':list(origin),'size_mm':list(size),
          'actual_material_removed_mm3':before-m['parts'][base].Volume(),
          'protected_air_removed_mm3':air_overlap})
    if not m['parts'][base].isValid() or len(m['parts'][base].Solids())!=1:
        raise ValueError('Open-edge wire-bay floor must remain one attached solid')
    m['psu_meta']['wire_bay_floor_open_edges']={'part':base,'openings':floor_edges,
      'assembly':'Layfinishedloomsfromopenleftedge;donotthreadconnectorsthroughsmallclosedholes.',
      'part_single_solid':True,'physical_fit_strength_and_insulation_verified':False}
    if not m['air'][air_key].isValid() or len(m['air'][air_key].Solids())!=1:
        raise ValueError('Final PSU cold air must remain one connected valid domain')
    m['psu_meta']['final_cold_air_domain']={'connected_regions':1,
      'volume_mm3':m['air'][air_key].Volume(),'thermal_or_physical_acceptance_completed':False}

    info=p['routes']['CABLE_R6_GPU_FACTORY300'];required=info['modeled_centerline_mm']+24+15
    gpu_budget={'modeled_complete_centerline_mm':info['modeled_centerline_mm'],
      'connector_allowance_mm':24.,'assembly_slack_mm':15.,
      'required_with_allowances_mm':required,'nominal_stock_mm':300,
      'remaining_length_margin_mm':300-required,'geometric_length_budget_passed':required<=300,
      'factory_measurement_origin_and_installed_flex_verified':False,
      'connector_allowance_is_engineering_assumption':True}
    info['complete_length_budget']=gpu_budget;p['GPU_complete_length_budget']=gpu_budget
    p['native_factory_exit_points_engineering']['GPU']=[26,96,205.5]
    if required>300:checks.append({'route':'CABLE_R6_GPU_FACTORY300','kind':'complete_stock_length_short','required_mm':required,'available_mm':300})

    complete_budgets={**budgets,'CABLE_R6_GPU_FACTORY300':gpu_budget}
    # ATX now includes the explicit PSU face-to-gland segment in its actual
    # curved centerline. No second unmodeled length allowance is added.
    atx_factory='CABLE_R6_ATX_FACTORY300'
    for key,head_allowance,head_lower_bound,exit_allowance in (
      ('CABLE_R6_ATX_FACTORY300',24.,12.,0.),
      ('CABLE_R6_ATX_PHANTEKS_PH_CB24P_BK500',40.,36.,0.),
      ('CABLE_R6_GPU_FACTORY_SECOND150',24.,18.,0.)):
        info=p['routes'][key]
        required=info['modeled_centerline_mm']+head_allowance+15.+exit_allowance
        budget={'modeled_complete_centerline_mm':info['modeled_centerline_mm'],
          'modeled_connector_length_lower_bound_mm':head_lower_bound,
          'connector_allowance_mm':head_allowance,'assembly_slack_mm':15.,
          'unmodeled_factory_face_transition_length_allowance_mm':exit_allowance,
          'required_with_allowances_mm':required,'nominal_stock_mm':info['nominal_stock_mm'],
          'remaining_length_margin_mm':info['nominal_stock_mm']-required,
          'geometric_length_budget_passed':required<=info['nominal_stock_mm'],
          'factory_measurement_origin_and_installed_flex_verified':False,
          'connector_allowance_is_engineering_assumption':True}
        if key==atx_factory:
            budget.update(factory_face_transition_geometry_verified=True,
              complete_source_segment_modeled=True,
              source_face_point_engineering_xyz_mm=[24.,96.,215.],
              source_coordinates_received_hardware_verified=False,
              scope='Complete CAD source segment included; factory exit dimensions still require received-hardware measurement.')
        complete_budgets[key]=budget;info['complete_length_budget']=budget
        if required>info['nominal_stock_mm']:
            checks.append({'route':key,'kind':'complete_stock_length_short',
              'required_mm':required,'available_mm':info['nominal_stock_mm']})
    p['complete_stock_length_budgets']=complete_budgets

    p['exact_same_net_junction_spheres']=[]
    p['native_gland_exit_points_engineering'].update(ATX=[24,82,215],EPS=[37,82,218],GPU=[26,85.8,205.5])
    p['checks']=[v for v in p.get('checks',[]) if v.get('route') not in changed_wires]+checks
    # Recompute the changed stock surplus without erasing the unmodeled lengths.
    packing=p['surplus_packing'];per=[]
    for key,v in p['routes'].items():
        if 'unmodeled_surplus_mm' in v:
            per.append({'route':key,'surplus_mm':v['unmodeled_surplus_mm'],
              'insulated_material_volume_mm3':v['surplus_insulated_material_mm3']})
    packing['per_route']=per
    material=sum(v['insulated_material_volume_mm3'] for v in per)+750*math.pi*2.75**2+300*math.pi*2.25**2
    packing['total_insulated_material_minimum_mm3']=material
    packing['minimum_with_factor_mm3']=2*material
    packing['packing_accepted']=False
    meta={'changed_wire_keys':changed_wires,'changed_head_keys':changed_heads,
      'removed_wire_keys':removed_wires,'removed_head_keys':removed_heads,
      'routes':newroutes,'checks':checks,'exact_same_net_junction_spheres':[],
      'EPS_standard_extension':{'SKU':'MODDIY CO581','nominal_length_mm':600,
        'source_url':eps_source,'connector':'4pinmotherboardfemale-to-4pinmotherboardmale',
        'stock_availability_confirmed':False,'not_PSU_proprietary_modular_cable':True},
      'EPS_complete_length_budgets':budgets,'EPS_isolated_factory_exit_transition':sleeve,
      'GPU_complete_length_budget':gpu_budget,'GPU_isolated_factory_exit_transition':gpu_sleeve,
      'ATX_isolated_factory_exit_transition':atx_sleeve,
      'GPU_factory_bottom_open_arch':arch_meta,
      'complete_stock_length_budgets':complete_budgets,
      'gland_y_status':'All ATX/EPS/GPU face-to-gland segments are modeled; face Y96 source XYZ remain engineering assumptions pending received hardware.',
      'SATA_coordination':'SATArefine owns all SATA shapes; native GPU route is below the PSU floor at Z190/Y64; EPS low crossing is Z162.',
      'EPS_joint_bbox_mm':{k:bbox(heads[k]) for k in changed_heads},
      'GPU_factory_standard_joint':p['GPU_factory_joint'],
      'limits':['OriginalEPS4+4 halfseparation,keyed4pinextensionfitandreceived-cablelengthrequirephysicalverification;no PSUinternalpinout changes.',
        'Round sections and bend radii are engineering envelopes,not manufacturer cable exterior CAD.',
        'Nominalcenterline/slack alone does not certify factory total usable wire length or packed surplus.',
        'No EPSsame-netforkcollisionallowance remains;the4pinextension has no unused4pinbranch.']}
    m['atx_refine_meta']=meta
    return meta
