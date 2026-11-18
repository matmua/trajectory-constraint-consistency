"""Oracle reachability check in a separate process/experiment; no model/API client."""
import os,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['APPWORLD_ROOT']=str(ROOT/'aw')
from appworld import AppWorld
def main():
    n=int(os.getenv('TARGET_N','20'))
    ids=json.loads((ROOT/f'app-manifest-{n}.json').read_text())['selected']
    for i in ids:
        p=ROOT/'output/E4_control'/(i+'.json');p.parent.mkdir(exist_ok=True)
        if p.exists():continue
        with AppWorld(task_id=i,experiment_name='r1_offline_reachability',ground_truth_mode='full',raise_on_failure=False,random_seed=233) as w:
            w.execute(w.task.ground_truth.compiled_solution_code+"\nsolution(apis, requester)")
            t=w.evaluate()
            tmp=p.with_suffix('.part');tmp.write_text(json.dumps({'id':i,'success':t.success,'passed':t.pass_count,'total':t.num_tests}));tmp.replace(p)
if __name__=='__main__':main()
