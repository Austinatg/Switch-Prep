import json, os, urllib.request

def ask_tutor(question, context=''):
    api_key=os.getenv('AI_API_KEY','').strip()
    base=os.getenv('AI_API_BASE_URL','https://api.openai.com/v1').rstrip('/')
    model=os.getenv('AI_MODEL','gpt-4o-mini')
    if not api_key:
        return None, 'AI tutor is not configured yet. Add AI_API_KEY, AI_MODEL and AI_API_BASE_URL to your environment. The rest of DataForge works without an AI key.'
    prompt='Learning context:\n'+context[:6000]+'\n\nQuestion:\n'+question[:5000]
    payload={'model':model,'messages':[{'role':'system','content':'You are DataForge, a practical Data Engineering tutor. Explain clearly, give safe code examples, mention assumptions, and never claim to execute code.'},{'role':'user','content':prompt}]}
    req=urllib.request.Request(base+'/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+api_key,'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=45) as response: data=json.loads(response.read().decode())
        return data['choices'][0]['message']['content'],None
    except Exception:
        return None,'The AI service could not be reached. Check your API endpoint, key, model and provider quota.'
