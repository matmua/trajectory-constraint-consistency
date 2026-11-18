"""Low-computation companion to the filter/sort/format revision task."""
import sys, json, random, itertools, re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dynamic import R,chat,user,save,NEUTRAL
FIELDS=['destination','service','seal']
VOCAB=[['Harbor','Summit','Meadow','Orchard','River','Market'],['Express','Ground','Courier','Priority','Economy','Freight'],['Indigo','Pearl','Amber','Jade','Ruby','Silver']]
def test(job):
    i,n,lag,mode=job;path=R/'out/dispatch'/f'{i:02}_{n}_{lag}_{mode}.json'
    if path.exists():return
    rng=random.Random(3811+i);k=i%3
    pairs=[rng.sample(v,2) for v in VOCAB];active=list(range(3)) if n==3 else [k]
    final={FIELDS[j]:pairs[j][int(j==k)] for j in active}
    ack={'role':'assistant','content':'Understood.'}
    initial=user('Prepare a shipping label when I later give the release command. Remember these label fields: '+', '.join(FIELDS[j]+' = '+pairs[j][0] for j in active)+'. Acknowledge only.')
    change=user('For the shipping label, revise '+FIELDS[k]+' to '+pairs[k][1]+'. Acknowledge only.')
    fillers=[]
    for q,a in NEUTRAL:fillers+=[user(q+' Reply only with the number.'),{'role':'assistant','content':a}]
    prompt='Release the shipping label for parcel '+str(801+i)+'. Return only a JSON object with fields '+', '.join(FIELDS[j] for j in active)+', using the current settings.'
    msgs=[initial,ack]+(fillers if lag==0 else [])+[change,ack]+(fillers if lag else [])+[user(prompt)]
    if mode=='static':msgs=[user('Current label settings: '+', '.join(FIELDS[j]+' = '+final[FIELDS[j]] for j in active)+'. '+prompt)]
    raw=chat(msgs,110)['message']['content'] or ''
    try:o=json.loads(re.sub(r'^~~~(?:json)?\s*|\s*~~~$','',raw.strip().replace(chr(96)*3,'~~~'),flags=re.I))
    except ValueError:o=None
    valid=isinstance(o,dict)
    checks=[valid and o.get(FIELDS[j])==final[FIELDS[j]] for j in active]
    save(path,dict(template=i,active=n,lag=lag,mode=mode,field=FIELDS[k],valid=valid,revised=bool(valid and o.get(FIELDS[k])==final[FIELDS[k]]),stale=bool(valid and o.get(FIELDS[k])==pairs[k][0]),retained=[c for j,c in zip(active,checks) if j!=k],joint=bool(valid and o==final),raw=raw,expected=final,messages=msgs))
if __name__=='__main__':
    jobs=[(i,n,d,'history') for i,n,d in itertools.product(range(20),(1,3),(0,4))]+[(i,n,0,'static') for i,n in itertools.product(range(20),(1,3))]
    random.Random(233).shuffle(jobs)
    with ThreadPoolExecutor(4) as pool:list(pool.map(test,jobs))
