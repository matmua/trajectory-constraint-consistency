"""Paired AppWorld ablation. All task material and traces stay private on server."""
import sys, os, json, argparse, re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R.parent/'round1/src'))
from app_execute import SYSTEM, code_of, attach
from common import chat, save, read, user
from appworld import AppWorld

def echo_hooks(world):
    docs=[]
    group=world.apis.api_docs
    for name in ('show_app_descriptions','show_api_descriptions','show_api_doc'):
        if name not in group:continue
        def wrap(fn):
            def call(*a,**kw):
                value=fn(*a,**kw)
                docs.append(value)
                return value
            return call
        group[name]=wrap(group[name])
    return docs

def run(job):
    import fcntl
    lockdir=R/'out/app_locks'
    lockdir.mkdir(exist_ok=True,parents=True)
    with (lockdir/(job[1]+'_'+job[0]+'.lock')).open('w') as gate:
        fcntl.flock(gate,fcntl.LOCK_EX)
        return run_locked(job)

def run_locked(job):
    i,arm=job
    path=R/'out/app'/arm/(i+'.json')
    if path.exists():return
    limit=20 if arm.endswith('20') else 50
    world=AppWorld(task_id=i,experiment_name='round2_'+arm,random_seed=233,max_interactions=limit+2,max_api_calls_per_interaction=150,timeout_seconds=45,raise_on_failure=True,raise_on_unsafe_syntax=True,null_patch_unsafe_execution=True)
    try:
        p=world.task.supervisor
        prompt=f"Simulated supervisor: {p.first_name} {p.last_name}, email {p.email}, phone {p.phone_number}. Simulator time: {world.task.datetime}.\nUser task: {world.task.instruction}"
        system=SYSTEM.replace('20 turns',f'{limit} turns')
        base=[{'role':'system','content':system},user(prompt)]
        history=[]; trace=[]; events=attach(world); docs=echo_hooks(world); done=False
        for step in range(1,limit+1):
            tail=history[:]
            while len(tail)>2 and sum(len(m['content']) for m in tail)>50000:tail=tail[2:]
            cache=R/'out/app_steps'/arm/i/f'{step:02}.json'
            # Re-execute any cached prefix in a fresh simulator on recovery.
            resp=read(cache)['response'] if cache.exists() else chat(base+tail,1000)
            completion=resp['message']['content'] or ''
            ix=len(events);dx=len(docs)
            try:obs=world.execute(code_of(completion))
            except (SyntaxError,ValueError) as e:obs='Execution failed: '+str(e)
            echoed=False
            if arm.startswith('echo') and obs.strip()=='Execution successful.' and len(docs)>dx:
                obs=json.dumps(docs[dx:],ensure_ascii=False,default=str);echoed=True
            done=world.task_completed()
            row=dict(step=step,response=resp,obs=obs[:4500],echoed=echoed,events=events[ix:],submitted=done)
            save(cache,row);trace.append(row)
            history.extend([{'role':'assistant','content':completion},user('Environment output:\n'+obs[:4500])])
            if done:break
        t=world.evaluate()
        save(path,dict(id=i,arm=arm,tgc=bool(t.success),tests=t.to_dict(),submitted=done,trace=trace))
    finally:world.close()

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('arms',nargs='+');ap.add_argument('--reverse',action='store_true');ap.add_argument('--workers',type=int,default=3);args=ap.parse_args()
    ids=read(R.parent/'round1/app-manifest-20.json')['selected'][:10]
    save(R/'out/app_ids.json',ids)
    jobs=[(i,g) for g in args.arms for i in (list(reversed(ids)) if args.reverse else ids)]
    with ProcessPoolExecutor(max_workers=args.workers,max_tasks_per_child=1) as pool:
        fs={pool.submit(run,j):j for j in jobs}
        for f in as_completed(fs):f.result();print('finished',fs[f],flush=True)
