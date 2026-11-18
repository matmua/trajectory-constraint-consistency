"""Aggregate on experiment host; no AppWorld task text or per-task metadata in release."""
import json, sys, math, random, hashlib, statistics
from pathlib import Path
from collections import Counter,defaultdict
R=Path(__file__).resolve().parents[1];O=R/'out';P=R.parent/'round1'
sys.path.insert(0,str(P/'src'))
from common import read,save
def rows(path,n):
    a=[read(p) for p in sorted(path.glob('*.json'))]
    assert len(a)==n,(path,len(a),n)
    return a
def grouped(rs,keys):
    groups=defaultdict(list)
    for r in rs:groups[tuple(r[k] for k in keys)].append(r)
    return groups
def matrix(rs,u='understood',e='acted'):
    return dict(n=len(rs),U=sum(r[u] for r in rs),E=sum(r[e] for r in rs),both=sum(r[u] and r[e] for r in rs),onlyU=sum(r[u] and not r[e] for r in rs),onlyE=sum(not r[u] and r[e] for r in rs),neither=sum(not r[u] and not r[e] for r in rs))
def summary(rs,keys):return dict(n=len(rs),**{k:sum(r[k] for r in rs) for k in keys})
def changes(before,after):
    assert set(before)==set(after)
    up=sum(not before[k] and after[k] for k in before);down=sum(before[k] and not after[k] for k in before)
    return dict(n=len(before),gain=up,loss=down)
def cluster_interval(diffs):
    rng=random.Random(4271);arr=sorted(sum(rng.choices(diffs,k=len(diffs)))/len(diffs) for _ in range(15000))
    return [round(arr[int((len(arr)-1)*q)]*100,1) for q in (.025,.975)]
def probes():
    web=rows(O/'web',120);ledger=rows(O/'web_ledger',80)
    groups={};matched={};lookup={}
    for tag,items in [('plain',web),('ledger',ledger)]:
        for (a,),rs in grouped(items,['arm']).items():
            groups[tag+'_'+a]=dict(**matrix(rs),legal=sum(x['valid'] for x in rs))
            lookup[tag,a]={(x['template'],x['order']):x for x in rs}
    for key in lookup['plain','same']:
        rs=[v[key] for v in lookup.values()]
        assert len({x['page_hash'] for x in rs})==1 and len({x['target'] for x in rs})==1
    for tag in ('plain','ledger'):
        s=lookup[tag,'same'];o=lookup[tag,'other']
        paired=[s[k]['acted'] and o[k]['acted'] for k in s]
        matched[tag]=dict(both=sum(paired),n=len(paired),understood_both=sum(s[k]['understood'] and o[k]['understood'] for k in s))
    for arm in ('same','other'):
        a=lookup['plain',arm];b=lookup['ledger',arm]
        matched['index_'+arm]=changes({k:r['acted'] for k,r in a.items()},{k:r['acted'] for k,r in b.items()})
        matched['index_'+arm]['cluster_ci_pp']=cluster_interval([sum(int(b[(i,j)]['acted'])-int(a[(i,j)]['acted']) for j in (0,1))/2 for i in range(20)])
    matched['same_actions']=Counter(r['raw_e'] for r in web if r['arm']=='same' and not r['acted'])
    matched['same_by_next']={e:matrix([r for r in web if r['arm']=='same' and r['expected']==e]) for e in ('description','features')}
    matched['n_products']=len({r['target'] for r in web})
    allr=rows(O/'full_web',20)
    full={a:dict(**summary(v,['done','shopping','atoms','ordered','joint']),mean_reward=round(statistics.mean(x['reward'] for x in v),3)) for (a,),v in grouped(allr,['arm']).items()}
    full['paired_joint']=changes({x['template']:x['joint'] for x in allr if x['arm']=='plain'},{x['template']:x['joint'] for x in allr if x['arm']=='ledger'})
    c=rows(O/'cctu',60);cs=read(O/'cctu_manifest.json');assert len(cs)==20
    # Binding is the decision to issue the documented lookup with the correct value. A native no-record is an observed response to a legitimate lookup.
    from jsonschema import Draft7Validator
    data={t['id']:t for t in map(json.loads,(P/'upstream/CCTU/data/input_data.jsonl').open())}
    for x in c:
        schemas={t['function']['name']:t['function']['parameters'] for t in json.loads(data[x['id']]['tools'])}
        x['bound']=x['argument_exact'] and all(Draft7Validator(schemas[o['name']]).is_valid(o['args']) for o in x['outputs'])
    cg={'text_menu_sensitivity':{a:matrix(v,e='bound') for (a,),v in grouped(c,['arm']).items()}}
    def shared(kind,items):
        for x in items:
            sx=read(O/(kind+'_shared')/(x['id']+'_'+x['arm']+'.json'));assert x['state']==sx['snapshot']
            x.update(understood=sx['understood'],native_call_instead=sx['native_call_instead'])
    shared('cctu',c)
    cg.update({a:dict(**matrix(v,e='bound'),u_called=sum(x['native_call_instead'] for x in v)) for (a,),v in grouped(c,['arm']).items()})
    by={(x['id'],x['arm']):x for x in c}
    cg['match']=dict(both=sum(by[x['id'],'counter']['bound'] and by[x['id'],'reference']['bound'] for x in cs),n=20)
    cg['natural']=dict(traces=sum(bool(x['prior']['calls']) for x in cs),with_receipt=sum(x['prior']['ever_received'] for x in cs),with_good_then_bound=sum(any(y['verified_source_before'] and y['argument_exact'] for y in x['prior']['calls']) for x in cs),downstream_calls=sum(len(x['prior']['calls']) for x in cs),without_source_wrong=sum(not y['verified_source_before'] and not y['argument_exact'] for x in cs for y in x['prior']['calls']),wrong_tasks=sum(any(not y['argument_exact'] for y in x['prior']['calls']) for x in cs))
    om=read(O/'order_manifest.json');oz=rows(O/'order',2*len(om['eligible']))
    shared('order',oz)
    cg['precedence']={arm:dict(**matrix(z),selected=sum(t['selected'] for t in z),u_called=sum(t['native_call_instead'] for t in z)) for (arm,),z in grouped(oz,['arm']).items()}
    cg['order_eligible']=len(om['eligible']);cg['order_screened']=len(om['screened'])
    return dict(web=groups,web_matched=matched,full_web=full,cctu=cg)
