# SPDX-License-Identifier: MIT
"""R6 compact case, independent feet/filter, real panel and fan fixings.

All dimensions mm.  This is a new layout; R1--R5 remain immutable.
"""
import itertools,math
import cadquery as cq
from build import box,cylinder,merge,bbox

W=D=250.;H=255.;FOOT=20.
TOP=(176.5,120.);BOTTOM=(170.,136.)
POSTS=list(itertools.product((10.,240.),(10.,240.)))

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

def build_frame():
    p={};hw={};air={};sv={};refs={};res={};joints=[]
    base=ring(3,3,0,244,244,5,10)
    fanring=box((130,130,2),(105,71,3)).cut(cylinder(57,4,(170,136,2)))
    # Narrow struts remain outside the circular fan inlet.
    base=merge(base,fanring,box((96,6,2),(12,133,3)),box((14,6,2),(234,133,3)),
      box((6,60,2),(167,12,3)),box((6,44,2),(167,202,3)))
    top=ring(3,3,247,244,244,4,10)
    top=merge(top,box((14,38,4),(173,10,247)))
    for x,y in POSTS:
        n=f'FRAME_R6_corner_{int(x)}_{int(y)}'
        s=box((8,8,242),(x-4,y-4,5)).cut(cylinder(1.7,244,(x,y,4)))
        # Separate bottom and lid nuts, side-entry toward the interior.
        for z in (7.4,244.):
            po=x-2.95 if x==10 else x-4.1
            s=s.cut(box((7.1,5.9,2),(po,y-2.95,z-.1)))
            nn=f'FRAME_R6_{int(x)}_{int(y)}_DIN562_M3_{z:g}';hw[nn]=nut3(x,y,z)
        base=base.cut(cylinder(1.7,7,(x,y,-1))).cut(cq.Solid.makeCone(3,1.5,1.5,cq.Vector(x,y,0),cq.Vector(0,0,1)))
        hw[f'FRAME_R6_base_M3x12_CSK_{int(x)}_{int(y)}']=csk(12,(x,y,0))
        # Lid bolts pass through the top ring to captured post nuts.
        top=top.cut(cylinder(1.7,8,(x,y,246)))
        p[n]=one(s,n)
    # Four bolted feet, with recessed screw heads and captured base nuts.
    feet=ring(2,2,-20,246,246,5,10)
    for i,(x,y) in enumerate(itertools.product((16.,234.),(16.,234.)),1):
        feet=merge(feet,box((14,14,15),(x-7,y-7,-15)))
        base=merge(base,box((12,12,5),(x-6,y-6,0)))
        base=base.cut(cylinder(1.7,7,(x,y,-1)))
        # Captured nut top3.6, leaves1.4mm roof under the base top.
        base=base.cut(box((5.9,12.2,2),(x-2.95,y-6.1,1.7)))
        feet=feet.cut(cylinder(1.7,22,(x,y,-21))).cut(cylinder(3.1,6.1,(x,y,-20)))
        hw[f'FOOT_R6_M3x20_pan_{i}']=pan(20,(x,y,-14))
        hw[f'FOOT_R6_DIN562_M3_{i}']=nut3(x,y,1.8)
    p['FRAME_R6_feet20']=one(feet,'feet')
    # Conservative26mm fan proxy ends at32.  Shim thickness is conditional
    # on the real fan so the long screws and filter clearance stay bounded.
    bf=box((120,120,26),(110,76,6))
    for i,(x,y) in enumerate(itertools.product((117.5,222.5),(83.5,188.5)),1):
        hole=cylinder(2.4,46,(x,y,-8));bf=bf.cut(hole);base=base.cut(hole)
        p[f'BOTTOM_R6_shim1mm_{i}']=cylinder(4.5,1,(x,y,5)).cut(cylinder(2.4,2,(x,y,4.5)))
        hw[f'BOTTOM_R6_M4x35_{i}']=pan(35,(x,y,32),(0,0,-1),4)
        hw[f'BOTTOM_R6_M4_hex_nut_{i}']=nut4(x,y,-.2)
    hw['bottom_fan_body']=one(bf,'bottomfan')
    lid=box((250,250,4),(0,0,251)).cut(cylinder(69,6,(176.5,120,250)))
    grille=[box((140,2,2),(106.5,y,253)) for y in range(54,189,8)]
    lid=merge(lid,*grille)
    # Raise the intact fan one millimetre above the x8 cable fan-out. A
    # shorter spacer preserves the lid, frame and external case dimensions.
    tf=box((140,140,26),(106.5,50,221))
    fan_nodes=['TOP_R6_lid','top_fan_body']
    for i,(x,y) in enumerate(itertools.product((114.25,238.75),(57.75,182.25)),1):
        #4.8 clearance permits the124.5/125mm catalogue-drawing difference.
        tf=tf.cut(cylinder(2.4,30,(x,y,218)))
        top=top.cut(cylinder(4.75,8,(x,y,245)))
        lid=lid.cut(cylinder(2.4,6,(x,y,250))).cut(cylinder(3.95,2.5,(x,y,252.6)))
        sn=f'TOP_R8_spacer4mm_{i}';p[sn]=cylinder(4.5,4,(x,y,247)).cut(cylinder(2.4,4,(x,y,247)))
        a=f'TOP_R6_M4x40_{i}';b=f'TOP_R6_M4_hex_nut_{i}'
        hw[a]=pan(40,(x,y,252.6),(0,0,-1),4);hw[b]=nut4(x,y,217.8)
        fan_nodes +=[sn,a,b]
    for i,(x,y) in enumerate(POSTS,1):
        lid=lid.cut(cylinder(1.7,6,(x,y,250))).cut(cq.Solid.makeCone(3,1.5,1.5,cq.Vector(x,y,255),cq.Vector(0,0,-1)))
        hw[f'TOP_R6_lid_M3x12_CSK_{i}']=csk(12,(x,y,255),(0,0,-1));fan_nodes.append(f'TOP_R6_lid_M3x12_CSK_{i}')
    p['TOP_R6_lid']=one(lid,'lid');hw['top_fan_body']=one(tf,'topfan')
    # Flush side skins and recessed power button (added by controls module).
    skins={'front':box((244,2.4,246),(3,0,5)), 'back':box((244,2.4,246),(3,247.6,5)),
      'left':box((2.4,244,246),(0,3,5)),'right':box((2.4,244,246),(247.6,3,5))}
    def vents(s,side,a0,a1,z0,z1):
        for a in range(int(a0),int(a1),7):
            for z in range(int(z0),int(z1),24):
                if side in ('front','back'):cut=box((4,6,min(20,z1-z)),(a,-1 if side=='front' else 246,z))
                else:cut=box((6,4,min(20,z1-z)),(-1 if side=='left' else 246,a,z))
                s=s.cut(cut)
        return s
    skins['front']=vents(skins['front'],'front',9,100,18,175)
    skins['front']=vents(skins['front'],'front',43,98,201,240)
    skins['left']=vents(skins['left'],'left',144,233,64,195)
    skins['right']=vents(skins['right'],'right',62,188,100,219)
    # Keep ports open: GPU, motherboard IO, and the isolated PSU AC/exhaust.
    skins['back']=skins['back'].cut(box((50,6,140),(127,246,60))).cut(box((48,6,174),(185,246,42)))
    skins['back']=skins['back'].cut(box((86,6,46),(14,246,198)))
    # Four screws/nuts/spacers for each removable skin; cross axes staggered.
    for side in ('front','back','left','right'):
        ai=1 if side in ('front','back') else 0
        normal=(0,1,0) if side=='front' else (0,-1,0) if side=='back' else (1,0,0) if side=='left' else (-1,0,0)
        zs=(50.,225.) if ai==1 else (70.,205.)
        for lateral,z in itertools.product((10.,240.),zs):
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
            xyz=(10 if (side=='left' or ai==1 and lateral==10) else 240,
                 10 if (side=='front' or ai==0 and lateral==10) else 240)
            pn=f'FRAME_R6_corner_{xyz[0]}_{xyz[1]}'
            p[pn]=p[pn].cut(cylinder(1.7,15,(pos-v).toTuple(),normal))
            po=ns[:];size=[5.9]*3;size[ai]=2.0
            for j in range(3):
                if j!=ai:po[j]-=.2
            po[ai]-=.1
            # Side-load on the other horizontal axis toward case interior.
            other=1-ai;lo=xyz[other]-4;hi=xyz[other]+4
            if xyz[other]==10:size[other]=hi+.1-po[other]
            else:size[other]=po[other]+size[other]-(lo-.1);po[other]=lo-.1
            p[pn]=p[pn].cut(box(size,po)).clean()
            sp_start=pos+v*2.4
            hw[sn+'_spacer3p6mm']=cylinder(3,3.6,sp_start.toTuple(),normal).cut(cylinder(1.6,3.8,(sp_start-v*.1).toTuple(),normal))
        p['SKIN_R6_'+side]=one(skins[side],side)
    # Inset front-pull filter, no external handle or added depth.
    filt=box((133.4,133.4,2),(103.3,69.3,-8.4)).cut(cylinder(58,4,(170,136,-9)))
    filt=merge(filt,box((18,59.4,2),(161,10,-8.4)))
    p['FILTER_R6_inset_front_pull']=one(filt,'filter')
    refs['filter_media_POROUS_REFERENCE']=box((128,128,.3),(106,72,-6.4))
    for x in (101.,237.):
        ledge_x=101 if x==101 else 235
        hanger_x=102 if x==101 else 231
        guide=merge(box((4,138,1.6),(ledge_x,67,-10)),box((2,138,5.4),(x,67,-8.4)),
          box((8,6,8),(hanger_x,80,-3)),box((8,6,8),(hanger_x,190,-3)))
        base=merge(base,guide)
    # Module bearing lands connect to the perimeter/fan ring, with actual
    # tapped-nut pockets rather than fasteners suspended in an open floor.
    base=merge(base,box((105,10,5),(3,16,0)),box((105,10,5),(3,129,0)),
      box((14,12,5),(168,14,0)),box((12,12,5),(174,62,0)))
    for x,y in ((7,21),(101,21),(7,134),(101,134)):
        base=base.cut(cylinder(1.7,7,(x,y,-1))).cut(box((5.9,5.9,2.6),(x-2.95,y-2.95,1.1)))
    for x,y in ((175,20),(167,240)):
        base=base.cut(cylinder(1.7,7,(x,y,-1))).cut(cq.Solid.makeCone(3,1.5,1.5,cq.Vector(x,y,0),cq.Vector(0,0,1)))
    for x,y in ((180,68),(180,244)):
        base=base.cut(cylinder(1.7,7,(x,y,-1)))
    for x,y in ((180,42),(180,244)):
        top=top.cut(cylinder(1.7,6,(x,y,246))).cut(cq.Solid.makeCone(3,1.5,1.5,cq.Vector(x,y,251),cq.Vector(0,0,-1)))
    # Bearing-land unions above must not refill earlier corner/foot holes.
    for x,y in POSTS:
        base=base.cut(cylinder(1.7,7,(x,y,-1))).cut(cq.Solid.makeCone(3,1.5,1.5,cq.Vector(x,y,0),cq.Vector(0,0,1)))
    for x,y in itertools.product((16.,234.),(16.,234.)):
        base=base.cut(cylinder(1.7,7,(x,y,-1))).cut(box((5.9,12.2,2),(x-2.95,y-6.1,1.7)))
    # Bottom bolt heads remain tool-accessible without first taking feet off.
    for x,y in POSTS+[(175.,20.),(167.,240.),(180.,68.),(180.,244.)]:
        #Y244/R4 would only touch the outerY248 edge, a non-manifold pinch.
        #A4.2mm radius makes a proper open service notch with finite width.
        feet=feet.cut(cylinder(4.2 if (x,y)==(180.,244.) else 4,23,(x,y,-21)))
    p['FRAME_R6_feet20']=one(feet,'feet with access holes')
    p['FRAME_R6_base']=one(base,'base');p['FRAME_R6_top']=one(top,'top')
    air['AIR_bottom_fan_intake']=cylinder(56,24,(170,136,-18))
    air['AIR_gpu_intake22']=box((22,220.5,120.25),(105,14,65))
    air['AIR_top_rotor_keepout']=cylinder(68,26,(176.5,120,221))
    air['AIR_top_external_exhaust']=cylinder(67,45,(176.5,120,255))
    # The GPU occupies X128..169.6.  Protect its actual fan-face supply gap,
    # rather than claiming an empty vertical column through the card itself.
    air['AIR_gpu_lower_supply']=box((17,110,30),(110,78,35))
    meta={'body_mm':[250,250,255],'feet_mm':20,'target_static_overall_mm':[250,250,275],
      'top_module_nodes':fan_nodes,'fan_proxy_note':'25mm nominal,26mm conservative; top fan raised1mm; shim sets top faces32/247',
      'top_fan_Z_mm':[221,247],'top_spacer_proxy_mm':4.,
      'actual_25mm_top_fan_Z_mm':[221,246],
      'top_spacer_for_actual_25mm_fan_mm':5.,
      'top_fan_axes':list(itertools.product((114.25,238.75),(57.75,182.25))),
      'bottom_fan_axes':list(itertools.product((117.5,222.5),(83.5,188.5))),
      'first_drive_removal_precondition':['remove front/left skins and their screws/nuts/spacers','remove front-left post base bolt and its lid bolt','move front-left post-Y16,retain other3posts/topframe'],
      'materials':'PETG structural, TPU only at selected contacts; physical creep/load acceptance pending',
      'geometry_is_thermal_validation':False}
    return p,hw,refs,air,sv,res,meta
