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
    # Original GPU cable mates to the standard extension at the front-right.
    head='GPU8_R6_card_8pin_HEAD_ENGINEERING_PROXY';joint='GPU8_R6_Phanteks_extension_FEMALE_HEAD_PROXY'
    hd[head]=box((14,12,18),(136,184,185.25));hd[joint]=box((14,18,18.3),(178,16,185))
    tail=[(143,190,203.05),(143,190,211.5),(143,210,211.5),(143,210,238),(236,210,238)]
    fixed=[(185,25,203.05),(185,25,211.5),(243.3,25,211.5),(243.3,50,207.5),(243.3,210,207.5),(236,210,225),(236,210,238)]
    tn='GPU8_R6_free_service_tail';fn='GPU8_R6_Phanteks_fixed_extension_route'
    w[tn]=_pipe(tail,8,8)
    fp=rounded_wire(fixed,8)
    w[fn]=cq.Workplane(cq.Plane(origin=fixed[0],normal=(0,0,1))).circle(4).sweep(cq.Workplane().newObject([fp]),isFrenet=True).val().clean()
    target=_rounded_wire(tail,8).Length()
    def parking(a):return [(236,210,238),(236,228,238),(a,228,238),(a,228,218),(222,228,218),(222,210,218),(222,210,243.05)]
    lo,hi=185.,205.
    for _ in range(35):
        a=(lo+hi)/2
        if _rounded_wire(parking(a),8).Length()>target:lo=a
        else:hi=a
    park=parking((lo+hi)/2)
    sh='SERVICE_GPU_R6_power_head_PARKED';st='SERVICE_GPU_R6_power_tail_PARKED'
    delta=(79,20,40);sv[sh]=hd[head].translate(delta);sv[st]=_pipe(park,8,8)
    sv['SERVICE_GPU_R6_power_unplug_plusZ40']=sweep_box(hd[head],(0,0,40))
    sv['SERVICE_GPU_R6_power_head_side79_AFTER_up40']=sweep_box(hd[head].translate((0,0,40)),(79,0,0))
    sv['SERVICE_GPU_R6_power_head_rear20_AFTER_side']=sweep_box(hd[head].translate((79,0,40)),(0,20,0))
    card=m['gpu_meta']['gpu_card_only'];card.update({'power_head':head,'free_wire':tn,'parked_head_service':sh,'parked_tail_service':st,'power_head_park_delta_mm':delta,
      'power_head_parking_stages_mm':[[0,0,40],[79,0,0],[0,20,0]],'remove_tail_from_normal_obstacles_only_after_park':True,
      'free_tail_park_condition':'Top/fan off;unplug40up,move79right then20rear; release tail tie,keep fixed vertical anchor.'})
    mates += [[head,tn],[joint,fn],[tn,fn]]
    # Fixed clip is below the horizontal free tail and attached to the top
    # frame. The free lead's equal-length parked pose stays right of the card.
    clip=cylinder(6.4,6,(236,210,224)).cut(cylinder(4.8,6,(236,210,224)))
    clip=clip.cut(box((8,2,6.2),(228,209,223.9)))
    arm=box((4,8,25),(242,206,224))
    p['FRAME_R6_top']=merge(p['FRAME_R6_top'],clip,arm).cut(cylinder(2,12,(246,204,233),(0,1,0))).clean()
    m['gpu_power_meta']={'extension':'Phanteks PH-CB8V_BK 500mm standardPCIe6+2 extension,18AWG','normal_paths':[fixed,tail],
      'modeled_wire_centerline_mm':fp.Length()+target,'free_tail_mm':target,'parked_tail_mm':_rounded_wire(park,8).Length(),
      'fixed_anchor_mm':[236,210,238],'park_path_mm':park,'wire_diameter_mm':8,'engineering_radius_mm':8,
      'source':'https://phanteks.com.tw/Extension-Cables.html',
      'length_limit':'Published500mm covers route plus heads;retain excess in right-front gutter.Actual exposed-wire length/head dimensions and stock packing still require sample acceptance.',
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
    # Stock fan400mm leads, routes use only the required length. Remaining
    # stock length is a declared fixed storage reserve in the rear-left bay.
    paths={
      'PWM_R6_bottom_route':([(230,196,20),(236,196,20),(236,218,20),(38,218,20),(38,218,74),(38,180,74)],400,'bottom'),
      'PWM_R6_top_route':([(243,190,233),(246,190,233),(246,218,233),(108,218,233),(108,218,188),(50,218,188),(50,218,92),(50,210,92),(38.3,210,92)],400,'top')}
    for n,(path,stock,tag) in paths.items():
        w[n]=_pipe(path,3,2.5);routes[n]={'path_mm':path,'stock_mm':stock,'modeled_mm':_rounded_wire(path,2.5).Length(),'excess':'retained in rear-left reserve;full loose stock packing not certified'}
        mates.append([n,hn[tag]]);mates.append([n,'top_fan_body' if tag=='top' else 'bottom_fan_body'])
    # Photo-derived SYS header, small straight4pin plug clears CPU40 circle.
    socket='PWM_R6_DS2501_SYS_HEADER_PHOTO_PROXY';plug='PWM_R6_DS2501_SYS_HEAD_PROXY'
    h[socket]=box((10,8,6),(188.3,71.67,183.63));hd[plug]=box((10,8,6),(198.3,71.67,183.63))
    path=[(208.1,75.67,186.63),(236,75.67,186.63),(236,224,186.63),(236,224,41.6),(44,224,41.6),(44,224,84),(44,194,84),(38.3,194,84)]
    cn='PWM_R6_SYS_to_powered_hub_control_route';w[cn]=_pipe(path,3,2.5);mates += [[cn,plug],[cn,hn['input']]]
    routes[cn]={'path_mm':path,'stock_mm':900,'modeled_mm':_rounded_wire(path,2.5).Length(),
      'stock':'NA-FH1 includedNA-EC1 300+twoadditionalNA-EC1 300;two coupling heads/stock surplus require sample packing',
      'header':'photo-derived4pin pinout/PWM mode needs actual board documentation;do not energize guessed pinout'}
    m['frame_meta']['top_module_nodes'] += ['PWM_R6_top_route',hn['top']]
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
    m['controls_meta']={'powered_fan_hub':{'model':'Noctua NA-FH1','body_mm':[93,43,12.5],'hardware':hub,'SATA_head_bbox_mm':[[28.5,143,96],[43,171,108]],
      'mount':'fixed-cage rear backing and two retained soft straps,not adhesive to removable side panel','power':'fourthfactorySATA,casefans12V;PWM/tachonlyfromSYS'},
      'routes':routes,'expected_mating_pairs':mates,'button':{'model':'ITW49-59111','center_XZ_mm':[cx,cz],'frontmost_Y_mm':.1,'recess_mm':6,'double_D_hole_mm':[16.1,14.95]},
      'CPUfan':'reuse complete original cooler/fan/lead on originalCPUFAN;not a new AM5 kit','limits':['Lead/connector detailed seating and unknown pinouts require board sample','Wire diameter/radii are engineering proxies;remaining factory wire reserves are not proof of physical packing','Top fan wire and its hub head are unplugged and removed with top module before GPU extraction']}
    return m['controls_meta']
