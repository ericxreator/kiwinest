#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reproduce local NF-A20 proxy and HDD-mouth checks without publishing CAD.

Requires the normal CadQuery environment plus optional Shapely 2.1.2. Supply
an independently obtained, checksum-pinned manufacturer STEP explicitly. Only
scalar results and source hashes are emitted; no supplier mesh, projected
polygon or BRep is exported. This is geometry verification, not CFD.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
OFFICIAL_STEP_SHA256='4dba51c63094d461351024ba1314afb87714d43e6bee220bdab2d93a21563498'
OFFICIAL_ARCHIVE_URL='https://cdn.noctua.at/media/4d019b79/NF-A20_Public-CAD.zip?download=true'
OFFICIAL_ARCHIVE_SHA256='83021bdf2aaf15f97c705ac1a9f3a4c93725db18dcc828b4039a62b4becaf10b'


def verify(official_step: Path) -> dict:
    import cadquery as cq
    try:
        import shapely
        from shapely.geometry import Polygon,Point,box
        from shapely.ops import unary_union
    except ImportError as error:
        raise RuntimeError('Optional check dependency missing: install shapely==2.1.2') from error
    if shapely.__version__!='2.1.2':raise RuntimeError('Use the pinned optional verifier dependency shapely==2.1.2')
    sys.path.insert(0,str(ROOT/'design'))
    import r9_frame
    import r9_storage
    digest=hashlib.sha256(official_step.read_bytes()).hexdigest()
    if digest!=OFFICIAL_STEP_SHA256:
        raise ValueError('Official STEP checksum differs; review the supplier version before running this check')
    source_hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                   for name in ('design/r9_frame.py','design/r9_storage.py')}
    _,_,_,_,_,storage=r9_storage.build_storage()
    proof=storage['airflow']['top_outlet_projection_proof']
    assert proof['source_sha256']==digest
    raw=cq.importers.importStep(str(official_step)).val();solids=raw.Solids()
    if len(solids)!=11 or not all(s.isValid() for s in solids):
        raise ValueError('Unexpected official NF-A20 solid structure')
    # Fixed source membership: housing/stator0, rotor1 and motor label9.
    # The other eight supplier components are removable anti-vibration pads.
    proxy=r9_frame.top_fan_proxy();center=r9_frame.TOP
    outside=[]
    for index in (0,1,9):
        actual=solids[index].rotate((0,0,0),(1,0,0),90).translate(
            (center[0],center[1],r9_frame.LID_Z-23.47))
        residue=actual.cut(proxy)
        if not residue.isValid():raise ValueError('Invalid official/proxy difference')
        volume=residue.Volume()
        if volume < -1e-5 or volume>1e-4:raise ValueError('Complete official fan material is outside the original proxy')
        outside.append(max(0.,volume))
    frame=solids[0];rotor=solids[1]
    radii=[edge.radius() for edge in frame.Edges() if edge.geomType()=='CIRCLE']
    opening=proof['nominal_frame_opening_radius_mm'];radius=proof['conservative_rotor_disk_radius_mm']
    if not any(abs(value-opening)<1e-5 for value in radii):
        raise ValueError('Declared frame opening radius is absent from official CAD')
    rb=rotor.BoundingBox()
    rotor_domain=cq.Solid.makeCylinder(radius,rb.ylen+.2,cq.Vector(0,rb.ymin-.1,0),cq.Vector(0,1,0))
    rotor_outside=rotor.cut(rotor_domain).Volume()
    if rotor_outside>1e-4:raise ValueError('Declared conservative rotor disk does not contain the complete rotor')
    tolerance=proof['frame_tessellation_linear_deflection_mm']
    angular=proof['frame_tessellation_angular_deflection_radians']
    padding=proof['projected_frame_expansion_mm']
    if padding<2*tolerance:raise ValueError('Projection padding is below the configured mesh allowance')
    vertices,triangles=frame.tessellate(tolerance,angular)
    polygons=[]
    for triangle in triangles:
        polygon=Polygon([(center[0]+vertices[i].x,center[1]-vertices[i].z) for i in triangle])
        if polygon.area>1e-10:polygons.append(polygon)
    projected=unary_union(polygons)
    if not projected.is_valid:raise ValueError('Invalid private frame projection')
    expanded=projected.buffer(padding,quad_segs=32)
    (x0,y0),(x1,y1)=proof['mouth_rectangle_xy_mm']
    mouth=box(x0,y0,x1,y1).intersection(Point(*center).buffer(radius,quad_segs=512))
    obstruction=mouth.intersection(expanded).area
    clear=mouth.difference(expanded).area
    minimum=storage['airflow']['unobstructed_main_gap_area_mm2']
    if clear<minimum:raise ValueError('HDD mouth clear projection is smaller than its four passages')
    if abs(clear-proof['net_clear_area_lower_bound_mm2'])>1e-4:
        raise ValueError('Recomputed clear mouth differs from the stored scalar proof')
    physical=cq.Solid.makeBox(x1-x0,y1-y0,1,cq.Vector(x0,y0,0)).intersect(
        cq.Solid.makeCylinder(radius,1,cq.Vector(*center,0)))
    gross=physical.Volume()
    if abs(gross-storage['airflow']['top_rotor_mouth_gross_area_mm2'])>1e-4:
        raise ValueError('Stored gross mouth does not match the original circle/rectangle geometry')
    for name,expected in source_hashes.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('Design source changed during verification')
    return {
      'official_archive_url':OFFICIAL_ARCHIVE_URL,'official_archive_sha256':OFFICIAL_ARCHIVE_SHA256,
      'official_step_sha256':digest,'geometry_source_hashes':source_hashes,
      'verification_software':{'cadquery':cq.__version__,'shapely':shapely.__version__},
      'fan_center_xy_mm':list(center),'official_no_AVP_solid_indices':[0,1,9],
      'official_material_outside_original_proxy_mm3':outside,
      'official_rotor_outside_R94_mm3':max(0.,rotor_outside),
      'frame_opening_radius_mm':opening,'original_throat_radius_mm':radius,
      'mouth_rectangle_xy_mm':proof['mouth_rectangle_xy_mm'],
      'mouth_gross_CAD_area_mm2':gross,'inscribed_mouth_polygon_area_mm2':mouth.area,
      'conservatively_projected_fixed_frame_obstruction_mm2':obstruction,
      'clear_mouth_projection_lower_bound_mm2':clear,'four_passage_area_mm2':minimum,
      'frame_mesh_linear_deflection_mm':tolerance,'frame_mesh_angular_deflection_radians':angular,
      'frame_projection_expansion_mm':padding,'private_frame_mesh_triangles':len(triangles),
      'dynamic_rotor_blades_excluded_from_fixed_obstruction':True,
      'supplier_geometry_or_projected_polygons_exported':False,'geometry_checks_passed':True,
      'installed_airflow_or_pressure_drop_verified':False,'thermal_or_physical_acceptance_completed':False,
      'limits':['Mesh projection with an expanded stationary frame is a conservative engineering estimate, not certified metrology.',
        'Clear area, proxy containment and connected passages do not establish installed airflow, temperature, noise or manufacturing acceptance.']}


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--official-step',type=Path,required=True,
                        help='Local NF-A20_Public-CAD.stp from the checksum-pinned official archive')
    parser.add_argument('--output',type=Path,help='Scalar JSON result; no source path or supplier geometry is written')
    parser.add_argument('--source-report',type=Path,
                        help='Optional passed full R9 report to bind by SHA-256 and matching design-source hashes')
    args=parser.parse_args()
    try:
        result=verify(args.official_step)
        if args.source_report:
            raw=args.source_report.read_bytes();report=json.loads(raw)
            if report['params']['release_revision']!='R9' or not report['geometric_checks_passed'] or any(report['checks'].values()):
                raise ValueError('Only a passed full R9 report can be bound to this result')
            for name,digest in result['geometry_source_hashes'].items():
                if report['geometry_source_hashes'].get(name)!=digest:
                    raise ValueError('Full report and top-fan proof use different design sources')
            result['source_report_sha256']=hashlib.sha256(raw).hexdigest()
    except OSError:parser.error('Cannot read a supplied local verification input')
    except (ValueError,RuntimeError) as error:parser.error(str(error))
    encoded=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(encoded)
    print(encoded,end='')


if __name__=='__main__':main()
