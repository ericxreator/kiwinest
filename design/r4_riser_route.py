# SPDX-License-Identifier: MIT
"""Original geometry helpers retained for the KiwiNest R6 model."""
from __future__ import annotations
import math
import cadquery as cq


def rounded_wire(points,radius=8.0):
    vv=[cq.Vector(*p) for p in points]
    # Remove redundant collinear points before computing tangent lengths.
    changed=True
    while changed:
        changed=False
        for i in range(1,len(vv)-1):
            a=(vv[i]-vv[i-1]).normalized();b=(vv[i+1]-vv[i]).normalized()
            if a.dot(b)>.99999999:
                vv.pop(i);changed=True;break
    directions=[(b-a).normalized() for a,b in zip(vv,vv[1:])]
    trims=[0.0]*len(vv);angles={}
    for i in range(1,len(vv)-1):
        dot=max(-1,min(1,directions[i-1].dot(directions[i])))
        angle=math.acos(dot)
        if angle>math.pi-1e-5:raise ValueError('A cable path cannot reverse through a zero-length fold')
        angles[i]=angle;trims[i]=radius*math.tan(angle/2)
    for i,(a,b) in enumerate(zip(vv,vv[1:])):
        if (b-a).Length < trims[i]+trims[i+1]+1e-6:
            raise ValueError(f'Path segment {i} is too short for R{radius}')
    edges=[];cursor=vv[0]
    for i in range(1,len(vv)-1):
        inc,out=directions[i-1],directions[i]
        before=vv[i]-inc*trims[i];after=vv[i]+out*trims[i]
        normal=(out-inc*math.cos(angles[i])).normalized()
        center=before+normal*radius
        mid=center+((before-center)+(after-center)).normalized()*radius
        if (before-cursor).Length>1e-7:edges.append(cq.Edge.makeLine(cursor,before))
        edges.append(cq.Edge.makeThreePointArc(before,mid,after));cursor=after
    if (cursor-vv[-1]).Length>1e-7:edges.append(cq.Edge.makeLine(cursor,vv[-1]))
    wire=cq.Wire.assembleEdges(edges)
    wire._r4_edges=edges
    return wire
