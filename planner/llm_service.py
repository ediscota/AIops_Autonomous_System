import time
import requests

OLLAMA_URL = "http://ollama_docker:11434/api/generate"
OLLAMA_MODEL = "tinyllama"
PLANNER_PROMPT = """
You are an AI Ops Planner.
Given the following description of some issues in a webapp, return for each container one of these solutions:
Restart, Kill, Scale up.
Description:
{description}
"""

def send_to_llm(data):
    prompt = PLANNER_PROMPT.format(description=data)
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}

    for attempt in range(3):
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result.get("response")
        except Exception as e:
            print(f"[Planner] Ollama error, retry {attempt+1}/3: {e}")
            time.sleep(2)
    return None