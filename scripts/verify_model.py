import hashlib,json,pathlib,time
r=pathlib.Path(__file__).resolve().parents[1];model=r/'models/Qwen3.5-9B';rows=json.loads((r/'reports/modelscope_model_files.json').read_text());verified=[]
for row in rows:
 if row.get('Type')=='tree' or 'Sha256' not in row:continue
 p=model/row['Path']
 if not p.resolve().is_relative_to(model.resolve()):raise RuntimeError('Invalid model path')
 if p.stat().st_size!=row['Size']:raise RuntimeError('Size mismatch: '+p.name)
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(16*1024*1024),b''):h.update(chunk)
 if h.hexdigest()!=row['Sha256']:raise RuntimeError('SHA256 mismatch: '+p.name)
 verified.append({'path':row['Path'],'bytes':row['Size'],'sha256':h.hexdigest()});print('MODEL_FILE_VERIFIED',p.name,flush=True)
(r/'reports/model_verified.json').write_text(json.dumps({'source':'ModelScope repository metadata','verified_count':len(verified),'files':verified,'unix_time':time.time()},indent=2));print('MODEL_INTEGRITY_OK',len(verified),flush=True)
