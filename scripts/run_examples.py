"""Run fixed WebShop examples against a local OpenAI-compatible model server."""
import argparse,concurrent.futures,json,os,pathlib,random,re,subprocess,time
import numpy as np
import requests
ROOT=pathlib.Path(__file__).resolve().parents[1]
SYSTEM='''You are a shopping agent in the WebShop benchmark. Follow the shopping instruction, search the catalog, inspect products, select all requested options, and buy the best matching product. You interact only with the provided simulated shop.
Return exactly one action and nothing else:
search[short product keywords]
click[an exact clickable value from the current page]
Only search when the search bar is available. Product IDs and option values must come from the current page. Inspect relevant details before buying. Use click[buy now] to finish. Do not repeat an action that did not change the page.'''

def request_action(session,base_url,model,messages):
 payload={'model':model,'messages':messages,'temperature':0,'max_tokens':192,'seed':233,'chat_template_kwargs':{'enable_thinking':False}}
 start=time.perf_counter();r=session.post(base_url+'/chat/completions',json=payload,timeout=(10,180));r.raise_for_status();d=r.json()
 return d['choices'][0]['message'].get('content',''),d.get('usage',{}),time.perf_counter()-start

def run_one(goal_id,env,args):
 session=requests.Session();session.trust_env=False
 obs,_=env.reset(session=goal_id);instruction=env.instruction_text
 messages=[{'role':'system','content':SYSTEM}];records=[];reward=0.0;done=False;error=None;start=time.perf_counter()
 trace_path=ROOT/'results'/f'episode_{goal_id:03d}.jsonl'
 with trace_path.open('w') as stream:
  stream.write(json.dumps({'type':'episode_start','goal_id':goal_id,'instruction':instruction,'model':args.model})+'\n');stream.flush()
  for step in range(args.max_steps):
   available=env.get_available_actions()
   prompt=f'Shopping instruction: {instruction}\n\nCurrent page:\n{obs}\n\nAvailable actions: {json.dumps(available)}\n\nChoose the next action.'
   messages.append({'role':'user','content':prompt})
   try:
    output,usage,elapsed=request_action(session,args.base_url,args.model,messages)
    match=re.search(r'(search|click)\[([^\]\n]+)\]',output or '',re.I)
    action=(match.group(1).lower()+'['+match.group(2)+']') if match else (output or '').strip()
    valid=bool(match) and ((match.group(1).lower()=='search' and available['has_search_bar']) or (match.group(1).lower()=='click' and match.group(2).lower() in {v.lower() for v in available['clickables']}))
    new_obs,reward,done,info=env.step(action)
    row={'type':'step','step':step+1,'observation':obs,'available_actions':available,'raw_output':output,'action':action,'valid_action':valid,'reward':float(reward),'done':bool(done),'latency_seconds':elapsed,'usage':usage,'next_observation':new_obs}
    records.append(row);stream.write(json.dumps(row,ensure_ascii=False)+'\n');stream.flush()
    messages.append({'role':'assistant','content':output or action})
    obs=new_obs
    print(json.dumps({'goal_id':goal_id,'step':step+1,'action':action,'reward':float(reward),'done':bool(done),'latency_seconds':round(elapsed,2)}),flush=True)
    if done:break
   except Exception as exc:
    error=f'{type(exc).__name__}: {str(exc)[:500]}'
    stream.write(json.dumps({'type':'error','error':error})+'\n');stream.flush();break
 result={'goal_id':goal_id,'instruction':instruction,'reward':float(reward),'success':bool(done and reward>=1.0-1e-8),'done':bool(done),'steps':len(records),'valid_actions':sum(x['valid_action'] for x in records),'elapsed_seconds':time.perf_counter()-start,'prompt_tokens':sum(x['usage'].get('prompt_tokens',0) for x in records),'completion_tokens':sum(x['usage'].get('completion_tokens',0) for x in records),'error':error,'trace':str(trace_path.relative_to(ROOT))}
 state=env.server.user_sessions.get(env.session,{})
 result.update(purchased_asin=state.get('asin'),selected_options=state.get('options'),goal_asin=state.get('goal',{}).get('asin'),reward_breakdown={k:(v.item() if isinstance(v,np.generic) else v) for k,v in state.get('verbose_info',{}).items()})
 (ROOT/'results'/f'episode_{goal_id:03d}_summary.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
 return result

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--goals',default='0,1,2,3,4');ap.add_argument('--max-steps',type=int,default=15);ap.add_argument('--concurrency',type=int,default=2);ap.add_argument('--base-url',default='http://127.0.0.1:8000/v1');ap.add_argument('--model',default='Qwen3.5-9B');args=ap.parse_args()
 random.seed(233);np.random.seed(233)
 from web_agent_site.envs.web_agent_text_env import WebAgentTextEnv
 goal_ids=[int(x) for x in args.goals.split(',')]
 initial=WebAgentTextEnv(observation_mode='text',num_products=1000,human_goals=True)
 envs=[initial]+[WebAgentTextEnv(observation_mode='text',server=initial.server,num_products=1000,human_goals=True) for _ in goal_ids[1:]]
 started=time.time()
 with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
  results=list(pool.map(lambda pair:run_one(pair[0],pair[1],args),zip(goal_ids,envs)))
 summary={'model':args.model,'dataset':'WebShop official small catalog (1000 products), mirrored raw data','goal_count':len(initial.server.goals),'goal_ids':goal_ids,'seed':233,'thinking_enabled':False,'temperature':0,'max_steps':args.max_steps,'concurrency':args.concurrency,'episodes':results,'mean_reward':sum(x['reward'] for x in results)/len(results),'success_count':sum(x['success'] for x in results),'completed_count':sum(x['done'] for x in results),'error_count':sum(x['error'] is not None for x in results),'elapsed_seconds':time.time()-started,'note':'Small smoke test, not a full WebShop benchmark. All fixed goal IDs are reported without selection.'}
 (ROOT/'results/summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False));print('EXAMPLES_COMPLETE',json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
