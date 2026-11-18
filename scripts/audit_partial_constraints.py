"""Audit partial satisfaction in the saved 20 trajectories, without new model actions."""
import json,pathlib,random
import numpy as np
from web_agent_site.envs.web_agent_text_env import WebAgentTextEnv
from web_agent_site.engine.goal import get_attribute_reward,get_option_reward,get_type_reward
ROOT=pathlib.Path(__file__).resolve().parents[1]
random.seed(233);np.random.seed(233)
initial=WebAgentTextEnv(observation_mode='text',num_products=1000,human_goals=True)
study=json.loads((ROOT/'results/constraint_study/summary.json').read_text())
rows=[]
def shopping_atoms(server,state):
    asin=state.get('asin')
    if not asin:return None
    product=server.product_item_dict[asin];goal=state['goal'];selected=state['options']
    atoms={'type':bool(get_type_reward(product,goal)['r_type']>=1-1e-8),
           'price':bool(server.product_prices[asin]<=goal['price_upper'])}
    for attr in goal['attributes']:
        atoms['attribute:'+attr]=bool(get_attribute_reward(product,dict(goal,attributes=[attr]))[0]>=1-1e-8)
    assert isinstance(goal['goal_options'],list)
    for option in goal['goal_options']:
        atoms['option:'+option]=bool(get_option_reward(list(selected.values()),[option])[0]>=1-1e-8)
    return atoms
for episode in study['episodes']:
    gid=episode['goal_id'];condition=episode['condition']
    env=WebAgentTextEnv(observation_mode='text',server=initial.server,num_products=1000,
        human_goals=True,session_prefix='partial_'+condition+'_')
    obs,_=env.reset(session=gid);views={};states=[];mismatches=[]
    trace=list(map(json.loads,(ROOT/episode['trace']).read_text().splitlines()))
    for row in [x for x in trace if x['type']=='step']:
        if obs!=row['observation']:mismatches.append(row['step'])
        before=env.server.user_sessions[env.session]
        if row['valid_action'] and row['action'].lower() in ['click[description]','click[features]'] and before.get('asin'):
            views.setdefault(before['asin'],{}).setdefault(row['action'][6:-1].lower(),row['step'])
        obs,reward,done,_=env.step(row['action'])
        assert bool(done)==row['done'] and abs(float(reward)-row['reward'])<1e-9
        state=env.server.user_sessions[env.session];asin=state.get('asin');atoms=shopping_atoms(env.server,state)
        checks=views.get(asin,{})
        both='description' in checks and 'features' in checks
        first,second=episode['required_order']
        order_ok=both and checks[first]<checks[second]
        if atoms is not None:
            states.append({'step':row['step'],'asin':asin,'shopping_atoms':atoms,'shopping_all':all(atoms.values()),
                'description_visited':'description' in checks,'features_visited':'features' in checks,
                'both_checks':both,'order_ok':order_ok,
                'all_prerequisites_except_purchase':all(atoms.values()) and both and (condition=='atomic' or order_ok)})
    final_atoms=shopping_atoms(env.server,env.server.user_sessions[env.session]) if episode['done'] else None
    max_checks=max((len(x) for x in views.values()),default=0)
    row={'goal_id':gid,'condition':condition,'trace_matches':not mismatches,'done':episode['done'],
         'joint_success':episode['joint_success'],'ever_description':any('description' in v for v in views.values()),
         'ever_features':any('features' in v for v in views.values()),
         'ever_any_required_check':max_checks>=1,'ever_both_checks_same_product':max_checks==2,
         'partial_checks_but_not_joint':max_checks>=1 and not episode['joint_success'],
         'both_checks_but_not_joint':max_checks==2 and not episode['joint_success'],
         'ever_all_shopping_constraints_same_state':any(x['shopping_all'] for x in states),
         'ever_all_prerequisites_except_purchase':any(x['all_prerequisites_except_purchase'] for x in states),
         'all_prerequisites_achieved_but_not_joint':any(x['all_prerequisites_except_purchase'] for x in states) and not episode['joint_success'],
         'purchased_atom_vector':final_atoms,
         'purchased_some_but_not_all_shopping':bool(final_atoms is not None and any(final_atoms.values()) and not all(final_atoms.values())),
         'views_by_product':views,'evaluated_candidate_states':states}
    rows.append(row)
groups={}
for name,subset in [('all',rows),('atomic',[r for r in rows if r['condition']=='atomic']),('ordered',[r for r in rows if r['condition']=='ordered'])]:
    fields=['ever_description','ever_features','ever_any_required_check','ever_both_checks_same_product',
            'partial_checks_but_not_joint','both_checks_but_not_joint',
            'ever_all_shopping_constraints_same_state','ever_all_prerequisites_except_purchase',
            'all_prerequisites_achieved_but_not_joint','purchased_some_but_not_all_shopping','joint_success','done']
    groups[name]={'n':len(subset),**{f:sum(x[f] for x in subset) for f in fields}}
report={'definition':'Partial = actual successful atomic checks within a trajectory, not separate single-constraint experiments. Both checks require the same product. Shopping atom vectors are evaluated at the same state; history is not combined across products.',
        'uncompleted_purchase_scores':'16 unfinished episodes have no purchased item; do not treat missing terminal shopping atoms as observed failures.',
        'groups':groups,'all_replays_match':all(x['trace_matches'] for x in rows),'episodes':rows}
out=ROOT/'results/followup';out.mkdir(exist_ok=True)
(out/'partial_constraint_audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
print('PARTIAL_AUDIT',json.dumps(groups),flush=True)
