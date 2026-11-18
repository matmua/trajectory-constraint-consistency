import concurrent.futures,hashlib,os
from pathlib import Path
import requests
from common import ROOT
from appworld.common.utils import unpack_bundle
from appworld.common.constants import PASSWORD,SALT
url='https://s3.us-west-2.amazonaws.com/appworld.dev/data-0.1.0.bundle'
(ROOT/'private').mkdir(exist_ok=True,mode=0o700)
size=34280074; block=1048576
def fetch(i):
    start=i*block;end=min(size,start+block)-1
    p=ROOT/'private'/f'awpart-{i}'
    if p.is_file() and p.stat().st_size==end-start+1:return p
    for trial in range(5):
        try:
            r=requests.get(url,headers={'Range':f'bytes={start}-{end}'},timeout=(12,45))
            assert r.status_code==206 and len(r.content)==end-start+1
            p.write_bytes(r.content);return p
        except Exception:
            if trial==4:raise
with concurrent.futures.ThreadPoolExecutor(16) as pool:
    parts=list(pool.map(fetch,range((size+block-1)//block)))
p=ROOT/'private/appworld.bundle';p.write_bytes(b''.join(f.read_bytes() for f in parts))
digest=hashlib.sha256(p.read_bytes()).hexdigest()
assert digest=='fd9f9608c2ec71ed0ac25c3633a738b9129a318a129e31230425b9188e508250'
print('sha256',digest,flush=True)
unpack_bundle(bundle_file_path=str(p),base_directory=str(ROOT/'aw'),password=PASSWORD,salt=SALT)
print('AppWorld ready',flush=True)
