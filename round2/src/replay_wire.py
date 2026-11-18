"""Resume paired offline rescoring as original trajectories become available."""
from concurrent.futures import ProcessPoolExecutor
import time
from app_assisted import R, assisted, read
if __name__=='__main__':
    ids=read(R/'out/app_ids.json')
    while True:
        todo=[i for i in ids if (R/'out/app/assisted20'/(i+'.json')).exists() and not (R/'out/app/wire20'/(i+'.json')).exists()]
        if todo:
            with ProcessPoolExecutor(max_workers=2,max_tasks_per_child=1) as pool:
                for f in [pool.submit(assisted,i,True) for i in todo]:f.result()
        if all((R/'out/app/wire20'/(i+'.json')).exists() for i in ids):break
        time.sleep(12)
