"""Native precedence constraints with provided, independently executable action packets."""
import sys,json,itertools,random,hashlib,re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from cctu_pairs import R,P,norm,user,read,save,chat,call_function
from jsonschema import Draft7Validator
PAIRS={'57':('literary_connection_finder','academic_relationship_finder'),'76':('award_winner_retriever','author_book_finder'),'89':('supplier_hospital_locator','hospital_survival_rate_analyzer'),'92':('capital_identifier','literary_award_search'),'93':('urban_feature_locator','commercial_district_locator'),'164':('philosopher_concept_identifier','historical_figure_info'),'165':('city_feature_identifier','historical_event_finder'),'172':('author_lookup','individual_location_finder'),'177':('historical_filmmaker_search','residence_locator'),'179':('biodiversity_database','satellite_info_retriever'),'182':('cultural_heritage_locator','mountain_peak_identifier'),'185':('historical_residence_finder','ancient_monument_finder'),'190':('artist_information_retriever','historical_visit_locator')}
def packets(t):
    i=t['id'];a,b=PAIRS[i];gold=json.loads(t['unsolved_set']);codes=json.loads(t['codes'])
    fs={q['function']['name']:q for q in json.loads(t['tools'])}
    if any(n not in gold or n not in fs for n in (a,b)):return
    from ast import parse,walk,Constant
    verified=[]
    for n in [a,b]:
        spec=fs[n]['function']['parameters'];keys=spec.get('required',[])
        calls=[json.loads(g['function']['arguments']) for m in read(P/'output/E2'/(i+'.json'))['messages'] for g in m.get('tool_calls',[]) if g['function']['name']==n and g['function']['arguments'].strip().startswith('{')]
        items=[x for vs in gold.values() for x in vs]
        literals=[v.value for v in walk(parse(codes[n])) if isinstance(v,Constant) and (isinstance(v.value,(float,int)) or isinstance(v.value,str) and 1<len(v.value)<80)]
        # Only use auto-generated fixtures that the native simulator and schema both verify against known outputs.
        if len(keys)<=2:
            candidates=[]
            for k in keys:
                field=spec['properties'][k]; pool=list(dict.fromkeys(items+literals))
                if field.get('type') in ('number','integer'):pool=[v for v in pool if isinstance(v,(float,int))]
                else:pool=[v for v in pool if isinstance(v,str) and all(c not in v for c in '\n{}')][:55]
                candidates.append(pool)
            calls+= [dict(zip(keys,c)) for c in itertools.product(*candidates)]
        fnns={};exec(codes[n],fnns,fnns)
        for arg in calls:
            if not Draft7Validator(spec).is_valid(arg):continue
            try:out=str(fnns[n](**arg))
            except Exception:continue
            if all(norm(z) in norm(out) for z in gold[n]) and not any(e in norm(out) for e in ('no specific','not found','"error"',"'error'",'no data')):
                verified.append((arg,call_function(n,arg,codes[n])));break
        else:return
    return a,b,verified,fs,codes
def test(job):
    t,packet,arm=job;i=t['id'];p=R/'out/order'/f'{i}_{arm}.json'
    if p.exists():return
    a,b,verified,fs,codes=packet
    labels=('W12','Q59') if int(i)%2 else ('Q59','W12')
    active=labels[0];context=dict(job=active if arm=='prior' else labels[1],tool=a,arguments=verified[0][0],returned=verified[0][1][:1100])
    given={name:pair[0] for name,pair in [(a,verified[0]),(b,verified[1])]}
    state=f'Process job {active}. Each job requires {a} before {b}; do each operation exactly once per job. A receipt from another job does not count. Take only the next outstanding operation. The dispatcher has already verified both argument packets. Use the packet for the operation that is due.\nPackets: '+json.dumps(given)+'\nAvailable receipt: '+json.dumps(context)
    expect=a if arm=='other' else b;args=given[expect]
    u=chat([user(state+'\nWhich operation is due next? Reply only with its exact tool name.')],80)['message']['content'] or ''
    m=chat([user(state+'\nExecute the next operation now.')],300,tools=list(fs.values()))['message'];calls=m.get('tool_calls') or []
    ok=False;right=False;executions=[]
    for c in calls:
        f=c['function'];n=f['name']
        try:d=json.loads(f['arguments']);o=call_function(n,d,codes[n]);executions.append((n,d,o));right=len(calls)==1 and n==expect;ok=right and Draft7Validator(fs[n]['function']['parameters']).is_valid(d) and all(norm(z) in norm(o) for z in json.loads(t['unsolved_set'])[n])
        except Exception as err:executions.append((n,None,str(err)))
    save(p,dict(id=i,arm=arm,expected=expect,understood=norm(u).strip('.\x60')==norm(expect),acted=ok,selected=right,raw_u=u,raw_e=m,executions=executions,state=state))
if __name__=='__main__':
    data={t['id']:t for t in map(json.loads,(P/'upstream/CCTU/data/input_data.jsonl').open())}
    eligible=[];jobs=[]
    for i in PAIRS:
        x=packets(data[i])
        if x:
            eligible.append(i);jobs.extend((data[i],x,arm) for arm in ('prior','other'))
    save(R/'out/order_manifest.json',dict(eligible=eligible,screened=list(PAIRS),selection='both native calls have schema-valid independently executable packets returning expected values'))
    random.Random(233).shuffle(jobs)
    with ThreadPoolExecutor(3) as pool:list(pool.map(test,jobs))
