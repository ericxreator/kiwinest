# SPDX-License-Identifier: MIT
"""R9 compact case, independent feet, side filter and200mm top exhaust.

All dimensions mm. The NF-A20 proxy is original basic geometry; the official
external CAD is used only for a separate containment check, never imported here.
"""
import itertools,math
import cadquery as cq
from build import box,cylinder,merge,bbox

W=D=250.;H=257.;FOOT=18.
LID_Z=H-4;TOP_FRAME_Z=H-8;FAN_Z=LID_Z-30
TOP=(146.55,125.);BOTTOM=(169.,136.)
POSTS=list(itertools.product((10.,240.),(10.,240.)))
TOP_POSTS=[(10.,10.),(50.,240.),(240.,10.),(240.,240.)]
FAN_AXES=list(itertools.product((61.55,231.55),(40.,210.)))
FRONT_LOWER='FRAME_R9_front_left_REMOVABLE_lower_post'
FRONT_JOINT='FRAME_R9_front_left_joint_M3x10'
FRONT_JOINT_NUT='FRAME_R9_front_left_joint_DIN562_M3'

def ring(x,y,z,w,d,h,t):return box((w,d,h),(x,y,z)).cut(box((w-2*t,d-2*t,h+2),(x+t,y+t,z-1))).clean()
def csk(length,point,axis=(0,0,1),d=3):
    v=cq.Vector(*axis);p=cq.Vector(*point);hh=1.5 if d==3 else 2
    return merge(cq.Solid.makeCone(d, d/2,hh,p,v),cylinder(d/2,length-hh,(p+v*hh).toTuple(),axis))
def pan(length,point,axis=(0,0,1),d=3):
    v=cq.Vector(*axis);p=cq.Vector(*point);r,hh=(2.75,2.4) if d==3 else (3.8,2.2)
    return merge(cylinder(d/2,length,point,axis),cylinder(r,hh,(p-v*hh).toTuple(),axis))
def nut3(x,y,z):return box((5.5,5.5,1.8),(x-2.75,y-2.75,z)).cut(cylinder(1.6,2,(x,y,z-.1)))
def nut4(x,y,z):return cq.Workplane('XY').polygon(6,7/math.cos(math.pi/6)).extrude(3.2).val().translate((x,y,z)).cut(cylinder(2.1,3.4,(x,y,z-.1)))
def one(s,n):
    s=s.clean();assert s.isValid() and len(s.Solids())==1,n;return s

def top_fan_proxy():
    """Conservative200x200x30 frame, filled rotor and0.5mm motor label.

    A complete200mm square contains the official housing and full rotor,
    without eight removable AVP pads; its central label is also retained.
    Only the selected170mm-pitch actualD4.3 bores are open in this proxy.
    """
    cx,cy=TOP
    q=box((200,200,30),(cx-100,cy-100,FAN_Z))
    q=merge(q,cylinder(29,.5,(cx,cy,FAN_Z-.5)))
    for x,y in FAN_AXES:q=q.cut(cylinder(2.15,32,(x,y,FAN_Z-1)))
    return one(q,'NF-A20 original conservative proxy')

