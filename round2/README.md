# 跨步骤约束的第二轮对照

[中文报告](report.md) · [离线 HTML](report.html) · [汇总指标](metrics.json) · [逐例评分](item_scores.json) · [已测样本](sample_manifest.json)

Qwen3.5-9B BF16，温度 0，种子 233，关闭 thinking。推理和环境操作均在实验服务器上进行。工具输入绑定、两种 WebShop 历史、动态替换与 AppWorld 提交适配的评价单位不同，见报告中的分母。

## 复现环境

保留仓库的 round1、round2、scripts 与 third_party 目录关系。按 [首轮说明](../round1/README.md) 准备模型服务、官方 CCTU 与 AppWorld 源数据及首轮冻结轨迹。首轮的部分私有轨迹需要在自己的环境重跑生成。动态任务仅依赖模型服务和 round1/src/common.py。WebShop 使用项目原有的 1000 商品小目录、Java 检索器与 Python 3.8 环境，其余脚本使用 round1/env 的 Python 3.12。默认服务地址为实验机回环端口 8000。

在 round2 下运行以下命令。每个实验按样本键落盘，已有结果会跳过。AppWorld 应在不同操作系统进程中运行不同世界。

~~~bash
../round1/env/bin/python src/dynamic.py
../round1/env/bin/python src/dynamic.py controls
../round1/env/bin/python src/dynamic.py --restated
../round1/env/bin/python src/dispatch.py
../round1/env/bin/python src/cctu_pairs.py
../round1/env/bin/python src/cctu_order.py
../round1/env/bin/python src/cctu_shared.py
bash ../scripts/run_webshop_python.sh "$PWD/src/web.py"
bash ../scripts/run_webshop_python.sh "$PWD/src/web.py" --ledger
bash ../scripts/run_webshop_python.sh "$PWD/src/full_web.py"
../round1/env/bin/python src/app.py echo20 echo50 native50
../round1/env/bin/python src/app_assisted.py
../round1/env/bin/python src/replay_wire.py
../round1/env/bin/python src/app_assisted.py --live
../round1/env/bin/python src/legacy_wire.py
../round1/env/bin/python src/analyze.py
../round1/env/bin/python src/public_export.py
../round1/env/bin/python src/make_report.py
~~~

## 评分与样本

- CCTU 参数传递以真正调到目标函数且参数通过原生 schema 并匹配当前工单为准。反事实输入可能在原生模拟数据库中查无记录。顺序实验还要求所调函数实际返回预先验证的目标数据。公开逐例表对理解分支采用与行动分支相同的原生工具列表。
- WebShop 同页检查点包含 20 个商品，每个有两个相反的检查顺序。完整购物测试使用 10 个人类目标，购买满分与流程合规分开评分。
- 两种动态任务分别由 20 个固定编号生成。无关对话为固定回复，延迟 0/4 的总轮数相同。规则直接识别、按历史交付、保留历史重述与去掉历史的静态任务分别计分。
- AppWorld 的文档回显及 20/50 步消融使用首轮固定 Dev 清单的前十项。旧提交复查涉及原来的 20 题 A/B/C 全部 60 条，实际回放发生过提交的轨迹。适配器仅处理明确的纯操作或单一数字回答。辅助接口读取公共 API 文档并调用模拟器登录，模型看不到参考解及评测断言。
- 扩样时按 sample_manifest.json 过滤已有键。CCTU 候选新题还需验证上下游边与替换值。新动态输入使用 20 起的编号。AppWorld 的精确顺序由首轮 app_select.py 再生。WebShop 完整任务超出这套小目录的 13 个目标时需要更大的原始目录。

AppWorld 的原始任务与衍生轨迹保存在服务器的私有 out 目录，公共分发遵循 [上游数据许可](../round1/AppWorld-data-LICENSE.txt)。CCTU 工具定义和模拟函数在运行时从 [CCTU](https://github.com/Junjie-Ye/CCTU) 载入。WebShop 使用 [官方模拟环境](https://github.com/princeton-nlp/WebShop)。
