"""Offline scoring of the same actions. Evaluator outputs are never provided to the agent."""
from common import *
from app_execute import code_of,attach
from concurrent.futures import ProcessPoolExecutor
def assertion_sets(world):
    t=world.evaluate().to_dict()
    return {z['requirement'] for z in t['passes']},{z['requirement'] for z in t['failures']}
def replay(path):
    from appworld import AppWorld
    r=read(path);i=r['id'];g=r['condition'];p=OUT/'E4_replay'/g/(i+'.json')
    if p.exists():return
    w=AppWorld(task_id=i,experiment_name='round1_offline_'+g,random_seed=233,max_interactions=22,max_api_calls_per_interaction=150,timeout_seconds=45,raise_on_failure=True,raise_on_unsafe_syntax=True,null_patch_unsafe_execution=True)
    try:
        events=attach(w);initial,missing=assertion_sets(w);stage=[];fail=missing;passed=initial
        same_calls=True;same_end=True
        for t in r['trace']:
            ix=len(events)
            try:obs=w.execute(code_of(t['completion']))
            except (SyntaxError,ValueError) as exc:obs='Execution failed: '+str(exc)
            same_calls &= [(a['app'],a['api'],a['ok']) for a in events[ix:]]==[(a['app'],a['api'],a['ok']) for a in t['apis']]
            same_end &= w.task_completed()==t['submitted']
            passed,fail=assertion_sets(w)
            stage.append({'step':t['step'],'initially_passing_now_failed':sorted(initial&fail),'newly_satisfied':sorted(passed-initial),'pass_count':len(passed)})
        same_terminal=passed=={a['requirement'] for a in r['tests']['passes']}
        save(p,{'id':i,'condition':g,'same_call_sequence_and_status':same_calls,'same_submission_steps':same_end,'same_final_assertions':same_terminal,'initially_passing':sorted(initial),'initially_missing':sorted(missing),'steps':stage})
    finally:w.close()
if __name__=='__main__':
    n=int(os.getenv('TARGET_N','20'))
    ids=read(ROOT/f'app-manifest-{n}.json')['selected']
    import multiprocessing
    while True:
        paths=[OUT/'E4'/g/(i+'.json') for g in 'ABC' for i in ids]
        pending=[p for p in paths if p.exists() and not (OUT/'E4_replay'/p.relative_to(OUT/'E4')).exists()]
        if pending:
            with ProcessPoolExecutor(3,max_tasks_per_child=1) as pool:
                for p,f in zip(pending,[pool.submit(replay,p) for p in pending]):
                    try:f.result()
                    except Exception as e:print('ERROR',p.stem,repr(e)[:200],flush=True)
        if all((OUT/'E4_replay'/p.relative_to(OUT/'E4')).exists() for p in paths):break
        time.sleep(12)
