"""Render the Chinese research report and a standalone offline HTML view on the server."""
import html
import re
from markdown_it import MarkdownIt
from common import *
def pct(x):return f'{100*x:.1f}%'
def f(pair):
    k,n=pair
    return f'{k}/{n}（{pct(k/n)}）' if n else '不适用'
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join('---' for _ in headers)+' |',*['| '+' | '.join(map(str,r))+' |' for r in rows]])
def make(summary):
    s=summary;e=s['E1'];c=s['E2'];z=s['E3'];aw=s['E4'];u=aw['understanding'];gg=aw['groups'];gs='ABC'
    aw_counts='、'.join(f"{g} 组 {f(gg[g]['rates']['tgc'])}" for g in gs)
    pair=e['pairs'];allc=c['all'];cut=sum(z[k]['finish'].get('length',0) for k in z)
    extraction=u['prf'];relations=u['edge_prf']
    n=s['n']
    label={'A':'A · 原始条件','B':'B · 加约束及关系','C':'C · 再加每步状态'}
    e4rows=[[label[g],f(gg[g]['rates']['tgc']),f(gg[g]['rates']['submitted']),f(gg[g]['rates']['mapped_outcomes']),f(gg[g]['rates']['assertions'])] for g in gs]
    relations_table=table(['理解层指标','匹配 / 预测 / 标注','精确率','召回率','F1'],[
        ['约束提取',' / '.join(map(str,u['counts'])),*(pct(x) for x in extraction)],
        ['直接有向依赖',' / '.join(map(str,u['edge_counts'])),*(pct(x) for x in relations)]])
    def e3cell(k,key):return f(z[k]['rates'].get(key,[0,0]))
    def stage_pair(k):
        p=aw['pairs'][k]
        return [k[0]+' → '+k[1],len(p['gain']),len(p['loss']),p['tie'],f"{p['p_exact']:.3f}"]
    k=aw['valid_replays']
    body=[
    '# 12 测试结果 · 轨迹级约束一致性',
    '2026 年 11 月 18 日｜Qwen3.5-9B BF16｜四个 benchmark 的首轮诊断',
    f"ComplexBench 中，完整题面上的单项约束通过 {f(e['csr'])}，整道题全部通过 {f(e['joint'])}。CCTU 中，最终成功 {f(allc['sr'])}，全程无违规且成功 {f(allc['psr'])}。两者的分母分别是生成任务和工具轨迹。",
    f"SEQUOR 中，每轮满足全部有效规则的比例为 Add {e3cell('add','per_turn')}、Replace {e3cell('replace','per_turn')}。AppWorld 的端到端成功率为 {aw_counts}。下文同时列出状态断言和失败步骤，供判断这些差距的来源。",
    f"本轮有证据支持局部达标而整体失败，也观察到了给出正确约束后仍错误宣告成功。C 组在 {f(gg['C']['rates']['action_success_claim_without_business_api'])} 的操作型任务里，尚无一次成功的业务 API 调用就宣告成功。三组 TGC 均处于零分下限，这批数据无法估计约束提示或状态提示对最终成功率的改善幅度。",
    '## 实验范围',
    table(['项目','正式样本与条件','评分单位'],[
        ['E1 · ComplexBench','20 个纯 AND 中文题，另做 20 个同题单评分项对照','逐项规则 / 语义评分和整题合取'],
        ['E2 · CCTU','Multi-Hop、Parallel Multi-Hop 各 10 题，各执行一次','官方工具与验证器，按实际反馈计算 SR / PSR'],
        ['E3 · SEQUOR','Add、Replace 各 10 个对话，每个 50 轮，step_size=5','每轮每条有效规则分别裁决'],
        ['E4 · AppWorld','20 个 Dev 任务 × A/B/C，另有 20 次独立的理解输出','官方沙盒状态测试、步骤日志与离线回放']]),
    '共有 80 个跨 benchmark 样本。AppWorld 为 20 个任务实例、19 个模板，其中两个实例的可见指令相同。各组均使用 Qwen3.5-9B，无训练，温度 0、种子 233、关闭 thinking，服务上下文上限 32,768 tokens。DeepSeek 的 deepseek-flash 只用于专项测试中的文本裁判和早期改写草稿。最终的单约束对照指令由逐题复核版本生成。',
    '## E1 · 独立约束能否同时成立',
    table(['口径','通过 / 总数'],[['原题所有评分项累计 · CSR（微平均）',f(e['csr'])],['原题全部同时满足 · ISR',f(e['joint'])],['原题至少一项满足但整题失败',f([e['partial'],n])],['原题没有任何评分项通过',f([e['none'],n])],['原题中预先选定的那一项',f(e['same_in_multi'])],['同一项独立作为要求，重新生成',f(e['single'])]]),
    f"每题按固定哈希选择一个评分项，保留基础任务、必要原文和该项要求，使用原评分问题再次评分。按同题同项对齐后，单独提出时有 {len(pair['gain'])} 题由失败转为通过、{len(pair['loss'])} 题反向变化，配对精确检验 p={pair['p_exact']:.3f}。覆盖的评分项里也有主题、可用性等基础任务要求。20 条单项对照仅代表所抽的一项，不能据此推断每题其余所有要求单独测试也都会通过。",
    f"仅选择纯 AND 且评分点无依赖的题。本文 CSR / ISR 是这个子集的逐项微平均和整题全部满足率。语义题沿用官方 evaluator 提示和解析，规则题沿用官方 extractor 提示、片段预处理和规则函数，裁判替换为 deepseek-flash。原题整题通过率的 Wilson 95% 区间为 {pct(e['joint_wilson'][0])}–{pct(e['joint_wilson'][1])}，样本不覆盖全数据集。",
    '## E2 · 依赖与工具调用',
    table(['环境子集','最终成功 SR','无违规成功 PSR','出现明确违规反馈的轨迹','含违规反馈的步骤','首次违规步数中位数'],
        [[k,f(v['sr']),f(v['psr']),f(v['violating_cases']),f(v['violating_steps']),v['median_first'] or '—'] for k,v in c.items()]),
    f"20 条轨迹共发起 {allc['calls']} 个模拟工具调用。{allc['sr_not_psr']} 条最终成功但此前有过违规。首次违规只在出现官方明确反馈标记的轨迹中计算。最常见的反馈类型为 "+'、'.join(f'{tag}（{count} 个步骤）' for tag,count in Counter(allc['violation_types']).most_common(4))+'。同一步可触发多类反馈。SR 与 PSR 由官方 judge 对整段消息重算。本轮明确标为 TOOL ORDER 和 TOOL PARALLEL 的反馈各出现在 1 步。依赖型题目上的总体失败率并非纯顺序错误率。',
    '## E3 · 新增或替换约束之后',
    table(['指标','新增 Add','替换 Replace'],[[title,e3cell('add',key),e3cell('replace',key)] for key,title in [
        ('per_constraint','所有有效约束逐项遵循'),('per_turn','每轮所有有效约束均满足'),('first5','最初 5 轮全部满足'),('change_turn','变更当轮全部满足'),('new_at_change','变更当轮的新规则被执行'),('retained_at_change','变更当轮仍保留的旧规则被执行'),('active_1','仅 1 条有效规则时整轮通过'),('active_2','2 条有效规则时整轮通过'),('active_3','3 条有效规则时整轮通过'),('task_relevance','第 1、6、11、50 轮回答切题'),('task_and_all','上述抽查轮既切题又全遵循')]]+[['连续 50 轮全部通过',f(z['add']['episode_perfect']),f(z['replace']['episode_perfect'])]]),
    f"Replace 在更新后保持 1 条有效规则，Add 依次累积至 3 条。对同一替换轮的输出另评旧规则，新规则失败但仍符合旧规则的次数为 {z['replace']['replacement_verdicts_new_old'].get('(False, True)',0)}/90。规则间可能相容，这一观察不能单独证明旧要求干扰。两组对话内容也不同，组间百分比差异是描述性比较。",
    f"50 轮来自同一对话，不能当作 50 个独立样本。按整段对话自助抽样得到整轮通过率的描述性 95% 区间，Add 为 {pct(z['add']['cluster_interval_95'][0])}–{pct(z['add']['cluster_interval_95'][1])}，Replace 为 {pct(z['replace']['cluster_interval_95'][0])}–{pct(z['replace']['cluster_interval_95'][1])}。生成上限每轮 512 tokens，共有 {cut}/1000 个回答触及上限，长篇幅规则可能受此影响。",
    '## E4 · 约束理解和实际执行',
    relations_table,
    f"独立理解测试只输入指令。{u['empty']}/{n} 条返回了空约束清单。首轮使用本研究根据可见任务编制的参考约束图，由 Codex 单次语义对齐，按一对一节点和直接有向边评分，尚无独立人工复标。模型拆分或合并节点会影响两个 F1。另按完整回答合并同义、拆分表述后，覆盖了 {f(u['holistic_covered'])} 的参考要求。此补充指标只有召回率。Dev 初始指令缺少动态撤销对照，Stage 1 对约束状态更新的诊断能力有限。",
    table(['执行条件','任务满分 TGC','实际提交','可映射要求组通过','全部官方断言通过'],e4rows),
    '每个任务均从同一初始状态独立执行三次，预算 20 次模型决策。A 组使用可见指令、标准 API 文档入口和环境反馈。B 组额外获得结构化约束及有向依赖。C 组每步再获得基于实际 API 回执和当前会话变量构造的进展摘要，包括成功读取、已接受的操作、当前对象、计数与错误。对象列表和最近记录有展示长度限制。约束清单为本研究标注，scope 使用较粗的“相关对象或操作 / 整体任务”区分。C 对应有界的可观察状态辅助，未验证其等价于全知状态。三组都不用标准答案、参考动作或官方解法。',
    table(['配对条件','新增成功','失去成功','结果相同','双侧配对精确 p'],[stage_pair('AB'),stage_pair('BC'),stage_pair('AC')]),
    table(['诊断指标','A','B','C'],[[title,*[f(gg[g]['rates'][key]) for g in gs]] for key,title in [
        ('positive_assertions','初始无操作时预期不满足的断言，最终通过'),('initial_pass_assertions','初始无操作时预期通过的断言，最终通过'),('ever_new_progress','回放中曾新满足至少一项初始未通过断言的任务'),('invariant_loss_task','回放中曾破坏至少一项初始已通过断言的任务'),('invariant_loss_step','某项初始已通过断言失效的步骤'),('api_call_error','模拟 API 调用报错次数 / 总调用'),('execution_error_step','有执行错误的模型回合'),('doc_success_without_print_step','文档查询成功但未打印结果的回合'),('consecutive_identical_unprinted_docs','连续重复同一未显示结果的文档查询的任务'),('action_success_claim_without_business_api','操作型任务中，业务 API 尚无一次成功调用便宣告成功'),('unsubmitted_at_limit','20 步耗尽仍未提交的任务'),('output_cap','达到输出 token 上限的回合'),('history_truncated','上下文预算导致省略早期对话对的回合')]]),
    f"独立执行官方参考解获得 {f(aw['reference_solutions'])} 的 TGC，证明所选任务可完成、评分可达。参考解检查与 Qwen 运行分开，参考解和评测断言均未出现在模型输入中。",
    f"官方断言既包含交付目标，也包含环境完整性检查。可映射要求组用任务专属映射将断言归并，动作类属性加上实际发生状态变化的前提。若官方只检查最终答案，该任务只计一个综合结果，不能拆成多个已经证实的细项。回放逐条核对调用顺序及成败、提交步骤与终态断言，全部三项一致的轨迹为 {f(k)}；过程指标仅使用这部分。首次未完成任务目标不等于已违规，表中过程违规仅指先满足后来失效的可检验断言。",
    '## 研究判断',
    f"独立要求同时出现时，单项和整题已有明显落差；同题同项重测还给出了独立请求与多要求请求的直接对照。对工具依赖，CCTU 可定位首次违规并区分纠正后的成功。对动态约束，SEQUOR 的更新轮给出了新增约束与保留约束各自的遵循率。三个专项的题材、分母和难度不同，不适合合并成一个总成功率。",
    f"AppWorld 的观察需结合可达性。三组共 {sum(gg[g]['rates']['submitted'][0] for g in gs)}/{3*n} 条轨迹实际提交。裸调用文档接口可以执行成功，但模型只有显式打印时才看到正文；原版环境与记录版环境对此行为一致。接口发现、参数填写、操作提交和步数预算都会影响 TGC。C 组的失败只能提示后续调查方向，需在同一决策点证明模型拿到充分状态、存在可行动作、且选择了违反具体约束的动作，才能支持独立执行缺陷。",
    f"另有 {len(aw['understood_but_false_submit'])} 个任务在独立理解测试中准确提取全部参考约束和直接关系，但在 C 条件下，尚无一次成功的业务应用 API 调用便以成功状态提交。这给出了可定位的无操作成功提交案例。理解测试与执行来自同一模型的两次独立调用；得到正确的约束表示并不保证每一步都执行正确。C 摘要显式显示当前步数和未提交状态，模型可能在预算用尽时据此提交。C 组此类无操作成功提交中，在第 20 步发生的有 {f(gg['C']['rates'].get('unsupported_claim_at_last_turn',[0,0]))}。",
    '## 数据、复现与扩样',
    '样本排序使用固定哈希 r1-v1，专项按类别分层；AppWorld 先覆盖模板再轮转。筛选在模型输出前完成。专项可选池预先排除了不适于本次普通能力评测的任务内容。记录包括官方 Git 修订、CCTU 文件哈希、AppWorld 数据包哈希、稳定样本 ID、条件、回合、模型输出和裁判结果。每个已完成样本或回合独立落盘。扩到每项 50 个样本时，前三项和 AppWorld 各自只新增 30 个任务；AppWorld 这 30 个任务另产生 90 条 A/B/C 轨迹及 30 次理解输出。',
    '服务器根目录为 \x60/root/autodl-tmp/icml_test/round1\x60。本轮名单在 \x60manifest-20.json\x60 和 \x60app-manifest-20.json\x60，逐题记录在 \x60output/\x60，数值汇总在 \x60output/summary-20.json\x60。测试阶段用于修正接口提示的轨迹和自动改写草稿都排除在正式结果之外。逐题样本使用固定的一次解码，区间和配对检验只作小样本描述。',
    '官方来源见 [ComplexBench](https://github.com/thu-coai/ComplexBench)、[CCTU](https://github.com/Junjie-Ye/CCTU)、[SEQUOR](https://github.com/deep-spin/SEQUOR) 和 [AppWorld](https://github.com/StonyBrookNLP/appworld)。',
    ]
    return '\n\n'.join(body)+'\n'
