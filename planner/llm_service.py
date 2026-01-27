import time
import requests
import configparser

# Config parsing
config = configparser.ConfigParser()
config.read("config.ini")

OLLAMA_URL = config["ollama"]["url"]
OLLAMA_MODEL = config["ollama"]["model"]
TIMEOUT = 120 # seconds
PLANNER_PROMPT = """
You are an AI Ops Planner component inside an autonomous MAPE-K loop.

You receive a textual description of issues affecting one or more containers.

Your task:
- Decide EXACTLY ONE action for EACH mentioned container.

Allowed actions:
- restart
- scale_up
- scale_down
- kill
- none

Rules:
- Always return VALID JSON
- One entry per container
- Keys must be container names
- Values must be one of the allowed actions
- Do NOT include explanations
- Do NOT use markdown
- Do NOT return text outside JSON

JSON example:
{
  "container_auth-service": "restart",
  "container_payment-service": "scale_up"
}

Description:
{description}
"""

def send_to_llm(description: str):
    prompt = PLANNER_PROMPT.format(description=description)

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }

    for attempt in range(3):
        try:
            response = requests.post(
                OLLAMA_URL,
                json=payload,
                timeout=TIMEOUT
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response")
        except Exception as e:
            print(f"[Planner] Ollama error, retry {attempt+1}/3: {e}")
            time.sleep(2)

    return None