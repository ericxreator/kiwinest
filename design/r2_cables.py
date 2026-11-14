# SPDX-License-Identifier: MIT
"""Original geometry helpers retained for the KiwiNest R6 model."""
from __future__ import annotations
import math
import cadquery as cq


def _v(point: tuple[float, float, float]) -> cq.Vector:
    return cq.Vector(*point)

def _rounded_wire(points: list[tuple[float, float, float]], radius: float) -> cq.Wire:
    """以精确切线圆弧替代每个 90° 折点；不靠离散折线伪装弯曲。"""
    pv = [_v(p) for p in points]
    directions = [(b - a).normalized() for a, b in zip(pv, pv[1:])]
    lengths = [(b - a).Length for a, b in zip(pv, pv[1:])]
    for index, length in enumerate(lengths):
        required = radius * (1 if index in (0, len(lengths) - 1) else 2)
        if length < required + 1e-5:
            raise ValueError(f"Segment {index} is too short for radius {radius}: {length}")
    edges: list[cq.Edge] = []
    cursor = pv[0]
    for index in range(1, len(pv) - 1):
        incoming, outgoing = directions[index - 1], directions[index]
        if abs(incoming.dot(outgoing)) > 1e-7:
            raise ValueError("Path corners must be perpendicular")
        vertex = pv[index]
        before = vertex - incoming * radius
        after = vertex + outgoing * radius
        center = vertex - incoming * radius + outgoing * radius
        middle = center + (incoming - outgoing) * (radius / math.sqrt(2))
        if (before - cursor).Length > 1e-7:
            edges.append(cq.Edge.makeLine(cursor, before))
        edges.append(cq.Edge.makeThreePointArc(before, middle, after))
        cursor = after
    edges.append(cq.Edge.makeLine(cursor, pv[-1]))
    return cq.Wire.assembleEdges(edges)

def _pipe(points: list[tuple[float, float, float]], diameter: float, radius: float) -> cq.Shape:
    path = _rounded_wire(points, radius)
    normal = (_v(points[1]) - _v(points[0])).normalized()
    profile = cq.Workplane(cq.Plane(origin=_v(points[0]), normal=normal)).circle(diameter / 2)
    shape = profile.sweep(cq.Workplane().newObject([path]), isFrenet=True).val().clean()
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("Cable sweep did not produce one valid solid")
    return shape.Solids()[0]
