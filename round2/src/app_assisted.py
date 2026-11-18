"""Generic assisted interface using documented simulator APIs only. Private traces."""
import sys, os, json, re
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
from app import R,AppWorld,code_of,attach,chat,user,save,read
SYSTEM="""Complete the user's task in a private AppWorld simulator. Write one fenced Python code block per turn. The Python session persists. All accounts, messages and effects exist only in the simulator. Helper functions are available:
catalog(app) lists the app's API names. doc(app, api) shows its public argument specification and success response shape. call(app, api, **kwargs) executes one real simulator API. Authentication is handled automatically. pages(app, api, **kwargs) reads all pages of a paginated list. All helpers return normal Python data. Use print(...) to inspect just the keys or sample you need. Use loops for repeated work. finish(answer) submits an answer to a question; finish() submits a completed action. Verify that the requested work and scopes are complete before submitting. Never invent a route, data or a result. If a call fails use doc to inspect parameters. Use the user's simulator date. You have up to 20 turns."""
def assisted(i, replay=False, live=False):
    arm='wire20' if replay else ('live20' if live else 'assisted20');path=R/'out/app'/arm/(i+'.json')
    if path.exists():return
    w=AppWorld(task_id=i,experiment_name='round2_'+arm,random_seed=233,max_interactions=22,max_api_calls_per_interaction=150,timeout_seconds=45,raise_on_failure=True,raise_on_unsafe_syntax=True,null_patch_unsafe_execution=True)
    try:
        apidir=R.parent/'round1/aw/data/api_docs/standard'
        docs={p.stem:read(p) for p in apidir.glob('*.json') if p.stem!='admin'}
        known=list(docs);tokens={};events=attach(w);results=[];p=w.task.supervisor
        from wire import install
        changes=install(w) if replay or live else []
        def catalog(app):return list(docs[app])
        def doc(app,api):
            info=docs[app][api]
            return {'description':info['description'],'parameters':[x for x in info['parameters'] if x['name']!='access_token'],'returns':info['response_schemas'].get('success')}
        def token(app):
            if app not in tokens:
                credentials={x['account_name']:x['password'] for x in w.apis.supervisor.show_account_passwords()}
                login=next(x for x in docs[app]['login']['parameters'] if x['name']=='username')
                phone='phone' in login['description'].lower()
                tokens[app]=w.apis[app]['login'](username=p.phone_number if phone else p.email,password=credentials[app])['access_token']
            return tokens[app]
        def call(app,api,**kwargs):
            info=docs[app][api]
            if any(x['name']=='access_token' for x in info['parameters']):
                kwargs['access_token']=token(app)
            value=w.apis[app][api](**kwargs)
            results.append(value)
            return value
        def pages(app,api,**kwargs):
            pars={x['name']:x for x in docs[app][api]['parameters']}
            if 'page_index' not in pars:raise ValueError('This route has no page_index. Use call instead.')
            size=pars.get('page_limit',{}).get('default') or 5
            kwargs=dict(kwargs);size=kwargs.pop('page_limit',size);kwargs.pop('page_index',None)
            output=[];prev=None
            for index in range(100):
                paging=dict(page_index=index)
                if 'page_limit' in pars:paging['page_limit']=size
                arr=call(app,api,**dict(kwargs,**paging))
                if not isinstance(arr,list):raise ValueError('Expected list. Inspect doc and use call for this response shape.')
                if not arr:return output
                if arr==prev:raise ValueError('Repeated page, inspect this endpoint manually.')
                output.extend(arr);prev=arr
                if 'page_limit' in pars and len(arr)<size:return output
            raise ValueError('Pagination budget reached')
        def finish(answer=None):
            return w.apis.supervisor.complete_task(**({'answer':str(answer)} if answer is not None else {}))
        w.shell.user_ns.update(catalog=catalog,doc=doc,call=call,pages=pages,finish=finish)
        ins=w.task.instruction
        compact=re.sub(r'[^a-z0-9]','',ins.lower())
        apps=[a for a in known if a.replace('_','') in compact]
        menu='\n'.join(a+': '+', '.join(catalog(a)) for a in apps)
        base=[{'role':'system','content':SYSTEM},user(f'Simulated supervisor: {p.first_name} {p.last_name}. Current date and time: {w.task.datetime}.\nUser task: {ins}\nApps: {", ".join(known)}\nPublic API names for apps mentioned in this request:\n'+menu)]
        if live:
            base[0]['content']+=' For an action request call finish() with no answer after executing the actions. For a numerical question compute the total from actual records and pass just the scalar to finish(value). Each page may be partial. Check public API documentation for the fields a listing includes and obtain details if needed. A failed request does not count as completed.'
        hist=[];trace=[];done=False
        for step in range(1,21):
            tail=hist[:]
            while len(tail)>2 and sum(len(m['content']) for m in tail)>44000:tail=tail[2:]
            cache=R/'out/app_steps'/arm/i/f'{step:02}.json'
            if replay:
                src=R/'out/app_steps/assisted20'/i/f'{step:02}.json'
                resp=read(src)['response']
            else:resp=read(cache)['response'] if cache.exists() else chat(base+tail,1200)
            text=resp['message']['content'] or ''
            ix=len(events);dx=len(results)
            try:obs=w.execute(code_of(text))
            except (SyntaxError,ValueError) as exc:obs='Execution failed: '+str(exc)
            if obs.strip()=='Execution successful.' and dx<len(results):obs='Last API result: '+json.dumps(results[-1],default=str)[:3200]
            done=w.task_completed();row=dict(step=step,response=resp,obs=obs[:4500],events=events[ix:],submitted=done)
            save(cache,row);trace.append(row);hist.extend([{'role':'assistant','content':text},user('Environment output:\n'+obs[:4500])])
            if done:break
        t=w.evaluate()
        save(path,dict(id=i,arm=arm,tgc=bool(t.success),tests=t.to_dict(),submitted=done,trace=trace,normalizations=changes))
    finally:w.close()
if __name__=='__main__':
    ids=read(R/'out/app_ids.json')
    with ProcessPoolExecutor(max_workers=3,max_tasks_per_child=1) as pool:
        fs={pool.submit(assisted,i,'--replay' in sys.argv,'--live' in sys.argv):i for i in ids}
        for f in as_completed(fs):f.result();print('finished',fs[f],flush=True)
