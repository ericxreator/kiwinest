# SPDX-License-Identifier: MIT
"""Bounded ATX/EPS/native-GPU routing corrections; base r6_power untouched.

Named standard-end connectors and installed routes remain explicit geometry.
Split source transitions and a bottom-open GPU arch separate wires from the
PSU intake without removing cable shapes. Physical wire/fit gates remain.
"""
from __future__ import annotations
import math
import cadquery as cq
from build import box,cylinder,bbox
from r6_power import _tube


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
    replace(k,[[24,82,215],[28.5,60,215],[24.5,60,202],[24.5,60,184.5],
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
      [22.5,42,218],[22.5,42,162],[22.5,24.75,162],[98,24.75,162],
      [98,24.75,188],[108.55,24.75,188],[108.55,24.75,193.5]],4.5,4,300)
    for key,origin in (
      ('POWER_R6_GPU_FACTORY_UNUSED_SECOND6plus2_PARKED_PROXY',(178,42,130)),):
        old=heads[key].BoundingBox()
        heads[key]=box((old.xlen,old.ylen,old.zlen),origin)
        changed_heads.append(key)
    # One original4pin half mates with a standard4pin female extension. The
    # unused factory4pin half remains counted/parked; the new4pin extension has
    # no second4pin branch. No PSU modification or private pinout is involved.
    active='POWER_R6_EPS_FACTORY4plus4_STANDARD_PROXY'
    heads[active]=box((9.5,9.5,12),(103.8,20,193.5));changed_heads.append(active)
    female='POWER_R7_EPS_PHANTEKS_4PIN_FEMALE_PROXY'
    heads[female]=box((9.5,9.5,12),(103.8,20,205.5));changed_heads.append(female)
    for key in ('POWER_R6_EPS_EXT4plus4_STANDARD_PROXY',
                'POWER_R6_EPS_EXTENSION_UNUSED4_HALF_PARKED_PROXY'):
        heads.pop(key,None);removed_heads.append(key)
    for key in ('CABLE_R6_EPS_AK_CBPW08_40BK400',
                'CABLE_R6_EPS_UNUSED4_HALF_BRANCH_PROXY'):
        wires.pop(key,None);p['routes'].pop(key,None)
        changed_wires.append(key);removed_wires.append(key)
    e=next(v['cable_exit_xyz_mm'] for v in m['mainboard_meta']['power'] if v['kind']=='ATX4_CPU')
    extension='CABLE_R7_EPS_PHANTEKS_PH_CB4P_BK500'
    replace(extension,[[108.55,24.75,217.5],[108.55,24.75,225],
      [123,24.75,225],[123,9.8,225],[180,9.8,206],[215,9.8,206],
      [237,39,204],[243.8,39,195],[243.8,80,115],[243.8,e[1],e[2]],e],6.5,7,500)
    p['extensions']['EPS']='PhanteksPH-CB4P_BK500mm,standard4pinmotherboardextension'
    p['standard_EPS_coupling_heads']=[active,female]
    p['EPS_native_half_plan']='Oneoriginal4pinhalf-to-standard4pinextension;retainunusedfactory4pinhalf.NoPSUinternalpinoutmodification.'
    eps_source='https://phanteks.com.tw/Extension-Cables.html'
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
    p['native_factory_exit_points_engineering']={'EPS':[37,96,218]}

    # Pass above the HDD heads and GPU front brace, then turn down into the
    # forward-facing standard coupling. The GPU card and fixed anchor stay put.
    gpu_native='POWER_R6_GPU_FACTORY6plus2_STANDARD_PROXY'
    heads[gpu_native]=box((14,18,18),(182,24.2,167));changed_heads.append(gpu_native)
    replace('CABLE_R6_GPU_FACTORY300',[[26,96,205.5],[26,82,205.5],
      [35,73,205.5],[35,73,193],[35,16,193],[112,16,193],
      [126,13.5,193],[176.5,13.5,193],[185.5,18,193],
      [185.5,18,176],[185.5,24.2,176]],6.5,6,300)
    replace('CABLE_R6_GPU_FACTORY_SECOND150',[[192.5,24.2,176],[192.5,18,176],[192.5,18,120],
      [185,51,120],[185,51,130]],6.5,6,150)
    joint=p['GPU_factory_joint']
    joint.update(bbox_mm=bbox(heads[gpu_native]),nose_axis=[0,1,0],root_extension_mating_plane_Y_mm=42.2)
    joint.pop('root_extension_mating_plane_Z_mm',None)

    # Separate, physically modeled factory-wire transitions. Each lower half
    # joins the fixed gutter, and each upper half joins the existing bolted
    # roof. Finished connectors are laid into open channels, never threaded
    # through undersized closed bores. Port XYZ remains an engineering fit-up.
    base='PSU_R6_isolated_cold_sleeve_and_wire_gutter_BASE'
    roof_key='PSU_R6_fixed_wire_gutter_REMOVABLE_roof'
    air_key='AIR_PSU_R6_front_and_ALL_FACE_cold_sleeve'
    fixed=m['parts'][base]
    flat=m['parts'][roof_key].cut(box((50,10,4),(0,4.5,242))).clean()
    roof=flat
    transitions={}
    components=[]
    port_specs=(
      ('EPS',37.,218.,3.75,2.75,82.,'CABLE_R6_EPS_FACTORY300',
       (33.25,80.,220.,2.,4.2,23.5)),
      ('GPU',26.,205.5,4.75,3.75,85.8,'CABLE_R6_GPU_FACTORY300',
       (31.,81.5,206.5,2.,1.8,37.)),
    )
    outer_envelopes=[]
    for label,x,z,ro,ri,y0,key,neck_box in port_specs:
        outer=cylinder(ro,96-y0,(x,y0,z),(0,1,0))
        inner=cylinder(ri,18,(x,79,z),(0,1,0))
        wall=outer.cut(inner).clean()
        lower=wall.intersect(box((2*ro+2,18,ro+1),(x-ro-1,79,z-ro-1))).clean()
        upper=wall.intersect(box((2*ro+2,18,ro+1),(x-ro-1,79,z))).clean()
        nx,ny,nz,nw,nd,nh=neck_box
        neck=box((nw,nd,nh),(nx,ny,nz)).cut(inner).clean()
        if label=='EPS':
            # A roof-carried divider lip fills its own vertical release slot.
            # This is a physical sliding joint, not a collision exemption. Its
            # whole width stays inside the existing wire bay/partition atY<=86.
            guide=box((7.5,4,27),(33.25,82,218)).cut(inner)
            guide_sweep=box((7.5,4,34.5),(33.25,82,218)).cut(inner)
            fixed=fixed.cut(guide_sweep)
            upper=upper.fuse(guide).clean()
            components.append(('neck',guide,(33.25,82,218,7.5,4,27,inner)))
        if label=='GPU':
            # Both small bridges stay beforeY86, inside the wire-only bay.
            # The neck is right of the retained ATX loom; the pipe itself
            # starts after that loom's outer end cap, avoiding service contact.
            support=box((14.75,5.8,2),(26,80,199.75))
            fixed=fixed.fuse(support)
            bridge=box((3,2.5,1.5),(30,83.3,206.5))
            upper=upper.fuse(bridge).clean()
            components.append(('bridge',bridge,None))
        # Seat the removable upper wall in the existing partition instead of
        # overlapping that partition. The lower wall remains the fixed support.
        fixed=fixed.fuse(lower).cut(inner).cut(upper).clean()
        roof=roof.fuse(upper).fuse(neck).clean()
        components.extend([('upper',outer,(x,z,ro,inner,y0)),('neck',neck,(nx,ny,nz,nw,nd,nh,inner))])
        outer_envelopes.append(outer)
        transitions[label]={'part':base,'removable_half_part':roof_key,
          'centerline_xyz_mm':[[x,y0,z],[x,96,z]],
          'outer_diameter_mm':2*ro,'inner_diameter_mm':2*ri,
          'wire_proxy_diameter_mm':p['routes'][key]['engineering_diameter_mm'],
          'nominal_radial_clearance_mm':ri-p['routes'][key]['engineering_diameter_mm']/2,
          'minimum_wire_to_wall_distance_mm':wires[key].distance(wall.fuse(neck)),
          'factory_face_reference_area_mm2':81.5*40.5,
          'wall_material_projected_area_mm2':math.pi*(ro**2-ri**2),
          'wall_material_fraction_of_reference_face':math.pi*(ro**2-ri**2)/(81.5*40.5),
          'isolated_outer_envelope_projected_area_mm2':math.pi*ro**2,
          'cold_air_face_area_fraction_displaced':math.pi*ro**2/(81.5*40.5),
          'source_exit_coordinates_status':'EngineeringXYZassumption;measurefactorywireexitbeforemanufacture.',
          'thermal_or_physical_acceptance_completed':False}
    if any(not q.isValid() or len(q.Solids())!=1 for q in (fixed,roof)):
        raise ValueError('Both split-wire-channel components must be attached single solids')
    if fixed.intersect(roof).Volume()>1e-4:
        raise ValueError('Fixed and removable wire-channel halves overlap')
    m['parts'][base]=fixed;m['parts'][roof_key]=roof
    # Exact continuous+Z translation: upper semicircular shells become an
    # upward capsule clipped above their centers, minus the original inner
    # circles. Every remaining neck/bridge lies above its void's upper branch.
    # Extruding the flat roof's actual leading planar face preserves its holes.
    shift=7.5
    flat_sweep=flat
    for face in flat.Faces():
        if face.geomType()=='PLANE' and face.normalAt().z>.999999:
            prism=cq.Solid.extrudeLinear(face.outerWire(),face.innerWires(),cq.Vector(0,0,shift))
            flat_sweep=flat_sweep.fuse(prism)
    sweep=flat_sweep
    for kind,shape,data in components:
        if kind=='upper':
            x,z,ro,inner,y0=data
            capsule=shape.fuse(shape.translate((0,0,shift))).fuse(
              box((2*ro,96-y0,shift),(x-ro,y0,z)))
            swept=capsule.intersect(box((2*ro+2,18,30),(x-ro-1,79,z))).cut(inner)
        elif kind=='neck':
            nx,ny,nz,nw,nd,nh,inner=data
            swept=box((nw,nd,nh+shift),(nx,ny,nz)).cut(inner)
        else:
            b=shape.BoundingBox()
            swept=box((b.xlen,b.ylen,b.zlen+shift),(b.xmin,b.ymin,b.zmin))
        sweep=sweep.fuse(swept)
    sweep=sweep.clean()
    if not sweep.isValid() or any(q.cut(sweep).Volume()>1e-4 for q in (roof,roof.translate((0,0,shift)))):
        raise ValueError('Invalid continuous wire-roof opening sweep')
    service_key='SERVICE_POWER_R7_WIRE_ROOF_open_plusZ7p5'
    m.setdefault('service',{})[service_key]=sweep
    service={'sweep_key':service_key,'translation_mm':[0,0,shift],
      'method':'Exactcontinuousleading-faceandsemicircularsliceconstruction;notdiscreteposes.',
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
      'temporary_support_required':'SupportPSUandmainboardbeforeunfasteningtopframe;releaseGPUcableanchorandcontrolbuttonleadsbeforeliftingframe.',
      'assembly_order':'LayfinishedfactoryEPS/GPUleadsintolowerhalvesbeforetopframeinstallation;lowerroofupperhalves,fitbothWIREFastener/nutpairs,sealjoinsafterfit-up.',
      'service_order':'ACoff;supportPSUandmainboard;removeaccesspanelsandalltopframeconnectionsincludingGPUlacing/controlleads;removetopframe;removebothWIREbolt/nutpairs;liftwire-roof+Z7.5.',
      'whole_top_frame_extraction_verified':False,
      'clip_strength_and_seal_verified':False}
    oldair=m['air'][air_key]
    envelope=outer_envelopes[0].fuse(outer_envelopes[1])
    newair=oldair.cut(envelope).clean()
    removed_air=oldair.Volume()-newair.Volume()
    exact_overlap=oldair.intersect(envelope).Volume()
    if abs(removed_air-exact_overlap)>1e-4:
        raise ValueError('Wire transitions changed protected air beyond their exact outer envelopes')
    m['air'][air_key]=newair
    for label in transitions:
        transitions[label].update(attached_single_solid=True,removable_roof_single_solid=True,
          fixed_moving_parts_overlap_mm3=0.,service=service,
          total_protected_air_removed_mm3=removed_air,
          exact_combined_outer_envelope_overlap_mm3=exact_overlap,
          air_change_scope='Onlythetwoexplicitwiretransitionouterenvelopes;allbridges/necksintheexistingwire-onlybay.')
    sleeve=transitions['EPS'];gpu_sleeve=transitions['GPU']
    m['psu_meta']['EPS_isolated_factory_exit_transition']=sleeve
    m['psu_meta']['GPU_isolated_factory_exit_transition']=gpu_sleeve

    # Bottom-open raised arch: the finished factory lead is placed from below
    # and held with removable soft straps. No terminal must pass a closed bore.
    arch_points=[[35,65,193],[35,16,193],[103.3,16,193]]
    arch_outer,_=_tube(arch_points,9.5,6)
    arch_inner,_=_tube(arch_points,7.5,6)
    upper_domain=box((110,85,12),(20,0,193))
    arch_outer=arch_outer.intersect(upper_domain).clean()
    arch_inner=arch_inner.intersect(upper_domain).clean()
    arch_wall=arch_outer.cut(arch_inner).clean()
    fixed=m['parts'][base].fuse(arch_wall).cut(arch_inner).clean()
    ear_shapes=[]
    for x in (43.,97.):
        ear=box((6,5,2),(x-3,20,193)).cut(box((4,3,4),(x-2,21,192)))
        fixed=fixed.fuse(ear).clean();ear_shapes.append(ear)
    if not fixed.isValid() or len(fixed.Solids())!=1:
        raise ValueError('Bottom-open GPU arch and strap ears must join the existing PSU base')
    m['parts'][base]=fixed
    old_arch_air=m['air'][air_key]
    updated_arch_air=old_arch_air.cut(arch_outer).clean()
    removed_arch_air=old_arch_air.Volume()-updated_arch_air.Volume()
    exact_arch_overlap=old_arch_air.intersect(arch_outer).Volume()
    if abs(removed_arch_air-exact_arch_overlap)>1e-4:
        raise ValueError('GPU arch changed protected air outside its actual outer upper sweep')
    m['air'][air_key]=updated_arch_air
    arch_meta={'part':base,'centerline_mm':arch_points,'outer_diameter_mm':9.5,
      'inner_diameter_mm':7.5,'opening':'bottom atZ193;finishedheadneednotthreadthroughbore',
      'wall_thickness_mm':1.,'outer_upper_Z_mm':197.75,
      'wire_proxy_diameter_mm':6.5,'minimum_wire_to_arch_wall_mm':wires['CABLE_R6_GPU_FACTORY300'].distance(arch_wall),
      'fixed_attached_single_solid':True,
      'soft_strap_ears':[{'center_X_mm':x,'slot_mm':[4,3,2],'bbox_mm':bbox(q)} for x,q in zip((43.,97.),ear_shapes)],
      'strap_material_and_installed_retention_verified':False,
      'protected_air_removed_mm3':removed_arch_air,'exact_outer_upper_overlap_mm3':exact_arch_overlap,
      'inner_upper_overlap_with_protected_air_mm3':old_arch_air.intersect(arch_inner).Volume(),
      'thermal_or_physical_acceptance_completed':False}
    m['psu_meta']['GPU_factory_bottom_open_arch']=arch_meta

    # Finished looms enter from the open left edge of the wire-bay floor.
    # These slots are outside the cold plenum and do not cut the GPU arch.
    floor_edges=[]
    for label,origin,size in (
      ('EPS',(10.5,39.25,195.3),(14.75,5.5,1.8)),
      ('ATX',(14.,54.,195.3),(16.5,12.,1.8))):
        opening=box(size,origin)
        air_overlap=m['air'][air_key].intersect(opening).Volume()
        arch_overlap=arch_wall.intersect(opening).Volume()
        if air_overlap>1e-4 or arch_overlap>1e-4:
            raise ValueError('Wire-bay open edges must preserve protected air and GPU arch walls')
        before=m['parts'][base].Volume()
        m['parts'][base]=m['parts'][base].cut(opening).clean()
        floor_edges.append({'loom':label,'origin_mm':list(origin),'size_mm':list(size),
          'actual_material_removed_mm3':before-m['parts'][base].Volume(),
          'protected_air_removed_mm3':air_overlap,'GPU_arch_wall_removed_mm3':arch_overlap})
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
    # Unlike the explicit EPS/GPU channels, the ATX loom's PSU-face transition
    # has no measured exterior/isolated channel yet. Reserve its nominal14mm
    # face-to-gland distance in the length calculation, and keep that geometry
    # and the actual factory source coordinates as explicit physical gates.
    atx_factory='CABLE_R6_ATX_FACTORY300'
    info=p['routes'][atx_factory]
    atx_face_allowance=14.
    required=info['modeled_centerline_mm']+atx_face_allowance+24.+15.
    atx_factory_budget={'modeled_complete_centerline_mm':info['modeled_centerline_mm'],
      'modeled_connector_length_lower_bound_mm':12.,'connector_allowance_mm':24.,
      'unmodeled_factory_face_to_gland_allowance_mm':atx_face_allowance,
      'assembly_slack_mm':15.,'required_with_allowances_mm':required,
      'nominal_stock_mm':300.,'remaining_length_margin_mm':300.-required,
      'geometric_length_budget_passed':required<=300.,
      'full_source_transition_geometry_modeled':False,
      'source_transition_air_isolation_or_clearance_verified':False,
      'source_transition_status':'14mmnominalfaceY96-to-engineeringglandY82reservedforlengthonly;actualfactoryexitandisolatedtransitiongeometryrequiremeasurement.',
      'factory_measurement_origin_and_installed_flex_verified':False,
      'connector_allowance_is_engineering_assumption':True}
    info['complete_length_budget']=atx_factory_budget
    complete_budgets[atx_factory]=atx_factory_budget
    if required>300.:
        checks.append({'route':atx_factory,'kind':'complete_stock_length_short',
          'required_mm':required,'available_mm':300.})
    for key,head_allowance,head_lower_bound,exit_allowance in (
      ('CABLE_R6_ATX_FACTORY300',24.,12.,14.),
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
        if exit_allowance:
            budget['factory_face_transition_geometry_verified']=False
            budget['scope']='ATXface-to-engineeringglandtransitionhaslengthallowanceonly;itsroutingandisolationremainunmodeled.'
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
      'EPS_standard_extension':{'SKU':'PhanteksPH-CB4P_BK','nominal_length_mm':500,
        'source_url':eps_source,'connector':'4pinmotherboardfemale-to-4pinmotherboardmale',
        'stock_availability_confirmed':False,'not_PSU_proprietary_modular_cable':True},
      'EPS_complete_length_budgets':budgets,'EPS_isolated_factory_exit_transition':sleeve,
      'GPU_complete_length_budget':gpu_budget,'GPU_isolated_factory_exit_transition':gpu_sleeve,
      'GPU_factory_bottom_open_arch':arch_meta,
      'complete_stock_length_budgets':complete_budgets,
      'gland_y_status':'EPSY82/GPUY85.8areengineeringinletassumptions;bothfaceY96sourceXYZremainunmeasured.',
      'SATA_coordination':'SATArefine owns all SATA shapes;DATA2/3 horizontal tailstationY53;DATA1front190/Y5.5,DATA2front184/Y11.2,DATA3front184/Y5.5;EPSgutterdropX28/Y62.',
      'EPS_joint_bbox_mm':{k:bbox(heads[k]) for k in changed_heads},
      'GPU_factory_standard_joint':p['GPU_factory_joint'],
      'limits':['OriginalEPS4+4 halfseparation,keyed4pinextensionfitandreceived-cablelengthrequirephysicalverification;no PSUinternalpinout changes.',
        'Round sections and bend radii are engineering envelopes,not manufacturer cable exterior CAD.',
        'Nominalcenterline/slack alone does not certify factory total usable wire length or packed surplus.',
        'No EPSsame-netforkcollisionallowance remains;the4pinextension has no unused4pinbranch.']}
    m['atx_refine_meta']=meta
    return meta
