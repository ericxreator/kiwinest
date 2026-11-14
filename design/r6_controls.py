# SPDX-License-Identifier: MIT
"""R6 GPU service lead, recessed switch and SATA-powered case fan controls.

Wire envelopes are routes, not certified vendor connector CAD or flex testing.
"""
import math
import cadquery as cq
from build import box,cylinder,merge,bbox
from r2_cables import _pipe,_rounded_wire
from r4_riser_route import rounded_wire
from r5_gpu import sweep_box

def apply_controls(m):
    p,h,w,hd,sv,res=(m[k] for k in ('parts','hardware','wires','heads','service','reserves'))
    mates=[];routes={}
    # The factory GPU lead now mates to a standard extension beside the PSU,
    # left of the card extraction column and above its intake air domain.
    head='GPU8_R6_card_8pin_HEAD_ENGINEERING_PROXY';joint='GPU8_R8_MODDIY_CAB534_FEMALE_HEAD_PROXY'
    hd[head]=box((14,12,18),(136,184,185.25));hd[joint]=box((14,18.3,18),(106,43.7,193.5))
    # The tail starts exactly on the card-head top and approaches the fixed
    # anchor from above. The fixed lead ends there from below: shared caps,
    # not a long overlapping pair of independently swept cable volumes.
    tail=[(143,190,203.25),(143,190,211.5),(143,210,211.5),
      (143,210,247),(236,210,247),(236,210,238)]
    # The coupling faces -Y. Rise ahead of its EPS neighbor, cross the front
    # above the switch, then descend beyond the GPU extraction column. Pass
    # outside the SYS lead before rising beyond the fan's front fixing bolt.
    # Keep the full8mm/R8 envelope, rear anchor and existing free service tail.
    fixed=[(113,43.7,202.5),(113,35.5,202.5),(113,35.5,234),
      (113,9,234),(180,9,234),(180,30,234),(180,30,190),
      (232,30,190),(232,68.6,190),(243.3,80,214.5),(243.3,150,214.5),
      (243.3,178,207.5),(243.3,210,207.5),(236,210,225),(236,210,238)]
    tn='GPU8_R6_free_service_tail';fn='GPU8_R8_MODDIY_CAB534_fixed_extension_route'
    w[tn]=_pipe(tail,8,8)
    fp=rounded_wire(fixed,8)
    tangent=fp._r4_edges[0].tangentAt(0)
    w[fn]=cq.Workplane(cq.Plane(origin=fixed[0],normal=tangent)).circle(4).sweep(cq.Workplane().newObject([fp]),isFrenet=True).val().clean()
    target=_rounded_wire(tail,8).Length()
    # Bend inward below the retained right-hand top ring before rising into
    # the open service space. Rise and return on separate20mm-spaced legs;
    # the return ends on the parked head top, never through its body.
    def parking(u):return [(236,210,238),(236,210,246.001),(218,210,246.001),
      (218,210,u),(218,230,u),(218,230,243.25)]
    # The lower inward dogleg needs two R8 tangent lengths before its next
    # turn. A lower bound at251.251 would include unconstructible spines.
    lo,hi=262.002,330.
    if not _rounded_wire(parking(lo),8).Length()<=target<=_rounded_wire(parking(hi),8).Length():
        raise ValueError('GPU tail cannot retain its full length in the bounded parked service route')
    for _ in range(35):
        u=(lo+hi)/2
        if _rounded_wire(parking(u),8).Length()<target:lo=u
        else:hi=u
    park=parking((lo+hi)/2)
    sh='SERVICE_GPU_R6_power_head_PARKED';st='SERVICE_GPU_R6_power_tail_PARKED'
    delta=(75,40,40);sv[sh]=hd[head].translate(delta);sv[st]=_pipe(park,8,8)
    sv['SERVICE_GPU_R6_power_unplug_plusZ40']=sweep_box(hd[head],(0,0,40))
    sv['SERVICE_GPU_R6_power_head_side75_AFTER_up40']=sweep_box(hd[head].translate((0,0,40)),(75,0,0))
    sv['SERVICE_GPU_R6_power_head_rear40_AFTER_side']=sweep_box(hd[head].translate((75,0,40)),(0,40,0))
    card=m['gpu_meta']['gpu_card_only'];card.update({'power_head':head,'free_wire':tn,'parked_head_service':sh,'parked_tail_service':st,'power_head_park_delta_mm':delta,
      'power_head_parking_stages_mm':[[0,0,40],[75,0,0],[0,40,0]],'remove_tail_from_normal_obstacles_only_after_park':True,
      'free_tail_park_condition':'Top/fan off;unplug40up,move75right then40rear; release tail tie,keep fixed vertical anchor; reserve open space above chassis for the equal-length free tail.'})
    # These cap interfaces remain in the normal collision checks; no whole
    # head/tail or fixed/free cable-pair overlap exemption is required.
    contact_checks={
      'card_head_vs_free_tail_mm3':hd[head].intersect(w[tn]).Volume(),
      'coupling_head_vs_fixed_wire_mm3':hd[joint].intersect(w[fn]).Volume(),
      'fixed_vs_free_tail_mm3':w[fn].intersect(w[tn]).Volume(),
      'parked_head_vs_parked_tail_mm3':sv[sh].intersect(sv[st]).Volume()}
    if any(volume>1e-4 for volume in contact_checks.values()):
        raise ValueError('GPU cable cap interfaces must touch without volumetric overlap')
    # Fixed clip is below the horizontal free tail and attached to the top
    # frame. The free lead's equal-length parked pose stays right of the card.
    clip=cylinder(6.4,6,(236,210,224)).cut(cylinder(4.8,6,(236,210,224)))
    clip=clip.cut(box((8,2,6.2),(228,209,223.9)))
    arm=box((4,8,25),(242,206,224))
    p['FRAME_R6_top']=merge(p['FRAME_R6_top'],clip,arm).cut(cylinder(2,12,(246,204,233),(0,1,0))).clean()
    m['gpu_power_meta']={'extension':'MODDIY CAB534 configured70cm standard8pinPCIe male-to-female extension','nominal_stock_mm':700.,'extension_SKU':'CAB534','normal_paths':[fixed,tail],
      'modeled_wire_centerline_mm':fp.Length()+target,'free_tail_mm':target,'parked_tail_mm':_rounded_wire(park,8).Length(),
      'fixed_anchor_mm':[236,210,238],'park_path_mm':park,'wire_diameter_mm':8,'engineering_radius_mm':8,
      'cap_interface_intersections_mm3':contact_checks,
      'parked_tail_service_above_chassis':True,
      'source':'https://www.moddiy.com/products/3281/Premium-Custom-PSU-Extension-Cable-8-Pin-PCIE-Power.html',
      'fixed_wire_key':fn,'free_wire_key':tn,
      'catalog_length_range_mm':[100,1000],
      'length_limit':'Selected700mm covers route plus heads;retain full surplus in the assigned stock-lead basket.Actual connector-inclusive usable length,wire dimensions and installed packing still require sample acceptance.',
      'physical_flexible_deformation_verified':False}
    # Hub uses the fourth factory SATA connector. Two case fans draw their
    #12V from SATA, while the unknown board header supplies PWM/tach only.
    hub='FANHUB_R6_Noctua_NAFH1_93x43x12p5_VENDOR_ENVELOPE'
    h[hub]=box((12.5,93,43),(16,143,65))
    cage='R6_STORAGE_COMMON_CAGE_open_floor_rear_skeleton'
    backing=merge(box((4,14,86),(12,136,65)),box((4,93,43),(12,143,65)))
    # Two retained soft straps pass through the four actual carrier ears.
    ears=[]
    for y in (180.,228.):
        for z in (61.,108.):
            ear=box((8,8,4),(10,y-4,z)).cut(box((5,4,6),(11.5,y-2,z-1)))
            ears.append(ear)
    p[cage]=merge(p[cage],backing,*ears)
    # End connectors remain explicitly estimated; no invented FH1 port CAD.
    hn={}
    for tag,y,z in (('bottom',180.,74.),('top',210.,92.),('input',194.,84.)):
        n='PWM_R6_hub_'+tag+'_HEAD_PROXY';hd[n]=box((10,12,8),(28.5,y-6,z-4));hn[tag]=n
    # Use the third NA-EC1 from the existing NA-SEC1 kit for the top fan.
    # The400mm factory lead ends above the basket; the standard joint is
    # unplugged before lifting the top module. Both full stock lengths stay
    # represented in the route and surplus budgets.
    paths={
      'PWM_R6_bottom_route':([(230,196,20),(236,196,20),(236,218,20),(38,218,20),(38,218,74),(38,180,74)],400,'bottom'),
      'PWM_R6_top_route':([(243,190,233),(246,190,233),(246,218,233),(108,218,233),(108,218,188),(50,218,188),(50,218,166)],400,'top')}
    for n,(path,stock,tag) in paths.items():
        w[n]=_pipe(path,3,2.5);routes[n]={'path_mm':path,'stock_mm':stock,'modeled_mm':_rounded_wire(path,2.5).Length(),'excess':'retained in rear-left reserve;full loose stock packing not certified'}
        if tag=='bottom':mates.append([n,hn[tag]])
        mates.append([n,'top_fan_body' if tag=='top' else 'bottom_fan_body'])
    top_native='PWM_R8_top_factory_4pin_MALE_ENGINEERING_PROXY'
    top_extension_head='PWM_R8_top_EC1_4pin_FEMALE_ENGINEERING_PROXY'
    hd[top_native]=box((10,12,8),(45,212,158))
    hd[top_extension_head]=box((10,12,8),(45,212,150))
    top_extension='PWM_R8_top_NA_EC1_300_extension'
    top_extension_path=[(50,218,150),(50,218,92),(50,210,92),(38.5,210,92)]
    w[top_extension]=_pipe(top_extension_path,3,2.5)
    routes[top_extension]={'path_mm':top_extension_path,'stock_mm':300,
      'modeled_mm':_rounded_wire(top_extension_path,2.5).Length(),
      'stock':'ThirdNA-EC1fromtheexistingNA-SEC1threepack;other2kitcablesplusNA-FH1includedcableformSYSchain.',
      'connector_shapes_are_engineering_proxies':True,
      'excess':'Retainwholeunusedstocklengthintheassignedleadbasket;physicalcoilpackingunverified.'}
    # Photo-derived SYS header, small straight4pin plug clears CPU40 circle.
    socket='PWM_R6_DS2501_SYS_HEADER_PHOTO_PROXY';plug='PWM_R6_DS2501_SYS_HEAD_PROXY'
    h[socket]=box((10,8,6),(188.3,71.67,183.63));hd[plug]=box((10,8,6),(198.3,71.67,183.63))
    # Leave the header forward of the round CPU inlet, then descend outside
    # its front edge before crossing below it. The full3mm/R2.5 wire remains
    # explicit;Y60 separates the descent from the GPU power lead atY68.6,
    # andX226 keeps it inboard of the DATA2 diagonal atX238.5.
    # Neither the CPU40 reserve nor the side intake is reduced.
    # Model each of the three actual300mm cables and both intermediate joints.
    # The new caps touch their head faces exactly; the stock lengths cannot be
    # pooled to hide a short individual segment or a missing coupling body.
    sys_paths={
      'PWM_R8_SYS_NA_EC1_1_route':[(208.3,75.67,186.63),(226,75.67,186.63),(226,60,186.63),(226,60,110),(226,186,110)],
      'PWM_R8_SYS_NA_EC1_2_route':[(226,202,110),(226,224,110),(226,224,41.6),(108,224,41.6)],
      'PWM_R8_SYS_NA_EC1_3_route':[(92,224,41.6),(44,224,41.6),(44,224,84),(44,194,84),(38.5,194,84)]}
    sys_heads={
      'PWM_R8_SYS_J1_NATIVE_HEAD_ENGINEERING_PROXY':((10,8,8),(221,186,106)),
      'PWM_R8_SYS_J1_EXT_HEAD_ENGINEERING_PROXY':((10,8,8),(221,194,106)),
      'PWM_R8_SYS_J2_NATIVE_HEAD_ENGINEERING_PROXY':((8,12,8),(100,218,37.6)),
      'PWM_R8_SYS_J2_EXT_HEAD_ENGINEERING_PROXY':((8,12,8),(92,218,37.6))}
    for name,(size,origin) in sys_heads.items():hd[name]=box(size,origin)
    for name,path in sys_paths.items():
        w[name]=_pipe(path,3,2.5)
        routes[name]={'path_mm':path,'stock_mm':300,
          'modeled_mm':_rounded_wire(path,2.5).Length(),
          'stock':'NA-FH1includedNA-EC1plus2NA-EC1fromNA-SEC1kit;3individual300mmsegments.',
          'connector_shapes_are_engineering_proxies':True,
          'header':'Photo-derived4pin pinout/PWM mode needs actual board documentation;do not energize guessed pinout.',
          'excess':'Retainall3individualstocklengthsurplusesintheassignedleadbasket;physicalcoilpackingunverified.'}
    m['frame_meta']['top_module_nodes'] += ['PWM_R6_top_route',top_native]
    res['RESERVE_PWM_R6_original_leads_and_control_excess_NOT_PACKED']=box((47,50,53),(45,174,75))
    # Recessed ITW switch; front of the dome stays atY0.1 within the250mm cube.
    cx,cz=215.,224.;normal=(0,1,0)
    barrel=cylinder(8,16,(cx,7.2,cz),normal).intersect(box((14.85,17,18),(cx-7.425,7,cz-9)))
    bezel=cylinder(9.9,5.1,(cx,7.2,cz),(0,-1,0));button=cylinder(8,2,(cx,2.1,cz),(0,-1,0))
    sw='CONTROL_R6_ITW49_59111_VENDOR_DIMENSION_PROXY';nt='CONTROL_R6_ITW_retainer_UNMEASURED_PROXY'
    h[sw]=merge(barrel,bezel,button);h[nt]=cylinder(12,5,(cx,9.6,cz),normal).cut(cylinder(8.1,5,(cx,9.6,cz),normal))
    # Small bridge is part of the top frame, with a double-D seat atY7.2.
    mount=merge(box((28,2.4,28),(201,7.2,210)),box((4,10,37),(201,7.2,214)),box((4,10,37),(225,7.2,214)))
    hole=cylinder(8.05,4,(cx,6.5,cz),normal).intersect(box((14.95,5,18),(cx-7.475,6,cz-9)))
    mount=mount.cut(hole).cut(cylinder(12.4,8,(cx,9.4,cz),normal))
    p['FRAME_R6_top']=merge(p['FRAME_R6_top'],mount)
    p['SKIN_R6_front']=p['SKIN_R6_front'].cut(cylinder(10.3,5,(cx,-1,cz),normal)).clean()
    ph='CONTROL_R6_2pin_POWER_HEADER_PHOTO_PROXY';hp='CONTROL_R6_Harwin_M20_1060200_HEAD_PROXY'
    h[ph]=box((5,5.4,3),(188.3,70.6,83.5));hd[hp]=box((14,5.4,3),(193.3,70.6,83.5))
    bp=[(215,23,224),(215,33,224),(208.9,33,224),(208.9,33,215),(208.9,52,215),(219,52,215),(219,52,85),(219,73.3,85),(207.1,73.3,85)]
    bn='CONTROL_R6_ITW_original500mm_lead_route';w[bn]=_pipe(bp,2,3);mates += [[bn,sw],[bn,hp]]
    routes[bn]={'path_mm':bp,'stock_mm':500,'modeled_mm':_rounded_wire(bp,3).Length(),'pinout':'DS2501 two power-switch pins must be confirmed;not MSI JFP1 mapping'}
    res['RESERVE_CONTROL_R6_button_lead_excess_NOT_PACKED']=box((14,25,30),(218,35,110))
    complete_budgets={}
    for name,info in routes.items():
        diameter,radius=(2.,3.) if name==bn else (3.,2.5)
        head_allowance=16. if name==bn else 24.
        required=info['modeled_mm']+head_allowance+15.
        budget={'modeled_complete_centerline_mm':info['modeled_mm'],
          'connector_allowance_mm':head_allowance,'assembly_slack_mm':15.,
          'required_with_allowances_mm':required,'nominal_stock_mm':info['stock_mm'],
          'remaining_length_margin_mm':info['stock_mm']-required,
          'geometric_length_budget_passed':required<=info['stock_mm'],
          'connector_allowance_is_engineering_assumption':True,
          'factory_measurement_origin_and_installed_flex_verified':False}
        info.update(engineering_diameter_mm=diameter,engineering_bend_R_mm=radius,
          complete_length_budget=budget,
          unmodeled_surplus_mm=info['stock_mm']-info['modeled_mm'],
          surplus_insulated_material_mm3=max(0.,info['stock_mm']-info['modeled_mm'])*math.pi*(diameter/2)**2)
        complete_budgets[name]=budget
    cap_pairs=[
      ('top_factory_to_head',w['PWM_R6_top_route'],hd[top_native]),
      ('top_joint',hd[top_native],hd[top_extension_head]),
      ('top_EC1_to_head',w[top_extension],hd[top_extension_head]),
      ('top_EC1_to_hub',w[top_extension],hd[hn['top']]),
      ('SYS1_to_header',w['PWM_R8_SYS_NA_EC1_1_route'],hd[plug]),
      ('SYS1_to_J1',w['PWM_R8_SYS_NA_EC1_1_route'],hd['PWM_R8_SYS_J1_NATIVE_HEAD_ENGINEERING_PROXY']),
      ('SYS_J1',hd['PWM_R8_SYS_J1_NATIVE_HEAD_ENGINEERING_PROXY'],hd['PWM_R8_SYS_J1_EXT_HEAD_ENGINEERING_PROXY']),
      ('SYS2_to_J1',w['PWM_R8_SYS_NA_EC1_2_route'],hd['PWM_R8_SYS_J1_EXT_HEAD_ENGINEERING_PROXY']),
      ('SYS2_to_J2',w['PWM_R8_SYS_NA_EC1_2_route'],hd['PWM_R8_SYS_J2_NATIVE_HEAD_ENGINEERING_PROXY']),
      ('SYS_J2',hd['PWM_R8_SYS_J2_NATIVE_HEAD_ENGINEERING_PROXY'],hd['PWM_R8_SYS_J2_EXT_HEAD_ENGINEERING_PROXY']),
      ('SYS3_to_J2',w['PWM_R8_SYS_NA_EC1_3_route'],hd['PWM_R8_SYS_J2_EXT_HEAD_ENGINEERING_PROXY']),
      ('SYS3_to_hub',w['PWM_R8_SYS_NA_EC1_3_route'],hd[hn['input']])]
    pwm_caps={name:{'overlap_mm3':a.intersect(b).Volume(),'distance_mm':a.distance(b)}
              for name,a,b in cap_pairs}
    if any(v['overlap_mm3']>1e-4 or v['distance_mm']>1e-5 for v in pwm_caps.values()):
        raise ValueError('PWM segment caps must touch their explicit heads without overlap')
    m['controls_meta']={'powered_fan_hub':{'model':'Noctua NA-FH1','body_mm':[93,43,12.5],'hardware':hub,'SATA_head_bbox_mm':[[28.5,143,96],[43,171,108]],
      'mount':'fixed-cage rear backing and two retained soft straps,not adhesive to removable side panel','power':'fourthfactorySATA,casefans12V;PWM/tachonlyfromSYS'},
      'complete_length_budgets':complete_budgets,'PWM_new_cap_interfaces':pwm_caps,
      'PWM_standard_joint_shapes_are_engineering_proxies':True,
      'NA_EC1_stock_allocation':{'NA_FH1_included_300mm':1,'NA_SEC1_kit_300mm':3,
        'SYS_chain_segments_300mm':3,'top_fan_extension_segments_300mm':1,
        'allocation':'SYSuseshubincluded1+kit2;topfanusestheremainingkit1.Noadditionalkit.'},
      'top_fan_standard_joint':{'factory_head':top_native,'extension_head':top_extension_head,
        'mating_plane_Z_mm':158.,'source_wire':'PWM_R6_top_route','extension_wire':top_extension,
        'extension_stays_installed_during_top_module_removal':True,
        'service':'Unplugthestandard4pinjointbeforeliftingtopfan;factoryheadand400mmleadgowithtopmodule,EC1andhubheadremaininstalled.',
        'received_connector_dimensions_and_physical_fit_verified':False},
      'routes':routes,'expected_mating_pairs':mates,'button':{'model':'ITW49-59111','center_XZ_mm':[cx,cz],'frontmost_Y_mm':.1,'recess_mm':6,'double_D_hole_mm':[16.1,14.95]},
      'CPUfan':'reuse complete original cooler/fan/lead on originalCPUFAN;not a new AM5 kit','limits':['Lead/connector detailed seating and unknown pinouts require board sample','Wire diameter/radii are engineering proxies;remaining factory wire reserves are not proof of physical packing','Unplugtopfanatmodeledinline4pinjoint;EC1extensionandhubheadstayinstalledbeforeGPUextraction']}
    return m['controls_meta']
