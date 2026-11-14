# SPDX-License-Identifier: MIT
"""Original geometry helpers retained for the KiwiNest R6 model."""
from __future__ import annotations
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface
from build import box,cylinder,merge


def screw_y(x,y,z,length):
    return merge(cylinder(1.5,length,(x,y,z),(0,-1,0)),cylinder(2.75,3,(x,y,z),(0,1,0)))

def sweep_box(s,d):
    b=s.BoundingBox();lo=(b.xmin,b.ymin,b.zmin);sz=(b.xlen,b.ylen,b.zlen)
    return box(tuple(sz[i]+abs(d[i]) for i in range(3)),tuple(lo[i]+min(0,d[i]) for i in range(3)))

def sweep_card_reference(s,travel):
    """Continuous +Z sweep of the actual qualified card-reference boundary.

    Body and keyed edge are orthogonal polyhedra.  Extruding their actual
    horizontal boundary faces, with inner wires, and uniting the exact start
    and end solids gives the union of all translated material columns.  The
    keyed edge's missing column below the notch roof therefore stays empty.

    The IO ear additionally has transverse round holes.  Its unperforated
    full-rectangle top/bottom faces sweep overlapping Z intervals when travel
    exceeds ear height; those two prisms alone equal the true complete union,
    so the holes correctly close in the swept occupation, not by guesswork.
    Reject future unsupported geometry rather than silently understating it.
    """
    if travel<=0:raise ValueError('Card-reference travel must be positive +Z')
    b=s.BoundingBox();caps=[];transverse=[]
    for f in s.Faces():
        kind=f.geomType()
        if kind=='PLANE':
            nz=abs(f.normalAt().z)
            if nz>1e-8 and nz<1-1e-8:
                raise ValueError('Card-reference sweep requires orthogonal planar steps')
            if nz>1-1e-8:caps.append(f)
        elif kind=='CYLINDER':
            axis=BRepAdaptor_Surface(f.wrapped).Cylinder().Axis().Direction()
            if abs(axis.Z())<1-1e-8:transverse.append(f)
        else:
            raise ValueError('Unsupported curved card-reference sweep face: '+kind)
    if not caps:raise ValueError('Card reference has no planar leading faces')
    if transverse:
        full=[f for f in caps if not f.innerWires() and
              abs(f.Area()-b.xlen*b.ylen)<1e-5]
        low=any(abs(f.Center().z-b.zmin)<1e-6 for f in full)
        high=any(abs(f.Center().z-b.zmax)<1e-6 for f in full)
        if not(low and high and travel>=b.zlen-1e-6):
            raise ValueError('Transverse holes lack a complete continuous-sweep proof')
    delta=cq.Vector(0,0,travel)
    pieces=[s,s.translate(delta)]+[
        cq.Solid.extrudeLinear(f.outerWire(),f.innerWires(),delta) for f in caps]
    swept=merge(*pieces)
    # The CEM keyed blade reference intentionally has two disconnected
    # contact groups.  Do not bridge its key just to demand one solid.
    if not swept.isValid() or len(swept.Solids())<1:
        raise ValueError('Actual-boundary card sweep has no valid solid material')
    for endpoint in (s,s.translate(delta)):
        if abs(swept.intersect(endpoint).Volume()-endpoint.Volume())>1e-4:
            raise ValueError('Card sweep does not contain an exact endpoint')
    return swept
