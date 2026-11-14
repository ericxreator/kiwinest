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

def fabrication_parts(meta):
    """Merge only explicitly declared original nonprinted fabrication parts."""
    parts=[];seen=set()
    for group in ('riser_meta','mainboard_meta'):
        for item in meta.get(group,{}).get('original_fabrication_parts',[]):
            key=item['hardware_key']
            if key in seen:raise ValueError('Duplicate original fabrication hardware key: '+key)
            seen.add(key);parts.append(item)
    return parts

def lower_flush_joints(meta):
    mount=meta.get('mainboard_meta',{}).get('mount',{})
    joints=mount.get('lower_flush_joints',[])
    return joints or ([mount['front_lower_flush_joint']] if mount.get('front_lower_flush_joint') else [])

def fastener_spec(n,v,meta):
    """Classify actual CAD instances; unresolved parts stay explicitly unknown."""
    dims=sorted(v['bbox_mm']['size']);low=n.lower();mm=meta.get('mainboard_meta',{});pm=meta.get('psu_meta',{})
    joint=next((q for q in lower_flush_joints(meta) if n in (q.get('washer'),q.get('screw'))),{})
    fabrication=next((q for q in fabrication_parts(meta) if q.get('hardware_key')==n),None)
    if fabrication:
        material=fabrication.get('material','').lower()
        if 'fr4' in material:
            thickness=fabrication.get('thickness_mm')
            label='自制FR4绝缘下压条'+(f' 厚{thickness:g}mm' if thickness is not None else ' 厚度待确认')
            return (label,'独立自有加工件，孔位/形状按最终CAD；不作为PETG打印件。绝缘、预压、拉脱、线束应变和x8链路均待实物验收')
        if 'silicone' in material:
            raw=fabrication.get('stock_thickness_mm');installed=fabrication.get('installed_thickness_mm')
            label='自制绝缘硅胶压垫'
            label+=f' 原片{raw:g}mm' if raw is not None else ' 原片厚度待确认'
            label+=f'／名义装配{installed:g}mm' if installed is not None else '／装配厚度待确认'
            return (label,'本地压接STEP为名义受压包络，公开STEP/DXF仅1.5mm平片；原片按外形和两孔裁切，不按电缆曲面铣槽。压缩曲线、回弹、夹持/拉脱及绝缘未验收')
        if 'steel' in material and n==joint.get('washer'):
            label=f'自制钢制沉头承载垫 OD{joint["custom_steel_washer_OD_mm"]:g}×{joint["washer_thickness_mm"]:g}mm／孔{joint["washer_bore_mm"]:g}／90°D{joint["washer_90deg_countersink_major_D_mm"]:g}'
            return (label,'主板下位安装轴专用，STEP为沉头/台阶加工依据，不是普通平垫或打印件；材料、头/孔配合、托盘承压/蠕变和夹持强度未验收')
        return ('自制加工件 '+fabrication.get('material','材料待确认')+' '+size_text(v)+'mm','仅按最终模块metadata中的自有加工件分类；不得从厂商端头推导采购/加工规格')
    if n==joint.get('screw'):
        length=joint['screw_nominal_length_including_head_mm']
        return (f'M3x{length:g} 90°沉头（长度含头）','只替换主板下位原rear M3x6盘头，与自制钢制沉头承载垫配套；最终头径/工具、进入量/扭矩和强度待实配')
    if re.fullmatch(r'R8_RISER_MALE_M2_hex_\d+|R8_RISER_LATCH_PARK_M2_HEX',n):
        thickness,af,_=sorted(v['bbox_mm']['size'])
        return (f'M2六角螺母 AF{af:g}×{thickness:g}mm','新增螺母数量来自真实CAD实例；原厂中/后位M2螺钉保留，不按厂商STEP重复表示加购。捕获腔、预紧/扭矩及防松待实配')
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
        return ('M3承载垫圈 ID3.2/OD9×0.5mm','仅保留使用平垫的安装位；D5.4可调托盘孔与GPU/完整riser PCB间隙按最终整机CAD和实配核对')
    if 'insert' in low:
        return ('M3嵌件/隔套：'+size_text(v)+' mm，按逐件CAD','不能用包络自动认定热熔规格/滚花/螺纹；先核实际座与供应商')
    if 'DIN562' in n or re.search(r'(?:square.*nut|M3_square)',n,re.I):
        return (f'M3方母5.5×5.5×{dims[0]:g}mm'+('（DIN562薄型）' if abs(dims[0]-1.8)<.02 else ''),'不同厚度分组；实际捕获腔、扭矩、尼龙压缩待验收')
    if 'M4' in n and ('nut' in low):return ('M4六角螺母 AF7×3.2mm','顶/底风扇按相应座面；不得把底扇母移到扇顶占riser层')
    if re.search(r'M3_hex(?:_|$)',n,re.I):
        return ('M3六角螺母 AF5.5×2.4mm','转接座原生安装轴；按实际2.4mm捕获层，不混同DIN562薄方母')
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

