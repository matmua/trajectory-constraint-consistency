"""Validate goal updates and score discriminability before model rollouts."""
import copy,json,random,pathlib
import numpy as np
from run_goal_switch_study import assign_goal,build_cases,snap
from web_agent_site.envs.web_agent_text_env import WebAgentTextEnv
from web_agent_site.engine.goal import get_reward,get_option_reward
R=pathlib.Path(__file__).resolve().parents[1]
random.seed(233);np.random.seed(233)
env=WebAgentTextEnv(observation_mode='text',num_products=1000,human_goals=True)
cases=build_cases(env.server);rows=[]
for c in cases:
    if c['changed_option']:
        x=c['changed_option']
        raw=get_option_reward([x['old_value']],[x['new_value']])[0]
        rows.append({'case_id':c['case_id'],'old_value':x['old_value'],'new_value':x['new_value'],
                     'raw_fuzzy_reward_for_old_option':raw,'exact_match_for_old_option':x['old_value']==x['new_value']})
# Exercise a real environment transition: open almonds, select old flavor, then update without reset.
c=cases[1];env.reset(session=c['original_goal_id']);env.step('search[blue diamond almonds pecan]')
assert 'b003i567w4' in env.get_available_actions()['clickables']
env.step('click[b003i567w4]');env.step('click[pecan]')
before=snap(env);obs=assign_goal(env,c['final_goal']);after=snap(env)
assert all(before[k]==after[k] for k in ['asin','options','url'])
assert 'honey cinnamon' in env.instruction_text and 'pecan flavor' not in obs
env.step('click[honey cinnamon]');_,reward,done,_=env.step('click[buy now]')
assert done and reward>=1-1e-8
report={'goal_update_preserves_state':True,'new_instruction_visible':True,
        'new_goal_reward_verified':float(reward),'old_option_discriminability':rows}
(R/'reports/goal_switch_reward_checks.json').write_text(json.dumps(report,indent=2))
print('GOAL_UPDATE_VALIDATION',json.dumps(report),flush=True)
