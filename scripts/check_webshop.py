import os,json,random,pathlib,numpy as np
root=pathlib.Path(__file__).resolve().parents[1]
random.seed(233);np.random.seed(233)
from web_agent_site.envs.web_agent_text_env import WebAgentTextEnv
env=WebAgentTextEnv(observation_mode='text',num_products=1000,human_goals=True)
obs,_=env.reset(session=0)
actions=env.get_available_actions()
obs2,reward,done,info=env.step('search[shampoo]')
report={'product_count':len(env.server.all_products),'goal_count':len(env.server.goals),'instruction':env.instruction_text,'initial_observation':obs,'initial_actions':actions,'search_observation':obs2,'search_actions':env.get_available_actions(),'status':'ok'}
(root/'reports/webshop_smoke.json').write_text(json.dumps(report,indent=2))
print('WEBSHOP_SMOKE_OK',report['product_count'],report['goal_count'],flush=True)
