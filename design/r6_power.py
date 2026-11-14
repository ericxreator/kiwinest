# SPDX-License-Identifier: MIT
"""R6 factory power looms, standard-end extensions and three direct SATA leads.

All cable sections/connector shells are installation proxies.  Nominal stock
length is compared with actual curved centerline; surplus is not erased.
Factory loom gland, packing, insulation diameters and final flex are unmeasured.
"""
from __future__ import annotations
import math
import cadquery as cq
from build import box,cylinder,merge,bbox
from r4_riser_route import rounded_wire


def _tube(points,diameter=5.5,radius=6.):
    path=rounded_wire(points,radius)
    tangent=path._r4_edges[0].tangentAt(0)
    profile=cq.Workplane(cq.Plane(origin=points[0],normal=tangent)).circle(diameter/2).val()
    shape=cq.Solid.sweep(profile,[],path,True,False).clean()
    if not shape.isValid() or len(shape.Solids())!=1:
        raise ValueError('Cable sweep must be one valid solid')
    return shape,path.Length()


def apply_power(m):
    """Mutate only the supplied R6 assembly; return JSON-safe integration data."""
    p,h,heads,wires,res=m['parts'],m['hardware'],m['heads'],m['wires'],m['reserves']
    routes={};checks=[];tail_keys={str(i):[] for i in (1,2,3)}
    native_starts={'ATX':[24,85.5,215],'EPS':[34,85.5,221],
      'GPU':[34,85.5,208],'SATA_A':[18,85.5,206],
      'SATA_B':[18,85.5,224],'MOLEX_FDD':[28,85.5,224]}

    def route(name,points,d=5.5,R=6.,nominal=None,tail_boxes=()):
        s,L=_tube(points,d,R)
        keys=[]
        # Geometric split preserves the continuous bend; never delete an entire
        # two-drive factory string when only one drive is unplugged.
        for owner,label,origin,size in tail_boxes:
            cut=box(size,origin);tail=s.intersect(cut).clean();s=s.cut(cut).clean()
            if tail.Solids():
                key=name+'_'+label;wires[key]=tail;keys.append(key);tail_keys[str(owner)].append(key)
        if s.Solids():wires[name]=s;keys.insert(0,name)
        info={'keys':keys,'vertices_mm':[list(v) for v in points],
          'modeled_centerline_mm':L,'engineering_diameter_mm':d,'engineering_bend_R_mm':R,
          'full_length_installed_and_flex_verified':False}
        if nominal is not None:
            info.update(nominal_stock_mm=nominal,unmodeled_surplus_mm=nominal-L,
                surplus_insulated_material_mm3=max(0,nominal-L)*math.pi*(d/2)**2)
            if L>nominal+1e-4:checks.append({'kind':'stock_length_short','route':name,'required_mm':L,'available_mm':nominal})
        routes[name]=info
        return L

    def head(name,size,origin):heads[name]=box(size,origin);return name
    # Standard ATX24 coupling stays above the drive bodies, below the PSU floor,
    # and left of the GPU air/extraction column.  52x14 is a shell assumption.
    atx_native=head('POWER_R6_ATX_FACTORY24_STANDARD_MALE_PROXY',(12,52,14),(47,18,181.2))
    atx_extension=head('POWER_R6_ATX_EXT24_STANDARD_FEMALE_PROXY',(12,52,14),(59,18,181.2))
    eps_native=head('POWER_R6_EPS_FACTORY4plus4_STANDARD_PROXY',(12,18,18),(188,30,195))
    eps_extension=head('POWER_R6_EPS_EXT4plus4_STANDARD_PROXY',(12,18,18),(200,30,195))
    head('POWER_R6_EPS_FACTORY_UNUSED4_HALF_PARKED_PROXY',(10,9.5,9.5),(24,60,229))
    gpu_native=head('POWER_R6_GPU_FACTORY6plus2_STANDARD_PROXY',(14,18,18),(178,16,167))
    gpu_park=head('POWER_R6_GPU_FACTORY_UNUSED_SECOND6plus2_PARKED_PROXY',(14,18,18),(217,16,100))
    eps_unused=head('POWER_R6_EPS_EXTENSION_UNUSED4_HALF_PARKED_PROXY',(10,9.5,9.5),(229,225,43.75))

    route('CABLE_R6_ATX_FACTORY300', [native_starts['ATX'],[26,78,215],
      [26,78,174.5],[26,30,174.5],[40,30,174.5],[40,30,188.2],
      [40,44,188.2],[47,44,188.2]],11,6,300)
    power={x['kind']:x for x in m['mainboard_meta']['power']}
    aend=power['ATX24']['cable_exit_xyz_mm'];eend=power['ATX4_CPU']['cable_exit_xyz_mm']
    route('CABLE_R6_ATX_PHANTEKS_PH_CB24P_BK500',[[71,44,188.2],[80,44,188.2],
      [80,30,188.2],[80,30,174.5],[80,8,174.5],[200,8,174.5],
      [200,8,145],[240,32,145],[240,aend[1],aend[2]],aend],11,6,500)
    route('CABLE_R6_EPS_FACTORY300',[native_starts['EPS'],[34,68,221],
      [34,68,191.5],[34,11.2,191.5],[178,11.2,191.5],[178,39,204],[188,39,204]],4.5,4,300)
    route('CABLE_R6_EPS_AK_CBPW08_40BK400',[[212,39,204],[228,39,204],
      [243.8,39,195],[243.8,eend[1],eend[2]],eend],6.5,7,400)
    route('CABLE_R6_EPS_UNUSED4_HALF_BRANCH_PROXY',[[243.8,eend[1],eend[2]],
      [243.8,229.75,48.5],[239,229.75,48.5]],3.2,2,None)

    # Two separate wire exits at the first daisy-chain head avoid pretending
    # the incoming and outgoing factory conductors occupy one solid tube.
    route('CABLE_R6_GPU_FACTORY300',[native_starts['GPU'],[34,75,208],
      [34,75,163],[34,5.8,163],[181.5,5.8,163],[181.5,25,155],[181.5,25,167]],6.5,6,300)
    route('CABLE_R6_GPU_FACTORY_SECOND150',[[188.5,25,167],[188.5,25,84],
      [224,25,84],[224,25,100]],6.5,6,150)

    # SATA A: first/second drive.  Local tails alone are movable at service time.
    dcon=m['drive_meta']['connectors']
    c={}
    for i in (1,2,3):
        q=dcon[f'R6_SATA_power_{i}_HDD_HEAD_ENGINEERING_PROXY'];o=q['origin_mm'];sz=q['size_mm']
        c[i]=[o[0]+sz[0]/2,o[1]+sz[1]/2,o[2]+sz[2]]
    x1,y1,z1=c[1];x2,y2,z2=c[2];x3,y3,z3=c[3]
    route('CABLE_R6_SATA_A_FACTORY300',[[18,85.5,206],[18,76,206],
      [28,76,188],[28,114,188],[x1-3,114,188],[x1-3,y1,188],[x1-3,y1,z1]],5.5,4,300,
      [(1,'DRIVE1_IN_FREE_TAIL',[x1-6,75,177],[6,36,18])])
    route('CABLE_R6_SATA_A_NEXT150',[[x1+3,y1,z1],[x1+3,y1,188],
      [x1+3,114,188],[x2,114,188],[x2,y2,188],[x2,y2,z2]],5.5,4,150,
      [(1,'DRIVE1_OUT_FREE_TAIL',[x1,75,177],[6,36,18]),
       (2,'DRIVE2_IN_FREE_TAIL',[x2-3,75,177],[6,36,18])])
    # SATA B: third drive and the fourth factory SATA connector for NA-FH1.
    route('CABLE_R6_SATA_B_FACTORY300',[native_starts['SATA_B'],[18,51,224],
      [18,51,188],[58,51,188],[58,114,188],
      [x3-3,114,188],[x3-3,y3,188],[x3-3,y3,z3]],5.5,4,300,
      [(3,'DRIVE3_IN_FREE_TAIL',[x3-6,75,177],[6,36,18])])
    hubkey='POWER_R6_NA_FH1_SATA_HEAD_ENGINEERING_PROXY'
    if hubkey not in heads:head(hubkey,(14.5,28,12),(28.5,143,96))
    route('CABLE_R6_SATA_B_NEXT150_TO_NA_FH1',[[x3+3,y3,z3],[x3+3,y3,188],
      [x3+3,142,174],[53,157,102],[43,157,102]],5.5,4,150,
      [(3,'DRIVE3_OUT_FREE_TAIL',[x3,75,177],[6,36,18])])

    # Three 457.2mm StarTechLSATA18 direct data leads. Circular5.5mm is an
    # engineering routing section, not a retrieved manufacturer cable diameter.
    sata=m['mainboard_meta']['SATA']['selected_ports']
    for i,(fronty,highz,lanex) in enumerate(((5.5,184.,231.),(5.5,190.,231.),(11.,184.,225.)),1):
        q=dcon[f'R6_SATA_data_{i}_HDD_HEAD_ENGINEERING_PROXY'];o=q['origin_mm'];sz=q['size_mm']
        hx=o[0]+sz[0]/2;hy=o[1]+sz[1]/2;hz=o[2]+sz[2]
        end=next(v['cable_exit_xyz_mm'] for v in sata if v['drive']==i)
        bypass={1:19.,2:31.,3:90.}[i]
        pts=[[hx,hy,hz],[hx,hy,highz],[hx,43,highz],[bypass,43,highz],
          [bypass,fronty,highz],[219 if i==3 else 226,fronty,highz],
          [lanex,25,highz-10],[lanex,end[1],end[2]],[end[0],end[1],end[2]]]
        route(f'CABLE_R6_SATA_DATA_{i}_STARTECH_LSATA18_457p2',pts,5.5,3,457.2,
          [(i,f'DRIVE{i}_DATA_FREE_TAIL',[hx-3,48,176],[6,25,18])])

    # Gutter outlets are real openings in the supplied copy, never edits to the
    # frozen r6_psu source. They open only the wire bay, not the separate cold duct.
    cut=box((25,56,4),(14,30,194.5))
    base='PSU_R6_isolated_cold_sleeve_and_wire_gutter_BASE'
    if base in p:p[base]=p[base].cut(cut).clean()

    # Original unused Molex/FDD is retained explicitly.  Packing reserves contain
    # the unmodeled surplus, not invented exact full-length coils.
    unused=[]
    for i,z in enumerate((204.,215.,226.),1):
        n=f'POWER_R6_FACTORY_UNUSED_MOLEX_{i}_PARKED_PROXY';head(n,(18,12,10),(12.6,24,z-5));unused.append(n)
    head('POWER_R6_FACTORY_UNUSED_FDD_PARKED_PROXY',(12,8,6),(14,39,234))
    route('CABLE_R6_FACTORY_MOLEX_FDD_TO_PARK',[native_starts['MOLEX_FDD'],[28,55,224],
      [31,55,238],[31,33,238],[20,33,238],[20,39,238]],5.5,3,None)
    res['RESERVE_R6_FACTORY_UNUSED_MOLEX_FDD_FULL750_PACKING']=box((26.6,76,44),(12.8,7,198))
    res['RESERVE_R6_FACTORY_AND_EXTENSION_SURPLUS_RIGHT_FRONT_PACKING']=box((17,25,93),(229,16,65))
    packing=[]
    for key,v in routes.items():
        if 'unmodeled_surplus_mm' in v:
            packing.append({'route':key,'surplus_mm':v['unmodeled_surplus_mm'],
              'insulated_material_volume_mm3':v['surplus_insulated_material_mm3']})
    # The unused original EPS4 half remains300mm of four insulated conductors.
    total_material=sum(v['insulated_material_volume_mm3'] for v in packing)+750*math.pi*(5.5/2)**2+300*math.pi*(4.5/2)**2
    available=26.6*76*44+17*25*93

    # Simple root-connected lace ears; the root provides two M3 seat bosses on
    # the fixed front rail.  These do not clamp a moving hard-drive tray.
    ears=[]
    for i,(x,z) in enumerate(((105.,41.),(225.,41.)),1):
        n=f'POWER_R6_front_fixed_lacing_ear_{i}'
        s=box((12,4,12),(x-6,14,z-6)).cut(box((7,5,2),(x-3.5,13.5,z+2)))
        s=s.cut(cylinder(1.7,6,(x,13,z-2),(0,1,0))).clean();p[n]=s;ears.append(n)
    meta={'status':'R6_POWER_AND_DATA_INSTALLATION_PLANNING_NOT_PHYSICAL_RELEASE',
      'routes':routes,'checks':checks,'native_gland_exit_points_engineering':native_starts,
      'factory_exit_source':'unmeasured;splitglandfromr6_psu,notfactoryXYZ',
      'extensions':{'ATX24':'PhanteksPH-CB24P_BK500mm','EPS':'AkasaAK-CBPW08-40BK400mm,4+4split',
        'GPU':'PhanteksPH-CB8V_BK500mm,root owns its complete path'},
      'rejected_wrong_ATX_SKU':'AK-CBPW27-30BK is NOT an ATX24extension',
      'SATA_data_SKU':'StarTechLSATA18 nominal18in/457.2mm,three direct motherboard-to-drive leads',
      'GPU_factory_joint':{'head':gpu_native,'bbox_mm':bbox(heads[gpu_native]),'nose_axis':[0,0,1],
        'unused_second_head':gpu_park,'root_extension_mating_plane_Z_mm':185},
      'standard_ATX_coupling_heads':[atx_native,atx_extension],
      'standard_EPS_coupling_heads':[eps_native,eps_extension],
      'EPS_native_half_plan':'Useoneoriginal4pinhalftostandardEPSextension;originalunused4halflength300mustbepackedandverifiedphysicallyseparable.NoprivatePSUpinoutmodification.',
      'drive_local_free_tail_wire_keys':tail_keys,
      'HDD_service_conditions':['Poweroff;unplug only target heads+Z15;release target local tails from lace/straps and move flexible tails above/away from target draw path.',
        'Fixed main spans and all other drives stay in place. The flexible-tail reposition is a physical gate; no entire factory chain may be hidden to claim extraction.'],
      'surplus_packing':{'per_route':packing,'unused_Molex_FDD_nominal_segments_mm':[300,150,150,150],
        'unused_original_EPS4_half_mm':300,
        'unused_heads':unused+['POWER_R6_FACTORY_UNUSED_FDD_PARKED_PROXY'],
        'total_insulated_material_minimum_mm3':total_material,'reserved_box_volume_mm3':available,
        'suggested_packing_allowance_factor':2,'minimum_with_factor_mm3':2*total_material,
        'packing_accepted':False,'note':'Materialvolumeisnotinstalledcoilvolume;unusedbranchesandextensionendsrequireactualpacking.'},
      'cuts_applied_to_copy':[{'part':base,'bbox_mm':bbox(cut),'reason':'wire-onlygutterbottomoutlet,splitsealrequired'}],
      'lacing_interfaces':{'parts':ears,'root_required_M3_axes_XYZ_mm':[[105,14,39],[225,14,39]],
        'axis':[0,1,0],'root_connection':'AddfixedfrontframebossesandM3fasteners/nuts;earsnotcompletefasteneduntilrootintegrates.',
        'strap_slots_mm':[7,2],'soft_releasable_straps_required':True},
      'head_shapes_are_engineering_proxies':True,'wire_sections_measured':False,
      'mating_pairs':[],
      'limits':['No PSUinternalpinout,privatePSUmodularcableorSATA-to-GPUadapter.',
        'Diameters,bendradii,couplers,branchsplitsandglandlocationareengineeringpackingassumptions.',
        'Nominalfactorylengthmayincludeconnectorbodies;modeledcenterlinealoneisnotpurchaseorinstalled-lengthproof.',
        'Actualretainedsurplus,strainrelief,glandairtightnessandHDDflex-tailparkingmustbeacceptedonthereceivedhardware.']}
    if 2*total_material>available:checks.append({'kind':'surplus_packing_volume_unqualified','estimated_2x_material_mm3':2*total_material,'reserved_mm3':available})
    m['power_meta']=meta
    return meta
