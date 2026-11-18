"""Paired AppWorld agent runs using the official IPython environment and state tests."""
import ast
import json
import os
import re
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor,as_completed
from common import *
from app_gold import oracle
os.environ['APPWORLD_ROOT']=str(ROOT/'aw')
SYSTEM="""Act for the user in the AppWorld simulation. Respond with one fenced Python code block per turn. The Python session persists. The object named apis is already in the namespace. Do not import apis. For example, run print(apis.api_docs.show_api_descriptions(app_name="spotify")). Use apis.<app>.<api>(named_arguments). Discover routes with apis.api_docs.show_api_descriptions(app_name=...) and apis.api_docs.show_api_doc(app_name=..., api_name=...). View the simulated account credentials through apis.supervisor.show_account_passwords(). Use print to observe results. Paginate when necessary. When finished use apis.supervisor.complete_task(answer=...) for questions or apis.supervisor.complete_task() for actions. Read and modify only the task-relevant simulator apps. Use the given current date. You have at most 20 turns."""
BLOCK={'open','exec','eval','compile','getattr','setattr','delattr','globals','locals','vars','type','dir','input','help','builtins','requester','get_ipython','exit','quit','In','Out','breakpoint','ApiCollection','Requester','admin'}
def code_of(text):
    blocks=re.findall(r'\x60\x60\x60(?:python|py)?\s*\n(.*?)\x60\x60\x60',text,re.S|re.I)
    code='\n'.join(blocks) if blocks else text.strip()
    tree=ast.parse(code)
    for node in ast.walk(tree):
        if isinstance(node,(ast.ClassDef,ast.Global,ast.Nonlocal)):raise ValueError('Unsupported syntax')
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            if isinstance(node,ast.Import) and any(a.name=='apis' for a in node.names):raise ValueError('apis is an already loaded Python object. Remove the import line and use apis directly.')
            mods=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module or '']
            if any(x not in ['datetime','calendar','math','collections','itertools','json','re','statistics','functools'] for x in mods):raise ValueError('Use simulator APIs and Python data operations only')
        name=node.id if isinstance(node,ast.Name) else node.attr if isinstance(node,ast.Attribute) else ''
        if name in BLOCK or name.startswith('_') or name in {'mro','func_globals','format_map'}:raise ValueError('Use public simulator APIs and documented objects')
    return code
def brief(x,cap):
    return json.dumps(x,ensure_ascii=False,default=str)[:cap]
def public_view(x,depth=0):
    if depth>3:return '…'
    if isinstance(x,dict):
        return {str(k):public_view(v,depth+1) for k,v in list(x.items())[:12] if not any(w in str(k).lower() for w in ('password','token','secret'))}
    if isinstance(x,(list,tuple,set)):
        return {'count':len(x),'sample':[public_view(v,depth+1) for v in list(x)[:3]]}
    if isinstance(x,(bool,float,int)) or x is None:return x
    return str(x)[:110]
def attach(world):
    events=[]
    def wrap(app,api,fn):
        def call(*args,**kwargs):
            row={'app':app,'api':api,'arguments':public_view(kwargs)}
            try: result=fn(*args,**kwargs)
            except Exception as exc:
                row.update(ok=False,error=str(exc)[:180]);events.append(row);raise
            preview=public_view(result) if 'password' not in api and api!='login' else 'authenticated/credentials returned'
            row.update(ok=True,returned=preview)
            events.append(row)
            return result
        return call
    for app in world.apis.keys():
        if app in ('admin','_requester'):continue
        group=world.apis[app]
        for name,fn in list(group.items()):
            if not name.startswith('_') and callable(fn):group[name]=wrap(app,name,fn)
    return events
