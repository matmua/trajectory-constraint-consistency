"""Post-run rule recognition probes; these are not additional shopping episodes."""
import json,pathlib,requests,time
from run_constraint_study import workflow
ROOT=pathlib.Path(__file__).resolve().parents[1]
session=requests.Session();session.trust_env=False
rows=[]
for goal_id in range(10):
    procedure,first,second=workflow(goal_id,'ordered')
    prompt=(procedure+'\n\nFor the same product, which sequence satisfies the procedure?\n'
            'A: visit Description, then visit Features, then click Buy Now.\n'
            'B: visit Features, then visit Description, then click Buy Now.\n'
            'Reply with exactly A or B.')
    start=time.perf_counter()
    response=session.post('http://127.0.0.1:8000/v1/chat/completions',
        json={'model':'Qwen3.5-9B','messages':[{'role':'user','content':prompt}],
              'max_tokens':16,'temperature':0,'seed':233,
              'chat_template_kwargs':{'enable_thinking':False}},timeout=(5,180))
    response.raise_for_status();data=response.json()
    output=(data['choices'][0]['message'].get('content') or '').strip()
    expected='A' if first=='description' else 'B'
    rows.append({'goal_id':goal_id,'prompt':prompt,'output':output,'expected':expected,
                 'correct':output==expected,'latency_seconds':time.perf_counter()-start,
                 'usage':data.get('usage',{})})
    print('PROBE',goal_id,output,expected,flush=True)
report={'note':'Post-run, isolated forced-choice recognition; easier than online execution and not proof of identical internal understanding.',
        'correct':sum(x['correct'] for x in rows),'total':len(rows),'rows':rows}
(ROOT/'results/constraint_study/order_recognition_probes.json').write_text(json.dumps(report,indent=2))
