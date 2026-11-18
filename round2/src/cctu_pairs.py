"""Direct source binding on native CCTU downstream functions; paired snapshot probes."""
import sys, re, json, hashlib, random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
R=Path(__file__).resolve().parents[1];P=R.parent/'round1'
sys.path[:0]=[str(P/'src'),str(P/'upstream/CCTU')]
from common import user,chat,save,read
from utils.utils import call_function
def norm(x):return str(x).strip().casefold()
# Type-matched alternatives for the counterfactual docket. Native no-match is a valid response.
alternates={'51':'Mount Kilimanjaro','56':'Maple Grove Orchard','57':'Harold Bloom','76':'Colson Whitehead','83':'Navajo','89':'Cambridge Medical Supplies','90':'Mountain Sage','92':'Kiran Desai','93':'Seattle','95':'Bayou Kitchen Supply','164':'Sparta','165':'Vera Rubin','172':'Kanda River','174':'Canada','177':'Jean Gabin','179':'Dian Fossey','182':'Ali Smith','183':'Trilobite','185':'Samuel Taylor Coleridge','190':'Frida Kahlo'}
def discover():
    selected=read(P/'manifest-20.json')['selected']
    ids=selected['E2_Multi-Hop']+selected['E2_Parallel Multi-Hop']
    data={t['id']:t for t in map(json.loads,(P/'upstream/CCTU/data/input_data.jsonl').open())}
    cases=[]
    for ident in ids:
        t=data[ident];gold=json.loads(t['unsolved_set']);codes=json.loads(t['codes'])
        tools={x['function']['name']:x for x in json.loads(t['tools'])}
        edges=[]
        for a,values in gold.items():
            for b,down in gold.items():
                schema=tools[b]['function']['parameters'];req=schema.get('required',[])
                if a==b or len(req)!=1 or schema['properties'][req[0]].get('type')!='string':continue
                k=req[0]
                for v in values:
                    if not isinstance(v,str):continue
                    try:out=call_function(b,{k:v},codes[b]);altout=call_function(b,{k:alternates[ident]},codes[b])
                    except Exception:continue
                    if all(norm(z) in norm(out) for z in down) and all(norm(z) not in norm(v) and norm(z) not in norm(altout) for z in down):
                        edges.append(dict(id=ident,source=a,dest=b,key=k,value=v,alt=alternates[ident],native_expected=down))
        if not edges:continue
        case=edges[0]
        cases.append((case,t,tools,codes))
    return cases
def audit(case,t):
    seen={};receipt=False;occ=[];a,b,k,v=[case[x] for x in ('source','dest','key','value')]
    for m in read(P/'output/E2'/(t['id']+'.json'))['messages']:
        for c in m.get('tool_calls',[]):
            f=c['function'];seen[c['id']]=f
            if f['name']==b:
                try:arg=json.loads(f['arguments']).get(k)
                except ValueError:arg=None
                occ.append(dict(verified_source_before=receipt,argument_exact=norm(arg)==norm(v)))
        if m.get('role')=='tool' and seen.get(m.get('tool_call_id'),{}).get('name')==a and 'error' not in m['content'].lower() and norm(v) in norm(m['content']):receipt=True
    return dict(ever_received=receipt,calls=occ)
def test(job):
    case,t,tools,codes,arm=job;i=t['id'];path=R/'out/cctu'/f'{i}_{arm}.json'
    if path.exists():return
    a,b,k,v,x=[case[q] for q in ('source','dest','key','value','alt')]
    labels=['R17','K42'] if int(i)%2 else ['K42','R17']
    evidence=[dict(docket=labels[0],tool=a,returned=v),dict(docket=labels[1],tool=a,returned=x)]
    if int(i)%3: evidence.reverse()
    atomic=arm=='atomic';wanted=x if arm=='counter' else v
    available=list(tools.values())
    header=f'The next operation is a lookup using {b}. Use the record exactly as recorded, including proper names. Perform one lookup even when the database might have no match.'
    if atomic:state=header+f'\nThe input value for {k} is {v}.'
    else:state=header+f'\nYour assigned docket for this lookup is {labels[int(arm=="counter")]}. Use the upstream return for that docket. Two completed lookup receipts are attached in log order:\n'+json.dumps(evidence)
    common=[user(state)]
    u=chat(common+[user('What exact input value belongs to the requested lookup? Return the value only.')],75)['message']['content'] or ''
    m=chat(common+[user('Execute the requested operation now.')],220,tools=available)['message']
    cs=m.get('tool_calls') or [];outputs=[]
    for c in cs:
        f=c['function'];name=f['name']
        try:
            args=json.loads(f['arguments']);out=call_function(name,args,codes[name]);ok='error:' not in norm(out) and '"error"' not in norm(out) and not norm(out).startswith('invalid')
        except Exception as err:args={};out=str(err);ok=False
        outputs.append(dict(name=name,args=args,output=out,accepted=ok))
    exact=len(outputs)==1 and outputs[0]['name']==b and norm(outputs[0]['args'].get(k))==norm(wanted)
    acted=bool(exact and outputs[0]['accepted'])
    us=norm(u).strip(' ."\x27\x60')==norm(wanted).strip(' ."\x27\x60')
    save(path,dict(id=i,arm=arm,understood=us,acted=acted,tool_selected=len(outputs)==1 and outputs[0]['name']==b,argument_exact=exact,raw_u=u,raw_e=m,outputs=outputs,state=state,hash=hashlib.sha256(state.encode()).hexdigest(),expected=wanted))
if __name__=='__main__':
    cases=discover()
    save(R/'out/cctu_manifest.json',[dict(**c,prior=audit(c,t)) for c,t,_,_ in cases])
    jobs=[(*x,arm) for x in cases for arm in ('atomic','reference','counter')]
    random.Random(233).shuffle(jobs)
    with ThreadPoolExecutor(4) as pool:list(pool.map(test,jobs))
