#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Estimate the union of cable XY projections over a fan disk.

Inputs are STEP solids in the case's millimetre XYZ coordinates. Each solid
is clipped to a Z interval before tessellation. Projected triangles are
rasterized into one shared Boolean mask, so overlapping cables count once.
This is a geometric projection estimate, not CFD or a flow-loss prediction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def project_cables(
    paths: list[Path],
    center: tuple[float, float] = (169.0, 136.0),
    radius: float = 56.0,
    z_min: float = 32.0,
    z_max: float = 65.0,
    step: float = 0.25,
) -> dict:
    """Return a cell-centre raster estimate of projected occupied disk area."""
    if not paths:
        raise ValueError('No cable STEP files matched; projection was not computed')
    values = (*center, radius, z_min, z_max, step)
    if not all(math.isfinite(value) for value in values):
        raise ValueError('Projection parameters must be finite numbers')
    if radius <= 0 or step <= 0 or z_max <= z_min:
        raise ValueError('Radius and step must be positive, and z_max must exceed z_min')
    x = np.arange(center[0] - radius + step / 2, center[0] + radius, step)
    y = np.arange(center[1] - radius + step / 2, center[1] + radius, step)
    xx, yy = np.meshgrid(x, y)
    disk = (xx - center[0]) ** 2 + (yy - center[1]) ** 2 <= radius ** 2
    disk_pixels = int(disk.sum())
    if not disk_pixels:
        raise ValueError('The raster contains no fan-disk cells; use a smaller step')
    union_mask = np.zeros_like(disk)
    triangle_count = 0
    inputs = []
    mesh_tolerance = 0.1
    angular_tolerance = 0.15
    for path in paths:
        raw = path.read_bytes()
        shape = cq.importers.importStep(str(path)).val()
        if not shape.isValid() or not shape.Solids():
            raise ValueError(f'Cable input is not a valid solid: {path.name}')
        bounds = shape.BoundingBox()
        slab = cq.Solid.makeBox(
            bounds.xlen + 2, bounds.ylen + 2, z_max - z_min,
            cq.Vector(bounds.xmin - 1, bounds.ymin - 1, z_min),
        )
        clipped = shape.intersect(slab)
        record = {
            'filename': path.name,
            'sha256': hashlib.sha256(raw).hexdigest(),
            'bytes': len(raw),
            'intersects_z_interval': bool(clipped.Solids()),
        }
        inputs.append(record)
        if not record['intersects_z_interval']:
            continue
        vertices, triangles = clipped.tessellate(mesh_tolerance, angular_tolerance)
        vertices = np.array([vertex.toTuple() for vertex in vertices])
        for triangle in triangles:
            points = vertices[list(triangle), :2]
            area = ((points[1, 0] - points[0, 0]) * (points[2, 1] - points[0, 1])
                    - (points[1, 1] - points[0, 1]) * (points[2, 0] - points[0, 0]))
            if abs(area) < 1e-10:
                continue
            triangle_count += 1
            x_min = max(0, int(np.searchsorted(x, points[:, 0].min(), side='left')))
            x_max = min(len(x), int(np.searchsorted(x, points[:, 0].max(), side='right')))
            y_min = max(0, int(np.searchsorted(y, points[:, 1].min(), side='left')))
            y_max = min(len(y), int(np.searchsorted(y, points[:, 1].max(), side='right')))
            if x_min >= x_max or y_min >= y_max:
                continue
            tx = xx[y_min:y_max, x_min:x_max]
            ty = yy[y_min:y_max, x_min:x_max]
            inside = np.ones_like(tx, dtype=bool)
            for a, b in ((points[0], points[1]), (points[1], points[2]), (points[2], points[0])):
                cross = (b[0] - a[0]) * (ty - a[1]) - (b[1] - a[1]) * (tx - a[0])
                inside &= cross >= -1e-9 if area > 0 else cross <= 1e-9
            union_mask[y_min:y_max, x_min:x_max] |= inside
    occupied_pixels = int((union_mask & disk).sum())
    return {
        'method': 'Union of rasterized XY projections of Z-clipped STEP-solid surface triangles',
        'units': 'mm',
        'center_xy_mm': list(center),
        'disk_radius_mm': radius,
        'z_clip_mm': [z_min, z_max],
        'raster_step_mm': step,
        'mesh_tolerance_mm': mesh_tolerance,
        'angular_tolerance_rad': angular_tolerance,
        'occupied_pixels': occupied_pixels,
        'disk_pixels': disk_pixels,
        'projected_fraction': occupied_pixels / disk_pixels,
        'projected_area_mm2': occupied_pixels * step ** 2,
        'projected_triangles': triangle_count,
        'input_files': inputs,
        'geometry_is_thermal_validation': False,
        'interpretation': 'Geometric projection estimate only; not pressure drop, airflow loss, or thermal acceptance. Raster and tessellation error are not a certified uncertainty bound.',
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cables-dir', type=Path, default=ROOT / 'out-r9/cables')
    parser.add_argument('--pattern', default='CABLE_R8_K83*.step')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--center-x', type=float, default=169.0)
    parser.add_argument('--center-y', type=float, default=136.0)
    parser.add_argument('--radius', type=float, default=56.0)
    parser.add_argument('--z-min', type=float, default=32.0)
    parser.add_argument('--z-max', type=float, default=65.0)
    parser.add_argument('--step', type=float, default=0.25)
    args = parser.parse_args()
    paths = sorted(path for path in args.cables_dir.glob(args.pattern) if path.is_file())
    try:
        result = project_cables(
            paths, (args.center_x, args.center_y), args.radius,
            args.z_min, args.z_max, args.step,
        )
    except ValueError as error:
        parser.error(str(error))
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    print(encoded, end='')


if __name__ == '__main__':
    main()