def refresh_components(rows,report):
    """Resolve fabrication rows from actual exported module metadata."""
    rows=[dict(row) for row in rows];by_id={row['id']:row for row in rows}
    envelopes=report.get('envelopes',{})
    joints=lower_flush_joints(report)
    washer_joints=[q for q in joints if q.get('washer') in envelopes]
    screw_joints=[q for q in joints if q.get('screw') in envelopes]
    if 'motherboard_flush_load_washer' in by_id and washer_joints:
        row=by_id['motherboard_flush_load_washer'];row['quantity']=str(len(washer_joints))
        row['sku']='；'.join(sorted({fastener_spec(q['washer'],envelopes[q['washer']],report)[0] for q in washer_joints}))
        row['specification']='；'.join(sorted({f'OD{q["custom_steel_washer_OD_mm"]:g}×{q["washer_thickness_mm"]:g}mm钢件／通孔D{q["washer_bore_mm"]:g}／90°D{q["washer_90deg_countersink_major_D_mm"]:g}' for q in washer_joints}))+'；下位index'+ '/'.join(str(q['mount_index']) for q in washer_joints)+'；STEP为加工依据，逐件包络见五金明细'
    if 'motherboard_flush_screw_M3x8' in by_id and screw_joints:
        row=by_id['motherboard_flush_screw_M3x8'];row['quantity']=str(len(screw_joints))
        row['sku']='；'.join(sorted({fastener_spec(q['screw'],envelopes[q['screw']],report)[0] for q in screw_joints}))
        row['specification']='；'.join(sorted({f'M3，90°沉头，名义全长{q["screw_nominal_length_including_head_mm"]:g}mm（含头），CAD大径D{q["washer_90deg_countersink_major_D_mm"]:g}' for q in screw_joints}))+'；标准商品具体SKU与实配头径待核'
    rm=report.get('riser_meta',{})
    if rm.get('electrical_lanes')!=8:return rows
    model=rm.get('selected_model')
    lengths=sorted({q['wire_only_nominal_mm'] for q in rm.get('wire_paths',{}).values()
                    if 'wire_only_nominal_mm' in q})
    free_lengths=sorted({q['free_bundle_nominal_mm'] for q in rm.get('wire_paths',{}).values() if 'free_bundle_nominal_mm' in q})
    sleeves=sorted({q['factory_sleeve_allowance_mm'] for q in rm.get('wire_paths',{}).values() if 'factory_sleeve_allowance_mm' in q})
    wire_length=f'名义线长{lengths[0]:g}mm' if len(lengths)==1 else '各段名义线长按最终riser_meta'
    if len(free_lengths)==len(sleeves)==1:
        wire_length+=f'（自由束线{free_lengths[0]:g}mm＋保留原厂套管合计{sleeves[0]:g}mm）'
    if 'riser' in by_id and model:
        row=by_id['riser'];row['sku']=f'ADT-Link {model} / {wire_length} / x8自制绝缘下压条候选'
        row['specification']=f'PCIe{rm.get("link_generation",3):g}.0电气目标×8；完整×8公端PCB/触点→×16母座；{wire_length}；线束外包络/弯曲半径为工程代理，非厂家弯曲认证'
        row['source']=rm.get('source_product_url',row['source'])
        row['notes']='最终型号及名义线长/自由段/套管口径来自本次导出riser_meta；名义总长不能替代自由束线长度。保留完整x8触点、原厂线束及中后位M2；自制下压条/垫/打印托架与新增螺母分别列项。实板插槽、x8协商、装配载荷/夹持、绝缘/导通与稳定性均未实物验收。'
    for part in rm.get('original_fabrication_parts',[]):
        key=part.get('hardware_key');material=part.get('material','').lower()
        identifier='riser_custom_fr4_clamp' if 'fr4' in material else 'riser_custom_silicone_pad' if 'silicone' in material else None
        if identifier not in by_id or key not in envelopes:continue
        row=by_id[identifier];row['quantity']='1'
        dimensions=size_text(envelopes[key])+'mm装配CAD包络'
        if 'fr4' in material:
            thickness=part.get('thickness_mm')
            row['specification']=dimensions+'；FR4绝缘层压板；'+(f'名义厚{thickness:g}mm' if thickness is not None else '材料厚度待确认')+'；孔位以独立加工CAD为准'
        else:
            raw=part.get('stock_thickness_mm');installed=part.get('installed_thickness_mm')
            row['specification']=dimensions+'；'+(f'原片{raw:g}mm' if raw is not None else '原片厚度待确认')+'；'+(f'名义装配{installed:g}mm' if installed is not None else '装配厚度待确认')+'；泡棉原片按公开1.5mm平片STEP/DXF外形及两孔裁切；1.4mm压接曲面仅供本地验证'
    nuts=[(name,value) for name,value in envelopes.items() if re.fullmatch(r'R8_RISER_MALE_M2_hex_\d+|R8_RISER_LATCH_PARK_M2_HEX',name)]
    if 'riser_custom_m2_nuts' in by_id and nuts:
        row=by_id['riser_custom_m2_nuts'];row['quantity']=str(len(nuts))
        labels=sorted({fastener_spec(name,value,report)[0] for name,value in nuts})
        row['sku']='；'.join(labels)+'，按最终捕获腔实配'
        row['specification']='真实CAD实例'+str(len(nuts))+'颗；'+ '；'.join(labels)+'；螺纹与夹持性能仍待实物核验'
    return rows

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'out-r8/report.json')
    args=parser.parse_args();report=json.loads(args.input.read_text())
    groups=defaultdict(list);conditions={};details=[['实际CAD五金／自制非打印件实例','数量','采购／加工规格','包络mm','条件']]
    fabricated_keys={q['hardware_key'] for q in fabrication_parts(report)}
    for name,value in report['envelopes'].items():
        spec=fastener_spec(name,value,report)
        if spec is None:continue
        label,note=spec;groups[label].append(name);conditions[label]=note
        details.append([name,1,label,size_text(value),note])
    summary=[['五金／自制非打印件规格','装配数量（真实CAD实例）','建议备料数','对应实例','条件']]
    for label,names in sorted(groups.items()):
        suggested=len(names) if set(names)<=fabricated_keys else len(names)+2
        summary.append([label,len(names),suggested,'；'.join(names),conditions[label]])
    printed=[['CAD打印件','CAD数量／实配补量','材料','包络mm','制造条件']]
    for name,value in report['parts'].items():
        material='TPU' if 'TPU' in name else 'PETG／PETG HF'
        quantity=1;note='工程原型；切片／公差／刚度／蠕变／试装待验证'
        if name.startswith('BOTTOM_R6_shim1mm_'):
            quantity='1 CAD；25mm实扇配置每编号打印3片'
            note='同形M4垫片可复用：每孔底扇下方2片、顶扇上方补1片；四编号合计12片。保持底扇顶Z32、顶扇底Z221，实测后调整。'
        elif name.startswith('TOP_R8_spacer4mm_'):
            note='26mm CAD风扇Z221..247配4mm上隔柱；25mm实扇Z221..246配总5mm上隔距（本4mm+一片上述1mm垫），保持底Z221。'
        printed.append([name,quantity,material,size_text(value),note])
    write_csv(ROOT/'bom/fasteners-detailed.csv',details)
    write_csv(ROOT/'bom/fasteners.csv',summary)
    write_csv(ROOT/'bom/printed-parts.csv',printed)
    component_path=ROOT/'bom/components.csv'
    with component_path.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;components=list(reader)
    components=refresh_components(components,report)
    write_csv(component_path,[fields]+[[row.get(field,'') for field in fields] for row in components])
    print(json.dumps({'fastener_instances':len(details)-1,'fastener_groups':len(groups),'printed_parts':len(printed)-1}))

if __name__=='__main__':main()
