import json,pathlib,concurrent.futures,hashlib,subprocess
root=pathlib.Path('/root/autodl-tmp/icml_test');d=json.loads((root/'reports/webshop_tree.json').read_text())
files=[x for x in d['tree'] if x['type']=='blob' and (x['path'].startswith(('web_agent_site/','search_engine/','run_envs/')) or x['path'] in ['README.md','LICENSE.md','requirements.txt','setup.sh']) and not x['path'].endswith('chromedriver')]
def gitsha(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def download(x):
 path=x['path'];p=root/'third_party/WebShop'/path;p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists() or gitsha(p.read_bytes())!=x['sha']:
  temp=p.with_name(p.name+'.download')
  url='https://raw.githubusercontent.com/princeton-nlp/WebShop/master/'+path
  subprocess.run(['curl','-q','-fsSL','--retry','4','--retry-all-errors','--connect-timeout','15','--max-time','90',url,'-o',str(temp)],check=True)
  assert gitsha(temp.read_bytes())==x['sha'],f'Upstream changed: {path}'
  temp.replace(p)
 b=p.read_bytes();print('source',path,flush=True);return {'path':path,'bytes':len(b),'git_blob_sha':x['sha'],'sha256':hashlib.sha256(b).hexdigest()}
rows=list(concurrent.futures.ThreadPoolExecutor(3).map(download,files))
(root/'reports/webshop_source.json').write_text(json.dumps({'repository':'https://github.com/princeton-nlp/WebShop','tree_sha':d['sha'],'files':rows},indent=2))
print('WEBSHOP_SOURCE_COMPLETE',len(rows),flush=True)
