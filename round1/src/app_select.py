"""Dev tasks, rotating through generator families before repeating one."""
from collections import defaultdict
from common import *
def main():
    ids=(ROOT/'aw/data/datasets/dev.txt').read_text().splitlines()
    groups=defaultdict(list)
    for i in sorted(ids,key=rank):groups[i.split('_')[0]].append(i)
    order=[g[j] for j in range(max(map(len,groups.values()))) for g in groups.values() if len(g)>j]
    n=int(os.getenv('TARGET_N','20'));p=ROOT/f'app-manifest-{n}.json'
    value={'order':order,'selected':order[:n],'source':'appworld PyPI 0.1.3.post1, data 0.1.0','bundle_sha256':'fd9f9608c2ec71ed0ac25c3633a738b9129a318a129e31230425b9188e508250'}
    if p.exists():assert read(p)==value
    else:save(p,value)
if __name__=='__main__':main()
