# Trajectory-level Constraint Consistency

Research code for studying how language-model agents follow constraints across a sequence of decisions. The current implementation uses Qwen3.5-9B with the text interface of WebShop.

## WebShop pilot

The scripts support paired evaluations with ordered product checks and mid-episode goal updates. They record actions, environment transitions and rewards for replay.

- Run shopping episodes with `scripts/run_examples.sh`.
- Compare ordered and unordered product checks with `scripts/run_constraint_study.sh`.
- Evaluate mid-episode goal updates with `scripts/run_webshop_python.sh scripts/run_goal_switch_study.py`.

The original setup uses Linux, a WebShop conda environment with Java, and a separate vLLM environment for inference. Some experiment scripts assume the checkout is at `/root/autodl-tmp/icml_test`. Create `data/`, `logs/` and `results/` in the checkout before first use. Dependency snapshots and upstream file manifests are in `reports/`. The setup and download scripts are in `scripts/`.

The vendored WebShop runtime retains its [upstream license](third_party/WebShop/LICENSE.md).
