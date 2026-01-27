import requests
import configparser

# Config parsing
config = configparser.ConfigParser()
config.read("config.ini")

OLLAMA_URL = config["ollama"]["url"]
OLLAMA_MODEL = config["ollama"]["model"]
TIMEOUT = 120 # seconds
ANALYZER_PROMPT = """
You are an AI Ops Analyzer component inside an autonomous MAPE-K loop.

Your task is to analyze runtime metrics of containers and identify operational problems.
You must reason strictly based on the provided numeric values. Do NOT invent data.

Metrics definitions:
- cpu: CPU usage percentage (0–100)
- memory: RAM usage in GB
- latency: request latency in milliseconds
- rps: requests per second

Instructions:
1. Analyze each container independently.
2. Detect abnormal, degraded, or critical conditions.
3. Describe WHAT the problem is and WHY it is happening.
4. Use clear, technical, concise language.
5. Do NOT suggest actions or solutions.
6. If a container shows no issues, explicitly state that it is healthy.

Output format:
- Plain English text
- One short paragraph per container
- Clearly mention the container name in each paragraph

Metrics:
{metrics}
"""

def send_to_llm(data):
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": ANALYZER_PROMPT.format(metrics=data),
        "stream": False
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=TIMEOUT
        )
        response.raise_for_status()
        return response.json().get("response")

    except requests.exceptions.ReadTimeout:
        print("[Analyzer] Ollama still warming up, skipping this cycle")
        return None

    except Exception as e:
        print("[Analyzer] Ollama error:", e)
        return None