READ_PREFIX=('show','list','get','search','find','retrieve','count','check','is_','login')
def ledger(events,world,initial,step):
    ok=[x for x in events if x['ok'] and x['app']!='api_docs']
    writes=[x for x in ok if not x['api'].startswith(READ_PREFIX)]
    counts=Counter(x['app']+'.'+x['api'] for x in ok)
    bindings={}
    for k,v in world.shell.user_ns.items():
        if k in initial or k.startswith('_') or any(w in k.lower() for w in ('pass','token','cred','auth')):continue
        if isinstance(v,(dict,list,tuple,int,float,bool,str,set)):bindings[k]=public_view(v)
    return {'turn':step,'successful_api_counts':dict(counts),'accepted_effect_calls':len(writes),'recent_effects':writes[-5:],'recent_successful_reads':[x for x in ok if x['api'].startswith(READ_PREFIX)][-4:],'current_session_variables':dict(list(bindings.items())[-12:]),'unsuccessful_api_calls':sum(not x['ok'] for x in events),'task_submitted':False}
def evaluate(job):
    from appworld import AppWorld
    i,group=job;dest=OUT/'E4'/group/(i+'.json')
    if dest.exists():return
    world=AppWorld(task_id=i,experiment_name='round1_'+group,random_seed=233,max_interactions=22,max_api_calls_per_interaction=150,timeout_seconds=45,raise_on_failure=True,raise_on_unsafe_syntax=True,null_patch_unsafe_execution=True)
    try:
        instruction=world.task.instruction; profile=world.task.supervisor
        stamp=str(world.task.datetime)
        identity=f"Simulated supervisor: {profile.first_name} {profile.last_name}, email {profile.email}, phone {profile.phone_number}. Simulator time: {stamp}."
        prompt=identity+'\nUser task: '+instruction
        if group!='A':prompt+='\nVerified active constraints and dependencies:\n'+json.dumps(oracle(i),ensure_ascii=False)
        base=[{'role':'system','content':SYSTEM},user(prompt)]
        history=[];trace=[];events=attach(world);initial=set(world.shell.user_ns)
        for step in range(1,21):
            # Keep complete action/observation pairs until a conservative 32k-context reserve is reached.
            tail=history[:]
            while len(tail)>2 and sum(len(m['content']) for m in tail)>50000:tail=tail[2:]
            messages=base+tail; state=None
            if group=='C':
                state=ledger(events,world,initial,step)
                messages=messages+[user('Current verified simulator progress. Counts are cumulative. Results below are observations, and session variables are current. The structured requirements above remain in effect.\n'+brief(state,9500))]
            resp=chat(messages,1000); text=resp['message']['content'] or ''
            ix=len(events)
            try:
                code=code_of(text)
                obs=world.execute(code)
            except (SyntaxError,ValueError) as exc:
                code='';obs='Execution failed: '+str(exc)
            done=world.task_completed()
            trace.append(dict(step=step,completion=text,observation=obs,state=state,apis=events[ix:],finish=resp['finish'],submitted=done,usage=resp['usage'],history_pairs_omitted=(len(history)-len(tail))//2))
            save(OUT/'E4_steps'/group/i/f'{step:02}.json',trace[-1])
            history.extend([{'role':'assistant','content':text},user('Environment output:\n'+obs[:4500])])
            if done:break
        tracker=world.evaluate()
        test=tracker.to_dict()
        save(dest,{'id':i,'condition':group,'tgc':tracker.success,'tests':test,'submitted':done,'trace':trace})
    finally:world.close()
if __name__=='__main__':
    n=int(os.getenv('TARGET_N','20'))
    ids=read(ROOT/f'app-manifest-{n}.json')['selected']
    jobs=[(i,g) for i in ids for g in sorted('ABC',key=lambda c:rank(i+c)) if not (OUT/'E4'/g/(i+'.json')).exists()]
    with ProcessPoolExecutor(max_workers=6,max_tasks_per_child=1) as pool:
        futures={pool.submit(evaluate,j):j for j in jobs}
        for future in as_completed(futures):
            try:future.result();print('finished',futures[future],flush=True)
            except Exception as e:print('ERROR',futures[future],repr(e)[:600],flush=True)
