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
        target = action_payload.get("container")
        severity = action_payload.get("severity", "warning")  # default is "warning"

        container = next((c for c in self.containers if c.name == target), None)

        if not container:
            print(f"[Cluster {self.cluster_id}] Container {target} not found")
            return False

        # Multiplier based on the severity of the action
        multiplier = 2 if severity == "critical" else 1

        if action == "restart":
            print(f"[Cluster {self.cluster_id}] Restarting {target}")
            container.restart()  # resets all fields of the container

        elif action == "kill":
            print(f"[Cluster {self.cluster_id}] Killing {target}")
            container.kill()  # every field set to 0

        elif action == "scale_up":
            increment = multiplier
            container.number_of_instances += increment
            
            container.cpu_usage = max(0, container.cpu_usage - 10 * increment)
            container.memory_usage += 64 * increment
            container.service_time = max(10, container.service_time - 5 * increment)
            container.throughput += 2 * increment
            print(f"[Cluster {self.cluster_id}] Scaling up {target} by {increment} instances "
                f"(now {container.number_of_instances})")

        elif action == "scale_down":
            decrement = multiplier
            container.number_of_instances = max(1, container.number_of_instances - decrement)
            
            container.cpu_usage += 10 * decrement
            container.memory_usage = max(64, container.memory_usage - 32 * decrement)
            container.service_time += 5 * decrement
            container.throughput = max(1, container.throughput - 1 * decrement)
            print(f"[Cluster {self.cluster_id}] Scaling down {target} by {decrement} instances "
                f"(now {container.number_of_instances})")

        else:
            print(f"[Cluster {self.cluster_id}] Unknown action {action}")
            return False

        return True