"""Reviewed single-rubric instructions. Retain source passages verbatim where needed."""
def instruction(i,s):
    direct={
      12:'写出日常生活中会希望头发看起来更蓬松的场景。每个场景的标点只允许使用句号。',
      128:'给一个压力管理日记条目的例子。',
      200:'为雪梨威士忌和奥利奥咸奶油蛋糕组合的甜品命名，让名字准确描述甜品的特点。',
      212:'撰写“浮萍中的一些物质作为饲料的效用”这篇文献综述的展望部分。内容基于可信的事实和数据。',
      236:'写一篇劳动教育文章，主题为劳模精神、劳动精神和工匠精神融入高职思政课教学实践研究。',
      339:'生成包含年龄和出生年份的 CSV 示例数据。假设当前年份为 2023 年，每行的出生年份须与年龄相对应。',
      406:'改写“今天我要去海滩了”，保持原句意思。回答中不能使用逗号。',
      42:'解释成语“火树银花”的意思和出处，表达积极向上的态度。',
      56:'就新能源汽车领域写一份行业报告，使用专业、有条理的语言。',
      57:'为题为“柯肯达尔效应合成铂族金属纳米龙催化剂”的汇报列出副标题。',
      641:'你是呼吸科副主任医师，请向院长汇报本年度工作成果。用英文撰写。',
    }
    if i in direct:return direct[i]
    if i==141:return '根据以下参考内容写一份说明书。\n'+s.split('参考内容：',1)[1]
    if i==255:return '围绕义马市落实河长制的成果扩写这段文字，不带情感倾向。\n'+s.split('\n\n',1)[1]
    if i==284:return s.rsplit('\n\n',1)[0]+'\n\n根据材料起草该高中生的大学申请推荐信，将学生的学科竞赛成绩写入信中。'
    if i==328:return s.split('\n\n注意')[0]+'\n请用英文回复。'
    if i==442:return s.split('\n要求：')[0]+'\n总结不超过500字。'
    if i==556:return s.split('\n要求：')[0]+'\n内容应逻辑合理、符合事实，并与提供的材料相符。'
    if i==568:return s.split('你是一个火星探险队的队长')[0]+'描述探险队首次登陆火星的印象，内容须符合以上材料中的知识。'
    if i==629:return s.rsplit('\n\n',1)[0]+'\n\n以财务管理专业初学者的视角，针对上述办法提问。'
    if i==90:return '针对用户实际日程提出子日程提醒，从已给的用户日程库中选取。\n'+s.split('下面是用户的日程库：',1)[1]
    from common import ROOT,read
    reviewed=ROOT/'controls'/f'{i}.json'
    if reviewed.exists():return read(reviewed)['instruction']
    raise KeyError(f'Add the reviewed single-rubric text at {reviewed} for new item {i}')
