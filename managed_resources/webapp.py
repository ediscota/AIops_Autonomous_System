import random

class Container:
    def __init__(self, name, cluster_id):
        self.name = name
        self.cluster_id = cluster_id
        self.status = "RUNNING"  # RUNNING, CRASHED, STOPPED
        self.cpu_usage = 0.0
        self.memory_usage = 128 # megabytes of RAM used
        self.service_time = 50 # milliseconds it takes to complete one job
        self.throughput = 5 # jobs completed per unit of time
        self.number_of_instances = 1

    def tick(self):
        if self.status == "CRASHED":
            self.cpu_usage = 0
            self.service_time = 0
            self.service_time = 0
            self.throughput = 0
            self.number_of_instances = 0
            return

        self.cpu_usage = max(0, min(100, self.cpu_usage + random.uniform(-10, 10)))
        self.memory_usage = max(64, self.memory_usage + random.uniform(-32, 32))

        base_service_time = 50 if self.cpu_usage < 75 else 200
        self.service_time = max(10, base_service_time + random.uniform(-20, 20))

    def restart(self):
        print(f"[{self.name}] Restarting...")
        self.status = "RUNNING"
        self.cpu_usage = 0.0
        self.memory_usage = 128
        self.service_time = 50
        self.throughput = 5

    def kill(self):
        print(f"[{self.name}] Killed!")
        self.status = "CRASHED"


class Cluster:
    def __init__(self, cluster_id, containers):
        self.cluster_id = cluster_id
        self.containers = containers

    def update_state(self):
        for c in self.containers:
            c.tick()

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