def dynamics():
    dyn={};traces={}
    recall={(r['template'],r['active'],r['lag']):r for r in rows(O/'dynamic_recall',80)}
    for folder,count in [('dynamic',80),('dynamic_static',40),('dynamic_restated',80),('dispatch',120)]:
        data=rows(O/folder,count)
        for r in data:
            label=folder+('_'+r['mode'] if folder=='dispatch' else '')
            if label=='dynamic':r['understood']=recall[r['template'],r['active'],r['lag']]['understood']
            traces.setdefault((label,r['active'],r['lag']),{})[r['template']]=r
    for (label,n,lag),rs in traces.items():
        assert len(rs)==20
        v=list(rs.values());s=summary(v,['revised','joint','stale','valid'])
        s.update(retained=sum(sum(r['retained']) for r in v),retained_n=sum(len(r['retained']) for r in v))
        if label=='dynamic':
            s.update(understood=sum(r['understood'] for r in v),at_least_one_incomplete=sum(any(r['checks']) and not r['joint'] for r in v) if n==3 else None)
        dyn[f'{label}_{n}_{lag}']=s
    for label in ('dynamic','dispatch_history'):
        for n in (1,3):
            dyn[f'{label}_{n}_lagcontrast']=changes({i:x['revised'] for i,x in traces[label,n,0].items()},{i:x['revised'] for i,x in traces[label,n,4].items()})
    return dyn
def applications():
    ids=read(O/'app_ids.json');assert ids==read(P/'app-manifest-20.json')['selected'][:10]
    groups={};allrows={}
    for arm in ('native20','echo20','native50','echo50','assisted20','wire20','live20'):
        vs=[];allrows[arm]={}
        for i in ids:
            x=read((P/'output/E4/A' if arm=='native20' else O/'app'/arm)/(i+'.json'))
            allrows[arm][i]=x;tr=x['trace'];passing={v['requirement'] for v in x['tests']['passes']}
            init=read(P/'output/E4_replay/A'/(i+'.json'))['initially_passing']
            calls=[e for t in tr for e in t.get('events',t.get('apis',[]))]
            usable=[e for e in calls if e['ok'] and e['app'] not in ('supervisor','api_docs') and not any(z in e['api'] for z in ('password','token','login','logout','signup','verify_account'))]
            failed={q['requirement'] for q in x['tests']['failures']}
            if x['tgc']:category='success'
            elif not x['submitted']:category='no_submit_business' if usable else 'no_submit_no_business'
            elif failed=={'assert answers match.'}:category='submitted_answer_only'
            else:category='submitted_other_failure'
            vs.append(dict(category=category,tgc=x['tgc'],submitted=x['submitted'],business=bool(usable),steps=len(tr),passes=len(passing),tests=x['tests']['num_tests'],progress=bool(passing-set(init)),nonanswer_progress=bool((passing-set(init))-{'assert answers match.'}),echoes=sum(t.get('echoed',False) for t in tr),normalizations=len(x.get('normalizations',[]))))
        groups[arm]=summary(vs,['tgc','submitted','business','steps','passes','tests','progress','nonanswer_progress','echoes','normalizations'])
        groups[arm]['outcomes']=dict(Counter(x['category'] for x in vs))
    pair=0
    for i in ids:
        a=allrows['assisted20'][i];b=allrows['wire20'][i]
        assert [t['response']['message'] for t in a['trace']]==[t['response']['message'] for t in b['trace']]
        assert [[(e['app'],e['api'],e['ok']) for e in t['events']] for t in a['trace']]==[[(e['app'],e['api'],e['ok']) for e in t['events']] for t in b['trace']]
        assert {q['requirement'] for q in a['tests']['passes'] if q['requirement']!='assert answers match.'}=={q['requirement'] for q in b['tests']['passes'] if q['requirement']!='assert answers match.'}
        pair+=1
    groups['distinct_online_successes']=len({i for k in ('echo50','live20') for i,r in allrows[k].items() if r['tgc']})
    groups['live_unmodified_success']=sum(r['tgc'] and not r.get('normalizations',[]) for r in allrows['live20'].values())
    groups['wire_audit']=dict(matched=pair,**changes({i:r['tgc'] for i,r in allrows['assisted20'].items()},{i:r['tgc'] for i,r in allrows['wire20'].items()}))
    legacy={}
    for a in 'ABC':
        z=rows(O/'legacy_wire'/a,20)
        assert all(x['same_business'] and x['same_prefix'] for x in z)
        legacy[a]=summary(z,['tgc','replayed','changed'])
    groups['legacy']=legacy
    groups['oracle']={'success':sum(read(P/'output/E4_control'/(i+'.json'))['success'] for i in ids),'n':len(ids)}
    return groups
if __name__=='__main__':
    out=probes();out['dynamic']=dynamics();out['app']=applications()
    save(R/'deliverables/metrics.json',out)
    print('Verified four experiments, saved aggregate metrics.')
