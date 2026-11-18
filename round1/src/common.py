"""Shared HTTP transport, deterministic ordering, and atomic per-item resume."""
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
UP = ROOT / 'upstream'
OUT = ROOT / 'output'
def read(path):
    return json.loads(Path(path).read_text())
def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.part')
    tmp.write_text(json.dumps(value, ensure_ascii=False), encoding='utf8')
    tmp.replace(path)
def rank(value):
    return hashlib.sha256(('r1-v1:' + str(value)).encode()).hexdigest()
def user(content):
    return {'role':'user','content':content}
def chat(messages, limit=768, tools=None, judge=False):
    url = 'https://api.deepseek.com/chat/completions' if judge else 'http://127.0.0.1:8000/v1/chat/completions'
    payload = dict(model='deepseek-flash' if judge else 'Qwen3.5-9B', messages=messages, max_tokens=limit, temperature=0)
    headers = {}
    if judge:
        headers['Authorization'] = 'Bearer ' + (os.environ.get('DEEPSEEK_API_KEY') or (ROOT/'private/judge.key').read_text()).strip()
        payload['thinking'] = {'type':'disabled'}
    else:
        payload.update(seed=233,chat_template_kwargs={'enable_thinking':False})
    if tools is not None:
        payload['tools'] = tools
    for attempt in range(5):
        try:
            with requests.Session() as session:
                session.trust_env = False
                res = session.post(url,json=payload,headers=headers,timeout=(15,420))
            if res.status_code == 400:
                raise ValueError(res.text[:420])
            res.raise_for_status()
            result=res.json()
            choice=result['choices'][0]
            return {'message':choice['message'],'finish':choice['finish_reason'],'usage':result.get('usage',{}),'model':result.get('model')}
        except (requests.RequestException,KeyError) as e:
            if attempt == 4: raise
            time.sleep(2**attempt)
def judged(prompt,limit=1200):
    return chat([user(prompt)],limit,judge=True)['message']['content']
def run_pool(ids,fn,workers):
    def wrapped(item):
        try: fn(item)
        except Exception as e:
            import traceback
            print('ERROR',item,type(e).__name__,str(e)[:350],flush=True)
            traceback.print_exc()
    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(wrapped,ids))
