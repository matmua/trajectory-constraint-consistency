"""Chinese AND-only benchmark and separately generated, matched one-rubric prompts."""
import re,sys
from common import *
sys.path.insert(0,str(UP/'ComplexBench/evaluation'))
from prompts.RAL_evaluator import EVALUATION_PROMPT
from prompts.RAL_extractor import EXTRACTION_PROMPT,EXTRACTION_PROMPT_EACH
from rule_based_evaluation import preprocess,decompose_judge
from aggregation import get_rely_judgment

def judge_point(q,inst,answer):
    a=answer[:4000];i=inst[:6000]
    if q['rule'] is not None:
        template=EXTRACTION_PROMPT_EACH if 'each' in q['rule'] else EXTRACTION_PROMPT
        notes=judged(template.format(instruction=i,response=a,question=q['question']))
        _,spans=preprocess(answer,notes)
        result=decompose_judge(q['rule'],spans)
        if result not in (0,1):raise ValueError('Unsupported rule: '+q['rule'])
        return {'pass':bool(result), 'judge':notes,'method':'rule'}
    notes=judged(EVALUATION_PROMPT.format(input=i,output=a,question=q['question']))
    hits=re.findall(r'答案：是|答案：否',notes)
    ok=('是' in hits[0]) if len(hits)==1 else ('是' in notes and '否' not in notes)
    return {'pass':ok,'judge':notes,'method':'semantic'}
def run(item):
    r,group=item
    ident=str(r['main_id']); dest=OUT/'E1'/group/(ident+'.json')
    if dest.exists():return
    questions=r['scoring_questions']; inst=r['instruction']
    if group=='single_clean':
        from single_controls import instruction
        inst=instruction(r['main_id'],r['instruction'])
        candidates=[q for q in questions if len(q['constraint_dimensions'])==1]
        questions=[min(candidates or questions,key=lambda x:rank(str(r['main_id'])+'-'+str(x['point_id'])))]
        save(OUT/'E1_reviewed_prompts'/(ident+'.json'),{'instruction':inst,'point_id':questions[0]['point_id']})
    raw=OUT/'E1_answers'/group/(ident+'.json')
    if not raw.exists():save(raw,chat([user(inst)],2048))
    gen=read(raw);answer=gen['message']['content'] or ''
    items=[]
    for q in questions:
        one=OUT/'E1_points'/group/ident/(str(q['point_id'])+'.json')
        if not one.exists():save(one,dict(point_id=q['point_id'],**judge_point(q,inst,answer)))
        items.append(read(one))
    flags=[x['pass'] for x in items]
    if group=='multi': flags=get_rely_judgment(dict(scoring_questions=questions,point_judges=flags))['point_judges_rely']
    save(dest,{'id':ident,'group':group,'points':items,'flags':flags,'success':all(flags),'finish':gen['finish']})
if __name__=='__main__':
    n=int(os.getenv('TARGET_N','20'))
    ids=read(ROOT/f'manifest-{n}.json')['selected']['E1']
    data={r['main_id']:r for r in read(UP/'ComplexBench/data/data_final.json')}
    run_pool([(data[i],g) for i in ids for g in ['multi','single_clean']],run,6)
