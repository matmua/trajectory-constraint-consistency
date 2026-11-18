# First-round constraint consistency study

[中文结果](report.md) · [离线 HTML 报告](report.html) · [Aggregate metrics](metrics.json)

The pilot uses Qwen3.5-9B BF16 on 20 tasks per benchmark. ComplexBench includes paired one-rubric rewrites. CCTU uses the official simulator and validators. SEQUOR uses 50 conversational turns, five turns per update, and DeepSeek Flash for judging. AppWorld uses identical Dev instances across baseline, constraint, and constraint-plus-observed-state conditions. All sampling and scoring definitions are in the runner source and report.

## Prepare the experiment host

Use Python 3.12. Keep the vLLM 0.18.0 model environment separate from the benchmark environment. Run the following in the round1 directory on the experiment host.

~~~bash
python -m venv env
env/bin/pip install -r requirements.txt
env/bin/python src/prepare_sources.py
env/bin/appworld install
env/bin/python src/fetch_appdata.py
env/bin/python src/restore_annotations.py
env/bin/python src/select_samples.py
env/bin/python src/app_select.py
~~~

Supply the judge credential through DEEPSEEK_API_KEY in the process environment. Start the local model server in another terminal with bash serve.sh. MODEL_DIR and VLLM_BIN can point to existing installations.

## Run or resume

~~~bash
env/bin/python src/complexbench.py
env/bin/python src/cctu.py
env/bin/python src/sequor.py generate
env/bin/python src/sequor.py score
env/bin/python src/sequor_diagnostics.py
env/bin/python src/app_understand.py
env/bin/python src/app_execute.py
env/bin/python src/app_replay.py
env/bin/python src/positive_control.py
env/bin/python src/score_understanding.py
env/bin/python src/analyze.py
env/bin/python src/report.py
env/bin/python src/status.py
~~~

Keep output, the manifests and the task data on the server. Generation and judge calls are cached by original sample ID and condition. A completed AppWorld trajectory is skipped on resume. An interrupted AppWorld trajectory starts in a fresh environment. The SEQUOR scoring and auxiliary judging jobs read the per-turn files and can run as generation proceeds. A scoring watcher waits for its full expected set, so use status.py to check for missing generations if an upstream call fails.

## Extend from 20 to 50

Set TARGET_N=50, rerun the two selection scripts, then reuse the same output directory and runners. The first 20 selections are prefixes of the expanded sets within each sampling stratum. The next 30 tasks in each benchmark can therefore reuse all completed pilot runs. The unrun expansion ledger is reserve-21-50.json; the full AppWorld reserve is generated locally by app_select.py. The pilot single-controls file contains reviewed rewrites for the original 20 only. Place each new reviewed ComplexBench single-rubric prompt in controls/<main_id>.json with an instruction field. For newly generated Stage 1 responses, add reviewed predicted-to-reference node mappings and whole-response coverage to controls/understanding_extra.json. AppWorld oracle templates support all 57 Dev instances. analyze.py can produce the larger quantitative summary once the new annotations are available. The written narrative in report.py is specific to the 20-task pilot.

## Data availability

The server holds the original conversations, simulator outputs and task-level evaluations. This repository distributes aggregate results, runner code, source revisions and the ranked specialty sample manifest. AppWorld annotations are included in the upstream encrypted bundle format and are restored locally; the AppWorld manifest is regenerated from the official Dev split and the fixed sampling order. The official data, simulator credentials, raw model transcripts, and model weights stay on the experiment host. The protected AppWorld data license is included. ComplexBench remains under its upstream MIT license.

Official projects: [ComplexBench](https://github.com/thu-coai/ComplexBench), [CCTU](https://github.com/Junjie-Ye/CCTU), [SEQUOR](https://github.com/deep-spin/SEQUOR), [AppWorld](https://github.com/StonyBrookNLP/appworld).
