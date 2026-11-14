# SPDX-License-Identifier: MIT
"""R6 rear-IO GPU, independently removable upward. mm, fit-up references."""
from pathlib import Path
import cadquery as cq
from build import box,cylinder,merge,bbox
from r5_gpu import sweep_card_reference,sweep_box,screw_y
from r6_frame import csk,nut3,one
ROOT=Path(__file__).resolve().parents[1]
CORE='GPU_R6_fixed_open_spine'
JAW='GPU_R6_removable_IO_jaw'
EDGE='GPU_R6_CEM_keyed_edge_PLACEMENT_REFERENCE'
EAR='GPU_R6_IO_ear_PLACEMENT_REFERENCE'

def read(n):
    ss=cq.importers.importStep(str(ROOT/'references/original'/f'{n}.step')).solids().vals()
    return (ss[0] if len(ss)==1 else cq.Compound.makeCompound(ss)).translate((20,-32.5,0))

def build_gpu():
    p={};h={'gpu_body':read('gpu_body'),EAR:read('GPU_R5_IO_ear_PLACEMENT_REFERENCE')};sv={};res={}
    # Correct the inherited placement proxy using PCI-SIG CEM3 Fig6-3:
    #1.57acrosspads,1.90keynotch. Old1.60/1.30 misread blade-tip dimension.
    corrected=ROOT/'references/original/GPU_R6_CEM_correct1p57_notch1p90_REFERENCE.step'
    h[EDGE]=cq.importers.importStep(str(corrected)).val()
    # Posts and braces stay wholly to the +X side of the complete upward
    # extraction column. Lower brace clears the conservative fan top Z32.
    core=merge(box((2.8,4,208),(170.2,18,10)),box((2.8,4,208),(170.2,236.5,10)),
      box((2.8,222.5,4),(170.2,18,32)),box((2.8,222.5,4),(170.2,18,214)),
      box((14,12,5),(168,14,5)),box((10,10,5),(162,234,5)),
      box((46,4,8),(128,235.5,185.25)))
    # Narrow front shroud pads touch a side/end face, not either fan rotor.
    for i,z in enumerate((72.,160.),1):
        arm=merge(box((16,3.2,6),(158,10,z)),box((3.8,12,6),(170.2,10,z)))
        core=merge(core,arm)
        p[f'GPU_R6_TPU_front_end_pad_{i}']=box((11.6,.8,6),(158,13.2,z))
    fixed=[]
    for i,(x,y) in enumerate(((175,20),(167,240)),1):
        core=core.cut(cylinder(1.7,8,(x,y,4))).cut(box((5.9,5.9,2.6),(x-2.95,y-2.95,6.2)))
        sn=f'GPU_R6_frame_M3x10_CSK_{i}';nn=f'GPU_R6_frame_DIN562_M3_{i}'
        h[sn]=csk(10,(x,y,0));h[nn]=nut3(x,y,6.3);fixed += [sn,nn]
    jaw=box((41.6,5.4,8),(128,229.1,185.25));fast=[]
    for i,x in enumerate((139.1,159.42),1):
        core=core.cut(cylinder(1.7,6,(x,234.5,188.25),(0,1,0)))
        jaw=jaw.cut(cylinder(1.7,7,(x,228.9,188.25),(0,1,0))).cut(cylinder(2,4,(x,230.5,188.25),(0,1,0)))
        sn=f'GPU_R6_IO_M3x10_{i}';nn=f'GPU_R6_IO_insert_OD4_L4_fitup_{i}'
        h[sn]=screw_y(x,239.5,188.25,10)
        h[nn]=cylinder(2,4,(x,230.5,188.25),(0,1,0)).cut(cylinder(1.6,4,(x,230.5,188.25),(0,1,0)))
        fast += [sn,nn]
    p[CORE]=one(core,CORE);p[JAW]=one(jaw,JAW)
    moving=['gpu_body',EDGE,EAR]
    stages=['SERVICE_GPU_R6_disengage_plusZ12','SERVICE_GPU_R6_lift_plusZ300_AFTER12']
    sv[stages[0]]=merge(*(sweep_card_reference(h[n],12) for n in moving))
    sv[stages[1]]=merge(*(sweep_card_reference(h[n].translate((0,0,12)),300) for n in moving))
    sv['SERVICE_GPU_R6_jaw_forward12']=merge(sweep_box(jaw,(0,-12,0)),*(sweep_box(h[n],(0,-12,0)) for n in fast if 'insert' in n))
    sv['SERVICE_GPU_R6_jaw_up100_AFTER_forward12']=merge(sweep_box(jaw.translate((0,-12,0)),(0,0,100)),*(sweep_box(h[n].translate((0,-12,0)),(0,0,100)) for n in fast if 'insert' in n))
    meta={'selected_GPU':{'model':'Zotac ZT-B50620H-10M RTX5060Ti16GB TwinEdgeOC','vendor_dimensions_mm':[220.5,120.25,41.6],'body':bbox(h['gpu_body']),'power':'180W,one8pin'},
      'orientation':'fans-X,IO+Y,edge-Z; axial-fan open-air card, side fresh air and top exhaust',
      'intake_gap_mm':22,'rear_mainboard_pan_head_clearance_mm':.7,
      'frame_points_xy_mm':[[175,20],[167,240]],'core':CORE,'jaw':JAW,
      'frame_attachment':'M3x10CSK from base bottom; root cuts3.4holes,head recess; nut6.3..8.1',
      'gpu_card_only':{'moving_hardware':moving,'stage_service_names':stages,'stage_translations_mm':[[0,0,12],[0,0,300]],'remove_parts_before_service':[JAW,'TOP_R6_lid','top_fan_body'],'remove_hardware_before_service':fast,
        'removal_order':['断电拔显示器线，拆顶盖/顶扇及对应紧固件','拔GPU8pin并解除线夹，将线头停到右后侧','拆两颗IO螺钉，前夹与嵌件向-Y12再上提取出','显卡+Z12脱槽，再上提300；三盘、电源和主板留位'],
        'scope':'Actual continuous boundary sweep of CEM reference and conservative GPU body; real Zotac PCB/shroud/ports must be fitted'},
      'CEM_reference':{'thickness_across_pads_mm':1.57,'key_notch_mm':1.90,'source':'PCI-SIG CEM3 Fig6-3 p92 (external reference, not redistributed)','is_Zotac_vendor_CAD':False},
      'limits':['GPU厂尺寸包络真实；CEM金手指横向位置、IO耳及垫接触为参考并待实物校正','2.8mm脊柱和PETG支承需打印载荷/蠕变验收','母座固定件由r6_riser提供；不允许仅靠插槽承重','右侧主板背螺钉的0.7mm名义间隙尚未包含实物公差']}
    return p,h,sv,res,meta
