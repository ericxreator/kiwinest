# SPDX-License-Identifier: MIT
"""R6 original fixed-wire ENP-7660B, native rear flange and split cold sleeve.

Units mm.  Manufacturer drawing transcription lives in native-mechanical.json.
The fixed-wire exit/gland and permitted native-screw penetration are unmeasured.
R1--R5 are not imported or changed.  Frame mating bosses are explicit interfaces.
"""
from __future__ import annotations
import hashlib
import itertools
import json
from pathlib import Path
import cadquery as cq
from build import box, cylinder, merge, bbox

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'references/private/enp7660b-official-spec-20251008.pdf'
NATIVE = ROOT / 'references/original/native-mechanical.json'
BODY_MIN = (16.,96.,200.)
BODY_SIZE = (81.5,150.,40.5)
NATIVE_XZ = ((21.5,204.),(21.5,236.),(93.19,236.))
FRONT_AXES = ((12.,141.5),(101.,141.5))
TOP_AXES = ((22.,242.),(93.,242.))
FLANGE_AXES = ((44.,244.),(71.,244.))


def one(s, name):
    s=s.clean()
    if not s.isValid() or len(s.Solids()) != 1:
        raise ValueError(f'{name}: expected one valid solid; {len(s.Solids())}')
    return s


def pan(length, point, axis=(0,0,1), radius=1.5, head_radius=2.75, head_height=2.4):
    v=cq.Vector(*axis);p=cq.Vector(*point)
    return merge(cylinder(radius,length,point,axis),
                 cylinder(head_radius,head_height,(p-v*head_height).toTuple(),axis))


def csk(length, point, axis=(0,0,-1)):
    p=cq.Vector(*point);v=cq.Vector(*axis)
    return merge(cq.Solid.makeCone(3,1.5,1.5,p,v),
                 cylinder(1.5,length-1.5,(p+v*1.5).toTuple(),axis))


def nut_z(x,y,z):
    return box((5.5,5.5,1.8),(x-2.75,y-2.75,z)).cut(cylinder(1.6,2.2,(x,y,z-.2)))


def nut_y(x,y,z):
    return box((5.5,1.8,5.5),(x-2.75,y,z-2.75)).cut(cylinder(1.6,2.2,(x,y-.2,z),(0,1,0)))


