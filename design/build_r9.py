# SPDX-License-Identifier: MIT
"""R9 HDD-first integration with complete x8 geometry and retained stock."""
from pathlib import Path
import hashlib,json,math,sys
import cadquery as cq
from build import box,cylinder,merge,bbox
import build_r6 as previous
ROOT=Path(__file__).resolve().parents[1]


def build(use_riser_cache=False):
    source_snapshot={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT/'design').glob('*') if f.suffix in ('.py','.json')}
    from r9_frame import build_frame
    from r9_storage import build_storage
    from r9_mainboard import build_mainboard
    from r6_gpu import build_gpu
    from r9_psu import build_psu
    p,h,refs,air,sv,res,fm=build_frame()
    sp,sh,heads,sa,ss,sm=build_storage();p.update(sp);h.update(sh);air.update(sa);sv.update(ss)
    mp,mh,hd,ms,mr,mm=build_mainboard();p.update(mp);h.update(mh);heads.update(hd);sv.update(ms);res.update(mr)
    gp,gh,gs,gr,gm=build_gpu();p.update(gp);h.update(gh);sv.update(gs);res.update(gr)
    pp,ph,pw,pa,ps,pr,pm=build_psu();p.update(pp);h.update(ph);air.update(pa);sv.update(ps);res.update(pr)
    m={'parts':p,'hardware':h,'refs':refs,'air':air,'service':sv,'reserves':res,'heads':heads,'wires':{},
      'frame_meta':fm,'drive_meta':sm,'mainboard_meta':mm,'gpu_meta':gm,'psu_meta':pm,
      'params':{'name':'kiwinest-r9','revision':'R9_HDD_FIRST_200MM_TOP_INDEPENDENT_FEET_X8',
        'release_revision':'R9','required_electrical_lanes':8,'target_pcie_generation':3,
        'minimum_complete_cable_margin_mm':25.,'body_mm':[250,250,257],'target_overall_mm':[250,250,275],
        'physical_min_mm':[0,0,-18],'physical_max_mm':[250,250,257],
        'printing_build_volume_mm':[256,256,256],'stage':'GEOMETRY_PROTOTYPE_NOT_MANUFACTURING_RELEASE'},'geometry_source_hashes':{}}
    if use_riser_cache:
        cache=ROOT/'analysis/r8-work/final-source-cache';index=json.loads((cache/'index.json').read_text());meta=json.loads((cache/'metadata.json').read_text())
        # Candidate iteration only. Final exported build always reconstructs
        # the original complete manufacturer endpoints from checked STEP files.
        rm=meta['riser_meta'];m['riser_meta']=rm
        rm['female_feet_already_narrowed']=True
        rm['female_mounts']['nut_pockets_already_cut']=True
        keep=set(rm.get('external_hardware_names',[]))
        def reference_names(value):
            if isinstance(value,str) and value in index:keep.add(value)
            elif isinstance(value,dict):
                for child in value.values():reference_names(child)
            elif isinstance(value,(tuple,list)):
                for child in value:reference_names(child)
        reference_names(rm)
        for n,v in index.items():
            if ('RISER' in n or 'K83' in n or n in keep or n.startswith('CHECK_R8_') or n.startswith('RESERVE_R8_')):
                if n not in m.get(v['group'],{}):m.setdefault(v['group'],{})[n]=cq.Shape.importBrep(str(cache/v['file']))
        previous.integrate_riser(m)
    else:
        from r6_riser import build_riser
        rp,rh,rw,rs,rr,rm=build_riser();p.update(rp);h.update(rh);m['wires'].update(rw);sv.update(rs);res.update(rr);m['riser_meta']=rm
        previous.integrate_riser(m)
    # PSU interface slots/windows/fasteners are owned by r9_psu and integrated
    # against this actual frame before any cable checks.
    from r9_psu import integrate_psu
    integrate_psu(m)
    from r9_controls import apply_controls
    apply_controls(m)
    from r9_power import apply_power
    apply_power(m)
    # The six source stubs are represented by the same exact full sweep caps
    # in power routes. Verify containment before removing their duplicate copy.
    source_proof=[]
    for n,s in pw.items():
        tag=next((tag for tag in ('SATA_A','SATA_B','MOLEX','ATX','EPS','GPU') if tag in n),None)
        k={'ATX':'CABLE_R6_ATX_FACTORY300','EPS':'CABLE_R6_EPS_FACTORY300','GPU':'CABLE_R6_GPU_FACTORY300',
          'SATA_A':'CABLE_R6_SATA_A_FACTORY300','SATA_B':'CABLE_R6_SATA_B_FACTORY300','MOLEX':'CABLE_R6_FACTORY_MOLEX_FDD_TO_PARK'}[tag]
        outside=s.cut(m['wires'][k]).Volume()
        if outside>1e-4:raise ValueError('Missing complete PSU source material '+n+' '+str(outside))
        source_proof.append({'source_stub':n,'full_wire':k,'outside_full_wire_mm3':outside,'duplicate_stub_not_exported':True})
    assert len(source_proof)==6,'Incomplete fixed factory harness source attribution'
    pm['complete_factory_source_material_proof']=source_proof
    integrate_hdd_wall_channels(m)
    from r9_packing import apply_packing
    apply_packing(m)
    previous.integrate_gpu_factory_parking(m)
    for module in tuple(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if not filename:continue
        source=Path(filename).resolve()
        if source.parent==ROOT/'design' and source.suffix=='.py':m['geometry_source_hashes'][str(source.relative_to(ROOT))]=hashlib.sha256(source.read_bytes()).hexdigest()
    for rel in ['design/r9_routing_baseline.json','references/original/gpu_body.step','references/original/GPU_R5_IO_ear_PLACEMENT_REFERENCE.step',
      'references/original/GPU_R6_CEM_correct1p57_notch1p90_REFERENCE.step','references/original/native-mechanical.json',
      'references/private/enp7660b-official-spec-20251008.pdf']+[str(Path(rm[k]).resolve().relative_to(ROOT)) for k in ('male_source','female_source')]:
        m['geometry_source_hashes'][rel]=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
    if not use_riser_cache:
        for rel,sha in m['geometry_source_hashes'].items():
            if rel in source_snapshot and sha!=source_snapshot[rel]:raise ValueError('Design source changed during full build: '+rel)
    return m


def integrate_hdd_wall_channels(m):
    # Grommets are split original engineering annuli around the actual
    # installed5.5mm looms. Their bores do not erase HDD passage air masks.
    p,h=m['parts'],m['hardware'];changes=[]
    for i,q in enumerate(m['power_meta']['rear_wall_wire_channels'],1):
        x,z=q['center_xz_mm'];outer=cylinder(q['diameter_mm']/2,1.7,(x,233.3,z),(0,1,0))
        inner=cylinder(2.75,1.9,(x,233.2,z),(0,1,0))
        for n in [n for n in p if n.startswith('R9_HDD_rear_connector_hatch_')]:
            if previous.overlap(p[n],outer)>1e-5:p[n]=p[n].cut(outer).clean();changes.append(n)
        g=outer.cut(inner).cut(box((3.4,1.9,.1),(x,233.2,z-.05))).clean()
        # Collar only fills the actual1.2mm hatch thickness. The extra lip
        # remains accessible from the rear without entering the air header.
        key=f'R9_HDD_split_silicone_wire_seal_{i}';h[key]=g
        m['drive_meta'].setdefault('own_fabrication_parts',{})[key]={
          'material':'split electrically insulating silicone engineering candidate',
          'thickness_mm':1.7,'flat_axis':'Y','wire_bore_mm':5.5,'outer_diameter_mm':6.5,
          'radial_split_width_mm':.1,'compression_and_air_leakage_verified':False}
    # The standard data leads need a rear plane behind the power branches.
    # Their complete, unchanged5.5mm envelopes extend0.35mm into the original
    #2.4mm rear skin. Cut only their actual curved paths with0.2mm radial
    #clearance: the remaining outer wall is at least1.85mm, not a through vent.
    from r6_power import _tube
    skin=p['SKIN_R6_back'];pockets=[]
    for route_name,route in m['power_meta']['routes'].items():
        if not route_name.startswith('CABLE_R9_SATA_DATA_'):continue
        diameter=route['engineering_diameter_mm']+.4
        clearance,_=_tube(route['vertices_mm'],diameter,route['engineering_bend_R_mm'])
        bounds=clearance.BoundingBox()
        remaining=250.-bounds.ymax
        if remaining<1.8-1e-5:raise ValueError('Rear data relief leaves insufficient modeled skin')
        before=skin.Volume();skin=skin.cut(clearance).clean()
        removed=before-skin.Volume()
        pockets.append({'route':route_name,'wire_diameter_mm':route['engineering_diameter_mm'],
          'radial_clearance_mm':.2,'clearance_diameter_mm':diameter,
          'removed_material_mm3':removed,'minimum_nominal_outer_wall_mm':remaining,
          'maximum_pocket_depth_from_inner_Y247p6_mm':max(0.,bounds.ymax-247.6),
          'through_skin':False})
    if len(pockets)!=3 or not skin.isValid() or len(skin.Solids())!=1:
        raise ValueError('Rear data relief must preserve one valid skin and all3routes')
    p['SKIN_R6_back']=skin
    m['frame_meta']['rear_data_cable_reliefs']={'part':'SKIN_R6_back','routes':pockets,
      'method':'Full actual centerlines with enlarged5.9mm sections; no bounding-box removal or air-domain exception',
      'minimum_outer_wall_mm':min(q['minimum_nominal_outer_wall_mm'] for q in pockets),
      'actual_cable_flex_surface_fit_and_print_strength_physically_verified':False}
    m['drive_meta']['root_wire_grommets']={'channels':m['power_meta']['rear_wall_wire_channels'],
      'modified_hatches':sorted(set(changes)),'wire_diameter_mm':5.5,'bore_diameter_mm':5.5,
      'seal_type':'split silicone annulus engineering proxy; no cable cutting/threading required',
      'airtightness_and_compression_physically_verified':False}


def check(m):
    return _check(m)


# Same strict physical/service checks as R8, plus four-passage HDD and service
# checks. A separate function avoids changing any stable previous revision.

bounds=previous.bounds
overlap=previous.overlap
cross=previous.cross
_common_shapes=previous._common_shapes
def _check(m):
    p,h,hd,w,sv=m['parts'],m['hardware'],m['heads'],m['wires'],m['service'];allphys=p|h|hd|w
    rm=m.get('riser_meta',{});mates=m.get('controls_meta',{}).get('expected_mating_pairs',[])+rm.get('electrical_mating_pairs',[])+m.get('power_meta',{}).get('expected_mating_pairs',[])
    if rm:
        mates += [rm['GPU_CEM_reference']['root_mating_pair'],rm['motherboard_mating_pair']]
    c={'invalid_shapes':[n for n,s in allphys.items() if not s.isValid() or not s.Solids()],
       'disconnected_prints':[n for n,s in p.items() if len(s.Solids())!=1],
       'print_print':cross(p,p,True),'print_hardware':cross(p,h),
       'print_heads':cross(p,hd),'print_wires':cross(p,w),'hardware_hardware':cross(h,h,True,allow=mates),
       'hardware_heads':cross(h,hd,allow=mates),'hardware_wires':cross(h,w,allow=mates),'heads_heads':cross(hd,hd,True,allow=mates),'heads_wires':cross(hd,w,allow=mates),'wires_wires':cross(w,w,True,allow=mates)}
    # A grooved silicone clamp may preload only the actual coax inside its
    # explicitly bounded pad. Rigid, CPU, air and service checks stay strict.
    rm['validated_local_mechanical_contacts']=[]
    for contact in rm.get('mechanical_local_contacts',[]):
        a,b=contact['a'],contact['b'];domain=m['reserves'][contact['domain_key']]
        volume=overlap(allphys[a],allphys[b])
        common=_common_shapes.get(frozenset((id(allphys[a]),id(allphys[b]))))
        outside=common.cut(domain).Volume() if common is not None else 0.
        if outside>1e-4 or volume>contact['maximum_overlap_mm3']+1e-4:
            raise ValueError('Riser clamp contact escaped its bounded elastic pad')
        for group in ('hardware_hardware','hardware_wires','print_hardware','print_wires'):
            c[group]=[q for q in c[group] if {q['a'],q['b']}!={a,b}]
        rm['validated_local_mechanical_contacts'].append({
          'pair':[a,b],'domain_key':contact['domain_key'],
          'overlap_mm3':volume,'outside_domain_mm3':outside,
          'maximum_overlap_mm3':contact['maximum_overlap_mm3'],
          'physical_clamping_and_retention_verified':False})
    # Permit only the measured local intersection inside a declared electrical
    #fork sphere. Any material outside that sphere remains a collision.
    for fork in m.get('power_meta',{}).get('exact_same_net_junction_spheres',[]):
        for q in list(c['wires_wires']):
            if {q['a'],q['b']}!={fork['a'],fork['b']}:continue
            common=w[q['a']].intersect(w[q['b']],tol=1e-5)
            sphere=cq.Solid.makeSphere(fork['radius_mm'],cq.Vector(*fork['center_mm']),angleDegrees1=-90,angleDegrees2=90)
            outside=common.cut(sphere).Volume()
            if outside<=1e-4:
                c['wires_wires'].remove(q)
                m['power_meta'].setdefault('validated_local_electrical_forks',[]).append({'pair':[q['a'],q['b']],'overlap_mm3':q['volume_mm3'],'outside_allowed_sphere_mm3':outside,'sphere':fork})
    c['invalid_check_domains']=[{'group':group,'name':name} for group in ('air','service','reserves','refs') for name,shape in m[group].items() if not shape.isValid() or not shape.Solids()]
    c['reference_material_interference']=cross(m['refs'],allphys)
    c['print_build_volume']=[{'name':n,'bbox_mm':bounds(s)} for n,s in p.items() if any(size>limit+1e-5 for size,limit in zip(sorted(bounds(s)['size']),sorted(m['params']['printing_build_volume_mm'])))]
    c['stock_length_or_storage_volume']=m.get('power_meta',{}).get('checks',[])
    c['design_requirements']=[]
    required_lanes=m['params'].get('required_electrical_lanes')
    if required_lanes and rm.get('electrical_lanes',0)<required_lanes:
        c['design_requirements'].append({'requirement':'electrical_lanes',
          'required':required_lanes,'modeled':rm.get('electrical_lanes')})
    if required_lanes and m.get('power_meta'):
        exit_transition=m.get('psu_meta',{}).get('ATX_isolated_factory_exit_transition',{})
        if not exit_transition.get('complete_source_segment_modeled'):
            c['design_requirements'].append({'requirement':'complete_ATX_factory_exit',
              'modeled':False})
    margin=m['params'].get('minimum_complete_cable_margin_mm')
    if margin:
        if rm.get('electrical_lanes')==8:
            if not rm.get('wire_paths'):
                c['design_requirements'].append({'requirement':'complete_riser_stock_length','modeled':False})
            for name,path in rm.get('wire_paths',{}).items():
                loop=path.get('geometric_service_loop_allocation_mm',0.)
                if loop<margin-1e-5:
                    c['design_requirements'].append({'requirement':'riser_geometric_service_loop',
                      'route':name,'minimum_mm':margin,'modeled_mm':loop})
                if abs(path['centerline_mm']+path['factory_sleeve_allowance_mm']-path['wire_only_nominal_mm'])>1e-3:
                    c['design_requirements'].append({'requirement':'complete_riser_stock_length','route':name})
        budgets={name:route['complete_length_budget']
          for name,route in m.get('power_meta',{}).get('routes',{}).items()
          if 'complete_length_budget' in route}
        if m.get('gpu_power_meta',{}).get('complete_length_budget'):
            budgets['GPU_standard_extension']=m['gpu_power_meta']['complete_length_budget']
        for name,budget in budgets.items():
            if budget['remaining_length_margin_mm']<margin-1e-5:
                c['design_requirements'].append({'requirement':'complete_cable_margin',
                  'route':name,'minimum_mm':margin,'modeled_mm':budget['remaining_length_margin_mm']})
        for name,route in m.get('power_meta',{}).get('routes',{}).items():
            if route.get('nominal_stock_mm') is not None and 'complete_length_budget' not in route:
                c['design_requirements'].append({'requirement':'complete_length_budget_missing','route':name})
    cpu=m['reserves']['KEEP_DS2501_CPU_40mm_FROM_COMPONENT_FACE_HARD_LIMIT']
    c['CPU40_hard_clearance']=cross({'CPU40':cpu},{n:s for n,s in allphys.items() if n!='CPU_DS2501_stock_round_copper_25mm_TOTAL_PHOTO_PROXY'})
    card=m['gpu_meta']['gpu_card_only']
    removed=set(m['frame_meta']['top_module_nodes'])|set(card['moving_hardware'])|{m['gpu_meta']['jaw']}|set(card['remove_hardware_before_service'])|{card['power_head'],card['free_wire']}
    # Fixed top-frame corner bolts remain if outside the extraction column.
    obs={n:s for n,s in allphys.items() if n not in removed}
    obs['PARKED_GPU8_head']=sv[card['parked_head_service']];obs['PARKED_GPU8_tail']=sv[card['parked_tail_service']]
    parking=card.get('native_power_parking')
    if parking:
        obs.pop(parking['normal_wire'],None)
        obs['PARKED_GPU_factory300']=sv[parking['parked_service']]
        parked_obs={n:s for n,s in allphys.items() if n!=parking['normal_wire']}
        c['GPU_factory_cable_parking']=cross(
          {parking['parked_service']:sv[parking['parked_service']]},parked_obs)
    # Prove the declared parked extension pose and plug movements against
    # the actual retained chassis. Flexible deformation between poses still
    # requires a received cable and is explicitly not a CAD acceptance.
    cable_removed=set(m['frame_meta']['top_module_nodes'])|{card['power_head'],card['free_wire']}
    cable_obs={n:s for n,s in allphys.items() if n not in cable_removed}
    c['GPU_extension_cable_parking']=cross(
      {n:sv[n] for n in (card['parked_head_service'],card['parked_tail_service'])},cable_obs)
    stages=('SERVICE_GPU_R6_power_unplug_plusZ40',
      'SERVICE_GPU_R6_power_head_side75_AFTER_up40','SERVICE_GPU_R6_power_head_rear40_AFTER_side')
    c['GPU_extension_head_parking_motion']=cross({n:sv[n] for n in stages},cable_obs)
    if rm:
        obs.pop(rm['female_hardware'],None)
        obs['FEMALE_NON_SPRING_MATERIAL']=m['reserves'][rm['non_spring_material_check_shape']]
    c['GPU_upward_removal']=cross({n:sv[n] for n in m['gpu_meta']['gpu_card_only']['stage_service_names']},obs)
    if rm:
        from r5_gpu import sweep_card_reference
        c['GPU_body_ear_vs_entire_socket']=cross({n:sweep_card_reference(h[n],312) for n in ('gpu_body','GPU_R6_IO_ear_PLACEMENT_REFERENCE')},{rm['female_hardware']:h[rm['female_hardware']]})
    c['protected_air']=[]
    for n in ('AIR_gpu_intake22','AIR_gpu_lower_supply','AIR_bottom_fan_intake',
              'AIR_top_rotor_keepout','AIR_PSU_R6_front_and_ALL_FACE_cold_sleeve',
              'AIR_PSU_R6_straight_rear_exhaust'):
        # The installed fan itself intentionally occupies its rotor envelope.
        # Other cables, frame members and hardware are still checked normally.
        obstacles={key:shape for key,shape in allphys.items()
                   if not (n=='AIR_top_rotor_keepout' and key=='top_fan_body')}
        c['protected_air']+=cross({n:m['air'][n]},obstacles)
    cpu_meta=m['mainboard_meta']['CPU']
    cy,cz=cpu_meta['photo_center_yz_mm'];x0=cpu_meta['hard_clearance_x_mm'][1]
    cpu_inlet=cylinder(cpu_meta['hard_guard_diameter_mm']/2,247.6-x0,(x0,cy,cz),(1,0,0))
    m['air']['AIR_CPU_right_side_fresh_air']=cpu_inlet
    c['protected_air']+=cross({'CPU_right_side_fresh_air':cpu_inlet},allphys)
    c['drive_forward_removal']=[];c['HDD_front_lock_tool_service']=[];c['HDD_connector_withdrawal']=[];c['HDD_cable_parking']=[]
    dm=m['drive_meta'];pm=m['power_meta']
    c['HDD_complete_tail_service_length']=[]
    for i,parking in pm['HDD_service_tail_parking'].items():
        extra=parking.get('assembly_slack_used_for_park_mm',0.)
        if extra<0. or extra>15.+1e-5 or abs(parking['parked_length_mm']-parking['normal_length_mm']-extra)>1e-4:
            c['HDD_complete_tail_service_length'].append({'drive':i,'kind':'power_tail_length_not_conserved_within_counted_slack'})
        data=parking['data']
        if abs(data['parked_length_mm']-data['normal_length_mm'])>1e-4:
            c['HDD_complete_tail_service_length'].append({'drive':i,'kind':'data_tail_length_not_conserved'})
    back_access={n for n in p if n=='SKIN_R6_back'}
    back_access|={n for n in h if n.startswith('PANEL_R6_back_')}
    front_access={n for n in p if n=='SKIN_R6_front'}|{n for n in h if n.startswith('PANEL_R6_front_')}
    fan_removed=set(dm['front_fan_service']['removed_nodes'])
    for i in ('1','2','3'):
        info=dm['service'][i];connectors=set(info['connectors']);local=set(pm['drive_local_free_tail_wire_keys'][i])
        hatch=dm['rear_connector_hatches'][i]
        own_seals={f'R9_HDD_split_silicone_wire_seal_{j}' for j in (2*int(i)-1,2*int(i))}
        removed=back_access|connectors|local|own_seals|set(hatch['remove_before_head_withdrawal'])
        parking=pm['HDD_service_tail_parking'][i]
        data=parking['data']
        parked={parking['parked_tail_service']:sv[parking['parked_tail_service']],
          data['parked_tail_service']:sv[data['parked_tail_service']]}
        for q in dm['connectors'].values():
            if str(q['drive'])==i:parked[q['parked_head_service']]=sv[q['parked_head_service']]
        fixed={n:s for n,s in allphys.items() if n not in removed}
        c['HDD_cable_parking']+=cross(parked,fixed)
        c['HDD_cable_parking']+=cross(parked,parked,True)
        withdrawals={q['withdrawal_service']:sv[q['withdrawal_service']] for q in dm['connectors'].values() if str(q['drive'])==i}
        c['HDD_connector_withdrawal']+=cross(withdrawals,fixed)
        excluded=removed|front_access|fan_removed|set(dm.get('front_fan_attached_route_keys',[]))|set(info.get('remove_before_draw',[]))
        excluded|=set(dm['moving_parts'][i]+dm['moving_hardware'][i]+dm['front_lock_hardware'][i])
        if i=='1':excluded|={'FRAME_R9_front_left_REMOVABLE_lower_post','FRAME_R6_base_M3x12_CSK_10_10'}|set(m['frame_meta'].get('front_left_lower_post_service',{}).get('remove_hardware',[]))
        obstacles={n:s for n,s in allphys.items() if n not in excluded};obstacles.update(parked)
        c['drive_forward_removal']+=cross({info['front_draw']:sv[info['front_draw']]},obstacles)
        # Unlock before drawing the tray: its body, carrier and native screws
        # remain installed during the tool motion. Only actual access modules
        # and the selected rear connector tails have been removed/parked.
        tool_removed=front_access|fan_removed|set(dm.get('front_fan_attached_route_keys',[]))
        if i=='1':
            lower=m['frame_meta']['front_left_lower_post_service']
            tool_removed|=set(lower['removed_nodes'])|set(lower.get('remove_hardware',[]))
        tool_obstacles={n:s for n,s in fixed.items() if n not in tool_removed}
        tool_obstacles.update(parked)
        c['HDD_front_lock_tool_service']+=cross({info['tool']:sv[info['tool']]},tool_obstacles)
    c['HDD_front_fan_module_service']=[]
    for j,key in enumerate(dm['front_fan_service']['staged_service_keys']):
        removed=fan_removed|front_access|set(dm.get('front_fan_attached_route_keys',[]))
        if j<2:removed-=set(dm['front_fan_service'].get('fan_first_stage_retained_keys',[]))|{n for n in h if n.startswith('R9_HDD_PLENUM_M3x')}
        c['HDD_front_fan_module_service']+=cross({key:sv[key]},
          {n:s for n,s in allphys.items() if n not in removed})
    c['HDD_rear_hatch_service']=[]
    for i,hatch in dm.get('rear_connector_hatches',{}).items():
        for kind,shutter in hatch.get('shutters',{}).items():
            own={shutter['part'],shutter['bolt'],hatch['slot_seal'],
              f"R9_HDD_split_silicone_wire_seal_{shutter['root_annulus_index']}"}
            removed=own|{n for n in p if n=='SKIN_R6_back'}|{n for n in h if n.startswith('PANEL_R6_back_')}
            obstacles={n:shape for n,shape in allphys.items() if n not in removed}
            other=shutter['retained_other_slot_foam_service']
            obstacles[other]=sv[other]
            for key in shutter['staged_service_keys']:
                c['HDD_rear_hatch_service']+=cross({key:sv[key]},obstacles)
    c['HDD_PWM_unplug_service']=[]
    pwm=dm['front_fan_service'].get('PWM_unplug_sweep_key')
    if pwm:
        removed=front_access|set(dm.get('front_fan_attached_route_keys',[]))
        c['HDD_PWM_unplug_service']=cross({pwm:sv[pwm]},{n:s for n,s in allphys.items() if n not in removed})
    f=m['frame_meta']['filter'];filter_removed=set(f['moving_nodes'])|{'filter_media_POROUS_REFERENCE'}
    full_filter_sweep=merge(sv[f['service_sweep']],box((278,128,.3),(105,72,-6.4)))
    c['filter_right_pull_service']=cross({'FILTER_COMPLETE_MATERIAL_PLUSX150':full_filter_sweep},
      {n:s for n,s in (allphys|m['refs']).items() if n not in filter_removed})
    c['HDD_protected_air']=[]
    exclusions=dm.get('air_obstacle_exclusions',{})
    for n in dm['protected_air_keys']:
        c['HDD_protected_air']+=cross({n:m['air'][n]},
          {key:shape for key,shape in allphys.items() if key not in exclusions.get(n,[])})
    if dm['airflow']['top_rotor_mouth_net_area_mm2']<dm['airflow']['unobstructed_main_gap_area_mm2']:
        c['design_requirements'].append({'requirement':'HDD_top_diffuser_area','passed':False})
    c['EPS_wire_roof_opening']=[]
    sleeve=m.get('psu_meta',{}).get('EPS_isolated_factory_exit_transition')
    if sleeve:
        opening=sleeve['service']
        removed={sleeve['removable_half_part']}|set(opening['removed_parts_for_access'])
        removed|=set(opening['remove_bolts_and_captured_nuts'])
        removed|=set(m['frame_meta']['top_module_nodes'])
        removed|={name for name in h if name.startswith('PANEL_R6_left_')}
        c['EPS_wire_roof_opening']=cross(
            {opening['sweep_key']:sv[opening['sweep_key']]},
            {name:shape for name,shape in allphys.items() if name not in removed})
    c['riser_latch_park_service']=[]
    latch=rm.get('female_latch_pose',{})
    if latch.get('pin_service_sweep_key'):
        # Opening access skins changes no structural support. The moving pin
        # is excluded only from its own motion, with the whole socket retained.
        access={n for n in p if n.startswith(('SKIN_R6_front','SKIN_R6_left'))}
        access|={n for n in h if n.startswith(('PANEL_R6_front','PANEL_R6_left'))}
        pin=latch['pin_hardware_key']
        obstacles={n:s for n,s in allphys.items() if n not in access|{pin}}
        c['riser_latch_park_service']+=cross(
          {latch['pin_service_sweep_key']:sv[latch['pin_service_sweep_key']]},obstacles)
        # Only the detached latch leaves in the second step; the other 218
        # actual female components remain as exact service obstacles.
        obstacles.pop(rm['female_hardware'])
        obstacles['FEMALE_RETAINED_WITHOUT_PARKED_LATCH']=m['reserves'][latch['retained_female_without_latch_check_key']]
        c['riser_latch_park_service']+=cross(
          {latch['latch_service_sweep_key']:sv[latch['latch_service_sweep_key']]},obstacles)
    c['outside_target']=[{'name':n,'bbox':bounds(s)} for n,s in allphys.items() if any(bounds(s)['min'][i]<m['params']['physical_min_mm'][i]-1e-5 or bounds(s)['max'][i]>m['params']['physical_max_mm'][i]+1e-5 for i in range(3))]
    c['PSU_original_component_checks']=m['psu_meta'].get('checks',[])
    c['front_left_lower_post_service']=[]
    lower=m['frame_meta'].get('front_left_lower_post_service',{})
    if lower:
        excluded=set(lower['removed_nodes'])|front_access|fan_removed|set(dm.get('front_fan_attached_route_keys',[]))
        c['front_left_lower_post_service']=cross({lower['sweep_key']:sv[lower['sweep_key']]},{n:s for n,s in allphys.items() if n not in excluded})
    c['invalid_check_domains']=[{'group':group,'name':name} for group in ('air','service','reserves','refs') for name,shape in m[group].items() if not shape.isValid() or not shape.Solids()]
    return c
