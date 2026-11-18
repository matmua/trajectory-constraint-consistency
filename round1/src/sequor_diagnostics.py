"""Offline rejudging of the outgoing rule at replacement boundaries and task relevance at four probes."""
import ast,sys,re
from common import *
sys.path.insert(0,str(UP/'SEQUOR/multi_if'))
from extract_tasks import process_prompt
def score(job):
    k,i,turn,kind=job
    out=OUT/'E3_aux'/kind/k/i/f'{turn:02}.json'
    if out.exists():return
    rows=[json.loads(l) for l in (UP/'SEQUOR/data/testsets'/k/'step_size_5'/(i+'.jsonl')).read_text().splitlines()]
    a=read(OUT/'E3'/k/i/f'{turn:02}.json')['answer']
    if kind=='retired':
        target=rows[turn-2]['constraints_data'][0]['text']
        assert rows[turn-1]['constraints_data'][0]['id']!=rows[turn-2]['constraints_data'][0]['id']
    else:target=process_prompt(rows[turn-1]['prompt'])[0]
    prompt=templates['SYSTEM_PROMPT_CONSTRAINT' if kind=='retired' else 'SYSTEM_PROMPT_TASK'].format(answer=a,constraint=target)
    for attempt in range(3):
        judgment=judged(prompt)
        m=re.findall(r'Final Verdict:\s*\[\[(Yes|No)\]\]',judgment,re.I)
        if m:break
    if not m:raise ValueError('Unparsed auxiliary verdict')
    save(out,{'pass':m[-1].lower()=='yes','judgment':judgment})
if __name__=='__main__':
    tree=ast.parse((UP/'SEQUOR/multi_if/evaluation.py').read_text())
    templates={node.targets[0].id:ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and getattr(node.targets[0],'id','').startswith('SYSTEM_PROMPT_')}
    n=int(os.getenv('TARGET_N','20'));selected=read(ROOT/f'manifest-{n}.json')['selected'];jobs=[]
    for k in ('add','replace'):
        for i in selected['E3_'+k]:
            jobs.extend((k,i,t,'task') for t in (1,6,11,50))
            if k=='replace':jobs.extend((k,i,t,'retired') for t in range(6,50,5))
    while True:
        pending=[j for j in jobs if (OUT/'E3'/j[0]/j[1]/f'{j[2]:02}.json').exists() and not (OUT/'E3_aux'/j[3]/j[0]/j[1]/f'{j[2]:02}.json').exists()]
        run_pool(pending,score,12)
        if all((OUT/'E3_aux'/j[3]/j[0]/j[1]/f'{j[2]:02}.json').exists() for j in jobs):break
        time.sleep(15)
