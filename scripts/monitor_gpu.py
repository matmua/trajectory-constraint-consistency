"""Record GPU metrics until the specified model server exits."""
import argparse,csv,datetime,os,pathlib,subprocess,time
p=argparse.ArgumentParser();p.add_argument('--pid',type=int,required=True);p.add_argument('--output',required=True);args=p.parse_args()
fields=['timestamp_utc','memory_used_mib','memory_total_mib','gpu_util_percent','power_draw_w','temperature_c']
with pathlib.Path(args.output).open('w',newline='') as f:
 w=csv.writer(f);w.writerow(fields);f.flush()
 while pathlib.Path('/proc/'+str(args.pid)).exists():
  try:
   out=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.total,utilization.gpu,power.draw,temperature.gpu','--format=csv,noheader,nounits'],text=True,timeout=8)
   w.writerow([datetime.datetime.now(datetime.timezone.utc).isoformat()]+[x.strip() for x in out.splitlines()[0].split(',')]);f.flush()
  except Exception as exc:
   print(type(exc).__name__,str(exc)[:200],flush=True)
  time.sleep(2)
