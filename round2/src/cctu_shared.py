"""Second understanding branch with identical native tool availability on both branches."""
import json, re
from concurrent.futures import ThreadPoolExecutor
from cctu_pairs import R,P,read,save,user,chat,norm
def run(job):
    kind,path,t=job;x=read(path);dst=R/('out/'+kind+'_shared')/path.name
    if dst.exists():return
    state=x['state']
    if kind=='cctu':msgs=[user(state),user('What exact input value belongs to the requested lookup? Return the value only.')]
    else:msgs=[user(state+'\nWhich operation is due next? Reply only with its exact tool name.')]
    m=chat(msgs,75 if kind=='cctu' else 80,tools=json.loads(t['tools']))['message']
    raw=m.get('content') or '';calls=m.get('tool_calls') or []
    exact=not calls and norm(raw).strip(' ."\x27\x60')==norm(x['expected']).strip(' ."\x27\x60')
    save(dst,dict(understood=exact,native_call_instead=bool(calls),raw_u=raw,raw_calls=calls,snapshot=state))
if __name__=='__main__':
    rows={t['id']:t for t in map(json.loads,(P/'upstream/CCTU/data/input_data.jsonl').open())}
    targets=read(R/'out/order_manifest.json')
    for kind,n in [('cctu',60),('order',len(targets['eligible'])*2)]:
        paths=sorted((R/'out'/kind).glob('*.json'));assert len(paths)==n
        with ThreadPoolExecutor(3) as pool:list(pool.map(run,[(kind,p,rows[p.stem.split('_')[0]]) for p in paths]))
