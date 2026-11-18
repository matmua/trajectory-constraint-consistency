import importlib.metadata as m,json,pathlib,torch,transformers,vllm
r=pathlib.Path(__file__).resolve().parents[1]
assert torch.cuda.is_available()
a=torch.ones((1024,1024),device='cuda',dtype=torch.bfloat16)
b=a@a;torch.cuda.synchronize();assert float(b[0,0])==1024
report={'torch':torch.__version__,'transformers':transformers.__version__,'vllm':vllm.__version__,'cuda_runtime':torch.version.cuda,'gpu':torch.cuda.get_device_name(0),'compute_capability':torch.cuda.get_device_capability(0),'total_gpu_bytes':torch.cuda.get_device_properties(0).total_memory,'bf16_matmul':'passed'}
(r/'reports/inference_environment.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
packages=sorted({d.metadata['Name'].lower().replace('_','-')+'=='+d.version for d in m.distributions()})
(r/'reports/inference_requirements.txt').write_text('\n'.join(packages)+'\n')
