import time
import json
import llm_service
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient

# Config
MQTT_BROKER = "mosquitto"
MQTT_TOPIC = "AIops/analyzer"

INFLUX_URL = "http://influxdb:8086"
INFLUX_TOKEN = "my-super-secret-admin-token"
INFLUX_ORG = "AIops_org"
INFLUX_BUCKET = "AIops_bucket"

LOOP_INTERVAL = 5  # seconds

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

# MQTT Setup
mqtt_client = mqtt.Client()
connected = False
while not connected:
    try:
        mqtt_client.connect(MQTT_BROKER, 1883, 60)
        mqtt_client.loop_start()
        connected = True
    except Exception as e:
        print(f"[Analyzer] Waiting for MQTT broker... ({e})")
        time.sleep(2)

# Connection to InfluxDB with retry loop
print("[Analyzer] Connecting to InfluxDB...")
while True:
    try:
        client = InfluxDBClient(
            url=INFLUX_URL,
            token=INFLUX_TOKEN,
            org=INFLUX_ORG
        )
        health = client.health()
        if health.status != "pass":
            raise Exception(f"InfluxDB not ready: {health}")
        query_api = client.query_api()
        print("[Analyzer] Connected to InfluxDB!")
        break
    except Exception as e:
        print(f"[Analyzer] Waiting for InfluxDB... ({e})")
        time.sleep(3)

print("[Analyzer] Started")

# Main loop
while True:
    metrics = collect_metrics(query_api)

    if metrics:
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