def build_frame():
    p={};hw={};air={};sv={};refs={};res={};joints=[]
    base=ring(3,3,0,244,244,5,10)
    fanring=box((130,130,2),(104,71,3)).cut(cylinder(57,4,(169,136,2)))
    # Narrow struts remain outside the circular fan inlet.
    base=merge(base,fanring,box((96,6,2),(12,133,3)),box((14,6,2),(233,133,3)),
      box((6,60,2),(166,12,3)),box((6,44,2),(166,202,3)))
    top=ring(3,3,TOP_FRAME_Z,244,244,4,10)
    # Direct lid mounting carries the fan. The perimeter must clear its full
    # physical frame, including the corner mounting ears, at the right edge.
    top=top.cut(box((201.6,201.6,6),(TOP[0]-100.8,TOP[1]-100.8,TOP_FRAME_Z-1)))
    top=merge(top,box((14,14,4),(173,10,TOP_FRAME_Z)))
    for x,y in POSTS:
        n=f'FRAME_R6_corner_{int(x)}_{int(y)}'
        rear_left=(x,y)==(10.,240.)
        front_left=(x,y)==(10.,10.)
        if front_left:
            low=merge(box((8,8,110.8),(6,6,5)),box((3.2,8,9.8),(8.4,6,115.8)))
            low=low.cut(cylinder(1.7,10,(10,10,4)))
            low=low.cut(cylinder(1.7,12,(3.5,10,121),(1,0,0)))
            p[FRONT_LOWER]=low
            s=merge(box((8,8,TOP_FRAME_Z-116.6),(6,6,116.6)),box((3.4,8,9.4),(4.6,6,116.6)))
            s=s.cut(box((4,8.2,9.5),(8,5.9,116.5)))
            s=s.cut(cylinder(1.7,8,(10,10,H-14)))
            s=s.cut(cylinder(1.7,12,(3.5,10,121),(1,0,0)))
            # A1.5mm outside lip retains the nut; its pocket opens at+Y.
            s=s.cut(box((2,7.05,5.9),(6.1,7.05,118.05)))
            hw[FRONT_JOINT]=pan(10,(14,10,121),(-1,0,0))
            hw[FRONT_JOINT_NUT]=box((1.8,5.5,5.5),(6.2,7.25,118.25)).cut(cylinder(1.6,2.2,(6,10,121),(1,0,0)))
        elif rear_left:
            # Move the lower post clear of the rearward SATA service gallery.
            # The bridge lies beyond the HDD duct and below the rolled PSU.
            s=merge(box((8,8,130),(101,236,5)),box((63,8,8),(46,236,135)),
                    box((8,8,TOP_FRAME_Z-135),(46,236,135)),box((48,8,8),(6,236,H-18)))
            s=s.cut(cylinder(1.7,132,(105,240,4))).cut(cylinder(1.7,TOP_FRAME_Z-134,(50,240,135)))
        else:s=box((8,8,TOP_FRAME_Z-5),(x-4,y-4,5)).cut(cylinder(1.7,TOP_FRAME_Z-3,(x,y,4)))
        # Separate bottom and lid nuts, side-entry toward the interior.
        for z in (7.4,H-11.):
            xx=(50. if z==H-11. else 105.) if rear_left else x
            po=xx-2.95 if xx in (10.,50.,105.) else xx-4.1
            pocket=box((7.1,5.9,2),(po,y-2.95,z-.1))
            if front_left and z==7.4:p[FRONT_LOWER]=p[FRONT_LOWER].cut(pocket)
            else:s=s.cut(pocket)
            nn=f'FRAME_R6_{int(x)}_{int(y)}_DIN562_M3_{z:g}';hw[nn]=nut3(xx,y,z)
        if rear_left:
            for z in (151.,215.):
                s=s.cut(cylinder(1.7,10,(50,235,z),(0,1,0)))
                s=s.cut(box((7.05,2.2,5.9),(47.05,238.8,z-2.95)))
        bx=105. if rear_left else x
        if rear_left:base=merge(base,box((12,12,5),(99,234,0)))
        base=base.cut(cylinder(1.7,7,(bx,y,-1))).cut(cq.Solid.makeCone(3,1.5,1.5,cq.Vector(bx,y,0),cq.Vector(0,0,1)))
        hw[f'FRAME_R6_base_M3x12_CSK_{int(x)}_{int(y)}']=csk(12,(bx,y,0))
        # Lid bolts pass through the top ring to captured post nuts.
        top=top.cut(cylinder(1.7,8,(50. if rear_left else x,y,TOP_FRAME_Z-1)))
        p[n]=one(s,n)
    # Four bolted feet, with recessed screw heads and captured base nuts.
    for i,(x,y) in enumerate(itertools.product((16.,234.),(16.,234.)),1):
        foot=cylinder(10,FOOT,(x,y,-FOOT))
        base=merge(base,box((12,12,5),(x-6,y-6,0)))
        base=base.cut(cylinder(1.7,7,(x,y,-1)))
        # Captured nut top3.6, leaves1.4mm roof under the base top.
        base=base.cut(box((5.9,12.2,2),(x-2.95,y-6.1,1.7)))
        foot=foot.cut(cylinder(1.7,FOOT+2,(x,y,-FOOT-1))).cut(cylinder(3.1,FOOT-14,(x,y,-FOOT)))
        # Side notch preserves access to the adjacent corner's base screw.
        if (x,y)!=(16.,234.):
            foot=foot.cut(cylinder(4,FOOT+2,(10 if x==16 else 240,10 if y==16 else 240,-FOOT-1)))
        p[f'FRAME_R9_foot18_{i}']=one(foot,'independent foot')
        hw[f'FOOT_R6_M3x20_pan_{i}']=pan(20,(x,y,-14))
        hw[f'FOOT_R6_DIN562_M3_{i}']=nut3(x,y,1.8)
    # Conservative26mm fan proxy ends at32.  Shim thickness is conditional
    # on the real fan so the long screws and filter clearance stay bounded.
    bf=box((120,120,26),(109,76,6))
    for i,(x,y) in enumerate(itertools.product((116.5,221.5),(83.5,188.5)),1):
        hole=cylinder(2.4,46,(x,y,-8));bf=bf.cut(hole);base=base.cut(hole)
        p[f'BOTTOM_R6_shim1mm_{i}']=cylinder(4.5,1,(x,y,5)).cut(cylinder(2.4,2,(x,y,4.5)))
        hw[f'BOTTOM_R6_M4x35_{i}']=pan(35,(x,y,32),(0,0,-1),4)
        hw[f'BOTTOM_R6_M4_hex_nut_{i}']=nut4(x,y,-.2)
    hw['bottom_fan_body']=one(bf,'bottomfan')
    lid=box((250,250,4),(0,0,LID_Z)).cut(cylinder(96,6,(TOP[0],TOP[1],LID_Z-1)))
    grille=[box((200,2,2),(TOP[0]-100,y,H-2)) for y in range(33,220,8)]
    lid=merge(lid,*grille)
    # The30mm housing top meets theZ253 lid underside. The motor
    # label is conservatively retained0.5mm below the housing at its hub.
    tf=top_fan_proxy()
    fan_nodes=['TOP_R6_lid','top_fan_body']
    for i,(x,y) in enumerate(FAN_AXES,1):
        lid=lid.cut(cylinder(2.4,6,(x,y,LID_Z-1))).cut(cylinder(3.95,2.5,(x,y,H-2.4)))
        a=f'TOP_R6_M4x35_{i}';b=f'TOP_R6_M4_hex_nut_{i}'
        hw[a]=pan(35,(x,y,H-2.4),(0,0,-1),4);hw[b]=nut4(x,y,FAN_Z-3.2)
        fan_nodes +=[a,b]
    for i,(x,y) in enumerate(TOP_POSTS,1):
        lid=lid.cut(cylinder(1.7,6,(x,y,LID_Z-1))).cut(cq.Solid.makeCone(3,1.5,1.5,cq.Vector(x,y,H),cq.Vector(0,0,-1)))
        hw[f'TOP_R6_lid_M3x12_CSK_{i}']=csk(12,(x,y,H),(0,0,-1));fan_nodes.append(f'TOP_R6_lid_M3x12_CSK_{i}')
    p['TOP_R6_lid']=one(lid,'lid');hw['top_fan_body']=one(tf,'topfan')
    # Flush side skins and recessed power button (added by controls module).
    skins={'front':box((244,2.4,H-9),(3,0,5)), 'back':box((244,2.4,H-9),(3,247.6,5)),
      'left':box((2.4,244,H-9),(0,3,5)),'right':box((2.4,244,H-9),(247.6,3,5))}
    def vents(s,side,a0,a1,z0,z1):
        for a in range(int(a0),int(a1),7):
            for z in range(int(z0),int(z1),24):
                if side in ('front','back'):cut=box((4,6,min(20,z1-z)),(a,-1 if side=='front' else 246,z))
                else:cut=box((6,4,min(20,z1-z)),(-1 if side=='left' else 246,a,z))
                s=s.cut(cut)
        return s
    skins['front']=vents(skins['front'],'front',9,100,18,175)
    skins['front']=vents(skins['front'],'front',43,98,201,240)
    # Storage fan includes AVP:X11.5..104.5/Y16.5..43.5/Z14.5..107.5.
    skins['front']=skins['front'].cut(cylinder(42.8,5,(58,-1,61),(0,1,0)))
    skins['front']=merge(skins['front'],*[box((92,1.6,2),(12,0,z)) for z in range(19,106,8)])
    skins['left']=vents(skins['left'],'left',144,233,64,195)
    skins['left']=merge(skins['left'],box((2.4,194,114.4),(0,42,20.8)))
    skins['right']=vents(skins['right'],'right',62,188,100,219)
    # Keep ports open: GPU, motherboard IO, and the isolated PSU AC/exhaust.
    skins['back']=skins['back'].cut(box((50,6,140),(127,246,60))).cut(box((48,6,174),(185,246,42)))
    # The rolled PSU's rear opening is applied by the R9 PSU integration.
    # Four screws/nuts/spacers for each removable skin; cross axes staggered.
    for side in ('front','back','left','right'):
        ai=1 if side in ('front','back') else 0
        normal=(0,1,0) if side=='front' else (0,-1,0) if side=='back' else (1,0,0) if side=='left' else (-1,0,0)
        zs=(50.,225.) if ai==1 else (70.,205.)
        for lateral,z in itertools.product((10.,240.),zs):
            original_lateral,original_z=lateral,z
            if side=='left' and lateral==240 and z==70:continue
            if side=='back' and lateral==10:lateral=50. if z==225 else 105.
            if side=='left' and lateral==240 and z==205:z=H-14.
            point=(lateral,0 if side=='front' else 250,z) if ai==1 else (0 if side=='left' else 250,lateral,z)
            v=cq.Vector(*normal);pos=cq.Vector(*point);sn=f'PANEL_R6_{side}_{int(lateral)}_{int(z)}'
            hw[sn+'_M3x12_CSK']=csk(12,point,normal)
            skins[side]=skins[side].cut(cylinder(1.7,15,(pos-v).toTuple(),normal)).cut(cq.Solid.makeCone(3,1.5,1.5,pos,v))
            center=list(point);center[ai]=9.2 if normal[ai]>0 else 240.8
            ns=list(center);ns[ai]=min(center[ai],center[ai]+normal[ai]*1.8)
            for j in range(3):
                if j!=ai:ns[j]-=2.75
            sz=[5.5]*3;sz[ai]=1.8
            hw[sn+'_DIN562_M3']=box(sz,ns).cut(cylinder(1.6,2.2,(cq.Vector(*center)-v*.2).toTuple(),normal))
            xyz=(10 if (side=='left' or ai==1 and original_lateral==10) else 240,
                 10 if (side=='front' or ai==0 and lateral==10) else 240)
            pn=f'FRAME_R6_corner_{xyz[0]}_{xyz[1]}'
            if xyz==(10,10) and z<116.6:pn=FRONT_LOWER
            p[pn]=p[pn].cut(cylinder(1.7,15,(pos-v).toTuple(),normal))
            po=ns[:];size=[5.9]*3;size[ai]=2.0
            for j in range(3):
                if j!=ai:po[j]-=.2
            po[ai]-=.1
            # Side-load on the other horizontal axis toward case interior.
            other=1-ai
            actual_center=(50. if original_z==225 else 105.) if side=='back' and original_lateral==10 else xyz[other]
            lo=actual_center-4;hi=actual_center+4
            if xyz[other]==10:size[other]=hi+.1-po[other]
            else:size[other]=po[other]+size[other]-(lo-.1);po[other]=lo-.1
            p[pn]=p[pn].cut(box(size,po)).clean()
            sp_start=pos+v*2.4
            hw[sn+'_spacer3p6mm']=cylinder(3,3.6,sp_start.toTuple(),normal).cut(cylinder(1.6,3.8,(sp_start-v*.1).toTuple(),normal))
        p['SKIN_R6_'+side]=one(skins[side],side)
    p[FRONT_LOWER]=one(p[FRONT_LOWER],FRONT_LOWER)
    # Continuous conservative full-material sweep, with all three captured
    # lower nuts retained. Through holes are filled by the leading/trailing
    # material during this16mm travel; this does not omit the moving column.
    lower_sweep=merge(box((8,24,110.8),(6,-10,5)),box((3.2,24,9.8),(8.4,-10,115.8)))
    lower_nuts=['FRAME_R6_10_10_DIN562_M3_7.4','PANEL_R6_front_10_50_DIN562_M3','PANEL_R6_left_10_70_DIN562_M3']
    for nn in lower_nuts:
        b=hw[nn].BoundingBox()
        lower_sweep=merge(lower_sweep,box((b.xlen,b.ylen+16,b.zlen),(b.xmin,b.ymin-16,b.zmin)))
    sv['SERVICE_R9_FRONT_LEFT_LOWER_COLUMN_MINUSY16']=lower_sweep
    # Inset right-pull filter; legacy part key remains stable for integration.
    filt=box((133.4,133.4,2),(102.3,69.3,-8.4)).cut(cylinder(58,4,(169,136,-9)))
    filt=merge(filt,box((8.3,18,2),(235.7,127,-8.4)))
    p['FILTER_R6_inset_front_pull']=one(filt,'filter')
    refs['filter_media_POROUS_REFERENCE']=box((128,128,.3),(105,72,-6.4))
    for x in (101.,237.):
        ledge_x=101 if x==101 else 235
        hanger_x=102 if x==101 else 231
        guide=merge(box((4,138,1.6),(ledge_x,67,-10)),box((2,138,5.4),(x,67,-8.4)),
          box((8,6,8),(hanger_x,80,-3)),box((8,6,8),(hanger_x,190,-3)))
        guide=guide.rotate((170,136,0),(170,136,1),90).translate((-1,0,0))
        base=merge(base,guide)
    # Travel exceeds the116mm circular opening, so the leading/trailing
    # strips sweep the full rectangle. Add the grip's exact translated box.
    sv['SERVICE_R9_FILTER_WITHDRAW_PLUSX150']=merge(
        box((283.4,133.4,2),(102.3,69.3,-8.4)),box((158.3,18,2),(235.7,127,-8.4)))
    # Module bearing lands connect to the perimeter/fan ring, with actual
    # tapped-nut pockets rather than fasteners suspended in an open floor.
    base=merge(base,box((105,10,5),(3,46,0)),box((105,10,5),(3,211,0)),
      box((14,12,5),(168,14,0)),box((12,12,5),(174,62,0)))
    for x,y in ((7,51),(101,51),(7,215),(101,215)):
        base=base.cut(cylinder(1.7,7,(x,y,-1))).cut(box((5.9,5.9,2.6),(x-2.95,y-2.95,1.1)))
    for x,y in ((175,20),(167,240)):
        base=base.cut(cylinder(1.7,7,(x,y,-1))).cut(cq.Solid.makeCone(3,1.5,1.5,cq.Vector(x,y,0),cq.Vector(0,0,1)))
    for x,y in ((180,68),(180,244)):
        base=base.cut(cylinder(1.7,7,(x,y,-1)))
    for x,y in ((180,18),(180,244)):
        top=top.cut(cylinder(1.7,6,(x,y,TOP_FRAME_Z-1))).cut(cq.Solid.makeCone(3,1.5,1.5,cq.Vector(x,y,LID_Z),cq.Vector(0,0,-1)))
    # Bearing-land unions above must not refill earlier corner/foot holes.
    for x,y in POSTS:
        xx=105. if (x,y)==(10.,240.) else x
        base=base.cut(cylinder(1.7,7,(xx,y,-1))).cut(cq.Solid.makeCone(3,1.5,1.5,cq.Vector(xx,y,0),cq.Vector(0,0,1)))
    for x,y in itertools.product((16.,234.),(16.,234.)):
        base=base.cut(cylinder(1.7,7,(x,y,-1))).cut(box((5.9,12.2,2),(x-2.95,y-6.1,1.7)))
    p['FRAME_R6_base']=one(base,'base');p['FRAME_R6_top']=one(top,'top')
    air['AIR_bottom_fan_intake']=cylinder(56,FOOT+4,(169,136,-FOOT+2))
    air['AIR_gpu_intake22']=box((22,220.5,120.25),(105,14,65))
    air['AIR_top_rotor_keepout']=cylinder(94,30,(TOP[0],TOP[1],FAN_Z))
    air['AIR_top_external_exhaust']=cylinder(96,45,(TOP[0],TOP[1],H))
    # The GPU occupies X128..169.6.  Protect its actual fan-face supply gap,
    # rather than claiming an empty vertical column through the card itself.
    air['AIR_gpu_lower_supply']=box((17,110,30),(110,78,35))
    meta={'body_mm':[250,250,H],'feet_mm':FOOT,'target_static_overall_mm':[250,250,275],
      'top_module_nodes':fan_nodes,'fan_proxy_note':'NF-A20 PWM200x200x30 without removable AVP; complete0.5mm motor-label protrusion retained; no spacer',
      'top_fan_Z_mm':[FAN_Z-.5,LID_Z],'top_spacer_proxy_mm':0.,
      'top_fan_axes':FAN_AXES,
      'top_fan_model':'Noctua NF-A20 PWM,12V four-pin PWM',
      'top_fan_center_xy_mm':list(TOP),'top_fan_body_Z_mm':[FAN_Z,LID_Z],
      'top_fan_motor_label_Z_mm':[FAN_Z-.5,FAN_Z],
      'top_fan_mount_pitch_mm':[170.,170.],'top_fan_actual_bore_D_mm':4.3,
      'top_fan_fasteners':{'screw':'M4x35 pan,35mm under-head length','under_head_Z_mm':254.6,'tip_Z_mm':219.6,'nut_Z_mm':[219.8,223.],'nominal_nut_engagement_mm':3.2,'nominal_tip_projection_beyond_nut_mm':.2,'actual_end_chamfer_thread_engagement_and_tolerance_verified':False},
      'top_fan_catalogue_tolerances_mm':{'overall_extent':.7,'housing_thickness':.3},
      'top_fan_balanced_side_clearance':{'planned_PSU_partition_max_X_mm':45.5,'right_skin_inner_X_mm':247.6,
        'nominal_housing_X_mm':[TOP[0]-100.,TOP[0]+100.],
        'nominal_left_right_gap_mm':[TOP[0]-100.-45.5,247.6-(TOP[0]+100.)],
        'catalogue_max_width_mm':200.7,'centered_max_width_left_right_gap_mm':[TOP[0]-100.35-45.5,247.6-(TOP[0]+100.35)],
        'scope':'Housing width only with fixed centered datum; mounting-hole location, print tolerance and received fit remain unverified',
        'physical_fit_accepted':False},
      'top_fan_source_url':'https://www.noctua.at/en/products/nf-a20-pwm/specifications',
      'top_fan_source_PDF':'https://cdn.noctua.at/media/73165231/Noctua%20NF-A20%20PWM%20Specification.pdf?download=true',
      'top_fan_factory_wire_nominal_mm':200.,'top_fan_factory_wire_route_verified':False,
      'top_fan_wire_exit':{'cap_xyz_mm':[46.55,76.,237.],'exit_axis':[-1,0,0],'bundle_D_mm':3.,'coordinates_are_engineering_not_received_hardware_measurements':True,'included_extension':'Noctua NA-EC1,300mm'},
      'feet':{'parts':[f'FRAME_R9_foot18_{i}' for i in range(1,5)],'height_mm':FOOT,'diameter_mm':20.,'axes_xy_mm':list(itertools.product((16.,234.),(16.,234.)))},
      'filter':{'part':'FILTER_R6_inset_front_pull','direction':[1,0,0],'travel_mm':150.,'service_sweep':'SERVICE_R9_FILTER_WITHDRAW_PLUSX150','moving_nodes':['FILTER_R6_inset_front_pull'],'guide_bottom_mm':-10.,'nominal_guide_clearance_to_desk_mm':FOOT-10.,'tool_and_flex_physical_acceptance':False},
      'rear_left_column':{'base_axis_xy_mm':[105.,240.],'upper_axis_xy_mm':[50.,240.],'lower_Z_mm':[5.,135.],'lower_bridge_Z_mm':[135.,143.],'upper_Z_mm':[135.,TOP_FRAME_Z],'top_bridge_Z_mm':[H-18,H-10],'top_lid_bolt_axis_xy_mm':[50.,240.]},
      'left_skin_attachment':{'fastener_count':3,'removed_point_YZ_mm':[240.,70.],'reason':'Rear lower column moves toX105; no unsupported long screw. Left skin carried by front column and upper rear beam. Stiffness/vibration physically unverified.'},
      'front_left_split_column':{'fixed_upper_part':'FRAME_R6_corner_10_10','removable_lower_part':FRONT_LOWER,
        'lower_body_Z_mm':[5.,115.8],'fixed_upper_min_Z_mm':116.6,'tongue_bbox_mm':[[8.4,6.,115.8],[11.6,14.,125.6]],
        'socket_void_bbox_mm':[[8.,5.9,116.5],[12.,14.1,126.]],'socket_roof_Z_mm':[126.,130.],
        'joint_screw':FRONT_JOINT,'joint_axis':{'point':[14.,10.,121.],'axis':[-1,0,0]},'joint_nut':FRONT_JOINT_NUT,
        'joint_nut_bbox_mm':[[6.2,7.25,118.25],[8.,12.75,123.75]],'captured_lower_hardware':lower_nuts,
        'service_sweep':'SERVICE_R9_FRONT_LEFT_LOWER_COLUMN_MINUSY16','service_translation_mm':[0,-16,0],
        'moving_parts':[FRONT_LOWER],'moving_hardware':lower_nuts,
        'remove_before_service':['front skin/front fan module','FRAME_R6_base_M3x12_CSK_10_10',FRONT_JOINT,'PANEL_R6_front_10_50_M3x12_CSK','PANEL_R6_left_10_70_M3x12_CSK'],
        'retain_during_service':['fixed upper column','hub and backing','stock basket','other three columns'],
        'scope':'Continuous conservative whole lower-column+captured-nut material envelope; real tongue fit and loaded rigidity unverified'},
      'PSU_flange_frame_interfaces':[{'point_mm':[50.,247.,z],'axis':[0,-1,0],'through_D_mm':3.4,'bolt':'M3x10,provided by PSU module','nut':'DIN562 M3 thin,5.5x1.8','nut_bbox_mm':[[47.25,239.,z-2.75],[52.75,240.8,z+2.75]],'nut_pocket_entry':'+X from post right edge'} for z in (151.,215.)],
      'front_92mm_grille':{'center_xz_mm':[58.,61.],'rotor_opening_D_mm':85.6,'fan_body_mm':[[11.5,16.5,14.5],[104.5,43.5,107.5]],'physical_thermal_acceptance':False},
      'bottom_fan_axes':list(itertools.product((116.5,221.5),(83.5,188.5))),
      'bottom_fan_center_xy_mm':list(BOTTOM),'bottom_fan_shift_from_R8_mm':[-1.,0.,0.],
      'first_drive_removal_precondition':['remove front skin/fan module and lower-column side screws','remove front-left lower base bolt and transverse joint screw','move lower column and its captured nuts-Y16,retain upper column/hub/basket/topframe'],
      'materials':'PETG structural, TPU only at selected contacts; physical creep/load acceptance pending',
      'geometry_is_thermal_validation':False}
    access=['FRAME_R6_base_M3x12_CSK_10_10',FRONT_JOINT,'PANEL_R6_front_10_50_M3x12_CSK','PANEL_R6_front_10_50_spacer3p6mm','PANEL_R6_left_10_70_M3x12_CSK']
    meta['front_left_lower_post_service']={'sweep_key':'SERVICE_R9_FRONT_LEFT_LOWER_COLUMN_MINUSY16',
      'removed_nodes':[FRONT_LOWER]+lower_nuts+access+['PWM_R9_HDD_factory200'],'remove_hardware':lower_nuts+access,
      'moving_parts':[FRONT_LOWER],'captured_hardware_moves_with_lower':lower_nuts,
      'translation_mm':[0,-16,0],'prerequisites':['Power off','remove front skin and front fan/plenum module','remove base and transverse joint screws,front50 andleft70 skin screws'],
      'upper_column_hub_and_stock_basket_remain_installed':True,'physical_joint_strength_and_loaded_service_accepted':False}
    return p,hw,refs,air,sv,res,meta
