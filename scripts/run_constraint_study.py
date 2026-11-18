"""20 paired WebShop episodes separating atomic checks from their ordering."""
import argparse,concurrent.futures,json,pathlib,random,re,time
from types import SimpleNamespace
import numpy as np
import requests
from run_examples import SYSTEM,request_action
ROOT=pathlib.Path(__file__).resolve().parents[1]

def workflow(goal_id,condition):
 first,second=('Description','Features') if goal_id%2==0 else ('Features','Description')
 common='Additional shopping procedure: For the product you eventually buy, visit both its Description page and its Features page before clicking Buy Now. Visits for other products do not count.'
 if condition=='atomic':return common+' You may visit these two pages in either order.',first.lower(),second.lower()
 return common+f' Your FIRST visit to {first} for that product must occur BEFORE your FIRST visit to {second}. Then you may click Buy Now. This order is mandatory.',first.lower(),second.lower()

def clean(v):
 if isinstance(v,np.generic):return v.item()
 if isinstance(v,dict):return {k:clean(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [clean(x) for x in v]
 return v

def state(env):
 s=env.server.user_sessions.get(env.session,{})
 return {'asin':s.get('asin'),'options':dict(s.get('options',{})),'url':env.browser.current_url}

def run_one(job,env,args):
 goal_id,condition=job;procedure,first,second=workflow(goal_id,condition)
 session=requests.Session();session.trust_env=False
 obs,_=env.reset(session=goal_id);instruction=env.instruction_text
 messages=[{'role':'system','content':SYSTEM}];records=[];reward=0.0;done=False;error=None;start=time.perf_counter();visits={}
 outdir=ROOT/'results/constraint_study'/condition;outdir.mkdir(parents=True,exist_ok=True)
 trace_path=outdir/f'episode_{goal_id:03d}.jsonl'
 with trace_path.open('w') as stream:
  stream.write(json.dumps({'type':'episode_start','goal_id':goal_id,'condition':condition,'instruction':instruction,'procedure':procedure,'model':args.model})+'\n');stream.flush()
  for step in range(args.max_steps):
   available=env.get_available_actions();before=state(env)
   prompt=f'Shopping instruction: {instruction}\n\n{procedure}\n\nCurrent page:\n{obs}\n\nAvailable actions: {json.dumps(available)}\n\nChoose the next action.'
   messages.append({'role':'user','content':prompt})
   try:
    output,usage,elapsed=request_action(session,args.base_url,args.model,messages)
    match=re.search(r'(search|click)\[([^\]\n]+)\]',output or '',re.I)
    action=(match.group(1).lower()+'['+match.group(2)+']') if match else (output or '').strip()
    valid=bool(match) and ((match.group(1).lower()=='search' and available['has_search_bar']) or (match.group(1).lower()=='click' and match.group(2).lower() in {v.lower() for v in available['clickables']}))
    new_obs,reward,done,info=env.step(action)
    tab=match.group(2).lower() if match else None
    if valid and match.group(1).lower()=='click' and tab in ('description','features') and before['asin']:
     visits.setdefault(before['asin'],{}).setdefault(tab,step+1)
    row={'type':'step','step':step+1,'observation':obs,'available_actions':available,'state_before':before,'raw_output':output,'action':action,'valid_action':valid,'reward':float(reward),'done':bool(done),'latency_seconds':elapsed,'usage':usage,'next_observation':new_obs,'state_after':state(env)}
    records.append(row);stream.write(json.dumps(row,ensure_ascii=False)+'\n');stream.flush()
    messages.append({'role':'assistant','content':output or action});obs=new_obs
    print(json.dumps({'goal_id':goal_id,'condition':condition,'step':step+1,'action':action,'reward':float(reward),'done':bool(done),'latency_seconds':round(elapsed,2)}),flush=True)
    if done:break
   except Exception as exc:
    error=f'{type(exc).__name__}: {str(exc)[:500]}'
    stream.write(json.dumps({'type':'error','error':error})+'\n');stream.flush();break
 s=env.server.user_sessions[env.session];asin=s.get('asin');v=visits.get(asin,{})
 description=bool(done and 'description' in v);features=bool(done and 'features' in v);atoms=description and features
 order_ok=bool(atoms and v[first]<v[second])
 result={'goal_id':goal_id,'condition':condition,'instruction':instruction,'procedure':procedure,'reward':float(reward),'shopping_success':bool(done and reward>=1-1e-8),'done':bool(done),'steps':len(records),'valid_actions':sum(x['valid_action'] for x in records),'elapsed_seconds':time.perf_counter()-start,'prompt_tokens':sum(x['usage'].get('prompt_tokens',0) for x in records),'completion_tokens':sum(x['usage'].get('completion_tokens',0) for x in records),'max_prompt_tokens':max((x['usage'].get('prompt_tokens',0) for x in records),default=0),'error':error,'trace':str(trace_path.relative_to(ROOT)),'purchased_asin':asin if done else None,'selected_options':s.get('options'),'goal':{k:s['goal'].get(k) for k in ['asin','attributes','goal_options','price_upper']},'reward_breakdown':s.get('verbose_info',{}),'first_visits_for_purchased_product':v if done else {},'required_order':[first,second],'description_before_purchase':description,'features_before_purchase':features,'all_atomic_checks':bool(atoms),'order_ok':order_ok if condition=='ordered' else None,'diagnostic_order_ok':order_ok,'relation_violation_given_atoms':bool(condition=='ordered' and atoms and not order_ok),'procedure_compliant':bool(atoms and (condition=='atomic' or order_ok))}
 result['joint_success']=result['shopping_success'] and result['procedure_compliant'];result=clean(result)
 (outdir/f'episode_{goal_id:03d}_summary.json').write_text(json.dumps(result,indent=2,ensure_ascii=False));return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--max-steps',type=int,default=25);p.add_argument('--concurrency',type=int,default=2);p.add_argument('--model',default='Qwen3.5-9B');p.add_argument('--base-url',default='http://127.0.0.1:8000/v1');args=p.parse_args()
 random.seed(233);np.random.seed(233)
 from web_agent_site.envs.web_agent_text_env import WebAgentTextEnv
 initial=WebAgentTextEnv(observation_mode='text',num_products=1000,human_goals=True)
 jobs=[(i,c) for i in range(10) for c in ['atomic','ordered']];random.Random(233).shuffle(jobs)
 envs=[WebAgentTextEnv(observation_mode='text',server=initial.server,num_products=1000,human_goals=True,session_prefix=c+'_') for i,c in jobs]
 started=time.time()
 with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:results=list(pool.map(lambda x:run_one(x[0],x[1],args),zip(jobs,envs)))
 results=sorted(results,key=lambda x:(x['goal_id'],x['condition']));groups={}
 for condition in ['atomic','ordered']:
  a=[x for x in results if x['condition']==condition];atoms=sum(x['all_atomic_checks'] for x in a);violations=sum(x['relation_violation_given_atoms'] for x in a)
  groups[condition]={'episodes':len(a),'completed':sum(x['done'] for x in a),'shopping_successes':sum(x['shopping_success'] for x in a),'mean_reward':sum(x['reward'] for x in a)/len(a),'atomic_check_successes':atoms,'procedure_compliant':sum(x['procedure_compliant'] for x in a),'joint_successes':sum(x['joint_success'] for x in a),'relation_violations_given_atoms':violations if condition=='ordered' else None,'conditional_relation_violation_rate':violations/atoms if condition=='ordered' and atoms else None,'errors':sum(x['error'] is not None for x in a)}
 summary={'model':args.model,'design':'10 fixed human goals, paired atomic vs ordered procedure; NOT the original WebShop benchmark score','goal_ids':list(range(10)),'catalog_size':1000,'human_goal_pool_size':len(initial.server.goals),'seed':233,'thinking_enabled':False,'temperature':0,'max_steps':args.max_steps,'concurrency':args.concurrency,'max_context_tokens':16384,'instruction_repeated_each_step':True,'full_history':True,'external_action_enforcement':False,'execution_order':jobs,'groups':groups,'episodes':results,'elapsed_seconds':time.time()-started,'total_episodes':len(results)}
 (ROOT/'results/constraint_study/summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False));print('CONSTRAINT_STUDY_COMPLETE',json.dumps(groups),flush=True)
if __name__=='__main__':main()
