import requests

OLLAMA_URL = "http://ollama_docker:11434/api/generate"
OLLAMA_MODEL = "tinyllama"
ANALYZER_PROMPT = """
You are an AI Ops Analyzer.
Given the following metrics, detect anomalies and return a brief description of the issues.
Metrics:
{metrics}
"""

def send_to_llm(data):
    prompt = ANALYZER_PROMPT.format(metrics=data)

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=60
        )
        response.raise_for_status()

        result = response.json()
        return result.get("response")

    except Exception as e:
        print("[Analyzer] Ollama error:", e)
        return None