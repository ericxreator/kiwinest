# SPDX-License-Identifier: MIT
"""Fixed rear-left open basket for retained stock leads;not a packed-coil proof."""
import cadquery as cq
import math
from build import box,cylinder,merge,bbox
from r6_frame import ring,csk,nut3,one

def apply_packing(m):
    p,h,res=m['parts'],m['hardware'],m['reserves']
    #24in gives room for connector bodies and assembly slack;18in nominal
    #left only3mm on one route and did not establish usable exposed length.
    oldtag,newtag='STARTECH_LSATA18_457p2','STARTECH_LSATA24_609p6'
    rename=lambda key:key.replace(oldtag,newtag)
    m['wires']={rename(n):s for n,s in m['wires'].items()}
    pm=m['power_meta'];routes={}
    for n,v in pm['routes'].items():
        key=rename(n);v['keys']=[rename(k) for k in v['keys']]
        if n.startswith('CABLE_R6_SATA_DATA_'):
            v['nominal_stock_mm']=609.6;v['unmodeled_surplus_mm']=609.6-v['modeled_centerline_mm']
            v['surplus_insulated_material_mm3']=max(0,v['unmodeled_surplus_mm'])*math.pi*(v['engineering_diameter_mm']/2)**2
        routes[key]=v
    pm['routes']=routes
    for i,ks in pm['drive_local_free_tail_wire_keys'].items():pm['drive_local_free_tail_wire_keys'][i]=[rename(k) for k in ks]
    pm['SATA_data_SKU']='StarTech LSATA24,24in609.6mm,3directleads;head/stockcoilacceptancepending'
    pm['SATA_data_source']='https://media.startech.com/cms/pdfs/lsata24_datasheet.pdf'
    pm['checks']=[q for q in pm['checks'] if not (q.get('kind')=='stock_length_short' and q.get('route','').startswith('CABLE_R6_SATA_DATA_') and q.get('required_mm',0)<=609.6)]
    if 'sata_refine_meta' in m:
        sm=m['sata_refine_meta'];sm['changed_wire_keys']=[rename(k) for k in sm['changed_wire_keys']]
        sm['final_selected_stock_length_mm']=609.6;sm['short18in_not_purchase_selection']=True
        sm['superseded18in_length_checks']=sm['checks'];sm['checks']=[]
        sm['changes']={rename(n):dict(v,keys=[rename(k) for k in v['keys']],stock_mm=609.6 if n.startswith('CABLE_R6_SATA_DATA_') else v['stock_mm']) for n,v in sm['changes'].items()}
    packing=pm['surplus_packing']
    packing['per_route']=[{'route':n,'surplus_mm':v['unmodeled_surplus_mm'],'insulated_material_volume_mm3':v['surplus_insulated_material_mm3']} for n,v in routes.items() if 'unmodeled_surplus_mm' in v]
    packing['total_insulated_material_minimum_mm3']=sum(v['insulated_material_volume_mm3'] for v in packing['per_route'])+750*math.pi*2.75**2+300*math.pi*2.25**2
    packing['minimum_with_factor_mm3']=2*packing['total_insulated_material_minimum_mm3']
    basket=merge(ring(46.5,144,10,49.5,92,2,2.4),ring(46.5,144,70,49.5,92,2,2.4),ring(46.5,144,136,49.5,92,4,2.4))
    for x in (46.5,93.6):
        for y in (144.,233.6):basket=merge(basket,box((2.4,2.4,128),(x,y,12)))
    basket=merge(basket,box((14,12,5),(44,139,5)),box((14,12,5),(84,232,5)))
    base=merge(p['FRAME_R6_base'],box((14,18,5),(44,133,0)))
    for i,(x,y) in enumerate(((50,145),(90,240)),1):
        basket=basket.cut(cylinder(1.7,7,(x,y,4))).cut(box((5.9,5.9,2.6),(x-2.95,y-2.95,6.2)))
        base=base.cut(cylinder(1.7,7,(x,y,-1))).cut(cq.Solid.makeCone(3,1.5,1.5,cq.Vector(x,y,0),cq.Vector(0,0,1)))
        h[f'R6_PACKING_M3x10_CSK_{i}']=csk(10,(x,y,0));h[f'R6_PACKING_DIN562_M3_{i}']=nut3(x,y,6.3)
        p['FRAME_R6_feet20']=p['FRAME_R6_feet20'].cut(cylinder(4,23,(x,y,-21))).clean()
    # Open small lead saddles in the basket frame; these remove printable
    #material,never thin or delete the assigned cable envelope.
    basket=basket.cut(cylinder(2.1,8,(50,218,134)))
    from r6_power import _tube
    q=pm['routes']['CABLE_R6_SATA_B_NEXT150_TO_NA_FH1']
    saddle,_=_tube(q['vertices_mm'],q['engineering_diameter_mm']+1,q['engineering_bend_R_mm'])
    basket=basket.cut(saddle).clean()
    p['FRAME_R6_base']=one(base,'base+packingbearings')
    name='FRAME_R6_stock_lead_basket_FIXED';p[name]=one(basket,name)
    space=box((44.5,86,118),(49,147,20));raw=space.Volume()
    # Exclude existing assigned leads from the declared free storage volume.
    # AABB culling avoids touching the remote340-solid vendor endpoints.
    for n,s in (p|h|m['heads']|m['wires']).items():
        b=s.BoundingBox()
        if b.xmax<=49 or b.xmin>=93.5 or b.ymax<=147 or b.ymin>=233 or b.zmax<=20 or b.zmin>=138:continue
        space=space.cut(s)
    res['RESERVE_R6_RETAINED_STOCK_LEADS_REAR_LEFT_NOT_PACKED']=space.clean()
    packing=m['power_meta']['surplus_packing'];old=packing['reserved_box_volume_mm3']
    packing['reserved_box_volume_mm3']=old+space.Volume()
    m['power_meta']['checks']=[q for q in m['power_meta']['checks'] if q.get('kind')!='surplus_packing_volume_unqualified']
    if packing['minimum_with_factor_mm3']>packing['reserved_box_volume_mm3']:
        m['power_meta']['checks'].append({'kind':'surplus_packing_volume_unqualified','required_mm3':packing['minimum_with_factor_mm3'],'available_mm3':packing['reserved_box_volume_mm3']})
    m['packing_meta']={'part':name,'fixing_axes_xy_mm':[[50,145],[90,240]],'fasteners':'twoM3x10CSK andDIN562nuts,basebearinglandsandfeettoolholesincluded',
      'raw_additional_box_mm3':raw,'net_additional_space_mm3':space.Volume(),'free_volume_deducts':'existing hardware and assigned lead sweeps',
      'purpose':'retain factory and extension surplus in rear-left bay away fromGPU22mm intake and HDDdraws;softties through open frame',
      'packing_accepted':False,'limits':['Only a fixed open basket and free storage region are modeled;real coils/connector access/stocklength and flex not accepted','Volume allowance does not prove insulation radius,assembly sequence or load strength','Existing PWM surplus reserve is a shared allocation,not a second physical storage box']}
