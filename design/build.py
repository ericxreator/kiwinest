# SPDX-License-Identifier: MIT
"""Original geometry helpers retained for the KiwiNest R6 model."""
from __future__ import annotations
from pathlib import Path
import cadquery as cq
import trimesh


def box(size, origin=(0, 0, 0)):
    return cq.Solid.makeBox(*size, cq.Vector(*origin))

def cylinder(radius, height, origin, axis=(0, 0, 1)):
    return cq.Solid.makeCylinder(radius, height, cq.Vector(*origin), cq.Vector(*axis))

def merge(*pieces):
    return pieces[0].fuse(*pieces[1:]).clean()

def bbox(shape):
    b = shape.BoundingBox()
    return {"min": [b.xmin, b.ymin, b.zmin], "max": [b.xmax, b.ymax, b.zmax],
            "size": [b.xlen, b.ylen, b.zlen]}

def overlap(a, b):
    aa, bb = a.BoundingBox(), b.BoundingBox()
    if any((a1 <= b0 + 1e-6 or b1 <= a0 + 1e-6) for a0, a1, b0, b1 in
           ((aa.xmin, aa.xmax, bb.xmin, bb.xmax),
            (aa.ymin, aa.ymax, bb.ymin, bb.ymax),
            (aa.zmin, aa.zmax, bb.zmin, bb.zmax))):
        return 0.0
    return max(0.0, a.intersect(b).Volume())

def export_mesh(shape, path):
    cq.exporters.export(shape, str(path), tolerance=0.25, angularTolerance=0.2)
    mesh = trimesh.load_mesh(path)
    return {"watertight": bool(mesh.is_watertight), "winding_consistent": bool(mesh.is_winding_consistent),
            "vertices": len(mesh.vertices), "faces": len(mesh.faces), "bounds_mm": mesh.bounds.tolist()}
