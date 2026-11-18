"""Conservative submission adapter for explicit imperatives and scalar questions."""
import re
def normalize(instruction, answer):
    s=instruction.strip().lower()
    if '?' not in s and re.match(r'^(send|export|add|like|create|move|delete|remove|mark|put|schedule|archive)\b',s) and not re.search(r'\b(tell|report|return|how many|how much|what is)\b',s):
        return None
    if isinstance(answer,str) and re.search(r'\bhow (?:many|much)\b',s) and '?' in s:
        values=re.findall(r'(?<![\w.])-?\d+(?:,\d{3})*(?:\.\d+)?(?!\w)',answer)
        if len(values)==1:return values[0].replace(',','')
    return answer
def install(w):
    original=w.apis.supervisor.complete_task
    log=[]
    def submit(*args,**kwargs):
        # Preserve status, positional calls and any other arguments.
        if args or 'answer' not in kwargs:return original(*args,**kwargs)
        prev=kwargs['answer'];answer=normalize(w.task.instruction,prev)
        if prev!=answer:
            log.append({'kind':'empty_action_answer' if answer is None else 'scalar_answer'})
            if answer is None:kwargs.pop('answer')
            else:kwargs['answer']=answer
        return original(**kwargs)
    w.apis.supervisor['complete_task']=submit
    return log
