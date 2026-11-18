"""Compute every reported figure from finished server records. Incomplete runs fail loudly."""
from collections import Counter,defaultdict
from math import comb,sqrt
from statistics import mean,median
from common import *
from outcome_map import mapped,GROUPS

def rate(b):
    b=list(b);return [sum(bool(x) for x in b),len(b)]
def paired(a,b):
    assert a.keys()==b.keys()
    up=[i for i in a if not a[i] and b[i]];down=[i for i in a if a[i] and not b[i]]
    k=len(up)+len(down)
    p=min(1,2*sum(comb(k,j) for j in range(min(len(up),len(down))+1))/2**k) if k else 1
    return {'gain':up,'loss':down,'tie':len(a)-k,'p_exact':p}
def wilson(k,n):
    z=1.959963985;v=k/n;d=1+z*z/n;mid=(v+z*z/(2*n))/d;margin=z*sqrt(v*(1-v)/n+z*z/(4*n*n))/d
    return [mid-margin,mid+margin]
def e1(ids):
    many={};one={};same={};points=[];flags_per=[];ends=Counter()
    for i in ids:
        i=str(i);m=read(OUT/'E1/multi'/(i+'.json'));s=read(OUT/'E1/single_clean'/(i+'.json'))
        assert len(s['points'])==1
        target=s['points'][0]['point_id']
        same[i]=next(x['pass'] for x in m['points'] if x['point_id']==target)
        many[i]=m['success'];one[i]=s['success'];points.extend(m['flags']);flags_per.append(m['flags']);ends[m['finish']]+=1
    return {'joint':rate(many.values()),'csr':rate(points),'single':rate(one.values()),'same_in_multi':rate(same.values()),'pairs':paired(same,one),'partial':sum(any(f) and not all(f) for f in flags_per),'none':sum(not any(f) for f in flags_per),'joint_wilson':wilson(sum(many.values()),len(many)),'finish':ends}
def e2(sel):
    groups={};allrows=[]
    for k in ['Multi-Hop','Parallel Multi-Hop']:
        rows=[read(OUT/'E2'/(i+'.json')) for i in sel['E2_'+k]]
        groups[k]=rows;allrows+=rows
    groups['all']=allrows;table={}
    for k,rows in groups.items():
        s=[x for r in rows for x in r['steps']];first=[r['first_violation'] for r in rows if r['first_violation'] is not None]
        table[k]={'sr':rate(r['sr'] for r in rows),'psr':rate(r['psr'] for r in rows),'violating_cases':[len(first),len(rows)],'violating_steps':rate(bool(x['violations']) for x in s),'median_first':median(first) if first else None,'calls':sum(x['calls'] for x in s),'violation_types':Counter(t for x in s for t in set(x['violations'])),'sr_not_psr':sum(r['sr'] and not r['psr'] for r in rows)}
    return table
def e3(sel):
    res={}
    for kind in ('add','replace'):
        buckets=defaultdict(list);counts=Counter();episode=[];each=[];max_context=0;stale=Counter()
        for i in sel['E3_'+kind]:
            prev=set();convo=[];flags=[]
            for t in range(1,51):
                suffix=Path(kind)/i/f'{t:02}.json';r=read(OUT/'E3'/suffix);j=read(OUT/'E3_scores'/suffix)
                cur={c['id'] for c in r['constraints']};sc={x['id']:x['pass'] for x in j['items']};assert set(sc)==cur
                all_ok=all(sc.values());convo.append(all_ok);flags+=list(sc.values())
                buckets['per_constraint']+=list(sc.values());buckets['per_turn'].append(all_ok)
                buckets[f'active_{len(cur)}'].append(all_ok);buckets['first5' if t<=5 else 'after5'].append(all_ok)
                if t==1 or (t>1 and cur!=prev):
                    if t>1:
                        buckets['new_at_change'].extend(sc[x] for x in cur-prev)
                        buckets['retained_at_change'].extend(sc[x] for x in cur&prev)
                        buckets['change_turn'].append(all_ok)
                        if kind=='replace':
                            old=read(OUT/'E3_aux/retired'/suffix)['pass']
                            stale[str((all_ok,old))]+=1
                else:buckets['nonchange_excluding_first'].append(all_ok)
                if t in (1,6,11,50):
                    rel=read(OUT/'E3_aux/task'/suffix)['pass']
                    buckets['task_relevance'].append(rel);buckets['task_and_all'].append(rel and all_ok)
                counts[r['finish']]+=1;max_context=max(max_context,r['usage']['prompt_tokens']);prev=cur
            episode.append(all(convo));each.append(sum(convo)/len(convo))
        import random
        rng=random.Random(233);draws=sorted(mean(rng.choices(each,k=len(each))) for _ in range(2500))
        res[kind]={'rates':{k:rate(v) for k,v in buckets.items()},'episode_perfect':rate(episode),'per_episode_mean':mean(each),'cluster_interval_95':[draws[62],draws[-63]],'finish':counts,'max_prompt':max_context,'replacement_verdicts_new_old':stale}
    return res
