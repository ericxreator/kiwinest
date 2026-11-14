# SPDX-License-Identifier: MIT
"""Original geometry helpers retained for the KiwiNest R6 model."""
from __future__ import annotations
import math
import cadquery as cq
from build import box,cylinder,merge


def one(s,name):
    s=s.clean()
    if not s.isValid() or len(s.Solids())!=1:raise ValueError(f'{name}: one valid solid required')
    return s.Solids()[0]

def screw_z(length,seat,head_h=3):
    x,y,z=seat
    s=merge(cylinder(1.5,length,(x,y,z),(0,0,-1)),cylinder(2.75,head_h,(x,y,z)))
    recess=cq.Workplane('XY').polygon(6,2.88675).extrude(1.5).val().translate((x,y,z+head_h-1.5))
    return one(s.cut(recess),'M3 screw')

def native_screw_x(face_x,y,z):
    """McMaster99926A106 reference:6-32x1/4,100deg undercut Ø.307x.066in head."""
    major=3.5052/2;head_r=.307*25.4/2;hh=.066*25.4
    end_r=head_r-hh*math.tan(math.radians(50))
    head=cq.Solid.makeCone(head_r,end_r,hh,cq.Vector(face_x,y,z),cq.Vector(1,0,0))
    shank=cylinder(major,6.35-hh,(face_x+hh,y,z),(1,0,0))
    # 5/64in socket; recess depth remains a non-functional visual reference.
    recess=cq.Workplane(cq.Plane(origin=(face_x-.01,y,z),normal=(1,0,0))).polygon(6,(5/64*25.4)*2/math.sqrt(3)).extrude(1.0).val()
    return one(merge(head,shank).cut(recess),'6-32 flathead reference')
