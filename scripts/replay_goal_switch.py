"""Replay goal-switch logs and assess final-goal candidate states without changing scores."""
import json,pathlib,random
import numpy as np
from run_goal_switch_study import assign_goal,snap
from web_agent_site.envs.web_agent_text_env import WebAgentTextEnv
from web_agent_site.engine.goal import get_reward
ROOT=pathlib.Path(__file__).resolve().parents[1]
random.seed(233);np.random.seed(233)
initial=WebAgentTextEnv(observation_mode='text',num_products=1000,human_goals=True)
design=json.loads((ROOT/'reports/goal_switch_design.json').read_text())
study=json.loads((ROOT/'results/goal_switch/summary.json').read_text())
cases={c['case_id']:c for c in design['cases']};reports=[]
for episode in study['episodes']:
    cid=episode['case_id'];condition=episode['condition'];case=cases[cid]
    env=WebAgentTextEnv(observation_mode='text',server=initial.server,num_products=1000,human_goals=True,
        session_prefix='replay_goalupdate_'+condition+'_'+str(cid)+'_')
    env.reset(session=case['original_goal_id'])
    obs=assign_goal(env,case['original_goal'] if condition=='switch' else case['final_goal'])
    rows=list(map(json.loads,(ROOT/episode['trace']).read_text().splitlines()))
    transitioned=False;events=0;errors=[];candidate_states=[];repeats=0;seen=set();invalid=0;old_option_clicks=0
    for row in rows[1:]:
        if row['type']=='goal_update':
            assert obs==row['observation_before']
            before=snap(env);obs=assign_goal(env,case['final_goal']);after=snap(env)
            assert all(before[k]==after[k] for k in ['asin','options','url'])
            assert obs==row['observation_after']
            transitioned=True;events+=1;continue
        if row['type']!='step':raise RuntimeError('Unexpected record type: '+row['type'])
        assert obs==row['observation'],(cid,condition,row['step'],'observation mismatch')
        actions=env.get_available_actions();assert actions==row['available_actions']
        action=row['action'];valid=(action.startswith('search[') and actions['has_search_bar']) or (action.startswith('click[') and action[6:-1].lower() in actions['clickables'])
        assert bool(valid)==row['valid_action']
        invalid+=not valid
        if (obs,action) in seen:repeats+=1
        seen.add((obs,action))
        if transitioned and case['changed_option'] and action.lower()=='click['+case['changed_option']['old_value']+']':
            old_option_clicks+=1
        obs,reward,done,_=env.step(action)
        assert obs==row['next_observation']
        assert bool(done)==row['done'] and abs(float(reward)-row['reward'])<1e-8
        state=env.server.user_sessions[env.session]
        assert all(state.get(k)==row['state_after'][k] for k in ['asin','options'])
        if (transitioned or condition=='static') and state.get('asin'):
            product=env.server.product_item_dict[state['asin']]
            score,info=get_reward(product,case['final_goal'],env.server.product_prices[state['asin']],state['options'],verbose=True)
            change=case['changed_option']
            exact=state['options'].get(change['key'])==change['new_value'] if change else True
            candidate_states.append({'step':row['step'],'asin':state['asin'],'score_for_final_goal':float(score),
               'exact_changed_option':bool(exact),'all_final_requirements_ready':bool(score>=1-1e-8 and exact),
               'options':dict(state['options'])})
    assert events==1 and transitioned
    if episode['done']:
        state=env.server.user_sessions[env.session];product=env.server.product_item_dict[state['asin']]
        score,_=get_reward(product,case['final_goal'],env.server.product_prices[state['asin']],state['options'],verbose=True)
        change=case['changed_option'];exact=change is None or state['options'].get(change['key'])==change['new_value']
        assert bool(score>=1-1e-8 and exact)==episode['success']
    ready=[x['step'] for x in candidate_states if x['all_final_requirements_ready']]
    reports.append({'case_id':cid,'condition':condition,'kind':case['kind'],'replay_matches':True,
      'goal_update_events':events,'invalid_actions':invalid,'repeated_state_action_pairs':repeats,
      'old_option_clicks_after_update':old_option_clicks,
      'ever_selected_changed_option':any(x['exact_changed_option'] for x in candidate_states) if case['changed_option'] else None,
      'ever_final_requirements_ready':bool(ready),'first_ready_step':min(ready) if ready else None,
      'ready_but_not_purchased_successfully':bool(ready) and not episode['success'],
      'candidate_states':candidate_states})
groups={}
for condition in ['static','switch']:
    a=[x for x in reports if x['condition']==condition]
    groups[condition]={'n':len(a),'ever_final_requirements_ready':sum(x['ever_final_requirements_ready'] for x in a),
       'ready_but_not_purchased_successfully':sum(x['ready_but_not_purchased_successfully'] for x in a),
       'invalid_actions':sum(x['invalid_actions'] for x in a),
       'attribute_cases_ever_selected_new_option':sum(x['ever_selected_changed_option'] is True for x in a),
       'attribute_cases':sum(x['kind']=='attribute' for x in a),
       'old_option_clicks_after_update':sum(x['old_option_clicks_after_update'] for x in a)}
report={'all_replays_match':all(x['replay_matches'] for x in reports),'groups':groups,'episodes':reports,
        'note':'Shadow candidate scores are not purchases or extra model successes. All original rewards stay unchanged.'}
(ROOT/'results/goal_switch/replay_audit.json').write_text(json.dumps(report,indent=2))
print('SWITCH_REPLAY_AUDIT',json.dumps(groups),flush=True)
