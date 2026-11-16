# SPDX-License-Identifier: MIT
"""R9 tray upper-front support; all board/socket/CPU datums remain R8."""
from __future__ import annotations
import copy
from build import box,cylinder,merge
import r6_mainboard as previous

def build_mainboard():
    parts,hw,heads,service,reserves,meta=previous.build_mainboard()
    tray=parts[previous.TRAY]
    # Remove only the old upper-front vertical stem and its nut-bearing foot.
    # The replacement lower bridge lies below the200mm fan's housing floor.
    tray=tray.cut(box((13,10.2,33.3),(171.5,37.9,213.9)))
    # Rear upper foot also rises2mm; all native board lands stay untouched.
    tray=tray.cut(box((13,7.5,5.2),(171.5,239.9,241.9)))
    tray=merge(tray,box((3,52,4),(173.2,18,214)),box((3,8,30),(173.2,14,214)),
               box((3,7.4,30),(173.2,240,214)))
    foot=box((12,8,5),(172,14,244)).cut(cylinder(1.7,6,(180,18,243.5)))
    foot=foot.cut(box((5.9,8.2,2.2),(177.05,13.9,245.0)))
    tray=merge(tray,foot)
    rear=box((12,7.4,5),(172,240,244)).cut(cylinder(1.7,6,(180,244,243.5)))
    rear=rear.cut(box((5.9,7.6,2.2),(177.05,239.9,245.0)))
    tray=merge(tray,rear)
    parts[previous.TRAY]=previous._one(tray,previous.TRAY)
    nut='MAINBOARD_MOUNT_R6_frame_top_M3_square_nut_1'
    screw='MAINBOARD_MOUNT_R6_frame_top_M3x10_1'
    for n in (nut,screw):hw[n]=hw[n].translate((0,-24,2))
    for n in ('MAINBOARD_MOUNT_R6_frame_top_M3_square_nut_2','MAINBOARD_MOUNT_R6_frame_top_M3x10_2'):
        hw[n]=hw[n].translate((0,0,2))
    for n in list(service):
        if n.startswith('SERVICE_'+screw+'_'):service[n]=service[n].translate((0,-24,2))
        if n.startswith('SERVICE_MAINBOARD_MOUNT_R6_frame_top_M3x10_2_'):service[n]=service[n].translate((0,0,2))
    meta=copy.deepcopy(meta)
    meta['mount']['top_frame_points_xy_mm']=[[180.,18.],[180.,244.]]
    cuts=meta['mount']['frame_required_cuts']
    cuts['upper_bridge_z_mm']=[249.,253.]
    cuts['top_countersink_mm']['z']=[251.5,253.]
    cuts['top_fastener']='M3x10 90deg countersunk,overall including head; top flushZ253'
    cuts['top_square_nut']='DIN562 thin M3,5.5 square x1.8,z245.2..247'
    meta['mount']['r9_upper_front_support']={
        'old_axis_xy_mm':[180.,42.],'new_axis_xy_mm':[180.,18.],
        'stem_bbox_mm':[[173.2,14.,214.],[176.2,22.,244.]],
        'lower_bridge_bbox_mm':[[173.2,18.,214.],[176.2,70.,218.]],
        'foot_bbox_mm':[[172.,14.,244.],[184.,22.,249.]],
        'top_fastener':'original M3x10 CSK and DIN562 M3 thin nut, frontY-24 and both upper jointsZ+2',
        'matching_frame_bridge_bbox_mm':[[173.,10.,249.],[187.,24.,253.]],
        'board_CPU_socket_and_four_native_mount_datums_moved':False,
        'stiffness_creep_and_tool_access_physically_accepted':False}
    return parts,hw,heads,service,reserves,meta
