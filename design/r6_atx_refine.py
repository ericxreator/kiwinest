# SPDX-License-Identifier: MIT
"""Bounded R6 ATX/EPS/native-GPU routing corrections; frozen r6_power untouched.

Only named standard-end connector proxies and their installed planning routes
are replaced.  An exact small same-net fork volume is recorded, never a whole
wire-pair collision exclusion.  Stock-length and unmeasured wire gates remain.
"""
from __future__ import annotations
import math
import cadquery as cq
from build import box,bbox
from r6_power import _tube


def apply_atx_refine(m):
    p=m['power_meta'];heads=m['heads'];wires=m['wires']
    changed_wires=[];changed_heads=[];checks=[];newroutes={}

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

    # Keep the standard ATX coupling between DATA2/DATA3 columns.  SATA refine
    # moves their horizontal tail stations toY53, away from the Y44 power leads.
    k='CABLE_R6_ATX_FACTORY300'
    points=[list(v) for v in p['routes'][k]['vertices_mm']]
    points[0]=[24,82,215];points[1]=[26,72,215]
    replace(k,points,11,6,300)
    a=next(v['cable_exit_xyz_mm'] for v in m['mainboard_meta']['power'] if v['kind']=='ATX24')
    replace('CABLE_R6_ATX_PHANTEKS_PH_CB24P_BK500',[[71,44,188.2],[80,44,188.2],
      [80,30,188.2],[80,30,174.5],[80,8,174.5],[191,8,174.5],
      [240,32,38],[240,118,38],[240,118,51],[240,a[1],a[2]],a],11,6,500)

    # EPS4 active conductors use the rightmost wire-gutter lane.  The original
    # unused4pin half is still retained/parked and counted by r6_power metadata.
    replace('CABLE_R6_EPS_FACTORY300',[[37,82,218],[28,62,218],
      [28,62,191.5],[28,11.2,191.5],[195,11.2,191.5],
      [195,34.75,204],[205,34.75,204]],4.5,4,300)
    for key,origin in (
      ('POWER_R6_EPS_EXT4plus4_STANDARD_PROXY',(217,30,195)),
      ('POWER_R6_EPS_EXTENSION_UNUSED4_HALF_PARKED_PROXY',(202,225,43.75)),
      ('POWER_R6_GPU_FACTORY_UNUSED_SECOND6plus2_PARKED_PROXY',(228,16,110))):
        old=heads[key].BoundingBox()
        heads[key]=box((old.xlen,old.ylen,old.zlen),origin)
        changed_heads.append(key)
    # Count the original two4pin halves exactly once: active4 here and unused4
    # already parked in the gutter. The female extension remains a full8 socket.
    active='POWER_R6_EPS_FACTORY4plus4_STANDARD_PROXY'
    heads[active]=box((12,9.5,9.5),(205,30,199.25));changed_heads.append(active)
    e=next(v['cable_exit_xyz_mm'] for v in m['mainboard_meta']['power'] if v['kind']=='ATX4_CPU')
    replace('CABLE_R6_EPS_AK_CBPW08_40BK400',[[229,39,204],[237,39,204],
      [243.8,39,195],[243.8,e[1],e[2]],e],6.5,7,400)
    replace('CABLE_R6_EPS_UNUSED4_HALF_BRANCH_PROXY',[[230,219,48.5],
      [230,230,48.5],[212,230,48.5]],3.2,3)

    # Gland inlet is an unmeasured assumption. Move its outer endpoint forward
    # inside the actual wire-only bay, rather than cutting the independent air.
    # X36/Y74 is clear of ATX's X26/Y78 drop and the two fixed HDD head rows.
    replace('CABLE_R6_GPU_FACTORY300',[[34,82,208],[35,74,208],
      [35,74,163],[35,5.8,163],[181.5,5.8,163],
      [181.5,25,155],[181.5,25,167]],6.5,6,300)
    replace('CABLE_R6_GPU_FACTORY_SECOND150',[[188.5,25,167],[188.5,25,153],
      [188.5,42,153],[188.5,42,102],[235,42,102],[235,25,102],[235,25,110]],6.5,6,150)

    fork={'a':'CABLE_R6_EPS_AK_CBPW08_40BK400',
      'b':'CABLE_R6_EPS_UNUSED4_HALF_BRANCH_PROXY',
      'center_mm':[230,219,48.5],'radius_mm':4.,
      'sphere_latitude_degrees':[-90,90],
      'meaning':'Only the shared local4+4 conductor fork; an overlap outside this exact sphere remains a collision.',
      'source_status':'Engineering branch/separation position,not a dimensioned Akasa factory split'}
    p['exact_same_net_junction_spheres']=[fork]
    p['native_gland_exit_points_engineering'].update(ATX=[24,82,215],EPS=[37,82,218],GPU=[34,82,208])
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
      'routes':newroutes,'checks':checks,'exact_same_net_junction_spheres':[fork],
      'gland_y_status':'Y82 is an engineering inlet assumption in the wire-only gutter;source ENP exit remains unmeasured.',
      'SATA_coordination':'SATArefine owns all SATA shapes;DATA2/3 horizontal tailstationY53;DATA1front190/Y5.5,DATA2front184/Y11.2,DATA3front184/Y5.5;EPSgutterdropX28/Y62.',
      'EPS_joint_bbox_mm':{k:bbox(heads[k]) for k in changed_heads},
      'GPU_factory_male_joint_unchanged':p['GPU_factory_joint'],
      'limits':['Four-pin grouping/separation oforiginalEPS4+4 andAkasa4+4 requires received-cable fit-up;no PSUinternalpinout changes.',
        'Round sections and bend radii are engineering envelopes,not manufacturer cable exterior CAD.',
        'Nominalcenterline/slack alone does not certify factory total usable wire length or packed surplus.',
        'Only the explicit4mm same-net fork sphere is a connection allowance; no fullpair exemptions.']}
    m['atx_refine_meta']=meta
    return meta
