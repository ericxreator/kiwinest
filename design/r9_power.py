# SPDX-License-Identifier: MIT
"""R9 complete standard-end power/data looms and single-drive service tails.

Every factory segment, purchased extension and retained surplus is counted.
Source XYZ, connector shells and flexible states are engineering proxies.
"""
from pathlib import Path
import json,math
import cadquery as cq
from build import box,cylinder,merge,bbox
from r6_power import _tube
from r4_riser_route import rounded_wire

BASELINE=Path(__file__).with_name('r9_routing_baseline.json')
SATA_EXTENSION_SOURCE='https://www.moddiy.com/products/1662/SATA-Power-Extension-Cable-50cm.html'


def apply_power(m):
    p,h,hd,w,sv,res=(m[k] for k in ('parts','hardware','heads','wires','service','reserves'))
    baseline=json.loads(BASELINE.read_text());routes={};checks=[];budgets={};tails={str(i):[] for i in (1,2,3)}
    def route(name,path,d,R,stock=None,allowance=24.,source=None,connector_lower_bound=None):
        shape,L=_tube(path,d,R);w[name]=shape
        info={'keys':[name],'vertices_mm':[list(v) for v in path],'modeled_centerline_mm':L,
          'engineering_diameter_mm':d,'engineering_bend_R_mm':R,
          'full_length_installed_and_flex_verified':False}
        if stock is not None:
            required=L+allowance+15.
            budget={'modeled_complete_centerline_mm':L,'connector_allowance_mm':allowance,'assembly_slack_mm':15.,
              'nominal_stock_mm':stock,'required_with_allowances_mm':required,'remaining_length_margin_mm':stock-required,
              'geometric_length_budget_passed':required<=stock,'connector_allowance_is_engineering_assumption':True,
              'factory_measurement_origin_and_installed_flex_verified':False,
              'minimum_required_margin_mm':25.,'minimum_margin_passed':stock-required>=25.}
            if connector_lower_bound is not None:
                budget['modeled_connector_length_lower_bound_mm']=connector_lower_bound
                if allowance<connector_lower_bound:raise ValueError('Connector allowance shorter than modeled connector lengths: '+name)
            info.update(nominal_stock_mm=stock,unmodeled_surplus_mm=stock-L,
              surplus_insulated_material_mm3=max(0.,stock-L)*math.pi*(d/2)**2,complete_length_budget=budget)
            budgets[name]=budget
            if stock-required<25.-1e-5:checks.append({'kind':'complete_stock_margin_short','route':name,'remaining_mm':stock-required,'required_minimum_mm':25.})
        if source:info['source']=source
        routes[name]=info
        return info
    # Reuse original standard connector engineering envelopes; board datums
    # and the entire x8 endpoint assembly remain fixed.
    for name,bb in baseline['heads'].items():
        if name=='POWER_R6_NA_FH1_SATA_HEAD_ENGINEERING_PROXY':continue
        if name.startswith('POWER_R6_FACTORY_UNUSED_') or name=='POWER_R6_EPS_FACTORY_UNUSED4_HALF_PARKED_PROXY':continue
        hd[name]=box(bb['size'],bb['min'])
    # Rotate the keyed standard4pin coupling toward the front. Its complete
    # extension exits below the200mm fan instead of entering its frame.
    hd['POWER_R6_EPS_FACTORY4plus4_STANDARD_PROXY']=box((9.5,12,9.5),(103.8,31,198))
    hd['POWER_R8_EPS_MODDIY_4PIN_FEMALE_PROXY']=box((9.5,12,9.5),(103.8,19,198))
    route('CABLE_R8_EPS_MODDIY_CO581_600',[(108.55,19,202.75),(108.55,10,202.75),(125,10,190),
      (215,10,190),(237,39,204),(243.8,39,195),(243.8,80,115),
      (243.8,219,48.5),(219.3,219,48.5)],6.5,7,600,48.)
    hd['POWER_R6_ATX_FACTORY24_STANDARD_MALE_PROXY']=box((52,12,14),(52,45,145))
    hd['POWER_R6_ATX_EXT24_STANDARD_FEMALE_PROXY']=box((52,12,14),(52,33,145))
    route('CABLE_R9_ATX_MODDIY_CAB529_600',[(78,33,152),(78,8,152),(78,8,180),(193,8,180),
      (220,20,110),(224,20,75),(224,130,75),(238,130,75),(238,178.65,48.5),(225.3,178.65,48.5)],
      11,6,600,40.,'https://www.moddiy.com/products/3246/Premium-Custom-PSU-Extension-Cable-24-Pin-Main-Power.html')
    # PSU source pieces are fused into these full source-to-head sweeps by
    # root integration. Their 14mm centerline is present here from Y96.
    route('CABLE_R6_ATX_FACTORY300',[(28.4,96,153),(28.4,64,153),(28.4,64,177),(78,64,177),(78,64,152),(78,57,152)],11,6,300)
    route('CABLE_R6_EPS_FACTORY300',[(25.4,96,166),(25.4,76,166),(15,76,166),(15,42,166),(98,24.75,166),(98,24.75,188),(108.55,24.75,188),(108.55,52,188),(108.55,52,202.75),(108.55,43,202.75)],4.5,4,300)
    hd['POWER_R6_GPU_FACTORY6plus2_STANDARD_PROXY']=box((14,18,18),(94.5,92,193.5))
    hd['POWER_R6_GPU_FACTORY_UNUSED_SECOND6plus2_PARKED_PROXY']=box((14,18,18),(110.2,135,193.5))
    route('CABLE_R6_GPU_FACTORY300',[(37.9,96,155),(37.9,72,155),(37.9,64,141.5),(90,64,141.5),(90,104,141.5),(90,104,190),(98,118,190),(98,118,202.5),(98,110,202.5)],6.5,6,300)
    route('CABLE_R6_GPU_FACTORY_SECOND150',[(105,110,202.5),(105,125,202.5),(117.2,125,202.5),(117.2,135,202.5)],6.5,6,150,40.,connector_lower_bound=36.)
    # Four original SATA plugs become standard couplings in the upper basket.
    # No custom PSU modular cable, splitter/backplane or SATA-to-GPU adapter.
    couplings={1:(26.,125.),2:(65.,125.),3:(85.,155.),4:(48.,160.)}
    for i,(x,y) in couplings.items():
        hd[f'POWER_R9_factory_SATA_{i}_STANDARD_PROXY']=box((28,14.5,12),(x-14,y,122))
        extension_width=30. if i==4 else 28.
        hd[f'POWER_R9_SATA_extension_{i}_STANDARD_PROXY']=box((extension_width,14.5,12),(x-extension_width/2,y-14.5,122))
    route('CABLE_R6_SATA_A_FACTORY300',[(37.4,96,146.5),(37.4,76,146.5),(50,76,146.5),(50,101,119),(23,101,119),(23,151,119),(23,151,128),(23,139.5,128)],5.5,4,300)
    route('CABLE_R6_SATA_A_NEXT150',[(29,139.5,128),(29,150,128),(29,150,119),(68,150,119),(68,150,128),(68,139.5,128)],5.5,4,150,32.,connector_lower_bound=29.)
    route('CABLE_R6_SATA_B_FACTORY300',[(19.4,96,147),(19.4,70,147),(19.4,70,119),(19.4,82,119),(82,82,119),(82,178,119),(82,178,128),(82,169.5,128)],5.5,4,300)
    route('CABLE_R6_SATA_B_NEXT150_TO_NA_FH1',[(88,169.5,128),(88,194,128),(51,194,128),(51,174.5,128)],5.5,4,150,32.,connector_lower_bound=29.)
    route('CABLE_R9_SATA_HUB_STARTECH_SATAPOWEXT8_203p2',[(48,145.5,128),(48,140.5,128),(48,140.5,119),(70,140.5,119),(70,90,119),(79,85,125.25),(79,74.5,125.25)],5.5,3,203.2,40.,connector_lower_bound=29.)
    # Model all four original unused Molex/FDD string segments. Every whole
    #150mm branch remains accounted for, with surplus retained in the basket.
    for i,y in enumerate((80.,115.,150.),1):
        hd[f'POWER_R6_FACTORY_UNUSED_MOLEX_{i}_PARKED_PROXY']=box((18,12,10),(76,y,163))
    hd['POWER_R6_FACTORY_UNUSED_FDD_PARKED_PROXY']=box((12,8,6),(79,185,165))
    hd['POWER_R6_EPS_FACTORY_UNUSED4_HALF_PARKED_PROXY']=box((10,9.5,9.5),(50,165,154))
    route('CABLE_R6_FACTORY_MOLEX_FDD_TO_PARK',[(19.4,96,157),(19.4,54,157),
      (82,54,186),(82,104,186),(82,104,168),(82,92,168)],5.5,3,300)
    route('CABLE_R9_UNUSED_MOLEX_NEXT150_2',[(88,92,168),(88,97,168),(98,97,168),(98,111,168),(88,111,168),(88,115,168)],5.5,3,150)
    route('CABLE_R9_UNUSED_MOLEX_NEXT150_3',[(85,127,168),(85,150,168)],5.5,3,150)
    route('CABLE_R9_UNUSED_FDD_NEXT150',[(85,162,168),(85,185,168)],5.5,3,150)
    # Rear gallery is below the HDD collector header. Data and power use
    # distinct Y planes; only bounded split-grommet holes cross its rear wall.
    local_meta={};data_tail_anchors={};wall_channels=[]
    for i in (1,2,3):
        q=next(v for v in m['drive_meta']['connectors'].values() if v['drive']==i and v['kind']=='power')
        hx,hy,hz=q['exit_xyz_mm'];anchorx=hx+(13.5 if i==3 else 16.);yp=239.5
        incoming_x=hx+(16.6 if i==3 else 19.5)
        cx,cy=couplings[i]
        # A standard 500mm cable gives ample connector/slack and service
        # allowance; no daisy-chain branch is removed for a single drive.
        # Go over the left collector roof, then down behind the rear wall.
        lane={1:15.,2:25.,3:35.}[i]
        if i==1:
            pts=[(cx,cy-14.5,128),(cx,101,128),(58,101,128),(58,107,139.5),(58,115,139.5),
              (lane,115,139.5),(lane,yp,139.5),(lane,yp,125),
              (incoming_x,yp,125),(incoming_x,yp,hz),(anchorx,yp,hz)]
        elif i==2:
            pts=[(cx,cy-14.5,128),(cx,99,128),(cx,99,139.5),(cx,122,139.5),
              (lane,122,139.5),(lane,yp,139.5),(lane,yp,125),
              (incoming_x,yp,125),(incoming_x,yp,hz),(anchorx,yp,hz)]
        else:
            pts=[(cx,cy-14.5,128),(cx,cy-26,128),(cx,cy-26,139.5),
              (lane,cy-26,139.5),(lane,yp,139.5),(lane,yp,125),
              (incoming_x,yp,125),(incoming_x,yp,hz),(anchorx,yp,hz)]
        # Descend rear gallery branches in increasing height order so each
        #crossing stays below the next incoming vertical, without deleting wire.
        rear_level={1:109.,2:117.,3:125.}[i]
        pts=[(x,y,rear_level if z==125. else z) for x,y,z in pts]
        # Incoming cable uses the first side of the broad head. One cap on
        # the other side is intentionally unused: each purchased extension
        # has one HDD end, not a newly invented branch.
        tail=[(anchorx,yp,hz),(hx,yp,hz),(hx,hy,hz)]
        key=f'CABLE_R9_SATA_POWER_{i}_MODDIY_CAB456_500'
        fixed,fl=_tube(pts,5.5,3);normal,nl=_tube(tail,5.5,3)
        fk=key+'_FIXED';tk=key+'_DRIVE_FREE_TAIL';w[fk]=fixed;w[tk]=normal;tails[str(i)].append(tk)
        total=fl+nl;required=total+40+15
        budget={'modeled_complete_centerline_mm':total,'connector_allowance_mm':40.,'assembly_slack_mm':15.,
          'nominal_stock_mm':500.,'required_with_allowances_mm':required,'remaining_length_margin_mm':500-required,
          'modeled_connector_length_lower_bound_mm':34.5,'minimum_required_margin_mm':25.,'minimum_margin_passed':500-required>=25.,
          'geometric_length_budget_passed':required<=500.,'connector_allowance_is_engineering_assumption':True,
          'factory_measurement_origin_and_installed_flex_verified':False}
        routes[key]={'keys':[fk,tk],'paths_mm':[pts,tail],'modeled_centerline_mm':total,'engineering_diameter_mm':5.5,
          'engineering_bend_R_mm':3.,'nominal_stock_mm':500.,'unmodeled_surplus_mm':500.-total,
          'surplus_insulated_material_mm3':max(0,500.-total)*math.pi*2.75**2,'complete_length_budget':budget,
          'source':SATA_EXTENSION_SOURCE,'full_length_installed_and_flex_verified':False}
        budgets[key]=budget
        if budget['remaining_length_margin_mm']<25:checks.append({'kind':'complete_stock_margin_short','route':key,'remaining_mm':budget['remaining_length_margin_mm']})
        # The whole normal local tail stays with its drive plug; construct an
        # equal-length parked state after +Y15, using open rear service space.
        def parked(u):return [(anchorx,yp,hz),(anchorx-3.5,yp,hz),(anchorx-3.5,u,hz),(hx,u,hz),(hx,hy+15,hz)]
        lo=max(yp+6.001,hy+15+3.001);hi=lo+80
        if rounded_wire(parked(lo),3).Length()>nl+1e-6:
            raise ValueError('Cannot retain the complete normal power tail length in its parked pose')
        extra=0.;target=nl
        for _ in range(35):
            u=(lo+hi)/2
            if rounded_wire(parked(u),3).Length()<target:lo=u
            else:hi=u
        parkpath=parked((lo+hi)/2);pk=f'SERVICE_R9_SATA_POWER_{i}_TAIL_PARKED';sv[pk],pl=_tube(parkpath,5.5,3)
        if abs(pl-nl)>1e-5:raise ValueError('Power parking must retain its full normal tail length')
        local_meta[str(i)]={'normal_tail':tk,'parked_tail_service':pk,'normal_path_mm':tail,
          'parked_path_mm':parkpath,'normal_length_mm':nl,'parked_length_mm':pl,
          'assembly_slack_used_for_park_mm':extra,'same_purchased_cable':True,'physical_flex_verified':False}
        wall_channels.append({'center_xz_mm':[hx,hz],'diameter_mm':6.5,'wire_key':tk})
        # Three direct LSATA24 leads, no backplane. Cross the rear floor below
        # the original x8 low return, then approach the board's +X ports.
        qd=next(v for v in m['drive_meta']['connectors'].values() if v['drive']==i and v['kind']=='data')
        dx,dy,dz=qd['exit_xyz_mm'];data_y=245.2;end=next(v['cable_exit_xyz_mm'] for v in m['mainboard_meta']['SATA']['selected_ports'] if v['drive']==i)
        level=15.;cross_y={1:220.,2:226.,3:232.}[i];lane={1:232.3,2:238.5,3:244.5}[i]
        free=[(dx,dy,dz),(dx,data_y,dz),(dx,data_y,74.)]
        off={1:23.5,2:23.5,3:20.5}[i];vx=dx+off
        fixed=[(dx,data_y,74.),(dx,data_y,70.),(vx,data_y,70.),(vx,data_y,level),(vx,cross_y,level),
          (lane,cross_y,level),(lane,end[1],level),(lane,end[1],end[2]),end]
        dn=f'CABLE_R9_SATA_DATA_{i}_STARTECH_LSATA24_609p6'
        full=free+fixed[1:]
        info=route(dn,full,5.5,3,609.6,40.,connector_lower_bound=38.)
        w.pop(dn)
        df=dn+'_FIXED';dt=dn+'_DRIVE_FREE_TAIL'
        w[df],dfl=_tube(fixed,5.5,3);w[dt],dtl=_tube(free,5.5,3)
        assert abs(dfl+dtl-info['modeled_centerline_mm'])<1e-5
        info['keys']=[df,dt];tails[str(i)].append(dt)
        def data_parked(u):return [(dx,data_y,74.),(dx,data_y,78.),(dx,u,78.),(dx,u,dz),(dx,dy+15,dz)]
        lo=max(data_y+6.001,dy+15+3.001);hi=lo+80.
        assert rounded_wire(data_parked(lo),3).Length()<=dtl
        for _ in range(35):
            u=(lo+hi)/2
            if rounded_wire(data_parked(u),3).Length()<dtl:lo=u
            else:hi=u
        dpp=data_parked((lo+hi)/2);dpk=f'SERVICE_R9_SATA_DATA_{i}_TAIL_PARKED';sv[dpk],dpl=_tube(dpp,5.5,3)
        if abs(dpl-dtl)>1e-5:raise ValueError('Data parking must retain its full normal tail length')
        local_meta[str(i)]['data']={'normal_tail':dt,'parked_tail_service':dpk,
          'normal_path_mm':free,'parked_path_mm':dpp,'normal_length_mm':dtl,'parked_length_mm':dpl,
          'same_purchased_cable':True,'physical_flex_verified':False}
        wall_channels.append({'center_xz_mm':[dx,dz],'diameter_mm':6.5,'wire_key':f'CABLE_R9_SATA_DATA_{i}_STARTECH_LSATA24_609p6'})
    gpu=m['gpu_power_meta'];gr=gpu['route_key'];glen=gpu['modeled_wire_centerline_mm'];gstock=gpu['nominal_stock_mm'];greq=glen+48+15
    gb={'modeled_complete_centerline_mm':glen,'connector_allowance_mm':48.,'assembly_slack_mm':15.,'nominal_stock_mm':gstock,
      'required_with_allowances_mm':greq,'remaining_length_margin_mm':gstock-greq,
      'modeled_connector_length_lower_bound_mm':36.3,'minimum_required_margin_mm':25.,'minimum_margin_passed':gstock-greq>=25.,'geometric_length_budget_passed':greq<=gstock,
      'connector_allowance_is_engineering_assumption':True,'factory_measurement_origin_and_installed_flex_verified':False}
    gpu['complete_length_budget']=gb;budgets[gr]=gb
    routes[gr]={'keys':[gpu['fixed_wire_key'],gpu['free_wire_key']],'paths_mm':gpu['normal_paths'],
      'modeled_centerline_mm':glen,'engineering_diameter_mm':8.,'engineering_bend_R_mm':8.,'nominal_stock_mm':gstock,
      'unmodeled_surplus_mm':gstock-glen,'surplus_insulated_material_mm3':max(0,gstock-glen)*math.pi*16,
      'complete_length_budget':gb,'full_length_installed_and_flex_verified':False}
    if gb['remaining_length_margin_mm']<25:checks.append({'kind':'complete_stock_margin_short','route':gr,'remaining_mm':gb['remaining_length_margin_mm']})
    for name,v in m['controls_meta']['routes'].items():
        routes[name]={'keys':[name],'vertices_mm':v['path_mm'],'modeled_centerline_mm':v['modeled_mm'],
          'engineering_diameter_mm':v['engineering_diameter_mm'],'engineering_bend_R_mm':v['engineering_bend_R_mm'],
          'nominal_stock_mm':v['stock_mm'],'unmodeled_surplus_mm':v['unmodeled_surplus_mm'],
          'surplus_insulated_material_mm3':v['surplus_insulated_material_mm3'],'complete_length_budget':v['complete_length_budget'],
          'full_length_installed_and_flex_verified':False}
        budgets[name]=v['complete_length_budget']
    material=sum(r.get('surplus_insulated_material_mm3',0.) for r in routes.values())+300*math.pi*2.25**2+m['controls_meta'].get('NA_EC1_stock_allocation',{}).get('unused_300mm',300)*math.pi*1.5**2
    m['power_meta']={'status':'R9_COMPLETE_POWER_DATA_CAD_PHYSICAL_FLEX_PENDING','routes':routes,'checks':checks,
      'complete_stock_length_budgets':budgets,'drive_local_free_tail_wire_keys':tails,
      'HDD_service_tail_parking':local_meta,'rear_wall_wire_channels':wall_channels,
      'rear_gallery_Y_mm':{'power':239.5,'data':245.2},
      'extensions':{'ATX24':'MODDIY CAB529 configured600mm standard ATX24 male/female extension','EPS':'MODDIY CO581 600mm','GPU':gpu['extension'],
        'HDD_power':'3xMODDIY CAB456 500mm standard SATA15pin male/female','hub':'StarTech SATAPOWEXT8 203.2mm'},
      'SATA_data_SKU':'3xStarTech LSATA24 609.6mm direct motherboard-to-HDD',
      'SATA_data_source':'https://media.startech.com/cms/pdfs/lsata24_datasheet.pdf',
      'expected_mating_pairs':[],'exact_same_net_junction_spheres':[],
      'HDD_service_conditions':['Power off;remove rear skin/access covers;unplug only target heads +Y15 and retain full tail in its parked pose.',
        'Other drives,factory chains,standard couplings and fixed cable spans remain installed.'],
      'surplus_packing':{'total_insulated_material_minimum_mm3':material,'suggested_packing_allowance_factor':2,
        'minimum_with_factor_mm3':2*material,'reserved_box_volume_mm3':0.,'packing_accepted':False,
        'unused_Molex_FDD_nominal_segments_mm':[300,150,150,150],
        'unused_Molex_FDD_all_four_segments_modeled':True,'unused_original_EPS4_half_mm':300,
        'unused_included_NA_EC1_mm':m['controls_meta'].get('NA_EC1_stock_allocation',{}).get('unused_300mm',300),'per_route':[{'route':n,'surplus_mm':v['unmodeled_surplus_mm'],
          'insulated_material_volume_mm3':v['surplus_insulated_material_mm3']} for n,v in routes.items() if 'unmodeled_surplus_mm' in v]},
      'head_shapes_are_engineering_proxies':True,'wire_sections_measured':False,
      'native_factory_exit_points_engineering':{'ATX':[28.4,96,153],'EPS':[25.4,96,166],'GPU':[37.9,96,155],
        'SATA_A':[37.4,96,146.5],'SATA_B':[19.4,96,147],'MOLEX_FDD':[19.4,96,157]},
      'limits':['No PSU internal pinout, proprietary modular cable or cut factory lead.',
        'Nominal stock, complete CAD paths and packing volumes do not certify received cable usability,flexibility or thermal acceptance.']}
    return m['power_meta']
