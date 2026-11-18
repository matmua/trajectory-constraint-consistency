"""Check denominators, keyed records and the upstream final CCTU and AppWorld scores."""
import sys
from common import *
def main():
    n=int(os.getenv('TARGET_N','20'));sel=read(ROOT/f'manifest-{n}.json')['selected']
    ids=read(ROOT/f'app-manifest-{n}.json')['selected'];v=read(OUT/f'summary-{n}.json')
    assert v['E1']['joint'][1]==n==v['E1']['single'][1]
    sys.path.insert(0,str(UP/'CCTU'))
    from evaluation import judge
    c={r['id']:r for r in (json.loads(l) for l in (UP/'CCTU/data/input_data.jsonl').open())}
    for k in ['Multi-Hop','Parallel Multi-Hop']:
        for i in sel['E2_'+k]:
            r=read(OUT/'E2'/(i+'.json'));assert (r['sr'],r['psr'])==judge(r['messages'],c[i])
    for k in ('add','replace'):
        assert v['E3'][k]['rates']['per_turn'][1]==50*n//2
        assert v['E3'][k]['rates']['task_relevance'][1]==4*n//2
        assert len(sel['E3_'+k])==len(set(sel['E3_'+k]))==n//2
    assert sum(v['E3']['replace']['replacement_verdicts_new_old'].values())==9*n//2
    assert len(ids)==len(set(ids))==n
    for i in ids:
        for g in 'ABC':
            r=read(OUT/'E4'/g/(i+'.json'))
            assert r['tgc']==(not r['tests']['failures'] and len(r['tests']['passes'])==r['tests']['num_tests'])
            assert len(r['trace'])==len(list((OUT/'E4_steps'/g/i).glob('*.json')))
            assert all((s['state'] is not None)==(g=='C') for s in r['trace'])
    assert v['E4']['reference_solutions']==[n,n]
    save(OUT/'verification.json',{'n':n,'cctu_official_rescore':True,'unique_ids':True,'sequor_turns':50*n,'appworld_condition_trajectories':3*n,'reference_solution_passes':n,'strict_replay_matches':v['E4']['valid_replays']})
if __name__=='__main__':main()
