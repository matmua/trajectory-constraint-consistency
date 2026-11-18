"""Product-specific prerequisite probes in real resettable WebShop pages."""
import re, sys, json, hashlib, random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R.parent/'round1/src'))
from common import chat,save,user
from web_agent_site.envs.web_agent_text_env import WebAgentTextEnv
queries=['shampoo','shirt','cream','shorts','storage','soap','coffee','lamp','towel','dress','pants','chair','bottle','brush','tea','bag','gloves','mask','oil','shoe']
def run(arg):
    i,order,arm,env=arg
    p=R/('out/web_ledger' if '--ledger' in sys.argv else 'out/web')/f'{i:02}_{order}_{arm}.json'
    if p.exists():return
    history=[];obs,_=env.reset(session=i%10)
    def advance(act):
        nonlocal obs
        v=env.get_available_actions()
        if act.startswith('click['):assert act[6:-1] in v['clickables'],(i,arm,act,v)
        obs,reward,done,_=env.step(act)
        session=env.server.user_sessions[env.session]
        history.append(dict(action=act,asin=session.get('asin'),page=env.browser.current_url.split('/')[3]))
    advance('search['+queries[i]+']')
    results=[x for x in env.get_available_actions()['clickables'] if re.fullmatch('[a-z0-9]{10}',x)]
    assert len(results)>=2,(queries[i],results)
    target=results[i%2];other=results[1-i%2]
    first,second=('description','features') if order==0 else ('features','description')
    atomic=arm=='atomic'
    if not atomic:
        advance('click['+(target if arm=='same' else other)+']')
        advance('click['+first+']')
        advance('click[< prev]')
        advance('click[< prev]')
    advance('click['+target+']')
    v=env.get_available_actions();assert first in v['clickables'] and second in v['clickables']
    rule=(f'Open the {first} tab for item {target}.' if atomic else f'Inspect item {target}: first read its {first} tab, then its {second} tab. A tab visited on another item does not count. Go directly to the first outstanding tab on the current item; skip tabs already checked on it.')
    common=rule+'\nBrowser history (oldest first): '+json.dumps(history)+'\nCurrent page: '+obs+'\nAvailable actions: '+json.dumps(v)
    if '--ledger' in sys.argv:
        visits={}
        for h in history:
            if h['page']=='item_sub_page' and h['action'] in ['click[features]','click[description]']:
                visits.setdefault(h['asin'].lower(),[]).append(h['action'][6:-1])
        common+='\\nIndex of visits from this browser history, keyed by item ID: '+json.dumps(visits)
    expected=second if arm=='same' else first
    u=chat([user(common+'\nName the tab still due next. Output only its name.')],48)['message']['content'] or ''
    e=chat([user(common+'\nTake the next action. Output exactly one WebShop action in click[value] syntax.')],48)['message']['content'] or ''
    m=re.fullmatch(r'click\[([^\]\n]+)\]',e.strip(),re.I);chosen=m[1].lower() if m else ''
    valid=chosen in v['clickables'];before=env.browser.current_url
    if valid:after,reward,done,_=env.step('click['+chosen+']')
    applied=bool(valid and before!=env.browser.current_url)
    us=u.strip().strip('.').casefold()==expected
    save(p,dict(template=i,order=order,arm=arm,target=target,other=other,expected=expected,understood=us,acted=bool(chosen==expected and applied),valid=valid,applied=applied,raw_u=u,raw_e=e,prefix=common,page_hash=hashlib.sha256(obs.encode()).hexdigest(),snapshot_hash=hashlib.sha256(common.encode()).hexdigest()))
if __name__=='__main__':
    random.seed(233);init=WebAgentTextEnv(observation_mode='text',num_products=1000,human_goals=True)
    jobs=[(i,o,s) for i in range(20) for o in (0,1) for s in (('same','other') if '--ledger' in sys.argv else ('atomic','same','other'))]
    # Sequentially construct environments; each browser writes its own session.
    for start in range(0,len(jobs),6):
        batch=[(i,o,s,WebAgentTextEnv(observation_mode='text',server=init.server,num_products=1000,human_goals=True,session_prefix=f'round2_{i}_{o}_{s}_')) for i,o,s in jobs[start:start+6]]
        with ThreadPoolExecutor(3) as pool:list(pool.map(run,batch))
