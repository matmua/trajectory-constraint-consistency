"""Paired early goal-switch study: 10 final targets x static/switch, no added workflow checks."""
import argparse,concurrent.futures,copy,datetime,json,pathlib,random,re,time
import numpy as np
import requests
from bs4 import BeautifulSoup
from run_examples import SYSTEM,request_action
from web_agent_site.envs.web_agent_text_env import WebAgentTextEnv
from web_agent_site.engine.goal import get_reward
ROOT=pathlib.Path(__file__).resolve().parents[1]

def clean(v):
    if isinstance(v,np.generic):return v.item()
    if isinstance(v,dict):return {k:clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [clean(x) for x in v]
    return v

def snap(env):
    s=env.server.user_sessions[env.session]
    return {'asin':s.get('asin'),'options':dict(s.get('options',{})),
            'url':env.browser.current_url,'instruction':env.instruction_text}

def assign_goal(env,goal):
    """Change scoring target and visible instruction, preserving product, options, URL and history."""
    before=snap(env)
    env.server.user_sessions[env.session]['goal']=copy.deepcopy(goal)
    soup=BeautifulSoup(env.browser.page_source,'html.parser')
    heading=soup.find(id='instruction-text')
    if heading is None or heading.find('h4') is None:raise RuntimeError('Missing visible instruction header')
    heading.find('h4').string='Instruction: '+goal['instruction_text']
    env.browser.page_source=str(soup)
    env.instruction_text=env.get_instruction_text()
    after=snap(env)
    assert all(before[k]==after[k] for k in ['asin','options','url'])
    assert goal['instruction_text'] in env.observation
    return env.observation

def build_cases(server):
    attributes={
      1:('flavor name','pecan','honey cinnamon','pecan','honey cinnamon'),
      3:('size','60x40x40cm','40x40x40cm','60x40x40cm','40x40x40cm'),
      7:('size','small','large','small','large'),
      8:('size','1pcs','3pcs','an one','a three-piece (3pcs)'),
      9:('color','red','black','red','black'),
    }
    old_for_whole={0:1,2:3,4:5,5:6,6:7}
    cases=[]
    for final_id in range(10):
        if final_id in attributes:
            original=copy.deepcopy(server.goals[final_id]);final=copy.deepcopy(original)
            key,old,new,old_text,new_text=attributes[final_id]
            assert old in final['goal_options']
            final['goal_options']=[new if x==old else x for x in final['goal_options']]
            assert len(re.findall(r'\b'+re.escape(old_text)+r'\b',final['instruction_text'],re.I))==1
            final['instruction_text']=re.sub(r'\b'+re.escape(old_text)+r'\b',new_text,final['instruction_text'],flags=re.I)
            product=server.product_item_dict[final['asin']]
            assert new in product['options'][key],(key,new,product['options'])
            changed={'key':key,'old_value':old,'new_value':new}
            original_id=final_id;kind='attribute'
        else:
            original_id=old_for_whole[final_id]
            original=copy.deepcopy(server.goals[original_id]);final=copy.deepcopy(server.goals[final_id])
            changed=None;kind='whole_goal'
            assert original['asin']!=final['asin']
        # Verify that the intended target has a feasible full-reward option assignment in this simulator.
        product=server.product_item_dict[final['asin']];options={}
        for value in final['goal_options']:
            keys=[key for key,values in product['options'].items() if value in values]
            assert len(keys)==1,(final_id,value,keys)
            options[keys[0]]=value
        score,_=get_reward(product,final,server.product_prices[final['asin']],options,verbose=True)
        assert score>=1-1e-8,(final_id,score)
        cases.append({'case_id':final_id,'kind':kind,'original_goal_id':original_id,'final_goal_id':final_id,
            'original_goal':original,'final_goal':final,'changed_option':changed,
            'feasibility_check':{'reward':float(score),'options':options}})
    return clean(cases)

def execute(case,condition,env,args):
    session=requests.Session();session.trust_env=False
    env.reset(session=case['original_goal_id'])
    starting=case['original_goal'] if condition=='switch' else case['final_goal']
    obs=assign_goal(env,starting)
    messages=[{'role':'system','content':SYSTEM}]
    out=ROOT/'results/goal_switch'/condition;out.mkdir(parents=True,exist_ok=True)
    path=out/('case_%03d.jsonl'%case['case_id'])
    steps=[];transition=False;transition_step=None;event=None;done=False;reward=0.;error=None;started=time.perf_counter()
    with path.open('w') as f:
        f.write(json.dumps({'type':'episode_start','case_id':case['case_id'],'condition':condition,'kind':case['kind'],
          'original_instruction':case['original_goal']['instruction_text'],'final_instruction':case['final_goal']['instruction_text'],
          'starting_instruction':starting['instruction_text']})+'\n');f.flush()
        for step in range(1,args.max_steps+1):
            available=env.get_available_actions();before=snap(env)
            notice=event if event is not None else ''
            prompt=f'{notice}\n\nCurrent shopping instruction: {env.instruction_text}\n\nCurrent page:\n{obs}\n\nAvailable actions: {json.dumps(available)}\n\nChoose the next action.'
            event=None;messages.append({'role':'user','content':prompt})
            try:
                output,usage,latency=request_action(session,args.base_url,args.model,messages)
                match=re.search(r'(search|click)\[([^\]\n]+)\]',output or '',re.I)
                action=(match.group(1).lower()+'['+match.group(2)+']') if match else (output or '').strip()
                valid=bool(match) and ((match.group(1).lower()=='search' and available['has_search_bar']) or
                     (match.group(1).lower()=='click' and match.group(2).lower() in {v.lower() for v in available['clickables']}))
                new_obs,reward,done,_=env.step(action)
                row={'type':'step','step':step,'phase':'final_goal' if transition else 'prefix',
                    'observation':obs,'available_actions':available,'state_before':before,
                    'raw_output':output,'action':action,'valid_action':valid,'reward':float(reward),'done':bool(done),
                    'usage':usage,'latency_seconds':latency,'next_observation':new_obs,'state_after':snap(env)}
                steps.append(row);f.write(json.dumps(clean(row),ensure_ascii=False)+'\n');f.flush()
                messages.append({'role':'assistant','content':output or action});obs=new_obs
                print(json.dumps({'case':case['case_id'],'condition':condition,'step':step,'action':action,'reward':float(reward),'done':bool(done)}),flush=True)
                if done:break
                # Update before the next decision, immediately after first product page; fallback after four steps.
                if not transition and ((env.server.user_sessions[env.session].get('asin') is not None and '/item_page/' in env.browser.current_url) or step>=4):
                    old_state=snap(env);old_observation=obs
                    obs=assign_goal(env,case['final_goal']);transition=True;transition_step=step
                    if condition=='switch':
                        if case['changed_option']:
                            change=case['changed_option']
                            event=f"USER UPDATE: Change the requested {change['key']} from {change['old_value']} to {change['new_value']}. Keep all other requirements. The complete current shopping instruction below supersedes the earlier request."
                        else:
                            event="USER UPDATE: Cancel the earlier shopping request. I now want the different item described in the complete current shopping instruction below. Buy only for this new request."
                    else:
                        event="USER CONFIRMATION: My shopping request has not changed. Continue with the complete current shopping instruction below."
                    f.write(json.dumps({'type':'goal_update','after_step':step,'changed':condition=='switch','notice':event,
                        'old_instruction':old_state['instruction'],'new_instruction':env.instruction_text,
                        'state_before':old_state,'state_after':snap(env),'observation_before':old_observation,
                        'observation_after':obs},ensure_ascii=False)+'\n');f.flush()
            except Exception as exc:
                error=f'{type(exc).__name__}: {str(exc)[:500]}'
                f.write(json.dumps({'type':'error','error':error})+'\n');f.flush();break
    state=env.server.user_sessions[env.session];old_reward=None;final_score=None;breakdown={}
    if done:
        product=env.server.product_item_dict[state['asin']];price=env.server.product_prices[state['asin']]
        final_score,breakdown=get_reward(product,case['final_goal'],price,state['options'],verbose=True)
        old_reward,_=get_reward(product,case['original_goal'],price,state['options'],verbose=True)
        assert transition,'Bought before goal intervention was delivered'
        assert abs(float(final_score)-float(reward))<1e-8,'Environment scored against the wrong goal'
    changed=case['changed_option']
    exact_change=bool(done and state['options'].get(changed['key'])==changed['new_value']) if changed else None
    official_success=bool(done and transition and reward>=1-1e-8)
    success=bool(official_success and (changed is None or exact_change))
    result={'case_id':case['case_id'],'condition':condition,'kind':case['kind'],'transition_delivered':transition,
        'transition_after_step':transition_step,'steps':len(steps),'post_transition_steps':sum(x['phase']=='final_goal' for x in steps),
        'done':bool(done),'success':success,'official_success':official_success,'strict_success':bool(success and (changed is None or exact_change)),
        'reward':float(reward),'final_goal_recomputed_reward':None if final_score is None else float(final_score),
        'original_goal_counterfactual_reward':None if old_reward is None else float(old_reward),
        'stale_original_goal_success':bool(condition=='switch' and done and old_reward>=1-1e-8 and not success),
        'changed_option_exactly_met':exact_change,'changed_option':changed,'selected_options':state.get('options'),
        'purchased_asin':state.get('asin') if done else None,'reward_breakdown':breakdown,
        'valid_actions':sum(x['valid_action'] for x in steps),'max_prompt_tokens':max((x['usage'].get('prompt_tokens',0) for x in steps),default=0),
        'elapsed_seconds':time.perf_counter()-started,'error':error,'trace':str(path.relative_to(ROOT))}
    result=clean(result);(out/('case_%03d_summary.json'%case['case_id'])).write_text(json.dumps(result,indent=2,ensure_ascii=False))
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--max-steps',type=int,default=25);p.add_argument('--concurrency',type=int,default=2)
    p.add_argument('--model',default='Qwen3.5-9B');p.add_argument('--base-url',default='http://127.0.0.1:8000/v1')
    p.add_argument('--prepare-only',action='store_true');args=p.parse_args()
    random.seed(233);np.random.seed(233)
    initial=WebAgentTextEnv(observation_mode='text',num_products=1000,human_goals=True)
    cases=build_cases(initial.server)
    design={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cases':cases,
        'n_pairs':10,'n_trajectories':20,'seed':233,'max_steps':args.max_steps,'concurrency':args.concurrency,
        'conditions':['static','switch'],'trigger':'After first product page opens, fallback after four actions, before purchase.',
        'static_control':'Final goal from the start, matched confirmation turn at trigger.',
        'switch_condition':'Old goal until trigger, then new goal; environment reward and page instruction both update; state and history preserved.',
        'extra_workflow_rules':False,'temperature':0,'thinking_enabled':False,'full_history':True,
        'scope':'5 single-option changes and 5 whole-goal changes; early switch only, no estimate for late or repeated changes.'}
    design_path=ROOT/'reports/goal_switch_design.json'
    if design_path.exists():
        existing=json.loads(design_path.read_text())
        assert existing['cases']==cases,'Case definitions changed since preparation'
    else:design_path.write_text(json.dumps(design,indent=2,ensure_ascii=False))
    print('GOAL_SWITCH_DESIGN_READY',[(c['case_id'],c['kind'],c['changed_option']) for c in cases],flush=True)
    if args.prepare_only:return
    jobs=[(c,condition) for c in cases for condition in ['static','switch']];random.Random(233).shuffle(jobs)
    envs=[WebAgentTextEnv(observation_mode='text',server=initial.server,num_products=1000,human_goals=True,
          session_prefix='switchstudy_'+condition+'_'+str(case['case_id'])+'_') for case,condition in jobs]
    started=time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results=list(pool.map(lambda x:execute(x[0][0],x[0][1],x[1],args),zip(jobs,envs)))
    results.sort(key=lambda x:(x['case_id'],x['condition']))
    groups={}
    for kind in ['all','attribute','whole_goal']:
        groups[kind]={}
        for condition in ['static','switch']:
            a=[x for x in results if x['condition']==condition and (kind=='all' or x['kind']==kind)]
            groups[kind][condition]={'n':len(a),'successes':sum(x['success'] for x in a),
                'success_rate':sum(x['success'] for x in a)/len(a),'official_successes':sum(x['official_success'] for x in a),'strict_successes':sum(x['strict_success'] for x in a),
                'completed':sum(x['done'] for x in a),'mean_reward':sum(x['reward'] for x in a)/len(a),
                'errors':sum(x['error'] is not None for x in a),'stale_original_goal_successes':sum(x['stale_original_goal_success'] for x in a)}
    pairs=[]
    for c in cases:
        a=next(x for x in results if x['case_id']==c['case_id'] and x['condition']=='static')
        b=next(x for x in results if x['case_id']==c['case_id'] and x['condition']=='switch')
        pairs.append({'case_id':c['case_id'],'kind':c['kind'],'static_success':a['success'],'switch_success':b['success'],
          'reward_difference':b['reward']-a['reward'],'success_difference':int(b['success'])-int(a['success'])})
    report={'model':args.model,'design':'reports/goal_switch_design.json','groups':groups,'pairs':pairs,
      'elapsed_seconds':time.time()-started,'episodes':results,'execution_order':[(c['case_id'],cond) for c,cond in jobs],
      'success_rate_change_pp':100*(groups['all']['switch']['success_rate']-groups['all']['static']['success_rate']),
      'note':'Primary success requires full FINAL-goal reward plus exact changed-option match in attribute cases. Raw official scores are also retained. No extra Description/Features procedure.'}
    out=ROOT/'results/goal_switch';out.mkdir(exist_ok=True)
    (out/'summary.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print('GOAL_SWITCH_COMPLETE',json.dumps(groups),flush=True)
if __name__=='__main__':main()