from collections import Counter
def render(md):
    article=MarkdownIt('commonmark',{'html':False}).enable('table').render(md)
    names=[]
    def heading(m):
        idx=len(names)+1;title=m.group(1);names.append((idx,title))
        return f'<h2 id="s{idx}">{title}</h2>'
    article=re.sub(r'<h2>(.*?)</h2>',heading,article)
    nav=''.join(f'<a href="#s{k}">{v}</a>' for k,v in names)
    article=article.replace('<table>','<div class="scroll"><table>').replace('</table>','</table></div>')
    css="""*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#faf9f5;color:#1d2928;font:16px/1.8 "Microsoft YaHei","PingFang SC",sans-serif}main{max-width:1024px;margin:auto;padding:48px 40px 85px}h1,h2{font-family:"Source Han Serif SC","Songti SC",SimSun,serif;line-height:1.35}h1{font-size:clamp(28px,4vw,46px);font-weight:650;margin:0 0 12px}h1+p{font-size:14px;color:#586762;border-bottom:2px solid #315c51;padding-bottom:18px}h2{font-size:26px;margin:48px 0 14px;scroll-margin-top:20px}p{margin:14px 0}a{color:#1c5d50;text-underline-offset:3px}nav{display:flex;flex-wrap:wrap;gap:5px 20px;margin:5px 0 27px;font-size:14px}nav a{text-decoration:none;border-bottom:1px solid #a0ada4}nav a:focus-visible{outline:2px solid #174c40}.scroll{overflow-x:auto;margin:15px 0 20px}table{width:100%;border-collapse:collapse;font-size:14px;font-variant-numeric:tabular-nums}td,th{text-align:left;vertical-align:top;padding:9px 12px;border-bottom:1px solid #ced6cf}th{background:#e6ede6;color:#223f36;font-weight:650}td:not(:first-child){min-width:95px}tr:nth-child(even){background:#f1f3ee}code{font:0.89em Consolas,monospace;overflow-wrap:anywhere}button{color:#215548;border:1px solid #a7b6ac;padding:6px 12px;background:transparent;cursor:pointer}footer{margin-top:36px} @media(max-width:650px){main{padding:24px 15px 50px}table{font-size:13px}td,th{padding:7px 8px}h2{font-size:22px}} @media print{body{background:white}main{padding:0;max-width:none}nav,button{display:none}h2{break-after:avoid}tr{break-inside:avoid}.scroll{overflow:visible}table{font-size:10px}a{color:inherit}} @media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}"""
    article=article.replace('</p>','</p><nav aria-label="报告目录">'+nav+'</nav>',1)
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>12 测试结果 · 轨迹级约束一致性</title><style>'+css+'</style></head><body><main>'+article+'<footer><button onclick="window.print()">打印报告</button></footer></main></body></html>'
def main():
    n=int(os.getenv('TARGET_N','20'));md=make(read(OUT/f'summary-{n}.json'))
    if n!=20:raise ValueError('This narrative is specific to the 20-item pilot; use analyze.py for expanded quantitative results.')
    dest=ROOT/'deliverables';dest.mkdir(exist_ok=True)
    (dest/'12测试结果.md').write_text(md,encoding='utf8')
    (dest/'12测试结果.html').write_text(render(md),encoding='utf8')
if __name__=='__main__':main()
