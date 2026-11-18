"""Native CCTU tool schemas, simulator feedback and official SR/PSR."""
import sys
from copy import deepcopy
from common import *
sys.path.insert(0,str(UP/'CCTU'))
from response_generator import get_feedback
from utils.constraint_checker import DialogueConstraintChecker
from evaluation import judge,has_if_error_in_text,_ERR_RE
def run(r):
    ident=r['id']; dest=OUT/'E2'/(ident+'.json')
    if dest.exists():return
    messages=deepcopy(r['messages']); tools=json.loads(r['tools'])
    checker=DialogueConstraintChecker(sample=r,max_turns=20,validators_dir=str(UP/'CCTU/data'))
    steps=[]
    for turn in range(1,21):
        p=OUT/'E2_calls'/ident/(str(turn)+'.json')
        if not p.exists(): save(p,chat(messages,1024,tools=tools))
        res=read(p);raw=res['message']
        msg={k:v for k,v in raw.items() if k in ('role','content','tool_calls') and v is not None}
        messages.append(msg)
        done,feedback=get_feedback(msg,r,checker)
        messages.extend(deepcopy(feedback))
        errors=[err for f in feedback for err in _ERR_RE.findall(f.get('content',''))]
        steps.append({'turn':turn,'violations':errors,'calls':len(msg.get('tool_calls',[])),'finish':res['finish']})
        if done:break
    sr,psr=judge(messages,r)
    save(dest,dict(id=ident,group=r['data_source'],sr=sr,psr=psr,steps=steps,first_violation=next((s['turn'] for s in steps if s['violations']),None),messages=messages))
if __name__=='__main__':
    n=int(os.getenv('TARGET_N','20'))
    selected=read(ROOT/f'manifest-{n}.json')['selected']
    ids=selected['E2_Multi-Hop']+selected['E2_Parallel Multi-Hop']
    data={r['id']:r for r in (json.loads(l) for l in (UP/'CCTU/data/input_data.jsonl').open())}
    run_pool([data[i] for i in ids],run,4)
