"""Publish a compact bilingual-keyed aggregate as Chinese Markdown and standalone HTML."""
import sys,html
from pathlib import Path
from analyze import R,read
from report import render
def frac(x,n):return f'{x}/{n}'
def table(head,rows):
    return '\n'.join(['| '+' | '.join(map(str,head))+' |','| '+' | '.join('---' for _ in head)+' |']+['| '+' | '.join(map(str,row))+' |' for row in rows])
def build(m):
    w=m['web'];pair=m['web_matched'];c=m['cctu'];d=m['dynamic'];a=m['app'];full=m['full_web'];p=[]
    add=p.append
    add('# 13 测试结果 · 模型能说出约束后，会照着做吗？')
    add('2026 年 11 月 18 日｜Qwen3.5-9B BF16｜跨步骤依赖、动态修订与 AppWorld 归因')
    add('**跨步骤依赖最清楚的失败发生在 WebShop。** 同一商品、同一页面、同一条检查顺序，只改变先前检查的是当前商品还是另一件商品。先前查的是别的商品时，下一步点对 40/40；先前已经查过当前商品、应当转向第二个标签时，只点对 13/40。其中 26 次模型能在独立提问中说对下一步，这 26 次里有 13 次在实际浏览器里仍然点错。')
    add('**动态替换取决于新规则怎样被使用。** 简单填标签的四个条件全部 20/20。需要按更新后的规则筛选、排序或变换大小写时，模型在 80/80 次直接询问中能指出当前规则，80 次实际输出只有 2 次完全合格。直接在交付请求中重述当前规则能救回一批样本；三条规则合用时仍有明显的执行难度。')
    add(f"**AppWorld 的旧零分有多个来源。** 用原模型输出复评，只修正提交格式，旧 B 组从 0/20 变为 {a['legacy']['B']['tgc']}/20。未提交及实际操作错误的任务仍然失败。相同的 10 个 Dev 任务上，修复接口后重新让模型决策并执行，官方全题通过 {a['live20']['tgc']}/10。")
    add('## 1　同一状态下，分别问和做')
    add('理解支（U）只要求输出当前所需的标签、工具名或值；行动支（E）从相同的历史与可见状态独立生成点击或工具调用。两支都看不到另一支的答案。下表的“只说对”为 U 对且 E 错，“只做对”为 U 错且 E 对。每个格子计一个检查点，表中的检查点可以共享题目或商品。')
    rows=[]
    for label,v in [('WebShop · 单独要求点击',w['plain_atomic']),('WebShop · 首查属于另一商品',w['plain_other']),('WebShop · 首查属于当前商品',w['plain_same']),('CCTU · 直接指定输入',c['atomic']),('CCTU · 工单引用原值',c['reference']),('CCTU · 工单引用替换值',c['counter']),('CCTU 顺序 · 前置操作已在本工单完成',c['precedence']['prior']),('CCTU 顺序 · 前置操作仅在另一工单完成',c['precedence']['other'])]:
        rows.append([label,v['n'],v['U'],v['E'],v['both'],v['onlyU'],v['onlyE'],v['neither']])
    add(table(['检查点','数量','说对','做对','均对','只说对','只做对','均错'],rows))
    add('WebShop 的行动必须是可用点击且实际发生页面切换。CCTU 的两支收到相同的原生工具列表；理解以正确的简短文本作答，行动须真正调用模拟器。理解支违反文本格式也会丢分，因此“只做对”可以包含回答接口的影响。这些配对分数衡量下一步决策。完整任务单独计分。')
    add('## 2　哪些跨步骤依赖有直接证据')
    add('**WebShop · 同一操作如何因为历史改变。** 从 20 个不同商品出发，各测 Description → Features 和 Features → Description。浏览器先在当前或另一件商品执行第一项检查，再回到目标商品。两段历史长度相同，每组最终商品页的文本哈希完全相同。40 个方向检查点的两项点击单独要求时全部可执行。当前商品已查时的 27 个行动错误中，26 次重开刚查过的标签，1 次选了商品选项。要求下一步点 Description 时只对 1/20，要求点 Features 时对 12/20。顺序方向也影响表现。')
    add('把历史中真实发生的标签访问按商品 ID 列成索引，并保留原始历史。索引只包含已发生的访问。模型仍需按规则推导下一步。')
    rows=[]
    for label,key in [('先前查当前商品','same'),('先前查另一商品','other')]:
        plain=w['plain_'+key];aug=w['ledger_'+key];change=pair['index_'+key];ci=change['cluster_ci_pp']
        rows.append([label,frac(plain['E'],40),frac(aug['E'],40),change['gain'],change['loss'],f'{ci[0]:+.1f} 至 {ci[1]:+.1f}'])
    add(table(['历史条件','直接读历史','加访问索引','错→对','对→错','正确率差的 95% 区间（百分点）'],rows))
    add(f"同一商品、同一顺序下，两种历史都采取正确行动的有 {pair['plain']['both']}/40；加索引后为 {pair['ledger']['both']}/40。区间按商品重抽样 15,000 次，每次同时保留两个顺序方向。索引同时改变了表示和提示长度；另一个商品条件出现回退，不能把改善外推到所有状态。")
    add('同一模型还从首页重新执行了 10 个原始人类购物目标，每个目标每组至多 25 步。两组都要求在最终购买的商品上按顺序检查两个标签。')
    add(table(['自由购物轨迹','完成购买','购物奖励满分','购买物两标签均查','购买物顺序合规','购物和顺序都合格','平均奖励'],[[label]+[frac(full[key][f],10) for f in ('done','shopping','atoms','ordered','joint')]+[full[key]['mean_reward']] for label,key in [('原始历史','plain'),('加访问索引','ledger')]]))
    add('两组各只有 1/10 完成购买，购物奖励满分和最终联合成功均为 0/10。检查点上的提升未转化为这批任务的整单成功。完整轨迹把搜索、选品、选规格和购买也计入结果。没买到商品的轨迹不能获得“购买物顺序合规”。这个分母说明检查点上的收益能否延伸到购物全过程。')
    n=c['natural'];pr=c['precedence']
    add(f"**CCTU · 区分缺证据、参数绑定与先后次序。** 为上轮 20 题各选一条由原生下游函数验证的输入边。旧自由轨迹有 {n['traces']}/20 题实际尝试该下游调用；{n['with_good_then_bound']} 题在上游反馈已显示目标值后正确调用。未观察到来源且参数也错的 {n['without_source_wrong']} 次调用集中在 {n['wrong_tasks']} 题。其余未触发下游调用的轨迹无法判定绑定能力。")
    add(f"在独立检查点提供两份有工单标识的受控回执，原值和同类替换值分别被指定为当前值。模型直接拿到参数时做对 {c['atomic']['E']}/20，引用原值时 {c['reference']['E']}/20，引用替换值时 {c['counter']['E']}/20，两种工单都绑定正确 {c['match']['both']}/20。替换回执用于反事实干预，下游实际执行 CCTU 函数；查无记录也可正确执行了这一次查询。把空结果直接判为行动错，会混入数据库覆盖不足。")
    add(f"另从带明确顺序要求的 {c['order_screened']} 题筛查，可为前后两个原生函数都构造能返回预期结果的参数包有 {c['order_eligible']} 题。改变已有前置调用所属工单，观察模型会补做前置还是继续下游。两支分别做对 {pr['other']['E']}/{pr['other']['n']} 和 {pr['prior']['E']}/{pr['prior']['n']}。顺序题中有 9 个口头判断报出了相反的工具名，逐条检查后均属选错工具。行动分支往往还能选对。配对差异的方向取决于任务及回答接口。参数包、工单边界以及决策点由实验提供。这些对照比官方端到端 SR 更能隔离具体错误，适用范围也更窄。")
    add('## 3　修订一项后，隔四轮再用')
    add('每种任务有 20 组固定输入，均跨四个条件配对。同一轮只改一项；三约束条件保留另两项。四个无关的算术问答采用固定正确回复。立即组将这四轮放在修订前，延迟组放在修订后。总轮数相同，中间没有使用或复述新值。修订后的首次正式使用只发生在最后。')
    rr=[]
    for count in (1,3):
        for lag in (0,4):
            simple=d[f'dispatch_history_{count}_{lag}'];v=d[f'dynamic_{count}_{lag}'];res=d[f'dynamic_restated_{count}_{lag}']
            rr.append([count,lag,frac(simple['joint'],20),frac(v['understood'],20),frac(v['revised'],20),frac(v['retained'],v['retained_n']) if v['retained_n'] else '—',frac(v['joint'],20),frac(v['stale'],20),frac(res['joint'],20)])
    add(table(['有效规则','延迟轮数','简单标签全对','变换任务能指出新规则','执行新规则','未改规则逐项','最终全对','仅满足旧版本¹','同轮重述后全对'],rr))
    add('¹ 旧版通过且新版失败，评的是同一个被修改的维度。两版都没做对时应记为其他执行错误。简单任务填写运输标签，复杂任务从八条记录生成 ID 清单，评分分别检查奇偶筛选、数量排序及大小写。顺序评分至少需要两个有效 ID。完整成功还要求遵守无专门规则时的默认行为。')
    add(f"简单任务的静态对照也为 {d['dispatch_static_1_0']['joint']}/20 和 {d['dispatch_static_3_0']['joint']}/20。复杂任务在删去历史、把最终规则与数据一起给出时，单约束全对 {d['dynamic_static_1_0']['joint']}/20，三约束全对 {d['dynamic_static_3_0']['joint']}/20。保留完整历史并在最终请求中重述时，单约束恢复到 {d['dynamic_restated_1_0']['joint']}/20 与 {d['dynamic_restated_1_4']['joint']}/20。三约束即使重述也只有 {d['dynamic_restated_3_0']['joint']}/20 与 {d['dynamic_restated_3_4']['joint']}/20。")
    add(f"三约束立即组有 {d['dynamic_3_0']['at_least_one_incomplete']}/20 至少满足一条但整项没通过，延迟组有 {d['dynamic_3_4']['at_least_one_incomplete']}/20。直接询问当前规则是二选一识别，实际交付还要逐条执行。简单任务达到了满分，复杂任务多个条件接近零分；这组数据能区分调用历史要求和实际变换的难度，无法稳定估计延迟四轮本身的损失。这些是自建对照，与上轮 SEQUOR 每轮使用规则的 Replace 口径不同。")
    add('## 4　AppWorld 为什么得零，怎么修')
    labels=[('旧 A · 原生接口，20 步','native20'),('只自动回显文档，20 步','echo20'),('原生接口，50 步','native50'),('自动回显文档，50 步','echo50'),('辅助接口，20 步','assisted20'),('复用上述动作，适配提交格式','wire20'),('辅助接口与提交提示，重新推理','live20')]
    app_rows=[]
    for label,key in labels:
        v=a[key];app_rows.append([label,frac(v['tgc'],10),frac(v['submitted'],10),frac(v['business'],10),frac(v['nonanswer_progress'],10),frac(v['passes'],v['tests']),v['steps']])
    add(table(['同一批 Dev 任务','官方全题通过','已提交','有成功业务调用','新增非答案状态断言','最终通过断言¹','总步数'],app_rows))
    add('¹ 总断言含初始就通过的保护性检查。“新增”用上一轮在同一初始状态的官方回放作基线。“有成功业务调用”统计 supervisor 和 api_docs 以外的成功 API，排除登录和密码等认证操作。调用成功仍可能用错对象，也可能只读了资料。')
    add(f"**文档和步数。** 10 题按上一轮清单取固定前十，同一模型、同一沙盒。原生 20 步复用已冻结的 A 组，另外三个条件实跑；50 步组也把上限告知模型。自动回显只作用于成功查文档、但环境文字仅为执行成功的步骤，20 步触发 {a['echo20']['echoes']} 次，50 步触发 {a['echo50']['echoes']} 次。两种预算分别从 {a['native20']['tgc']} 到 {a['echo20']['tgc']} 题、从 {a['native50']['tgc']} 到 {a['echo50']['tgc']} 题通过。仅将预算提高到 50 步，10 题仍均没有成功业务调用或提交。回显文档后，20 步组有 4 题、50 步组有 5 题发起成功业务调用。")
    add(f"**业务接口和提交格式。** 辅助接口提供公共目录、文档、模拟账户登录和分页函数。模型自行决定业务 API、参数及操作顺序。先运行该接口，然后将完全相同的模型输出从初始状态回放。提交适配器对明确的纯操作请求去掉说明文字，对明确的数字问题且回答仅含一个数值时提取该数值。{a['wire_audit']['matched']}/10 组回放的模型输出、API 名称与调用成功序列、非答案断言一致；全题通过由 {a['assisted20']['tgc']}/10 变为 {a['wire20']['tgc']}/10。其中一次，7 项业务状态检查均通过，原提交因额外说明文字而失败。适配器只处理窄范围的提交语义。")
    add(f"把同一适配器用于旧 20 题 A/B/C 三组，原始三组均为零。实际提交的 {sum(a['legacy'][k]['replayed'] for k in 'ABC')}/60 条在官方环境回放，其余从未调用成功提交的轨迹结果沿用；三组官方通过分别为 {a['legacy']['A']['tgc']}/20、{a['legacy']['B']['tgc']}/20、{a['legacy']['C']['tgc']}/20。B 里有一题，模型已算对数字，只因附加了自然语言而被官方答案比较判错。旧 A 的零分无法单靠这项修复解决。当前这 10 题的官方参考解均通过。")
    o=a['live20']['outcomes']
    add(f"重新让模型在改过的接口下决策，{o.get('success',0)}/10 官方通过，其中 {a['live_unmodified_success']} 题在提交时无需适配器改写模型答案。{o.get('no_submit_business',0)+o.get('no_submit_no_business',0)} 题未提交；{o.get('submitted_answer_only',0)} 题提交后仅答案断言不通过；{o.get('submitted_other_failure',0)} 题提交后仍有其他状态断言不通过。仅答案错也可能源于计算错误。回显加 50 步与改进后的 20 步在线策略共覆盖 {a['distinct_online_successes']} 个不同的成功任务，各自成功率都是 1/10。辅助条件同时改变了提示与适配器，无法再单独归因为登录、分页或措辞。")
    add('## 5　结论边界与后续样本')
    add('论文若要主张“模型有时已经理解局部规则，却未把历史状态用于下一步行动”，WebShop 的同页反事实、理解与点击分离、以及按商品显示访问记录的干预提供了三层证据。CCTU 的参数查询接近满分，表明清楚标注来源的值传递相对容易；购物或 AppWorld 的总失败率都不宜直接当作跨步骤依赖错误率。')
    add('动态实验支持更具体的区分。简单替换可以延迟并与其他字段共存；需要把修订作用于多个数据项时，能认出当前规则与交付正确结果之间出现了缺口。若要量化延迟的独立影响，后续宜使用在立即条件下处于中等成功率的任务，保留同一批输入和静态能力对照。')
    add('本轮单模型、温度 0、种子 233、关闭 thinking、32K 上下文，在一张 32 GB RTX 5090 上运行。评分使用原生模拟器、官方断言或确定性规则。20 个商品各提供两个方向，动态测试有 20 个输入变体、三种规则维度，AppWorld 主消融有 10 个 Dev 任务。样本内部的多次观测相关，百分比应连同分母阅读。')
    add('服务器项目为 /root/autodl-tmp/icml_test/round2。out 保存每项真实输出、状态、模拟器调用、原始评分与私有 AppWorld 清单。公开仓库 round2 下的 metrics.json、item_scores.json 和 sample_manifest.json 分别给出汇总、可公开的逐例评分和已测清单。扩大样本时可跳过已有键；CCTU 留有候选题号。当前 WebShop 小目录只有 13 个人类购物目标，扩到 50 个独立完整购物任务需更大目录；检查点可另增商品。')
    return '\n\n'.join(p)+'\n'
