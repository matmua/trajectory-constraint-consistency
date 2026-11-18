"""Download official sources and verify immutable revisions on the experiment host."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
REPOS={'ComplexBench':'thu-coai/ComplexBench','CCTU':'Junjie-Ye/CCTU','SEQUOR':'deep-spin/SEQUOR','appworld':'StonyBrookNLP/appworld'}
def main():
    lock=json.loads((ROOT/'source-lock.json').read_text());up=ROOT/'upstream';up.mkdir(exist_ok=True)
    for name,repo in REPOS.items():
        dest=up/name;rev=lock['revisions'][name]
        if not (dest/'.git').is_dir():
            subprocess.run(['git','init','-q',str(dest)],check=True)
            subprocess.run(['git','-C',str(dest),'remote','add','origin','https://github.com/'+repo+'.git'],check=True)
        head=subprocess.run(['git','-C',str(dest),'rev-parse','--verify','HEAD'],text=True,capture_output=True)
        if head.returncode:
            subprocess.run(['git','-C',str(dest),'fetch','--depth=1','origin',rev],check=True)
            subprocess.run(['git','-C',str(dest),'checkout','--detach','FETCH_HEAD'],check=True)
        elif head.stdout.strip()!=rev:raise ValueError(f'{name}: unexpected existing revision')
    path=up/'CCTU/data/input_data.jsonl'
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=lock['cctu_data_sha256']:
        r=requests.get('https://huggingface.co/datasets/Junjie-Ye/CCTU/resolve/'+lock['cctu_dataset_revision']+'/input_data.jsonl',timeout=(15,180));r.raise_for_status()
        if hashlib.sha256(r.content).hexdigest()!=lock['cctu_data_sha256']:raise ValueError('CCTU dataset revision mismatch')
        tmp=path.with_suffix('.part');tmp.write_bytes(r.content);tmp.replace(path)
if __name__=='__main__':main()
