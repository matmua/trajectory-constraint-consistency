"""Paired original shopping goals with optional visited-tabs index, 25 steps."""
import sys, re, random, json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from web import R,chat,save,user,WebAgentTextEnv
sys.path.insert(0,str(R.parent/'scripts'))
from run_constraint_study import workflow,SYSTEM,state
def run(job):
    i,arm,e=job;path=R/'out/full_web'/f'{i}_{arm}.json'
    if path.exists():return
    obs,_=e.reset(session=i);ins=e.instruction_text
    procedure,first,second=workflow(i,'ordered');history=[{'role':'system','content':SYSTEM}];visits={};trace=[];done=False;reward=0
    for t in range(1,26):
        v=e.get_available_actions();before=state(e);prompt=f'Shopping instruction: {ins}\n\n{procedure}\n\nCurrent page:\n{obs}\n\nAvailable actions: {json.dumps(v)}\n\nChoose the next action.'
        if arm=='ledger':prompt+='\nIndex of past visits by item, tab and first step: '+json.dumps(visits)
        history.append(user(prompt));text=chat(history,192)['message']['content'] or ''
        m=re.search(r'(search|click)\[([^\]\n]+)\]',text,re.I)
        action=m[1].lower()+'['+m[2]+']' if m else text.strip()
        valid=bool(m and ((m[1].lower()=='search' and v['has_search_bar']) or (m[1].lower()=='click' and m[2].lower() in v['clickables'])))
        obs,reward,done,_=e.step(action)
        if valid and m[1].lower()=='click' and m[2].lower() in ('description','features') and before['asin']:
            visits.setdefault(before['asin'],{}).setdefault(m[2].lower(),t)
        trace.append(dict(step=t,action=action,valid=valid,before=before,after=state(e),raw=text,reward=float(reward)))
        history.append({'role':'assistant','content':text})
        if done:break
    v=visits.get(state(e)['asin'],{});atoms=bool(done and first in v and second in v);ordered=bool(atoms and v[first]<v[second])
    save(path,dict(template=i,arm=arm,done=bool(done),shopping=bool(done and reward>=1-1e-8),reward=float(reward),atoms=atoms,ordered=ordered,joint=bool(ordered and reward>=1-1e-8),trace=trace,visits=visits))
if __name__=='__main__':
    init=WebAgentTextEnv(observation_mode='text',num_products=1000,human_goals=True)
    jobs=[(i,a) for i in range(10) for a in ('plain','ledger')];random.Random(233).shuffle(jobs)
    for off in range(0,len(jobs),4):
        batch=[(i,a,WebAgentTextEnv(observation_mode='text',server=init.server,num_products=1000,human_goals=True,session_prefix=f'r2_checkout_{a}_{i}_')) for i,a in jobs[off:off+4]]
        with ThreadPoolExecutor(4) as pool:list(pool.map(run,batch))
