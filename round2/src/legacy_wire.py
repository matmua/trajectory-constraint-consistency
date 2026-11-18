"""Test the output adapter against *old* submitted trajectories using official resets."""
import sys
from concurrent.futures import ProcessPoolExecutor
from app import R,AppWorld,read,save,attach,code_of
from wire import install
def run(job):
    i,arm=job;out=R/'out/legacy_wire'/arm/(i+'.json')
    if out.exists():return
    row=read(R.parent/'round1/output/E4'/arm/(i+'.json'))
    original={x['requirement'] for x in row['tests']['passes']}
    if not row['submitted']:
        save(out,dict(tgc=row['tgc'],replayed=False,changed=0,same_business=True,same_prefix=True))
        return
    w=AppWorld(task_id=i,experiment_name='round2_legacy_wire_'+arm,random_seed=233,max_interactions=22,max_api_calls_per_interaction=150,timeout_seconds=45,raise_on_failure=True,raise_on_unsafe_syntax=True,null_patch_unsafe_execution=True)
    try:
        events=attach(w);changes=install(w);same_prefix=True
        for t in row['trace']:
            ix=len(events)
            try:w.execute(code_of(t['completion']))
            except (SyntaxError,ValueError):pass
            actual=[(e['app'],e['api'],e['ok']) for e in events[ix:]]
            expected=[(e['app'],e['api'],e['ok']) for e in t['apis']]
            same_prefix &= actual==expected and w.task_completed()==t['submitted']
        test=w.evaluate();passed={x['requirement'] for x in test.to_dict()['passes']}
        without_answer=lambda ss:{s for s in ss if s!='assert answers match.'}
        save(out,dict(tgc=bool(test.success),replayed=True,changed=len(changes),same_business=without_answer(original)==without_answer(passed),same_prefix=same_prefix))
    finally:w.close()
if __name__=='__main__':
    ids=read(R.parent/'round1/app-manifest-20.json')['selected']
    jobs=[(i,a) for i in ids for a in 'ABC']
    with ProcessPoolExecutor(max_workers=3) as pool:list(pool.map(run,jobs))
