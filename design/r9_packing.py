# SPDX-License-Identifier: MIT
"""Independent open stock basket above the HDDs, outside their forced air."""
import math
from build import box,cylinder,merge,bbox
from r6_frame import ring,pan
from r6_power import _tube


def apply_packing(m):
    p,h,res=m['parts'],m['hardware'],m['reserves']
    basket=merge(ring(19,67,116.6,83,138,2.4,2.4),ring(19,67,140.6,83,138,2.,2.4),
      ring(48,90,178,54,110,2,2.4))
    for x in (19.,99.6):
        for y in (67.,202.6):basket=merge(basket,box((2.4,2.4,21.6),(x,y,119)))
    for x in (48.,99.6):
        for y in (90.,197.6):basket=merge(basket,box((2.4,2.4,37.4),(x,y,140.6)))
    # Side plate clamps to the fixed upper column; the detachable lower
    # column and HDDs carry none of this stock. The ribs clear the independent
    # PSU front brace and join the basket's front upper ring.
    basket=merge(basket,box((4,8,23),(14,6,132)),box((6,59.4,4),(14,10,140)),
      box((6,59.4,4),(14,10,151)),box((6,4,11),(14,65.4,140)))
    post='FRAME_R6_corner_10_10';fixed=p[post]
    for i,z in enumerate((136.,148.),1):
        basket=basket.cut(cylinder(1.7,5,(13.5,10,z),(1,0,0)))
        fixed=fixed.cut(cylinder(1.7,10,(5,10,z),(1,0,0)))
        fixed=fixed.cut(box((2.2,7.1,5.9),(7.1,7.05,z-2.95)))
        h[f'R9_STOCK_BASKET_M3x12_pan_{i}']=pan(12,(18,10,z),(-1,0,0))
        h[f'R9_STOCK_BASKET_DIN562_M3_{i}']=box((1.8,5.5,5.5),(7.3,7.25,z-2.75)).cut(cylinder(1.6,2,(7.2,10,z),(1,0,0)))
    # Open cable/connector notches are only real occupied hardware envelopes
    # plus0.3mm assembly clearance. Never reduce cable diameters or air masks.
    changes=[]
    for n,s in (m['heads']|m['wires']|{n:s for n,s in h.items() if n.startswith('PSU_R9_')}|{n:s for n,s in p.items() if n.startswith('PSU_R9_')}).items():
        b=s.BoundingBox();bb=basket.BoundingBox()
        if b.xmax<bb.xmin or b.xmin>bb.xmax or b.ymax<bb.ymin or b.ymin>bb.ymax or b.zmax<bb.zmin or b.zmin>bb.zmax:continue
        if n in m['wires']:
            # Offset the actual curved solid locally rather than carve its
            # entire AABB, which would falsely erase large supporting ribs.
            try:clear=s.fuse(s.shell([], .3,kind='arc')).clean()
            except Exception:clear=s
        elif n in m['heads'] or n in h:
            clear=box((b.xlen+.6,b.ylen+.6,b.zlen+.6),(b.xmin-.3,b.ymin-.3,b.zmin-.3))
        else:clear=s
        before=basket.Volume();basket=basket.cut(clear).clean()
        if before-basket.Volume()>1e-5:changes.append(n)
    p[post]=fixed.clean();name='FRAME_R9_stock_lead_basket_ABOVE_HDD';p[name]=basket.clean()
    lower=box((78.2,133.2,21.6),(21.4,69.4,119))
    upper=box((49.2,105.2,35.),(50.4,92.4,143))
    space=merge(lower,upper);raw=space.Volume()
    for n,s in (p|h|m['heads']|m['wires']).items():
        b=s.BoundingBox();a=space.BoundingBox()
        if b.xmax<=a.xmin or b.xmin>=a.xmax or b.ymax<=a.ymin or b.ymin>=a.ymax or b.zmax<=a.zmin or b.zmin>=a.zmax:continue
        space=space.cut(s)
    space=space.clean();res['RESERVE_R9_RETAINED_STOCK_UPPER_L_BASKET_NOT_PACKED']=space
    packing=m['power_meta']['surplus_packing'];packing['reserved_box_volume_mm3']=space.Volume()
    if packing['minimum_with_factor_mm3']>space.Volume():m['power_meta']['checks'].append({'kind':'surplus_packing_volume_unqualified','required_mm3':packing['minimum_with_factor_mm3'],'available_mm3':space.Volume()})
    m['packing_meta']={'part':name,'raw_box_mm3':raw,'net_available_mm3':space.Volume(),
      'fixing':'Two M3x12 pan + DIN562 M3 on front-left fixed upper column,Z136/148,X18; twin cantilever ribs',
      'purpose':'Retain complete unused factory branches and every purchased cable surplus above HDDs,away from four forced air passages and rear chimney.',
      'notches_for_actual_routed_material':changes,'packing_accepted':False,
      'limits':['Volume allowance does not prove coil bend radius,connector access,retention strength or physical cable packing.',
        'Printed cantilever strength and creep require sample validation; no drive carrier supports the basket.']}
    return m['packing_meta']
