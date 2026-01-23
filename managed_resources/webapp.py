import random
import time
import json

class Microservice: #cambia in container
    def __init__(self, name):
        self.name = name
        self.status = "RUNNING"  # RUNNING, CRASHED, STOPPED
        self.cpu_usage = 10.0    # Percentage
        self.memory_usage = 100  # MB
        self.latency = 50        # ms (HTTP response time)
        self.requests_per_second = 5

    def tick(self):
        """Advance time by one step: fluctuate metrics based on status."""
        if self.status == "CRASHED":
            self.cpu_usage = 0
            self.latency = 0
            return

        # Simulate normal fluctuation
        self.cpu_usage = max(0, min(100, self.cpu_usage + random.uniform(-5, 5)))
        self.memory_usage = max(50, self.memory_usage + random.uniform(-10, 10))
        
        # Latency usually correlates with CPU
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

class ClusterSimulator:
    def __init__(self):
        self.services = [
            Microservice("auth-service"),
            Microservice("payment-service"),
            Microservice("inventory-db")
        ]

    def update_state(self):
        """Updates the state of all services."""
        for service in self.services:
            service.tick()

    def get_metrics(self):
        """Returns current metrics for all services."""
        data = []
        for service in self.services:
            data.append({
                "service": service.name,
                "status": service.status,
                "cpu": round(service.cpu_usage, 2),
                "memory": round(service.memory_usage, 2),
                "latency": round(service.latency, 2)
            })
        return data

    def execute_action(self, action_payload):
        """
        Executes an effector command.
        Expected payload: {"action": "restart", "target": "payment-service"}
        """
        action = action_payload.get("action")
        target_name = action_payload.get("target")

        # Find the service
        service = next((s for s in self.services if s.name == target_name), None)
        
        if not service:
            print(f"Error: Target {target_name} not found.")
            return

        if action == "restart":
            service.restart()
        elif action == "kill": # Useful for testing the AI's detection
            service.kill()
        else:
            print(f"Unknown action: {action}")