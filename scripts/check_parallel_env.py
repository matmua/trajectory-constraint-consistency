"""Validate two concurrent simulator sessions; this is not model evaluation."""
import concurrent.futures,json,pathlib,random
import numpy as np
from web_agent_site.envs.web_agent_text_env import WebAgentTextEnv
ROOT=pathlib.Path(__file__).resolve().parents[1]
random.seed(233);np.random.seed(233)
first=WebAgentTextEnv(observation_mode='text',num_products=1000,human_goals=True)
second=WebAgentTextEnv(observation_mode='text',server=first.server,num_products=1000,human_goals=True)
def run(pair):
 i,env=pair;env.reset(session=i)
 env.step('search[toothbrush]' if i==0 else 'search[shirt]')
 choices=env.get_available_actions()['clickables']
 products=[x for x in choices if len(x)==10 and x[0]=='b']
 if not products:raise RuntimeError('No search results')
 env.step('click['+products[0]+']')
 obs,reward,done,info=env.step('click[buy now]')
 assert done
 return {'session':env.session,'instruction':env.instruction_text,'reward':float(reward),'done':done,'asin':env.server.user_sessions[env.session].get('asin')}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 results=list(pool.map(run,enumerate([first,second])))
assert results[0]['session']!=results[1]['session']
(ROOT/'reports/parallel_env_check.json').write_text(json.dumps({'status':'ok','note':'Scripted environment plumbing check, not model performance','sessions':results},indent=2))
print('PARALLEL_ENV_OK',flush=True)
