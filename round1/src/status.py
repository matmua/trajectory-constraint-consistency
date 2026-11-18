"""Print completed units for the active manifest; used before any extension."""
from common import *
def main():
    n=int(os.getenv('TARGET_N','20'));s=read(ROOT/f'manifest-{n}.json')['selected'];aw=read(ROOT/f'app-manifest-{n}.json')['selected']
    entries={}
    for group in ['multi','single_clean']:entries['E1_'+group]=[OUT/'E1'/group/(str(i)+'.json') for i in s['E1']]
    entries['E2']=[OUT/'E2'/(i+'.json') for k in ('E2_Multi-Hop','E2_Parallel Multi-Hop') for i in s[k]]
    for root in ('E3','E3_scores'):
        entries[root]=[OUT/root/k/i/f'{t:02}.json' for k in ('add','replace') for i in s['E3_'+k] for t in range(1,51)]
    entries['E3_aux']=[OUT/'E3_aux'/label/k/i/f'{t:02}.json' for k in ('add','replace') for i in s['E3_'+k] for label,turns in [('task',[1,6,11,50]),('retired',range(6,50,5) if k=='replace' else [])] for t in turns]
    for a in ('E4','E4_replay'):entries[a]=[OUT/a/g/(i+'.json') for i in aw for g in 'ABC']
    for a in ('E4_understand','E4_control'):entries[a]=[OUT/a/(i+'.json') for i in aw]
    for k,paths in entries.items():print(f'{k}: {sum(p.exists() for p in paths)}/{len(paths)}')
if __name__=='__main__':main()
