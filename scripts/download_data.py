import requests,pathlib,json,hashlib,concurrent.futures,time
root=pathlib.Path('/root/autodl-tmp/icml_test')
files=['items_shuffle_1000.json','items_ins_v2_1000.json','items_human_ins.json']
repo='HongbangYuan/webshop'
r=requests.get('https://huggingface.co/api/datasets/'+repo,timeout=30);r.raise_for_status();sha=r.json()['sha']
def dl(name):
 u=f'https://huggingface.co/datasets/{repo}/resolve/{sha}/{name}'
 for n in range(4):
  try:
   r=requests.get(u,timeout=(15,90));r.raise_for_status();j=r.json();break
  except requests.RequestException:
   if n==3:raise
   time.sleep(3)
 p=root/'data'/name;p.write_bytes(r.content)
 return {'file':name,'url':u,'bytes':len(r.content),'sha256':hashlib.sha256(r.content).hexdigest(),'entries':len(j)}
rows=list(concurrent.futures.ThreadPoolExecutor(3).map(dl,files))
(root/'reports/dataset.json').write_text(json.dumps({'source':'Hugging Face mirror of original WebShop small dataset','repo':repo,'revision':sha,'files':rows},indent=2))
print('DATA_DOWNLOAD_COMPLETE',json.dumps(rows),flush=True)
