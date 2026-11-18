"""Delayed first application of a single revision, with a length-matched control."""
import sys, json, re, itertools, random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R.parent/'round1/src'))
from common import user, chat, save
KEYS=['selection','order','notation']
VALUES=[['include only records with an even quantity','include only records with an odd quantity'],
        ['sort by quantity ascending','sort by quantity descending'],
        ['write each ID in lowercase','write each ID in uppercase']]
NEUTRAL=[('How many letters are in "pink"?','4'),('What is 12 minus 3?','9'),('What is 7 plus 6?','13'),('What is 3 times 2?','6')]
def assess(i,n,d,mode="history"):
    path=R/('out/dynamic' if mode=='history' else 'out/dynamic_'+mode)/f'{i:02}_{n}_{d}.json'
    if path.exists():return
    rng=random.Random(919+i);target=i%3
    initial=[(i//3+j)%2 for j in range(3)]
    final=initial[:];final[target]=1-final[target]
    active=list(range(3)) if n==3 else [target]
    records=list(zip(rng.sample(['mavo','lena','tobi','nira','vatu','senu','kovi','peli','ranu','zavi','mevi','tamu'],8),rng.sample([2,4,6,8],4)+rng.sample([1,3,5,7],4)))
    rng.shuffle(records)
    begin=user('We will prepare a dispatch list later. For the final dispatch, apply these instructions: '+'; '.join(VALUES[j][initial[j]] for j in active)+'. Acknowledge only.')
    change=user('Revise the dispatch instruction for '+KEYS[target]+': '+VALUES[target][final[target]]+'. Acknowledge only.')
    fillers=[]
    for q,a in NEUTRAL:fillers += [user(q+' Reply only with the number.'),{'role':'assistant','content':a}]
    ack={'role':'assistant','content':'Understood.'}
    msgs=[begin,ack]+(fillers if d==0 else [])+[change,ack]+(fillers if d else [])
    payload=', '.join('%s=%d'%((name.title()),val) for name,val in records)
    msgs.append(user('Prepare the final dispatch from these ID=quantity records: '+payload+'. Output only a JSON array of the resulting ID strings. Omit quantities. Where no selection rule applies, include all records. Where no order rule applies, preserve input order. Where no notation rule applies, copy the ID spelling as given.'))
    if mode=='restated':
        msgs[-1]=user('Current final dispatch instructions: '+'; '.join(VALUES[j][final[j]] for j in active)+'. '+msgs[-1]['content'])
    if mode=='static':
        msgs=[user('Current final dispatch instructions: '+ '; '.join(VALUES[j][final[j]] for j in active)+'. '+msgs[-1]['content'])]
    if mode=='recall':
        labels=[['EVEN','ODD'],['ASCENDING','DESCENDING'],['LOWERCASE','UPPERCASE']][target]
        msgs=msgs[:-1]+[user('For the final dispatch, which '+KEYS[target]+' rule is current? Reply with one word: '+' or '.join(labels)+'.')]
        raw=chat(msgs,32)['message']['content'] or ''
        save(path,dict(template=i,active=n,lag=d,target=KEYS[target],understood=raw.strip().strip('.').upper()==labels[final[target]],raw=raw))
        return
    raw=chat(msgs,220)['message']['content'] or ''
    try:
        arr=json.loads(re.sub(r'^~~~(?:json)?\s*|\s*~~~$','',raw.strip().replace(chr(96)*3,'~~~'),flags=re.I))
        valid=isinstance(arr,list) and bool(arr) and all(isinstance(x,str) for x in arr)
    except ValueError:arr=[];valid=False
    qty=dict(records)
    ids=[x.lower() for x in arr] if valid else []
    valid=valid and all(x in qty for x in ids) and len(set(ids))==len(ids)
    def checks(rules):
        allowed=[x for x,q in records if 0 not in active or q%2==rules[0]]
        selection=set(ids)==set(allowed)
        source=[x for x,q in records if x in ids]
        order=ids==(sorted(source,key=qty.get,reverse=bool(rules[1])) if 1 in active else source)
        fn=(str.upper if rules[2] else str.lower) if 2 in active else str.title
        notation=all(s==fn(s) for s in arr) if valid else False
        # A singleton cannot demonstrate a directional ordering.
        return [bool(valid and selection),bool(valid and len(ids)>=2 and order),bool(valid and notation)]
    new=checks(final);old=checks(initial)
    save(path,dict(template=i,active=n,lag=d,target=KEYS[target],revised=new[target],stale=old[target] and not new[target],retained=[new[j] for j in active if j!=target],joint=all(new),valid=valid,checks=new,raw=raw,messages=msgs))
if __name__=='__main__':
    jobs=list(itertools.product(range(20),[1,3],[0,4]));random.Random(233).shuffle(jobs)
    if '--restated' in sys.argv:
        jobs=[(*t,'restated') for t in jobs]
    elif len(sys.argv)>1:
        jobs=[(*t,'recall') for t in jobs]+[(i,n,0,'static') for i in range(20) for n in (1,3)]
    with ThreadPoolExecutor(4) as pool:list(pool.map(lambda t:assess(*t),jobs))
