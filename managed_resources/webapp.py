import random

class Container:
    def __init__(self, name, cluster_id):
        self.name = name
        self.cluster_id = cluster_id
        self.status = "RUNNING"  # RUNNING, CRASHED, STOPPED
        self.cpu_usage = 10.0
        self.memory_usage = 100
        self.latency = 50
        self.requests_per_second = 5

    def tick(self):
        if self.status == "CRASHED":
            self.cpu_usage = 0
            self.latency = 0
            return

        self.cpu_usage = max(0, min(100, self.cpu_usage + random.uniform(-5, 5)))
        self.memory_usage = max(50, self.memory_usage + random.uniform(-10, 10))

        base_latency = 50 if self.cpu_usage < 80 else 500
        self.latency = max(10, base_latency + random.uniform(-20, 20))

    def restart(self):
        print(f"[{self.name}] Restarting...")
        self.status = "RUNNING"
        self.cpu_usage = 20
        self.latency = 50

    def kill(self):
        print(f"[{self.name}] Killed!")
        self.status = "CRASHED"


class Cluster:
    def __init__(self, cluster_id, containers):
        self.cluster_id = cluster_id
        self.containers = containers  # lista di Container

    def update_state(self):
        for c in self.containers:
            c.tick()

    def get_metrics(self):
        return [
            {
                "cluster": self.cluster_id,
                "container": c.name,
                "status": c.status,
                "cpu": round(c.cpu_usage, 2),
                "memory": round(c.memory_usage, 2),
                "latency": round(c.latency, 2)
            }
            for c in self.containers
        ]

    def execute_action(self, action_payload):
        action = action_payload.get("action")
        target = action_payload.get("target")

        container = next((c for c in self.containers if c.name == target), None)

        if not container:
            return False

        if action == "restart":
            container.restart()
        elif action == "kill":
            container.kill()
        else:
            print(f"Unknown action {action}")

        return True