def build_psu():
    """Return parts, hardware, air, reserves, JSON metadata; no external mutation."""
    parts={};hw={};air={};res={};checks=[]
    psu=box(BODY_SIZE,BODY_MIN)
    # Native rear bores are neutral thread envelopes, not fabricated thread teeth.
    for x,z in NATIVE_XZ:
        psu=psu.cut(cylinder(1.9,4.1,(x,246,z),(0,-1,0)))
    hw['PSU_R6_ENP7660B_ORIGINAL_FIXED_BODY_REFERENCE']=one(psu,'PSU')

    # Rear metal ring is independently manufactured; never an FDM part.
    outer=box((91.5,1.,51.),(11.,246.,196.))
    flange=outer.cut(box((80.7,3.,39.7),(16.4,245.,200.4)))
    for x,z in NATIVE_XZ:
        flange=merge(flange,cylinder(5.5,1,(x,246,z),(0,1,0)).intersect(outer))
        flange=flange.cut(cylinder(2.,3,(x,245,z),(0,1,0)))
    for x,z in FLANGE_AXES:
        flange=flange.cut(cylinder(1.7,3,(x,245,z),(0,1,0)))
    hw['PSU_R6_REPLACEABLE_1mm_METAL_FLANGE_NOT_PRINT']=one(flange,'metal flange')
    native_keys=[]
    for i,(x,z) in enumerate(NATIVE_XZ,1):
        n=f'PSU_R6_NATIVE_6_32_x3_16_LENGTH_UNVERIFIED_REFERENCE_{i}'
        hw[n]=one(pan(4.7625,(x,247,z),(0,-1,0),1.7526,3.25,2.2),n)
        native_keys.append(n)

    # All rear printed suspension material stays above Z240.8.
    hanger=box((91.5,9.,6.2),(11.,237.,240.8))
    for i,(x,y) in enumerate(TOP_AXES,1):
        hanger=hanger.cut(cylinder(1.7,8,(x,y,240.)))
        hanger=hanger.cut(box((5.9,8.2,2.),(x-2.95,236.8,242.3)))
        hw[f'PSU_R6_TOP_M3x10_CSK_{i}']=one(csk(10,(x,y,251)), 'top bolt')
        hw[f'PSU_R6_TOP_DIN562_M3_{i}']=one(nut_z(x,y,242.4),'top nut')
    for i,(x,z) in enumerate(FLANGE_AXES,1):
        hanger=hanger.cut(cylinder(1.7,11,(x,236.5,z),(0,1,0)))
        # Nut slides down from above before top frame is fitted; >5mm Y bearing.
        hanger=hanger.cut(box((5.9,2.,6.2),(x-2.95,238.9,241.05)))
        hw[f'PSU_R6_FLANGE_M3x10_PAN_{i}']=one(pan(10,(x,247,z),(0,-1,0)),'flange bolt')
        hw[f'PSU_R6_FLANGE_DIN562_M3_{i}']=one(nut_y(x,239.,z),'flange nut')
    parts['PSU_R6_rear_TOP_ONLY_suspension']=one(hanger,'rear suspension')

    # Solid posts sit behind the moving HDD bodies.  Rear feet accept real bolts.
    stand_bits=[box((4,3.35,47),(10,134.65,151)),
                box((4,3.35,47),(99,134.65,151)),
                box((93,3.35,4),(10,134.65,196)),
                box((6,25,2),(16,120,198)),box((6,25,2),(91.5,120,198))]
    for x,y in FRONT_AXES:
        stand_bits.append(box((8,10,7),(x-4,136.5,151)))
    stand=merge(*stand_bits)
    for i,(x,y) in enumerate(FRONT_AXES,1):
        stand=stand.cut(cylinder(1.7,9,(x,y,150.5)))
        hw[f'PSU_R6_FRONT_M3x10_PAN_{i}']=one(pan(10,(x,y,158),(0,0,-1)), 'front bolt')
        hw[f'PSU_R6_FRONT_DIN562_M3_{i}']=one(nut_z(x,y,148.8),'front nut')
    parts['PSU_R6_front_open_cradle_storage_bolted']=one(stand,'front cradle')

    # Sleeve side/bottom gaps enclose all broad and narrow potential intake faces.
    # The rear hanger replaces the last7mm of the sleeve roof without a rear post.
    shell=merge(box((91.5,239,1.6),(11,5,195.4)),
                box((1.6,239,46.3),(11,5,197)),
                box((1.6,239,46.3),(100.9,5,197)),
                box((1.6,81,48),(40,5,197)),
                box((29,1.6,46.3),(12.6,84.4,197)))
    # The short front transition chamber Y86..96 covers the whole PSU intake end.
    # A fitted split gland will isolate the fixed-wire gutter after sample fit-up.
    gland=box((25.6,4,24),(14,83.5,203))
    shell=shell.cut(gland)
    # Rear annular end, clear of the actual case body.
    rear=box((91.5,1.6,45.2),(11,242.4,195.4)).cut(
        box((82.3,3,41.3),(15.6,242,199.6)))
    shell=merge(shell,rear)
    # Hanger clearance and split sealing notches at the two structural penetrations.
    shell=shell.cut(box((92,8,5),(10.8,236.8,240.6)))
    for x in (10,99):
        shell=shell.cut(box((4.4,3.75,5.2),(x-.2,134.45,195.2)))
    # The continuous support crossmember crosses the floor as well as the two
    # narrow stem notches.  Give the entire structural penetration0.2mm clearance.
    shell=shell.cut(box((93.4,3.75,5.2),(9.8,134.45,195.2)))
    # Front partition reaches roof height; covers meet its opposite sides.
    shell=merge(shell,box((1.6,81,1.7),(40,5,243.3)))
    cold_cap=merge(box((60.7,81,1.5),(41.8,5,243.5)),
                   box((91.5,150.8,1.5),(11,86,243.5)))
    wire_cap=box((28.8,80.8,1.5),(11,5,243.5))
    cover_axes=[('cold',99.2,y) for y in (20.,75.,180.,220.)]
    cover_axes += [('cold',45.5,y) for y in (20.,75.)]
    cover_axes += [('cold',14.2,y) for y in (180.,220.)]
    cover_axes += [('wire',14.5,y) for y in (20.,75.)]
    for i,(which,x,y) in enumerate(cover_axes,1):
        boss=box((6.2,8,2.9),(x-3.1,y-4,240.6))
        # Attach the thin local bearing islands to the nearest wall or partition.
        if which=='wire':link=box((x-11,4,2.9),(11,y-2,240.6))
        elif x==99.2:link=box((102.5-(x-3.1),4,2.9),(x-3.1,y-2,240.6))
        elif x==45.5:link=box((8.6,4,2.9),(40,y-2,240.6))
        else:link=box((6.3,4,2.9),(11,y-2,240.6))
        shell=merge(shell,boss,link)
        shell=shell.cut(cylinder(1.7,7,(x,y,237.)))
        # M3 nut loaded laterally from the open enclosure before the roof cover.
        pocket=box((5.9,8.2,2),(x-2.95,y-4.1,242.1))
        shell=shell.cut(pocket)
        cap=cold_cap if which=='cold' else wire_cap
        cap=cap.cut(cylinder(1.7,3,(x,y,243))).cut(pocket)
        if which=='cold':cold_cap=cap
        else:wire_cap=cap
        hw[f'PSU_R6_{which.upper()}_COVER_M3x8_{i}']=one(pan(8,(x,y,245),(0,0,-1)), 'cover bolt')
        hw[f'PSU_R6_{which.upper()}_COVER_DIN562_M3_{i}']=one(nut_z(x,y,242.2),'cover nut')
    parts['PSU_R6_isolated_cold_sleeve_and_wire_gutter_BASE']=one(shell,'sleeve')
    parts['PSU_R6_cold_sleeve_REMOVABLE_roof']=one(cold_cap,'cold roof')
    parts['PSU_R6_fixed_wire_gutter_REMOVABLE_roof']=one(wire_cap,'wire roof')

    # Volume domains are clear space, not an assertion of measured pressure/CFM.
    cavity=box((88.3,237.4,46.5),(12.6,5,197))
    cavity=cavity.cut(box((29,81,48),(12.6,5,197))).cut(box(BODY_SIZE,BODY_MIN))
    for s in itertools.chain(parts.values(),hw.values()):
        cavity=cavity.cut(s)
    air['AIR_PSU_R6_front_and_ALL_FACE_cold_sleeve']=cavity.clean()
    outlet=box((81.5,29,40.5),(16,246,200))
    for s in hw.values():outlet=outlet.cut(s)
    air['AIR_PSU_R6_straight_rear_exhaust']=outlet.clean()
    # The wire port has no certified diameter/position.  Keep every such claim out
    # of the hardware dictionary, where it could be mistaken for actual geometry.
    res['RESERVE_PSU_R6_UNMEASURED_factory_wire_exit_and_split_gland']=box((25.6,17,30),(14,83,200))
    res['RESERVE_PSU_R6_integral_front_tongues_T_PLANE_UNKNOWN']=box((81.5,10,40.5),(16,86,200))
    res['RESERVE_PSU_R6_front_independent_WIRE_ONLY_gutter']=box((27.4,79.4,46.3),(12.6,5,197))
    res['RESERVE_PSU_R6_native_screw_penetration_NOT_ACCEPTED']=box((81.5,4.1,40.5),(16,241.9,200))

    meta={'model':'EnhanceENP-7660B ORIGINAL fixed manufacturer illustrated harness',
      'body_bbox_mm':bbox(hw['PSU_R6_ENP7660B_ORIGINAL_FIXED_BODY_REFERENCE']),
      'body_axes':'81.5X x150Y x40.5Z;AC at+Y246,cable/intake atY96',
      'manufacturer_airflow_global':[0,1,0],'native_hole_axes_xz_mm':[list(v) for v in NATIVE_XZ],
      'native_hole_thread':'UNC6-32;metalflange clearance4.0mm',
      'native_screw_hardware':native_keys,'native_screw_length_reference_mm':4.7625,
      'native_screw_intrusion_reference_mm':3.7625,'native_screw_length_and_penetration_verified':False,
      'metal_flange':{'key':'PSU_R6_REPLACEABLE_1mm_METAL_FLANGE_NOT_PRINT','material':'1mmsteel/aluminium,deburr;notFDM','Y_mm':[246,247],
        'outer_bbox_mm':bbox(flange),'native_holes':'three manufacturer axes,not factory case-assembly hex screws'},
      'frame_interfaces':{
       'front':{'contact_stem_centers_xyz_mm':[[12,136.325,151],[101,136.325,151]],
        'bolt_axes_xy_mm':[list(v) for v in FRONT_AXES],'bolt':'M3x10pan,seatZ158,tipZ148',
        'root_boss_bbox_mm':[[[x-4,137.5,147.3],[x+4,145.5,151]] for x,y in FRONT_AXES],
        'root_through_hole_diameter_mm':3.4,'root_nut_pocket_size_mm':[5.9,8.2,2.],
        'root_nut_pocket_z_mm':[148.7,150.7],'root_nut_z_mm':[148.8,150.6],
        'root_nut_loading':'openpockettoward+Y;addtofixedstoragecage,notmovingHDDtray'},
       'top':{'bolt_axes_xy_mm':[list(v) for v in TOP_AXES],'root_frame_z_mm':[247,251],
        'root_through_hole_diameter_mm':3.4,'bolt':'90degM3x10CSK,seatZ251,tipZ241;remove lid for access',
        'root_countersink_diameter_mm':6,'root_countersink_depth_mm':1.5,
        'head_z_mm':[249.5,251],'captured_nut_z_mm':[242.4,244.2]},
       'rear_flange':{'axes_xz_mm':[list(v) for v in FLANGE_AXES],'M3x10':'seatY247to237,head247..249.4;capturednut239..240.8',
        'printed_hanger_bbox_mm':bbox(hanger),'no_rear_support_below_z_mm':240.8}},
      'fixed_wire_front_port':{'status':'UNMEASURED_ENGINEERING_PORT_AND_FITTED_SPLIT_GLAND_REQUIRED',
       'port_bbox_mm':[[14,84.4,203],[39.6,86,227]],
       'wire_exit_nominal_xyz_mm':[26,96,214],'nominal_is_manufacturer_dimension':False,
       'transition_chamber_y_mm':[86,96],'separate_gutter_y_mm':[5,86],
       'seal':'Fit split compressible gland after measuring actual factory loom;no opening PSU,no cable cutting.Cold/gutter airtightness not certified.'},
      'sleeve_outer_target_mm':[[11,5,195.4],[102.5,244,245]],
      'air_gaps_nominal_mm':{'bottom':3,'top':3,'left_right':3.4},
      'duct_cover_release':'RemoveM3coverscrews,lift both thin roofs+Z after topfan/lid removal;release loom gland halves before lifting original wire loom. Fixed PSU need not be opened.',
      'cover_axes':cover_axes,
      'PSU_removal':'ACoff/unplug;disconnect DCloads and release retained loom;remove roofs/gland;support PSU;remove3native rear screws;lift body+Z. Native integral tongue detailed Tface remains unmeasured.',
      'CPU_reuse':'Ryzen5825U DS_2501 uses4pinCPU power;use one4pinhalf of EPS4+4 and retain unused half in the wiregutter. No MSI/7600/AXP dependency.',
      'native_harness':{'ATX24_mm':300,'EPS4plus4_mm':300,'PCIe6plus2_segments_mm':[300,150],
        'SATA_strings':2,'SATA_each_segments_mm':[300,150],'SATA_heads':4,
        'Molex3plusFDD_segments_mm':[300,150,150,150]},
      'source_file':str(SOURCE.relative_to(ROOT)),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
      'native_transcription_file':str(NATIVE.relative_to(ROOT)),'native_transcription_sha256':hashlib.sha256(NATIVE.read_bytes()).hexdigest(),
      'mating_pairs':[], 'checks':checks,
      'limits':['Body/grille/IEC/wire-exitareengineeringproxies;sourceis2Dnotmanufacturer3DCAD.',
       'OriginalfronttongueextendsY86..96;Tfaceunknown,reservednotfabricated.',
       'Rootmustaddactualfixed-cagefrontbossesandtopframeholesfromframe_interfaces.',
       'Nativenew6-32x3/16referenceisnotmanufacturer-approvedpenetration;verifyfactoryhardwarebeforemanufacture.',
       'Splitglandfit,printedcreep,strength,mains-cordapproach,temperature/noiseandinstalledwirepackingrequirephysicalacceptance.']}
    # Contact relationships are listed only for real geometry, not broad pair skips.
    for i in range(1,4):
        meta['mating_pairs'].append(['PSU_R6_ENP7660B_ORIGINAL_FIXED_BODY_REFERENCE',native_keys[i-1]])
    for i in range(1,3):
        meta['mating_pairs'] += [[f'PSU_R6_FRONT_M3x10_PAN_{i}',f'PSU_R6_FRONT_DIN562_M3_{i}'],
            [f'PSU_R6_TOP_M3x10_CSK_{i}',f'PSU_R6_TOP_DIN562_M3_{i}'],
            [f'PSU_R6_FLANGE_M3x10_PAN_{i}',f'PSU_R6_FLANGE_DIN562_M3_{i}']]
    for i,(which,x,y) in enumerate(cover_axes,1):
        meta['mating_pairs'].append([f'PSU_R6_{which.upper()}_COVER_M3x8_{i}',f'PSU_R6_{which.upper()}_COVER_DIN562_M3_{i}'])
    return parts,hw,air,res,meta