def e4(ids):
    us=read(OUT/f'understanding_scores-{len(ids)}.json')
    assert {r['id'] for r in us}==set(ids)
    understanding={}
    for prefix in ('','edge_'):
        tp,p,g=[sum(r[prefix+k] for r in us) for k in ['tp','pred','gold']]
        understanding[prefix+'counts']=[tp,p,g]
        understanding[prefix+'prf']=[tp/p,tp/g,2*tp/(p+g)]
    understanding['empty']=sum(x['empty'] for x in us)
    understanding['holistic_covered']=[sum(len(x['holistic_covered']) for x in us),sum(x['gold'] for x in us)]
    groups={};outcomes={};cases={};valid_replays=0
    for g in 'ABC':
        flags=defaultdict(list);lens=[];outcomes[g]={};error_steps=Counter();total_calls=0;max_prompt=0
        for i in ids:
            r=read(OUT/'E4'/g/(i+'.json'));q=read(OUT/'E4_replay'/g/(i+'.json'))
            score=r['tests']; reqs=read(ROOT/'aw/data/tasks'/i/'ground_truth/test_data.json')
            passed={x['requirement'] for x in score['passes']}; failed={x['requirement'] for x in score['failures']}
            assert len(score['passes'])+len(score['failures'])==score['num_tests']
            trace=r['trace'];lens.append(len(trace));outcomes[g][i]=r['tgc']
            flags['tgc'].append(r['tgc']);flags['submitted'].append(r['submitted']);flags['unsubmitted_at_limit'].append(not r['submitted'] and len(trace)==20)
            flags['assertions']+=([True]*len(score['passes'])+[False]*len(score['failures']))
            flags['mapped_outcomes']+=list(mapped(i,reqs,passed).values())
            flags['positive_assertions']+=[a['requirement'] in passed for a in reqs if a['label']=='no_op_fail']
            flags['initial_pass_assertions']+=[a['requirement'] in passed for a in reqs if a['label']=='no_op_pass']
            false_submit=False
            if i.split('_')[0] in GROUPS:
                business=[]
                for t in trace:
                    for event in t['apis']:
                        if not event['ok']:continue
                        if event['app'] not in ('api_docs','supervisor'):business.append(event)
                        if event['app']=='supervisor' and event['api']=='complete_task' and event['arguments'].get('status','success')=='success' and not business:
                            false_submit=True
                flags['action_success_claim_without_business_api'].append(false_submit)
                if false_submit:flags['unsupported_claim_at_last_turn'].append(len(trace)==20)
            ok=q['same_call_sequence_and_status'] and q['same_submission_steps'] and q['same_final_assertions']
            valid_replays+=int(ok)
            if ok:
                flags['invariant_loss_task'].append(any(v['initially_passing_now_failed'] for v in q['steps']))
                flags['invariant_loss_step'] += [bool(v['initially_passing_now_failed']) for v in q['steps']]
                flags['ever_new_progress'].append(any(v['newly_satisfied'] for v in q['steps']))
            bare=[]
            for t in trace:
                doc=[a for a in t['apis'] if a['ok'] and a['app']=='api_docs']
                b=(t['observation'].strip()=='Execution successful.' and bool(doc))
                bare.append([(x['api'],x['arguments']) for x in doc] if b else [])
                flags['doc_success_without_print_step'].append(b)
            flags['consecutive_identical_unprinted_docs'].append(any(x and y and x==y for x,y in zip(bare,bare[1:])))
            for t in trace:
                bad=t['observation'].lower().startswith(('execution failed','execution aborted','exception:'))
                flags['execution_error_step'].append(bad)
                if bad:
                    v=t['observation'].lower()
                    reasons=[('code/syntax',('syntax','could not parse','unterminated','invalid character')),('interface/arguments',('no api','does not exist','unexpected','invalid parameter','required','422','attributeerror','keyerror','no attribute')),('authentication',('401','not authenticated','unauthorized','access token'))]
                    reason=next((tag for tag,words in reasons if any(w in v for w in words)),'other');error_steps[reason]+=1
                flags['output_cap'].append(t['finish']=='length')
                flags['history_truncated'].append(t['history_pairs_omitted']>0)
                max_prompt=max(max_prompt,t['usage']['prompt_tokens'])
                for a in t['apis']:
                    total_calls+=1; flags['api_call_error'].append(not a['ok'])
            cases.setdefault(i,{})[g]={'success':r['tgc'],'submitted':r['submitted'],'steps':len(trace),'assertions':[len(score['passes']),score['num_tests']],'replay':ok,'success_claim_before_business_api':false_submit}
        groups[g]={'rates':{k:rate(v) for k,v in flags.items()},'median_steps':median(lens),'max_prompt':max_prompt,'api_calls':total_calls,'error_classes':error_steps}
    witnesses=[r['id'] for r in us if r['tp']==r['pred']==r['gold'] and r['edge_tp']==r['edge_pred']==r['edge_gold'] and cases[r['id']]['C']['success_claim_before_business_api']]
    return {'understood_but_false_submit':witnesses,'reference_solutions':rate(read(OUT/'E4_control'/(i+'.json'))['success'] for i in ids),'understanding':understanding,'groups':groups,'pairs':{x+y:paired(outcomes[x],outcomes[y]) for x,y in [('A','B'),('B','C'),('A','C')]},'valid_replays':[valid_replays,len(ids)*3],'cases':cases}
def main():
    n=int(os.getenv('TARGET_N','20'));s=read(ROOT/f'manifest-{n}.json')['selected'];a=read(ROOT/f'app-manifest-{n}.json')['selected']
    results={'n':n,'E1':e1(s['E1']),'E2':e2(s),'E3':e3(s),'E4':e4(a)}
    save(OUT/f'summary-{n}.json',results)
if __name__=='__main__':main()
