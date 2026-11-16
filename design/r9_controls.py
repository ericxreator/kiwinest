# SPDX-License-Identifier: MIT
"""R9 independent HDD fan, front-mounted SATA hub and retained GPU service lead.

Cable diameters and connector shells are engineering envelopes. The full stock
and connector/slack budgets are counted individually; physical flex is pending.
"""
import math
import cadquery as cq
from build import box,cylinder,merge,bbox
from r6_power import _tube
from r4_riser_route import rounded_wire
from r5_gpu import sweep_box


def apply_controls(m):
    p,h,w,hd,sv,res=(m[k] for k in ('parts','hardware','wires','heads','service','reserves'))
    mates=[];routes={}
    def wire(name,path,stock,d=3.,R=2.5):
        shape,L=_tube(path,d,R);w[name]=shape
        allowance=16. if d==2 else 24.
        required=L+allowance+15.
        budget={'modeled_complete_centerline_mm':L,'connector_allowance_mm':allowance,
          'assembly_slack_mm':15.,'nominal_stock_mm':stock,'required_with_allowances_mm':required,
          'remaining_length_margin_mm':stock-required,'geometric_length_budget_passed':required<=stock,
          'minimum_required_margin_mm':25.,'minimum_margin_passed':stock-required>=25.,
          'connector_allowance_is_engineering_assumption':True,'factory_measurement_origin_and_installed_flex_verified':False}
        routes[name]={'path_mm':path,'stock_mm':stock,'modeled_mm':L,'engineering_diameter_mm':d,
          'engineering_bend_R_mm':R,'complete_length_budget':budget,'unmodeled_surplus_mm':stock-L,
          'surplus_insulated_material_mm3':max(0.,stock-L)*math.pi*(d/2)**2}
        return name
    head='GPU8_R6_card_8pin_HEAD_ENGINEERING_PROXY';joint='GPU8_R8_MODDIY_CAB534_FEMALE_HEAD_PROXY'
    hd[head]=box((14,12,18),(136,184,185.25));hd[joint]=box((14,18.3,18),(94.5,73.7,193.5))
    tail=[(143,190,203.25),(143,190,211.5),(165.7,190,211.5),(165.7,241.,211.5),(118,241.,211.5),(118,241.,198)]
    # Cross above the HDD diffuser, entirely on its+X side. The rear U-turn
    # lets the fixed wire reach the anchor from below, opposed to the free
    # tail's downward end, rather than superimposing two vertical wires.
    fixed=[(101.5,73.7,202.5),(101.5,60,202.5),(118,60,218.),(118,241.,218.),
      (98,241.,218.),(98,241.,185.5),(118,241.,185.5),(118,241.,198.)]
    tn='GPU8_R6_free_service_tail';fn='GPU8_R9_MODDIY_CAB534_fixed_extension_route'
    w[tn],target=_tube(tail,8,8);w[fn],fixedL=_tube(fixed,8,8)
    def parking(u):return [(118,241.,198),(118,241.,208),(109.5,221,208),(109.5,221,u),(116,200,u),(116,200,243.25)]
    lo,hi=251.251,330.
    if not rounded_wire(parking(lo),8).Length()<=target<=rounded_wire(parking(hi),8).Length():
        raise ValueError('Equal-length GPU parked route cannot fit')
    for _ in range(35):
        u=(lo+hi)/2
        if rounded_wire(parking(u),8).Length()<target:lo=u
        else:hi=u
    park=parking((lo+hi)/2)
    sh='SERVICE_GPU_R6_power_head_PARKED';st='SERVICE_GPU_R6_power_tail_PARKED'
    delta=(-27,10,40);sv[sh]=hd[head].translate(delta);sv[st],parkL=_tube(park,8,8)
    sv['SERVICE_GPU_R6_power_unplug_plusZ40']=sweep_box(hd[head],(0,0,40))
    sv['SERVICE_GPU_R6_power_head_side75_AFTER_up40']=sweep_box(hd[head].translate((0,0,40)),(-27,0,0))
    sv['SERVICE_GPU_R6_power_head_rear40_AFTER_side']=sweep_box(hd[head].translate((-27,0,40)),(0,10,0))
    card=m['gpu_meta']['gpu_card_only'];card.update(power_head=head,free_wire=tn,parked_head_service=sh,
      parked_tail_service=st,power_head_park_delta_mm=delta,power_head_parking_stages_mm=[[0,0,40],[-27,0,0],[0,10,0]],
      remove_tail_from_normal_obstacles_only_after_park=True,
        free_tail_park_condition='Remove lid/top fan;unplug +Z40,move X-27 then Y+10;release tail tie;retain equal full wire length.')
    contact_checks={n:a.intersect(b).Volume() for n,a,b in (
      ('card_head_vs_free_tail_mm3',hd[head],w[tn]),('coupling_head_vs_fixed_wire_mm3',hd[joint],w[fn]),
      ('fixed_vs_free_tail_mm3',w[fn],w[tn]),('parked_head_vs_parked_tail_mm3',sv[sh],sv[st]))}
    if any(v>1e-4 for v in contact_checks.values()):raise ValueError('GPU cap overlap')
    # Rear spine is outside the fan footprint and card lift column. A split
    # open saddle carries the fixed/free boundary with a releasable soft tie.
    saddle=cylinder(6.,6,(118,241.,194)).cut(cylinder(4.8,6,(118,241.,194)))
    saddle=saddle.cut(box((8,2,6.2),(110,241.5,193.9)))
    spine=box((8,1.5,51),(114,245.5,198))
    p['FRAME_R6_top']=merge(p['FRAME_R6_top'],spine,saddle).clean()
    m['gpu_power_meta']={'extension':'MODDIY CAB534 configured60cm standard8pinPCIe male-to-female extension',
      'nominal_stock_mm':600.,'extension_SKU':'CAB534','normal_paths':[fixed,tail],
      'modeled_wire_centerline_mm':fixedL+target,'free_tail_mm':target,'parked_tail_mm':parkL,
      'fixed_anchor_mm':[118,241.,198],'park_path_mm':park,'wire_diameter_mm':8,'engineering_radius_mm':8,
      'cap_interface_intersections_mm3':contact_checks,'parked_tail_service_above_chassis':True,
      'source':'https://www.moddiy.com/products/3281/Premium-Custom-PSU-Extension-Cable-8-Pin-PCIE-Power.html',
      'fixed_wire_key':fn,'free_wire_key':tn,'catalog_length_range_mm':[100,1000],
      'physical_flexible_deformation_verified':False,'route_key':'CABLE_R9_GPU_MODDIY_CAB534_600'}
    required=fixedL+target+48.+15.
    m['gpu_power_meta']['complete_length_budget']={'modeled_complete_centerline_mm':fixedL+target,
      'connector_allowance_mm':48.,'assembly_slack_mm':15.,'nominal_stock_mm':600.,
      'required_with_allowances_mm':required,'remaining_length_margin_mm':600.-required,
      'minimum_required_margin_mm':25.,'minimum_margin_passed':600.-required>=25.,
      'geometric_length_budget_passed':required<=600.,'connector_allowance_is_engineering_assumption':True,
      'factory_measurement_origin_and_installed_flex_verified':False}
    hub='FANHUB_R6_Noctua_NAFH1_93x43x12p5_VENDOR_ENVELOPE';h[hub]=box((93,43,12.5),(5,17,119))
    backing=merge(box((93,43,2.4),(5,17,116.6)),box((89,10,2.4),(9,10,116.6)))
    for x in (24.,83.):
        for y in (12.,62.):
            ear=box((8,8,2.4),(x-4,y-4,116.6)).cut(box((4,5,6),(x-2,y-2.5,114)))
            backing=merge(backing,ear)
    # Back ears connect to the backing with two short rear extensions.
    backing=merge(backing,box((8,10,2.4),(20,56,116.6)),box((8,10,2.4),(79,56,116.6)))
    backing=backing.cut(box((4,8.2,9.5),(8,5.9,116.5)))
    backing=backing.cut(cylinder(3.1,4,(13.8,10,121),(1,0,0)))
    p['FRAME_R6_corner_10_10']=merge(p['FRAME_R6_corner_10_10'],backing).clean()
    hn={}
    for tag,x in (('bottom',22.),('top',34.),('HDD',54.),('input',74.)):
        key='PWM_R9_hub_'+tag+'_HEAD_PROXY';hd[key]=box((8,10,8),(x-4,7,121.25));hn[tag]=key
    hd['POWER_R6_NA_FH1_SATA_HEAD_ENGINEERING_PROXY']=box((30,14.5,12),(64,60,119.25))
    # The HDD fan's finished hub plug leaves with its complete200mm lead.
    # The powered hub body and all other cable plugs remain installed.
    m['drive_meta']['front_fan_attached_route_keys']=list(dict.fromkeys(
      m['drive_meta'].get('front_fan_attached_route_keys',[])+['PWM_R9_HDD_factory200',hn['HDD']]))
    hdd_unplug='SERVICE_R9_HDD_PWM_HEAD_WITHDRAW_MINUSY10'
    sv[hdd_unplug]=sweep_box(hd[hn['HDD']],(0,-10,0))
    m['drive_meta']['front_fan_service'].update(PWM_head_key=hn['HDD'],PWM_unplug_sweep_key=hdd_unplug,
      PWM_unplug_translation_mm=[0,-10,0],PWM_unplug_removed_nodes=[hn['HDD'],'PWM_R9_HDD_factory200'],
      PWM_unplug_prerequisites=['Power off','remove front skin','release full attached factory lead from retention'],
      PWM_socket_and_other_plugs_remain_installed=True,
      PWM_unplug_distance_and_flexible_lead_motion_physically_verified=False)
    # Standard 8mm-long inline head pairs meet at a shared plane.
    caps=[]
    def pair(prefix,origin,size,axis):
        a=prefix+'_NATIVE_HEAD_ENGINEERING_PROXY';b=prefix+'_EXT_HEAD_ENGINEERING_PROXY'
        hd[a]=box(size,origin);o=list(origin);o[axis]-=size[axis];hd[b]=box(size,o)
        caps.append((prefix+'_joint',a,b));return a,b
    top_native,top_ext=pair('PWM_R9_top',(66,74,177),(8,12,8),2)
    # Keep both complete inline shells to the right of the plenum's draw.
    # The factory lead rises behind the front-lock tool; its extension moves
    # forward below the GPU inlet, then above the retained hub plugs.
    bottom_native,bottom_ext=pair('PWM_R9_bottom',(119,57,56.5),(8,12,8),1)
    wire('PWM_R9_bottom_factory400',[(229,196,20),(236,196,20),(236,202,20),(107,202,20),(107,202,14.5),(107,72,14.5),(123,72,14.5),(123,72,60.5),(123,69,60.5)],400)
    wire('PWM_R9_bottom_NA_EC1_300',[(123,45,60.5),(123,4,60.5),(123,4,131.25),(123,9.1,131.25),(22,9.1,131.25),(22,4,131.25),(22,4,125.25),(22,7,125.25)],300)
    top_exit=m['frame_meta'].get('top_fan_wire_exit',{}).get('cap_xyz_mm',[46.55,76,237])
    wire('PWM_R9_top_factory200',[top_exit,(43.5,76,237),(43.5,55,237),(43.5,55,204),(70,55,204),(70,80,204),(70,80,185)],200)
    wire('PWM_R9_top_NA_EC1_300',[(70,80,169),(70,80,136),(70,4,136),(34,4,136),(34,4,125.25),(34,7,125.25)],300)
    hdd_exit=m['drive_meta'].get('fan_wire_exit_xyz_mm',[11.5,28,106])
    wire('PWM_R9_HDD_factory200',[hdd_exit,(4.2,28,106),(4.2,4,106),(54,4,106),(54,4,125.25),(54,7,125.25)],200)
    socket='PWM_R6_DS2501_SYS_HEADER_PHOTO_PROXY';plug='PWM_R6_DS2501_SYS_HEAD_PROXY'
    h[socket]=box((10,8,6),(188.3,71.67,183.63));hd[plug]=box((10,8,6),(198.3,71.67,183.63))
    j1a='PWM_R9_SYS_J1_NATIVE_HEAD_ENGINEERING_PROXY';j1b='PWM_R9_SYS_J1_EXT_HEAD_ENGINEERING_PROXY'
    hd[j1a]=box((10,8,8),(221,160,106));hd[j1b]=box((10,8,8),(221,168,106))
    j2a='PWM_R9_SYS_J2_NATIVE_HEAD_ENGINEERING_PROXY';j2b='PWM_R9_SYS_J2_EXT_HEAD_ENGINEERING_PROXY'
    hd[j2a]=box((8,12,8),(230,102,72));hd[j2b]=box((8,12,8),(230,102,64))
    j3a='PWM_R9_SYS_J3_NATIVE_HEAD_ENGINEERING_PROXY';j3b='PWM_R9_SYS_J3_EXT_HEAD_ENGINEERING_PROXY'
    hd[j3a]=box((8,12,8),(168,51,24));hd[j3b]=box((8,12,8),(160,51,24))
    wire('PWM_R9_SYS_NA_EC1_1_route',[(208.3,75.67,186.63),(226,75.67,186.63),(226,60,186.63),(226,60,110),(226,160,110)],300)
    wire('PWM_R9_SYS_NA_EC1_2_route',[(226,176,110),(226,184,110),(240,184,110),(240,108,110),(234,108,110),(234,108,80)],300)
    wire('PWM_R9_SYS_NA_EC1_3_route',[(234,108,64),(234,108,61),(240,108,61),(240,108,88),(240,57,88),(184,57,88),(184,57,28),(176,57,28)],300)
    # Rise behind the lock-tool sweep before moving forward. The front leg
    # clears the entire shifted plenum and crosses above the native HDD band.
    wire('PWM_R9_SYS_NA_EC1_4_route',[(160,57,28),(119.3,57,28),(119.3,57,35.5),(119.3,4,35.5),(119.3,4,119),(74,4,119),(74,4,125.25),(74,7,125.25)],300)
    # Original recessed switch and its 500mm cable retain their board datum.
    cx,cz=215.,218.;normal=(0,1,0)
    barrel=cylinder(8,16,(cx,7.2,cz),normal).intersect(box((14.85,17,18),(cx-7.425,7,cz-9)))
    sw='CONTROL_R6_ITW49_59111_VENDOR_DIMENSION_PROXY';nt='CONTROL_R6_ITW_retainer_UNMEASURED_PROXY'
    h[sw]=merge(barrel,cylinder(9.9,5.1,(cx,7.2,cz),(0,-1,0)),cylinder(8,2,(cx,2.1,cz),(0,-1,0)))
    h[nt]=cylinder(12,5,(cx,9.6,cz),normal).cut(cylinder(8.1,5,(cx,9.6,cz),normal))
    mount=merge(box((28,2.4,28),(201,7.2,204)),box((4,10,43),(201,7.2,208)),box((4,10,43),(225,7.2,208)))
    hole=cylinder(8.05,4,(cx,6.5,cz),normal).intersect(box((14.95,5,18),(cx-7.475,6,cz-9)))
    p['FRAME_R6_top']=merge(p['FRAME_R6_top'],mount.cut(hole).cut(cylinder(12.4,8,(cx,9.4,cz),normal)))
    p['SKIN_R6_front']=p['SKIN_R6_front'].cut(cylinder(10.3,5,(cx,-1,cz),normal)).clean()
    ph='CONTROL_R6_2pin_POWER_HEADER_PHOTO_PROXY';hp='CONTROL_R6_Harwin_M20_1060200_HEAD_PROXY'
    h[ph]=box((5,5.4,3),(188.3,70.6,83.5));hd[hp]=box((14,5.4,3),(193.3,70.6,83.5))
    bp=[(215,23.2,218),(215,33,218),(208.9,33,218),(208.9,52,215),(219,52,215),(219,52,85),(219,73.3,85),(207.3,73.3,85)]
    bn=wire('CONTROL_R6_ITW_original500mm_lead_route',bp,500,2,3);mates += [[bn,sw],[bn,hp]]
    m['frame_meta']['top_module_nodes'] += ['PWM_R9_top_factory200',top_native]
    cap_pairs=[
      ('bottom_fan_to_factory','bottom_fan_body','PWM_R9_bottom_factory400'),
      ('bottom_factory_to_head','PWM_R9_bottom_factory400',bottom_native),
      ('bottom_inline_joint',bottom_native,bottom_ext),
      ('bottom_extension_to_head',bottom_ext,'PWM_R9_bottom_NA_EC1_300'),
      ('bottom_extension_to_hub','PWM_R9_bottom_NA_EC1_300',hn['bottom']),
      ('top_fan_to_factory','top_fan_body','PWM_R9_top_factory200'),
      ('top_factory_to_head','PWM_R9_top_factory200',top_native),
      ('top_inline_joint',top_native,top_ext),
      ('top_extension_to_head',top_ext,'PWM_R9_top_NA_EC1_300'),
      ('top_extension_to_hub','PWM_R9_top_NA_EC1_300',hn['top']),
      ('HDD_fan_to_factory','R9_HDD_NF_A9_PWM_WITH_PADS_ENGINEERING_PROXY','PWM_R9_HDD_factory200'),
      ('HDD_factory_to_hub','PWM_R9_HDD_factory200',hn['HDD']),
      ('SYS_socket_to_plug',socket,plug),('SYS_plug_to_1',plug,'PWM_R9_SYS_NA_EC1_1_route'),
      ('SYS_1_to_J1','PWM_R9_SYS_NA_EC1_1_route',j1a),('SYS_J1',j1a,j1b),
      ('SYS_J1_to_2',j1b,'PWM_R9_SYS_NA_EC1_2_route'),('SYS_2_to_J2','PWM_R9_SYS_NA_EC1_2_route',j2a),
      ('SYS_J2',j2a,j2b),('SYS_J2_to_3',j2b,'PWM_R9_SYS_NA_EC1_3_route'),
      ('SYS_3_to_J3','PWM_R9_SYS_NA_EC1_3_route',j3a),('SYS_J3',j3a,j3b),
      ('SYS_J3_to_4',j3b,'PWM_R9_SYS_NA_EC1_4_route'),('SYS_4_to_hub','PWM_R9_SYS_NA_EC1_4_route',hn['input']),
      ('switch_to_lead',sw,bn),('lead_to_board_head',bn,hp)]
    all_nodes=h|hd|w
    cap_proof={name:{'nodes':[a,b],'overlap_mm3':all_nodes[a].intersect(all_nodes[b]).Volume(),
      'distance_mm':all_nodes[a].distance(all_nodes[b])} for name,a,b in cap_pairs}
    if any(q['overlap_mm3']>1e-4 or q['distance_mm']>1e-5 for q in cap_proof.values()):
        raise ValueError('R9 controls cap gap/overlap: '+str({n:q for n,q in cap_proof.items() if q['overlap_mm3']>1e-4 or q['distance_mm']>1e-5}))
    m['controls_meta']={'powered_fan_hub':{'model':'Noctua NA-FH1','body_mm':[93,43,12.5],'hardware':hub,
      'mount':'Front upper fixed-column backing with two retained soft straps; no adhesive to removable skin',
      'power':'Fourth factory SATA through standard extension; three case fans draw SATA12V; SYS carries PWM/tach only'},
      'routes':routes,'expected_mating_pairs':mates,'cap_interfaces':cap_proof,
      'complete_length_budgets':{n:v['complete_length_budget'] for n,v in routes.items()},
      'top_fan_standard_joint':{'factory_head':top_native,'extension_head':top_ext,'mating_plane_Z_mm':177.,
        'source_wire':'PWM_R9_top_factory200','extension_wire':'PWM_R9_top_NA_EC1_300',
        'extension_stays_installed_during_top_module_removal':True},
      'NA_EC1_stock_allocation':{'NA_FH1_included_300mm':1,'NF_A20_included_300mm':1,
        'NF_A9_included_300mm':1,'NA_SEC1_kit_300mm':3,'used_SYS':4,'used_top':1,'used_bottom':1,
        'unused_300mm':0,'unused_stock_material_counted':True},
      'button':{'model':'ITW49-59111','center_XZ_mm':[cx,cz],'frontmost_Y_mm':.1,'recess_mm':6,'double_D_hole_mm':[16.1,14.95]},
      'CPUfan':'Reuse complete original CPU cooler/fan on original CPUFAN',
      'limits':['Fan lead exit coordinates, connector shells, bend radii and flexible parking are engineering assumptions.',
        'Actual SYS pinout,fan-control behavior and hub current limits require received-hardware verification.']}
    return m['controls_meta']
