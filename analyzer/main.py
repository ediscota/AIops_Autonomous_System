import os
import time
import json
import configparser
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient

# Config parsing
config = configparser.ConfigParser(interpolation=None)
config.read("config.ini")

# Environment Variables
MQTT_BROKER = os.environ.get("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_ANALYZER_USER")
MQTT_PASSWORD = os.getenv("MQTT_ANALYZER_PASSWORD")

MQTT_TOPIC = "AIops/analyzer"

INFLUX_URL = os.environ.get("INFLUXDB_URL")
INFLUX_TOKEN = os.environ.get("INFLUXDB_TOKEN")
INFLUX_ORG = os.environ.get("INFLUXDB_ORG")
INFLUX_BUCKET = os.environ.get("INFLUXDB_BUCKET")

ANALYZER_INTERVAL = int(config["general"]["analyzer_interval"])

# Dynamic Configuration Loading
METRIC_RULES = {} 

try:
    enabled_metrics_str = config["general"]["metrics"]
    enabled_metrics = [m.strip() for m in enabled_metrics_str.split(",")]
    
    for metric in enabled_metrics:
        section_name = f"metric_{metric}"
        if config.has_section(section_name):
            threshold = config[section_name].get("threshold")
            if threshold:
                METRIC_RULES[metric] = float(threshold)
                print(f"[Config] Monitoring '{metric}': threshold {threshold}")
except Exception as e:
    print(f"[Config] Error loading metric rules: {e}")

def collect_metrics(query_api) -> dict:
    metrics = {}
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
                cluster = record["cluster"]
                container = record["container"]
                metric_name = record.values.get("metric")
                
                if not metric_name and "topic" in record.values:
                    topic_parts = record["topic"].split("/")
                    metric_name = topic_parts[-1]

                value = record.get_value()
                if metric_name and value is not None:
                    metrics.setdefault(cluster, {})
                    metrics[cluster].setdefault(container, {})
                    metrics[cluster][container][metric_name] = value
    except Exception as e:
        print(f"[Analyzer] Error querying InfluxDB: {e}")
    return metrics

def evaluate_metrics(metrics: dict) -> dict:
    report = {}
    for cluster, containers in metrics.items():
        for container, container_metrics in containers.items():
            container_status = {}
            for metric_name, value in container_metrics.items():
                if metric_name in METRIC_RULES:
                    threshold = METRIC_RULES[metric_name]
                    
                    if value > threshold:
                        severity = "critical"
                    elif value > (threshold * 0.6):
                        severity = "warning"
                    elif value < (threshold * 0.2):
                        severity = "under_usage"
                    else:
                        severity = "normal" # Between 20% and 60% -> Dead Zone

                    container_status[metric_name] = {
                        "value": value,
                        "threshold": threshold,
                        "severity": severity
                    }
            if container_status:
                report.setdefault(cluster, {})
                report[cluster][container] = container_status
    return report

# Connection Setup
while True:
    try:
        client = mqtt.Client()
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        print("[Analyzer] MQTT ready")
        break
    except Exception as e:
        print(f"[Analyzer] MQTT not ready: {e}")
        time.sleep(2)

while True:
    try:
        influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        if influx_client.health().status == "pass":
            query_api = influx_client.query_api()
            print("[Analyzer] InfluxDB ready")
            break
    except Exception as e:
        print(f"[Analyzer] InfluxDB not ready: {e}")
        time.sleep(3)

print(f"[Analyzer] Started monitoring. Interval: {ANALYZER_INTERVAL}s")

while True:
    current_metrics = collect_metrics(query_api)
    if current_metrics:
        analysis_report = evaluate_metrics(current_metrics)
        
        client.publish(
            MQTT_TOPIC,
            json.dumps({
                "timestamp": time.time(),
                "anomalies": analysis_report
            })
        )
        print(f"[Analyzer] Report published for {len(analysis_report)} clusters")
    
    time.sleep(ANALYZER_INTERVAL)