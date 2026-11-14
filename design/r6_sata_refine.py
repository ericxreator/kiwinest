# SPDX-License-Identifier: MIT
"""R6 SATA-only postprocess; original r6_power.py is kept frozen.

Retains the original5.5mm planning section and HDD/motherboard ports. A
standard power extension moves the fourth factory head to a fixed coupling;
no flat cable section is invented merely to eliminate a crossing.
"""
import math
from build import box
from r6_power import _tube


def apply_sata_refine(m):
    wires=m['wires'];heads=m['heads'];pm=m['power_meta'];routes=pm['routes'];dm=m['drive_meta']['connectors']
    prefixes=('CABLE_R6_SATA_A_','CABLE_R6_SATA_B_','CABLE_R6_SATA_DATA_')
    names=[n for n in routes if n.startswith(prefixes)]
    old={n:routes[n] for n in names};oldkeys={k for n in names for k in old[n]['keys']}
    for k in oldkeys:wires.pop(k,None)
    tails=pm['drive_local_free_tail_wire_keys']
    for owner in tails:tails[owner]=[k for k in tails[owner] if k not in oldkeys]
    changes={};localchecks=[]

    def route(name,pts,R=4.,tail_boxes=(),new_stock=None):
        info=old[name] if name in old else {
          'engineering_diameter_mm':5.5,'nominal_stock_mm':new_stock,
          'full_length_installed_and_flex_verified':False}
        d=info['engineering_diameter_mm'];nominal=info['nominal_stock_mm']
        shape,L=_tube(pts,d,R);keys=[]
        for owner,label,origin,size in tail_boxes:
            cutter=box(size,origin);tail=shape.intersect(cutter).clean();shape=shape.cut(cutter).clean()
            if tail.Solids():
                key=name+'_'+label;wires[key]=tail;keys.append(key);tails[str(owner)].append(key)
        if shape.Solids():wires[name]=shape;keys.insert(0,name)
        new=dict(info,keys=keys,vertices_mm=[list(v) for v in pts],modeled_centerline_mm=L,
                 engineering_bend_R_mm=R,unmodeled_surplus_mm=nominal-L,
                 surplus_insulated_material_mm3=max(0,nominal-L)*math.pi*(d/2)**2)
        routes[name]=new;changes[name]={'old_vertices_mm':info.get('vertices_mm'),'new_vertices_mm':new['vertices_mm'],
            'centerline_mm':L,'stock_mm':nominal,'keys':keys,'engineering_diameter_mm':d}
        if L>nominal+1e-4:localchecks.append({'kind':'stock_length_short','route':name,'required_mm':L,'available_mm':nominal})

    p={}
    for i in (1,2,3):
        q=dm[f'R6_SATA_power_{i}_HDD_HEAD_ENGINEERING_PROXY'];o=q['origin_mm'];s=q['size_mm']
        p[i]=(o[0]+s[0]/2,o[1]+s[1]/2,o[2]+s[2])
    x1,y1,z1=p[1];x2,y2,z2=p[2];x3,y3,z3=p[3]
    route('CABLE_R6_SATA_A_FACTORY300',[(17.5,85.5,206),(17.5,76,206),
        (17.5,76,190),(x1-3,80,184),(x1-3,y1,184),(x1-3,y1,z1)],4,
        [(1,'DRIVE1_IN_FREE_TAIL',(x1-6,75,177),(6,36,18))])
    route('CABLE_R6_SATA_A_NEXT150',[(x1+3,y1,z1),(x1+3,y1,191),
        (x1+3,115,191),(x2,115,191),(x2,y2,191),(x2,y2,z2)],4,
        [(1,'DRIVE1_OUT_FREE_TAIL',(x1,75,177),(6,36,18)),
         (2,'DRIVE2_IN_FREE_TAIL',(x2-3,75,177),(6,36,18))])
    route('CABLE_R6_SATA_B_FACTORY300',[(18,85.5,224),(18,67.5,224),(18,67.5,191),
        (7.5,67.5,191),(7.5,123,191),(x3-3,123,191),(x3-3,y3,191),(x3-3,y3,z3)],4,
        [(3,'DRIVE3_IN_FREE_TAIL',(x3-6,75,177),(6,36,18))])
    # The fourth factory SATA head now mates with a standard extension above
    # the fixed basket. Only its HDD3-local tail moves at disk service; the
    # coupling and the rest of both cable spans remain fixed.
    native_hub='CABLE_R6_SATA_B_NEXT150_TO_NA_FH1'
    hub_extension='CABLE_R8_SATA_STARTECH_SATAPOWEXT8_203p2'
    route(native_hub,[(x3+3,y3,z3),(x3+3,y3,188),
        (x3+3,143,188),(70,163,188),(70,163,182)],4,
        [(3,'DRIVE3_OUT_FREE_TAIL',(x3,75,177),(6,36,18))])
    route(hub_extension,[(70,163,158),(70,163,132),(53,163,132),
        (53,157,102),(43,157,102)],4,new_stock=203.2)
    native_head='POWER_R8_SATA_FACTORY_FOURTH_STANDARD_COUPLING_PROXY'
    female_head='POWER_R8_SATAPOWEXT8_FEMALE_COUPLING_PROXY'
    hub_head='POWER_R6_NA_FH1_SATA_HEAD_ENGINEERING_PROXY'
    heads[native_head]=box((14.5,28,12),(62.75,149,170))
    # The official extension's product width is30mm, larger than the original
    # factory-head proxy. Its14.5mm axial length remains an engineering fit-up.
    heads[female_head]=box((14.5,30,12),(62.75,148,158))
    heads[hub_head]=box((14.5,30,12),(28.5,142,96))
    native_shape,_=_tube(routes[native_hub]['vertices_mm'],5.5,4)
    cap_checks={
      'native_wire_to_fourth_head_mm3':native_shape.intersect(heads[native_head]).Volume(),
      'inline_head_pair_mm3':heads[native_head].intersect(heads[female_head]).Volume(),
      'extension_wire_to_female_mm3':wires[hub_extension].intersect(heads[female_head]).Volume(),
      'extension_wire_to_hub_head_mm3':wires[hub_extension].intersect(heads[hub_head]).Volume()}
    if any(v>1e-4 for v in cap_checks.values()):
        raise ValueError('SATA extension cap interfaces must not overlap')
    hub_budgets={}
    for key,head_allowance in ((native_hub,24.),(hub_extension,30.)):
        q=routes[key];required=q['modeled_centerline_mm']+head_allowance+15.
        budget={'modeled_complete_centerline_mm':q['modeled_centerline_mm'],
          'connector_allowance_mm':head_allowance,'assembly_slack_mm':15.,
          'nominal_stock_mm':q['nominal_stock_mm'],
          'required_with_allowances_mm':required,
          'remaining_length_margin_mm':q['nominal_stock_mm']-required,
          'minimum_required_margin_mm':20.,
          'geometric_length_budget_passed':required<=q['nominal_stock_mm'],
          'minimum_margin_passed':q['nominal_stock_mm']-required>=20.,
          'connector_allowance_is_engineering_assumption':True,
          'factory_measurement_origin_and_installed_flex_verified':False}
        q['complete_length_budget']=budget;hub_budgets[key]=budget
        if not budget['minimum_margin_passed']:
            localchecks.append({'kind':'complete_stock_margin_short','route':key,
              'required_mm':required+20.,'available_mm':q['nominal_stock_mm']})
    hub_meta={'SKU':'StarTech SATAPOWEXT8','nominal_length_mm':203.2,
      'source_url':'https://media.startech.com/cms/pdfs/satapowext8_datasheet.pdf',
      'type':'Standard15pinSATApower male-to-female extension;not a modularPSUcable',
      'published_wire_gauge_AWG':18,'published_product_width_mm':30.,
      'published_product_height_mm':8.,
      'engineering_head_axial_length_mm':14.5,'engineering_head_height_mm':12.,
      'engineering_wire_diameter_mm':5.5,'engineering_bend_radius_mm':4.,
      'factory_fourth_SATA_head':native_head,
      'extension_female_head':female_head,'extension_hub_head':hub_head,
      'complete_length_budgets':hub_budgets,'cap_interface_intersections_mm3':cap_checks,
      'drive3_service_scope':'ReleaseonlythedeclaredHDD3localfreetail;fourthheadinlinecouplingandextensionremainfixed.Nofactorystringisexcludedfromcollisionchecks.',
      'stock_packing_connector_seating_retention_and_flex_verified':False}
    pm['SATA_hub_extension']=hub_meta
    pm['extensions']['SATA_hub']='StarTechSATAPOWEXT8,8in203.2mm,standard15pinSATApowerextension'
    m['controls_meta']['powered_fan_hub']['SATA_head_bbox_mm']=[[28.5,142.,96.],[43.,172.,108.]]
    m['drive_meta']['service']['3']['parking_limit']='Targetdriveheadsaremodeledat+Z15;onlylocalflexibletailsmove.ThefourthSATAheadinlinecouplingandNAFH1extensionremainfixed.'
    # Keep the front crossing belowY14; reach the outer right lanes only
    # after passing the right-front post. DistinctX lanes separate the long
    # descending diagonals, where merely separating topZ did not suffice.
    sata=m['mainboard_meta']['SATA']['selected_ports']
    for i,(fronty,highz,lanex,bypass,bypassy) in enumerate(
            ((5.5,192.,232.3,23.,43.),(5.5,184.,238.5,31.,53.),(11.2,184.,244.5,90.,53.)),1):
        q=dm[f'R6_SATA_data_{i}_HDD_HEAD_ENGINEERING_PROXY'];o=q['origin_mm'];s=q['size_mm']
        hx=o[0]+s[0]/2;hy=o[1]+s[1]/2;hz=o[2]+s[2]
        end=next(v['cable_exit_xyz_mm'] for v in sata if v['drive']==i)
        pts=[(hx,hy,hz),(hx,hy,highz)]
        if i!=1:pts += [(hx,bypassy,highz),(bypass,bypassy,highz)]
        pts += [(bypass,fronty,highz),(219 if i==3 else 226,fronty,highz),
                (lanex,25,highz-(24 if i==3 else 10))]
        if i==1:pts += [(lanex,end[1]-6,end[2])]
        pts += [(lanex,end[1],end[2]),tuple(end)]
        route(f'CABLE_R6_SATA_DATA_{i}_STARTECH_LSATA18_457p2',pts,3,
             [(i,f'DRIVE{i}_DATA_FREE_TAIL',(hx-3,48,176),(6,25,18))])
    # Replace only SATA-related length checks and packing rows. Do not hide
    # another owner's unresolved ATX/EPS or physical packing qualifications.
    pm['checks']=[v for v in pm['checks'] if v.get('route') not in names]+localchecks
    packing=pm['surplus_packing']
    packing['per_route']=[{'route':n,'surplus_mm':v['unmodeled_surplus_mm'],
        'insulated_material_volume_mm3':v['surplus_insulated_material_mm3']} for n,v in routes.items() if 'unmodeled_surplus_mm' in v]
    total=sum(v['insulated_material_volume_mm3'] for v in packing['per_route'])+750*math.pi*(5.5/2)**2+300*math.pi*(4.5/2)**2
    packing['total_insulated_material_minimum_mm3']=total;packing['minimum_with_factor_mm3']=2*total
    pm['SATA_refine']={'changes':changes,'changed_wire_keys':[k for n in changes for k in changes[n]['keys']],
       'checks':localchecks,'endpoint_positions_changed':True,'wire_section_changed':False,
       'endpoint_change_scope':'FactoryfourthSATAheadmovedtoinlineextensioncoupling;HDDandmotherboardportsunchanged;NAFH1portpositionunchanged.',
       'SATA_hub_extension':hub_meta,
       'power_layers_mm':{'A_in_z':184,'A_next_z_y':[191,115],'B_in_z_y':[191,123]},
       'data_lanes_X_mm':[232.3,238.5,244.5],'data_bypass_Y_mm':[None,53,53],
       'limits':['5.5mmdiameter/R3-4remainengineeringproxies,notmeasuredStarTechsectionorcertifiedminimumradius',
          'Root mustapplyATX/EPSrefine andnearbycontrolscheck;allflex-tailparkingandstockcoilsremainphysicalgates']}
    m['sata_refine_meta']=pm['SATA_refine']
    return m['sata_refine_meta']
