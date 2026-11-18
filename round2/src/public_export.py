"""Export a non-AppWorld item ledger and a license-safe expansion manifest."""
from analyze import R,P,O,read,save,rows
def main():
    src=R/'deliverables';table=[]
    for folder in ('web','web_ledger','full_web','cctu','order','dynamic','dynamic_recall','dynamic_static','dynamic_restated','dispatch'):
        for p in sorted((O/folder).glob('*.json')):
            a=read(p);keep=['id','template','arm','expected','order','active','field','lag','mode','target','understood','acted','valid','applied','argument_exact','tool_selected','revised','stale','retained','joint','checks','atoms','ordered','shopping','done','reward','page_hash','snapshot_hash']
            if folder in ('cctu','order'):
                u=read(O/(folder+'_shared')/p.name);a.update(understood=u['understood'],u_issued_call=u['native_call_instead'])
                keep.remove('expected');keep+=['u_issued_call']
                if folder=='cctu':
                    # Binding is a valid dispatched lookup, including database no-match returns.
                    import json
                    from jsonschema import Draft7Validator
                    row=next(t for t in map(json.loads,(P/'upstream/CCTU/data/input_data.jsonl').open()) if t['id']==a['id'])
                    schemas={t['function']['name']:t['function']['parameters'] for t in json.loads(row['tools'])}
                    a['acted']=a['argument_exact'] and all(Draft7Validator(schemas[o['name']]).is_valid(o['args']) for o in a['outputs'])
            table.append(dict(study=folder,key=p.stem,**{k:a[k] for k in keep if k in a}))
    save(src/'item_scores.json',table)
    manifest=read(O/'cctu_manifest.json');sel=read(P/'manifest-50.json')['selected']
    seen={v['id'] for v in manifest};reserve=[x for g in ['E2_Multi-Hop','E2_Parallel Multi-Hop'] for x in sel[g] if x not in seen]
    from ast import literal_eval,parse,Assign,Name
    tree=parse((R/'src/web.py').read_text());queries=next(literal_eval(n.value) for n in tree.body if isinstance(n,Assign) and any(isinstance(a,Name) and a.id=='queries' for a in n.targets))
    web=rows(O/'web',120)
    save(src/'sample_manifest.json',dict(cctu_completed=[{k:v[k] for k in ('id','source','dest','key')} for v in manifest],cctu_reserve_ids=reserve,cctu_precedence=read(O/'order_manifest.json'),web_checkpoints=[dict(template=i,query=q,target=next(v['target'] for v in web if v['template']==i)) for i,q in enumerate(queries)],web_native_goal_ids=list(range(10)),dynamic_ids=list(range(20)),dynamic_reserve_ids=list(range(20,50)),appworld='Use round1 app_select.py to regenerate the fixed Dev order. The ablation used its first ten; old submission checks used its first twenty. Exact ids and traces reside in the private experiment directory.'))
if __name__=='__main__':main()
