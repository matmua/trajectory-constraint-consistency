import hashlib,json,pathlib,time
r=pathlib.Path(__file__).resolve().parents[1];rows=json.loads((r/'reports/wheel_download_manifest.json').read_text())
for row in rows:
 p=r/'.cache/wheels'/row['filename']
 if p.with_name(p.name+'.aria2').exists():raise RuntimeError('Download still in progress: '+p.name)
 if p.stat().st_size!=row['bytes']:raise RuntimeError('Wrong size: '+p.name)
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
 if h.hexdigest()!=row['sha256']:raise RuntimeError('Wrong SHA256: '+p.name)
 print('VERIFIED',p.name,flush=True)
(r/'reports/wheels_verified.json').write_text(json.dumps({'verified_count':len(rows),'unix_time':time.time(),'source':'PyPI JSON SHA256, downloads from Aliyun mirror'}))
