import re

MAX_MSG_LEN = 4096

def should_ask_feedback(n):
    """Return True if user should be asked for feedback after n questions."""
    milestones = [5]
    while milestones[-1] < 10000:
        milestones.append(milestones[-1]*2)
    return n in milestones

def smart_truncate(text, max_length=MAX_MSG_LEN):
    """Truncate text to fit Telegram message limit, trying not to break sentences."""
    if len(text) <= max_length:
        return text
    sentences = re.split(r'(?<=[.!?]) +', text)
    result = ''
    for s in sentences:
        if len(result) + len(s) > max_length - 1:
            break
        result += s + ' '
    result = result.strip()
    if not result:
        return text[:max_length-20] + "\n\n[Shortened]"
    return result + "\n\n[Shortened. Ask for more if you need it.]"
