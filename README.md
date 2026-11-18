# Trajectory-level Constraint Consistency

Research code for studying how language-model agents follow constraints across a sequence of decisions. The experiments use Qwen3.5-9B to evaluate independent, dependent, and changing constraints.

## Paired decisions and delayed revisions

The follow-up compares stated understanding with executed actions in WebShop and CCTU, tests delayed use of revised rules, and isolates causes of zero task scores in AppWorld. [Results in Chinese](round2/report.md) · [Offline HTML](round2/report.html) · [Experiment guide and sample ledger](round2/README.md)

## First-round benchmark study

The study covers ComplexBench, CCTU, SEQUOR, and AppWorld. The [Chinese results report](round1/report.md) includes paired single-constraint controls, turn-level adherence, and the three AppWorld conditions. The [experiment guide](round1/README.md) describes the frozen samples, scoring, and how to extend the pilot. Download [the standalone HTML report](round1/report.html) to read it offline.

## WebShop pilot

The scripts support paired evaluations with ordered product checks and mid-episode goal updates. They record actions, environment transitions and rewards for replay.

- Run shopping episodes with `scripts/run_examples.sh`.
- Compare ordered and unordered product checks with `scripts/run_constraint_study.sh`.
- Evaluate mid-episode goal updates with `scripts/run_webshop_python.sh scripts/run_goal_switch_study.py`.

The original setup uses Linux, a WebShop conda environment with Java, and a separate vLLM environment for inference. Some experiment scripts assume the checkout is at `/root/autodl-tmp/icml_test`. Create `data/`, `logs/` and `results/` in the checkout before first use. Dependency snapshots and upstream file manifests are in `reports/`. The setup and download scripts are in `scripts/`.

The vendored WebShop runtime retains its [upstream license](third_party/WebShop/LICENSE.md).