def main():
    m=read(R/'deliverables/metrics.json');md=build(m);out=R/'deliverables'
    (out/'report.md').write_text(md,encoding='utf8')
    page=render(md).replace('<title>12 测试结果 · 轨迹级约束一致性</title>','<title>13 测试结果 · 跨步骤依赖与实际行动</title>')
    # Figure provides denominator and direct before/after labels in the offline HTML.
    parts=[]
    for title,k in [('首查属于当前商品','same'),('首查属于另一商品','other')]:
        v=m['web']['plain_'+k]['E'];l=m['web']['ledger_'+k]['E']
        parts+=['<div class="barrow"><strong>'+title+'</strong>'+''.join(f'<div><span>{txt}</span><meter min="0" max="40" value="{val}" aria-label="{title}，{txt}"></meter><b>{val}/40</b></div>' for txt,val in [('直接读历史',v),('加访问索引',l)])+'</div>']
    fig='<figure><figcaption>同一购物页上，按历史选对下一步的次数</figcaption>'+''.join(parts)+'</figure>'
    page=page.replace('</nav>','</nav>'+fig,1).replace('</style>','figure{margin:24px 0 30px;padding:18px 20px;border-left:3px solid #387065;background:#eef2ec}figcaption{font-weight:650;margin-bottom:10px}.barrow{display:inline-block;min-width:min(100%,270px);margin-right:30px}.barrow div{display:flex;align-items:center;gap:8px;font-size:13px}.barrow meter{height:15px;max-width:42%;width:115px}.barrow b{font-variant-numeric:tabular-nums}</style>')
    (out/'report.html').write_text(page,encoding='utf8')
if __name__=='__main__':main()
