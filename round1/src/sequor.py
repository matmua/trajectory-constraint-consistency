"""SEQUOR Add/Replace, step size 5, first 50 turns, full conversational history."""
import ast
import re
import sys
from common import *
mode=sys.argv[1] if len(sys.argv)>1 else 'generate'
n=int(os.getenv('TARGET_N','20'))
select=read(ROOT/f'manifest-{n}.json')['selected']
jobs=[(kind,ident) for kind in ('add','replace') for ident in select['E3_'+kind]]
def original_prompt():
    tree=ast.parse((UP/'SEQUOR/multi_if/evaluation.py').read_text())
    return next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and getattr(node.targets[0],'id','')=='SYSTEM_PROMPT_CONSTRAINT')
def generate(job):
    kind,ident=job
    rows=[json.loads(x) for x in (UP/'SEQUOR/data/testsets'/kind/'step_size_5'/(ident+'.jsonl')).read_text().splitlines()][:50]
    messages=[]
    for i,row in enumerate(rows):
        messages.append(user(row['prompt']))
        p=OUT/'E3'/kind/ident/f'{i+1:02}.json'
        if p.exists(): item=read(p)
        else:
            res=chat(messages,512)
            item={'turn':i+1,'answer':res['message']['content'] or '', 'finish':res['finish'],'usage':res['usage'],'constraints':row['constraints_data']}
            save(p,item)
        messages.append({'role':'assistant','content':item['answer']})
def score(path):
    p=OUT/'E3_scores'/path.relative_to(OUT/'E3')
    if p.exists():return
    row=read(path); scored=[]
    for c in row['constraints']:
        prompt=TEMPLATE.format(answer=row['answer'],constraint=c['text'])
        for attempt in range(3):
            verdict=judged(prompt,1100)
            m=re.findall(r'Final Verdict:\s*\[\[(Yes|No)\]\]',verdict,re.I)
            if m:break
        if not m:raise ValueError('Unparsed verdict')
        scored.append({'id':c['id'],'pass':m[-1].lower()=='yes','judgment':verdict})
    save(p,{'turn':row['turn'],'items':scored})
if __name__=='__main__':
    if mode=='generate':run_pool(jobs,generate,6)
    else:
        TEMPLATE=original_prompt()
        while True:
            paths=[p for k,i in jobs for p in (OUT/'E3'/k/i).glob('*.json')]
            missing=[p for p in paths if not (OUT/'E3_scores'/p.relative_to(OUT/'E3')).exists()]
            run_pool(missing,score,16)
            if len(paths)==len(jobs)*50 and all((OUT/'E3_scores'/p.relative_to(OUT/'E3')).exists() for p in paths):break
            time.sleep(12)
