import requests
import time
from influxdb_client import InfluxDBClient

INFLUX_URL = "http://influxdb:8086"
INFLUX_TOKEN = "my-super-secret-admin-token"
INFLUX_ORG = "AIops_org"
INFLUX_BUCKET = "AIops_bucket"

ANALYSIS_INTERVAL = 5  # seconds

OLLAMA_URL = "http://ollama:11434/api/generate"
OLLAMA_MODEL = "tinyllama"

class Analyzer:
    def __init__(self):
        print("[Analyzer] Connecting to InfluxDB...")
        while True:
            try:
                self.client = InfluxDBClient(
                    url=INFLUX_URL,
                    token=INFLUX_TOKEN,
                    org=INFLUX_ORG
                )
                self.query_api = self.client.query_api()
                self.client.health()
                print("[Analyzer] Connected to InfluxDB!")
                break
            except Exception as e:
                print(f"[Analyzer] Waiting for InfluxDB... ({e})")
                time.sleep(2)

    def send_to_ollama(self, metrics_text: str):
        prompt = f"""
        You are an AI Ops Analyzer.

        Given the following metrics, detect anomalies and suggest actions.
        Respond in JSON with a list of actions.

        Metrics:
        {metrics_text}
        """

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
            result = response.json()
            # print("[Analyzer] Ollama raw response:", result["response"])
            return result["response"]

        except Exception as e:
            print("[Analyzer] Ollama error:", e)
            return None

    def analyze_metrics(self):
        metrics_prompt = ""

        query = f'''
        from(bucket: "{INFLUX_BUCKET}")
        |> range(start: -1m)
        |> filter(fn: (r) =>
            r._measurement == "mqtt_consumer" and
            r._field == "value" and
            (
                r.metric == "cpu" or
                r.metric == "memory" or
                r.metric == "latency"
            )
        )
        |> last()
        '''

        try:
            tables = self.query_api.query(query)

            if not tables:
                print("[Analyzer] No metrics yet (waiting for Telegraf)...")
                return

            for table in tables:
                for record in table.records:
                    metric = record["metric"]
                    value = record.get_value()
                    cluster = record["cluster"]
                    container = record["container"]

                    metrics_prompt += (
                        f"[METRIC] cluster={cluster} "
                        f"container={container} "
                        f"{metric}={value}\n"
                    )

            if not metrics_prompt:
                print("[Analyzer] Metrics query returned no usable data.")
                return

            print("----- Metrics sent to LLM -----")
            print(metrics_prompt)
            print("-------------------------------")

            # Send the data to Ollama
            llm_response = self.send_to_ollama(metrics_prompt)

            # Prints the LLM response
            print("===== LLM Response =====")
            print(llm_response)
            print("========================")

        except Exception as e:
            print(f"[Analyzer] Error during analysis: {e}")

    def run(self):
        print("[Analyzer] Starting analysis loop...")
        while True:
            self.analyze_metrics()
            time.sleep(ANALYSIS_INTERVAL)


if __name__ == "__main__":
    Analyzer().run()