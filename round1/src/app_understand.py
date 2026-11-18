from common import *
PROMPT="""Extract the distinct requirements stated in the task, their scopes (local or task-wide) and current status. State directed dependencies between requirements: [prerequisite id, dependent id]. Use one entry per distinct, independently checkable requirement. Do not solve the task or list tool calls. Output exactly JSON {"requirements":[{"id":1,"text":"...","scope":"...","status":"..."}],"depends_on_edges":[[1,2]]}."""
def run(i):
    p=OUT/'E4_understand'/(i+'.json')
    if p.exists():return
    inst=read(ROOT/'aw/data/tasks'/i/'specs.json')['instruction']
    res=chat([{'role':'system','content':PROMPT},user(inst)],1200)
    save(p,res)
if __name__=='__main__':
    n=int(os.getenv('TARGET_N','20'))
    run_pool(read(ROOT/f'app-manifest-{n}.json')['selected'],run,4)
