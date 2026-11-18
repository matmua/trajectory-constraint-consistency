"""Replay saved trajectories, then test a separate final return/buy counterfactual."""
import json,pathlib,random
import numpy as np
from web_agent_site.envs.web_agent_text_env import WebAgentTextEnv
ROOT=pathlib.Path(__file__).resolve().parents[1]
random.seed(233);np.random.seed(233)
initial=WebAgentTextEnv(observation_mode='text',num_products=1000,human_goals=True)
summary=json.loads((ROOT/'results/constraint_study/summary.json').read_text())
reports=[]
for episode in summary['episodes']:
    gid=episode['goal_id'];condition=episode['condition']
    env=WebAgentTextEnv(observation_mode='text',server=initial.server,num_products=1000,
                       human_goals=True,session_prefix='replay_'+condition+'_')
    obs,_=env.reset(session=gid);visits={};mismatches=[]
    trace=[json.loads(x) for x in (ROOT/episode['trace']).read_text().splitlines()]
    steps=[x for x in trace if x['type']=='step']
    invalid=0;repeat_pairs=set();repeated=0
    for row in steps:
        if obs!=row['observation']:mismatches.append(row['step'])
        before=env.server.user_sessions[env.session]
        pair=(obs,row['action'])
        if pair in repeat_pairs:repeated+=1
        repeat_pairs.add(pair)
        if row['valid_action'] and row['action'].lower() in ['click[description]','click[features]'] and before.get('asin'):
            tab=row['action'][6:-1].lower()
            visits.setdefault(before['asin'],{}).setdefault(tab,row['step'])
        invalid+=not row['valid_action']
        obs,reward,done,info=env.step(row['action'])
        assert bool(done)==row['done'] and abs(float(reward)-row['reward'])<1e-9
    state=env.server.user_sessions[env.session];asin=state.get('asin');v=visits.get(asin,{})
    both='description' in v and 'features' in v
    first,second=episode['required_order']
    order_ok=both and v[first]<v[second]
    hypothetical=[];counter_reward=None
    if not episode['done'] and asin:
        actions=env.get_available_actions()['clickables']
        if 'buy now' not in actions and '< prev' in actions:
            env.step('click[< prev]');hypothetical.append('click[< prev]')
            actions=env.get_available_actions()['clickables']
        if 'buy now' in actions:
            _,counter_reward,finished,_=env.step('click[buy now]')
            assert finished
            hypothetical.append('click[buy now]')
    reports.append({'goal_id':gid,'condition':condition,'trace_matches_replay':not mismatches,
                    'mismatched_steps':mismatches,'invalid_actions':invalid,
                    'repeated_identical_observation_action_pairs':repeated,
                    'candidate_products_with_both_checks':len([x for x in visits.values() if len(x)==2]),
                    'final_candidate_asin':asin,'agent_checked_both_for_final_candidate':both,
                    'agent_order_correct_for_final_candidate':order_ok,
                    'counterfactual_actions':hypothetical,'counterfactual_shopping_reward':None if counter_reward is None else float(counter_reward),
                    'counterfactual_joint_success':bool(counter_reward is not None and counter_reward>=1-1e-8 and both and (condition=='atomic' or order_ok))})
report={'note':'Counterfactual actions are offline diagnostics, NOT model actions or model success. All original episode rewards remain unchanged.',
        'all_replays_match':all(x['trace_matches_replay'] for x in reports),
        'invalid_actions':sum(x['invalid_actions'] for x in reports),
        'counterfactual_joint_successes':sum(x['counterfactual_joint_success'] for x in reports),
        'episodes':reports}
(ROOT/'results/constraint_study/replay_diagnostics.json').write_text(json.dumps(report,indent=2))
print('REPLAY_DIAGNOSTICS',json.dumps({k:v for k,v in report.items() if k!='episodes'}),flush=True)
