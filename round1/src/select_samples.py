"""Immutable deterministic pilot IDs and ordered candidates for later additions."""
import re, subprocess, hashlib
from common import *
CCTU=UP/'CCTU/data/input_data.jsonl'
def main():
    e1=read(UP/'ComplexBench/data/data_final.json')
    clean=re.compile(r'bioweapon|weaponiz|weapon|munitions|explosive|detonat|malware|credential theft|intrusion|exfiltrat|reverse shell|penetration test|exploit development|pathogen|virolog|virus|viral vector|bacteri|recombinant|genome.edit|gene.edit|CRISPR|synthesis screening|nucleic acid|influenza|missile|firearm|ballistic|artillery|armed attack|ammunition|炸弹|爆炸物|武器|病毒改造|攻击代码|枪械|弹药',re.I)
    another=re.compile(r'NSFWGPT|DAN:|jailbreak|uncensored|BasedGPT|sexual|explicit erotic',re.I)
    eligible=[r for r in e1 if r['category']=='And' and all(not q['dep'] for q in r['scoring_questions']) and len(r['scoring_questions'])>=2 and not clean.search(r['instruction']+r.get('instruction_en',''))]
    pools={'E1':[r['main_id'] for r in sorted(eligible,key=lambda r:rank(r['main_id']))]}
    data=[json.loads(l) for l in CCTU.open()]
    for kind in ['Multi-Hop','Parallel Multi-Hop']:
        rows=[r for r in data if r['data_source']==kind and not clean.search(r['messages'][-1]['content'])]
        pools['E2_'+kind]=[r['id'] for r in sorted(rows,key=lambda r:rank(r['id']))]
    for kind in ['add','replace']:
        ids=[]
        for p in sorted((UP/'SEQUOR/data/testsets'/kind/'step_size_5').glob('*.jsonl'),key=lambda p:rank(kind+'/'+p.name)):
            rows=[json.loads(l) for l in p.read_text().splitlines()][:50]
            if len(rows)<50 or any(clean.search(r['prompt']) or another.search(r['prompt']) for r in rows): continue
            ids.append(p.stem)
        pools['E3_'+kind]=ids
    n=int(os.getenv('TARGET_N','20'))
    assert n>=2 and n%2==0
    manifest={'order':pools,'selected':{k:v[:n if k=='E1' else n//2] for k,v in pools.items()},'target':n,
              'revisions':{p.name:subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True).strip() for p in UP.iterdir() if (p/'.git').exists()},
              'cctu_data_sha256':hashlib.sha256(CCTU.read_bytes()).hexdigest()}
    out=ROOT/f'manifest-{n}.json'
    if out.exists(): assert read(out)==manifest
    else: save(out,manifest)
if __name__=='__main__': main()
