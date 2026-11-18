import os,time,json,pathlib
for k in ['http_proxy','https_proxy','HTTP_PROXY','HTTPS_PROXY','all_proxy','ALL_PROXY']: os.environ.pop(k,None)
os.environ['MODELSCOPE_CACHE']='/root/autodl-tmp/icml_test/.cache/modelscope'
os.environ['MODELSCOPE_DOWNLOAD_PARALLELS']='8'
from modelscope.hub.snapshot_download import snapshot_download
root=pathlib.Path('/root/autodl-tmp/icml_test')
started=time.time()
path=snapshot_download('Qwen/Qwen3.5-9B',local_dir=str(root/'models/Qwen3.5-9B'),max_workers=4)
report={'model_id':'Qwen/Qwen3.5-9B','source':'https://modelscope.cn/models/Qwen/Qwen3.5-9B','local_path':path,'elapsed_seconds':time.time()-started,'files':[{'path':str(p.relative_to(path)),'bytes':p.stat().st_size} for p in pathlib.Path(path).rglob('*') if p.is_file()]}
(root/'reports/model_download.json').write_text(json.dumps(report,indent=2))
print('MODEL_DOWNLOAD_COMPLETE',path,flush=True)
