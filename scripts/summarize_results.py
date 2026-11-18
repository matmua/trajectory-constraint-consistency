"""Summarize completed records without changing any recorded scores."""
import csv,json,pathlib,statistics
R=pathlib.Path(__file__).resolve().parents[1]
s=json.loads((R/'results/constraint_study/summary.json').read_text())
d=json.loads((R/'results/constraint_study/replay_diagnostics.json').read_text())
p=json.loads((R/'results/constraint_study/order_recognition_probes.json').read_text())
steps=[]
for e in s['episodes']:
    steps.extend(x for x in map(json.loads,(R/e['trace']).read_text().splitlines()) if x['type']=='step')
gpu=list(csv.DictReader((R/'reports/gpu_metrics.csv').open()))
peak=max(int(x['memory_used_mib']) for x in gpu)
metrics={'formal_episodes':20,'native_smoke_episodes':2,'total_shopping_episodes':22,
         'formal_elapsed_seconds':s['elapsed_seconds'],'formal_actions':len(steps),
         'invalid_actions':d['invalid_actions'],
         'invalid_action_episodes':sum(x['invalid_actions']>0 for x in d['episodes']),
         'step_limit_episodes':sum(not x['done'] and x['error'] is None for x in s['episodes']),
         'repeated_state_action_episodes':sum(x['repeated_identical_observation_action_pairs']>0 for x in d['episodes']),
         'median_action_latency_seconds':statistics.median(x['latency_seconds'] for x in steps),
         'max_prompt_tokens':max(x['usage']['prompt_tokens'] for x in steps),
         'peak_gpu_memory_mib':peak,'peak_gpu_memory_gib':peak/1024,
         'counterfactual_joint_successes':d['counterfactual_joint_successes'],
         'recognition_correct_responses':p['correct'],'recognition_responses':p['total'],
         'recognition_unique_prompts':len({x['prompt'] for x in p['rows']}),
         'all_replays_match':d['all_replays_match'],
         'primary_order_violation_denominator':s['groups']['ordered']['atomic_check_successes'],
         'primary_order_violation_rate':None,
         'interpretation':'Execution reliability problems observed; pure order-relation deficit NOT established because the conditioned completed-sample denominator is zero.'}
(R/'results/constraint_study/analysis_metrics.json').write_text(json.dumps(metrics,indent=2))
print(json.dumps(metrics,indent=2))
