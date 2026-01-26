import time
import json
import requests
import configparser
import llm_service
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient

# Config parsing
config = configparser.ConfigParser()
config.read("config.ini")

MQTT_BROKER = config["mqtt"]["client_address"]
MQTT_PORT = int(config["mqtt"]["port"])

INFLUX_URL = config["influx"]["url"]
INFLUX_TOKEN = config["influx"]["token"]
INFLUX_ORG = config["influx"]["org"]
INFLUX_BUCKET = config["influx"]["bucket"]

OLLAMA_URL = config["ollama"]["url"]
OLLAMA_MODEL = config["ollama"]["model"]

MQTT_TOPIC = "AIops/analyzer"
LOOP_INTERVAL = 30  # seconds

def collect_metrics(query_api) -> str:
    prompt = ""
    query = f'''
    from(bucket: "{INFLUX_BUCKET}")
    |> range(start: -1m)
    |> filter(fn: (r) =>
        r._measurement == "mqtt_consumer" and
        r._field == "value"
    )
    |> last()
    '''
    try:
        tables = query_api.query(query)
        for table in tables:
            for record in table.records:
                prompt += (
                    f"[METRIC] cluster={record['cluster']} "
                    f"container={record['container']} "
                    f"{record['metric']}={record.get_value()}\n"
                )
    except Exception as e:
        print(f"[Analyzer] Error querying InfluxDB: {e}")
    return prompt

# Waiting for MQTT
while True:
    try:
        mqtt_client = mqtt.Client()
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print("[Analyzer] MQTT ready")
        break
    except Exception as e:
        print(f"[Analyzer] MQTT not ready: {e}")
        time.sleep(2)

# Waiting for InfluxDB
while True:
    try:
        influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        health = influx_client.health()
        if health.status == "pass":
            query_api = influx_client.query_api()
            print("[Analyzer] InfluxDB ready")
            break
        else:
            raise Exception(health.message)
    except Exception as e:
        print(f"[Analyzer] InfluxDB not ready: {e}")
        time.sleep(3)

# Waiting for Ollama
payload = {
        "model": OLLAMA_MODEL,
        "prompt": "ping",
        "stream": False
    }

while True:
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=120)
        r.raise_for_status()
        print("[Analyzer] Ollama ready")
        break
    except Exception as e:
        print(f"[Analyzer] Ollama not ready: {e}")
        time.sleep(5)

print("[Analyzer] Started")

# Main loop
while True:
    metrics = collect_metrics(query_api)

    if metrics:
        print("[Analyzer] Metrics collected")
        response = llm_service.send_to_llm(metrics)
        if response is None:
            print("[Analyzer] No response from LLM, skipping publish")
        else:
            print("[Analyzer] Publishing anomalies")
            mqtt_client.publish(
                MQTT_TOPIC,
                json.dumps({
                    "timestamp": time.time(),
                    "response": response
                })
            )

    time.sleep(LOOP_INTERVAL)