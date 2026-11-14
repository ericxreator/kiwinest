#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Regenerate current hardware/print BOM from actual exported CAD instances."""
from __future__ import annotations
import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]

def size_text(v):return ' × '.join(f'{x:.3f}' for x in v['bbox_mm']['size'])

def fastener_spec(n,v,meta):
    """Classify actual CAD instances; unresolved parts stay explicitly unknown."""
    dims=sorted(v['bbox_mm']['size']);low=n.lower();mm=meta.get('mainboard_meta',{});pm=meta.get('psu_meta',{})
    if n in pm.get('native_screw_hardware',[]):
        return ('PSU原生6-32螺钉：优先随包，长度/进入量待实测','随包优先；CAD 3/16in只是参考，未核厂家允许进入量，不照代理长度盲买')
    if n.startswith('R6_STORAGE_NATIVE_') and '6_32' in n:
        return ('HDD McMaster99926A106 6-32UNC×6.35mm，100°沉头','native底孔；2.8mm承壁+0.8垫，进入2.75≤Seagate3.56mm上限，其他硬盘需另核')
    if n.startswith('R6_STORAGE_NATIVE_') and 'spacer' in low:
        return ('HDD隔垫 ID3.8/OD6×0.8mm','按原生螺接模型；材料/压缩及振动待实物')
    if 'M3_FF_10mm_standoff' in n:
        return ('M3内内铜柱10mm，AF5.5','名义参考；采购SKU未锁，不沿用旧6mm Harwin柱')
    if 'front_spacer_M3_0p5mm' in n:
        return ('M3尼龙垫 ID3.2/OD7×0.5mm','主板托盘至10mm柱之间；保持10.5mm板背距')
    if 'rear_loadwasher_M3_9mm' in n:
        return ('M3承载垫圈 ID3.2/OD9×0.5mm','用于D5.4可调托盘孔；后盘头与新GPU名义0.7mm间隙待实配')
    if 'insert' in low:
        return ('M3嵌件/隔套：'+size_text(v)+' mm，按逐件CAD','不能用包络自动认定热熔规格/滚花/螺纹；先核实际座与供应商')
    if 'DIN562' in n or re.search(r'(?:square.*nut|M3_square)',n,re.I):
        return (f'M3方母5.5×5.5×{dims[0]:g}mm'+('（DIN562薄型）' if abs(dims[0]-1.8)<.02 else ''),'不同厚度分组；实际捕获腔、扭矩、尼龙压缩待验收')
    if 'M4' in n and ('nut' in low):return ('M4六角螺母 AF7×3.2mm','顶/底风扇按相应座面；不得把底扇母移到扇顶占riser层')
    if re.search(r'M3_hex(?:_|$)',n,re.I):
        return ('M3六角螺母 AF5.5×2.4mm','R6转接座原生安装轴；按实际2.4mm捕获层，不混同DIN562薄方母')
    explicit=re.search(r'M[234]x\d+(?:p\d+)?',n,re.I)
    if explicit:
        spec=explicit.group(0)
        style='90°沉头（长度含头）' if re.search(r'CSK|countersunk|frame_top|_flat_',n,re.I) else '低圆头/按钮头≤2.2mm高（长度头下量）' if n.startswith(('TOP_R6_M4','BOTTOM_R6_M4')) else '盘头/内六角，按该模块座面（头下量）'
        return (spec+' '+style,'依据CAD实例名和实际座面；螺纹未建牙，实物长度/工具/进入量待装配核')
    if 'spacer' in low or 'washer' in low:
        return ('垫圈/隔距套 '+size_text(v)+'mm，按逐件尺寸','不得与打印隔距件重复采购；孔径/材料从对应模块核定')
    if re.search(r'(?:^|_)(?:nut|bolt|screw)(?:_|$)',n,re.I):
        return ('未锁采购规格：'+n,'仅有CAD实例，供应商尺寸/头型未核；暂缓该项而非猜规格')
    return None

def write_csv(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as stream:
        csv.writer(stream).writerows(rows)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'out-r6/report.json')
    args=parser.parse_args();report=json.loads(args.input.read_text())
    groups=defaultdict(list);conditions={};details=[['实际CAD五金实例','数量','采购规格','包络mm','条件']]
    for name,value in report['envelopes'].items():
        spec=fastener_spec(name,value,report)
        if spec is None:continue
        label,note=spec;groups[label].append(name);conditions[label]=note
        details.append([name,1,label,size_text(value),note])
    summary=[['五金规格','装配数量（真实CAD实例）','建议备料数','对应实例','条件']]
    for label,names in sorted(groups.items()):summary.append([label,len(names),len(names)+2,'；'.join(names),conditions[label]])
    printed=[['CAD打印件','CAD数量／实配补量','材料','包络mm','制造条件']]
    for name,value in report['parts'].items():
        material='TPU' if 'TPU' in name else 'PETG／PETG HF'
        printed.append([name,1,material,size_text(value),'工程原型；切片／公差／刚度／蠕变／试装待验证'])
    write_csv(ROOT/'bom/fasteners-detailed.csv',details)
    write_csv(ROOT/'bom/fasteners.csv',summary)
    write_csv(ROOT/'bom/printed-parts.csv',printed)
    print(json.dumps({'fastener_instances':len(details)-1,'fastener_groups':len(groups),'printed_parts':len(printed)-1}))

if __name__=='__main__':main()
