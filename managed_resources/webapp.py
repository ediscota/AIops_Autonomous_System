import random

class Container:
    def __init__(self, name, cluster_id, metric_configs):
        self.name = name
        self.cluster_id = cluster_id
        self.metric_configs = metric_configs
        
        # Dynamic initialization for metrics from the config.ini file
        self.metrics = {} 
        for metric_name, config in metric_configs.items():
            self.metrics[metric_name] = float(config.get('initial', 0))

    def tick(self):
        # Tick update for all the metrics
        for name, value in self.metrics.items():
            cfg = self.metric_configs[name]
            noise = float(cfg.get('noise', 0)) # default to 0
                
            # Random variation change
            change = random.uniform(-noise, noise)
            new_val = value + change
            
            # Applying min/max limits
            min_val = float(cfg.get('min', 0))
            max_val = float(cfg.get('max', 10000))
            self.metrics[name] = max(min_val, min(max_val, new_val))

    def restart(self):
        print(f"[{self.name}] Restarting...")
        # Reset to the initial config.ini values
        for name, cfg in self.metric_configs.items():
            self.metrics[name] = float(cfg.get('initial', 0))


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
        
        container = next((c for c in self.containers if c.name == target), None)
        if not container: return False

        if action == "restart":
            container.restart()
        elif action in ["scale_up", "scale_down"]:
            # Generic scaling logic
            print(f"[Cluster {self.cluster_id}] Executing {action} on {target}")
            
            for name, val in container.metrics.items():
                cfg = container.metric_configs[name]
                
                # We read from the config.ini file how much this metric needs to change
                # Example: CPU has scale_up_delta = -10
                key = f"{action}_delta" # it becomes "scale_up_delta" or "scale_down_delta"
                delta = float(cfg.get(key, 0)) # defaults to 0
                
                # Applying the delta
                new_val = val + delta
                
                # Following the limits
                min_val = float(cfg.get('min', 0))
                max_val = float(cfg.get('max', 10000))
                container.metrics[name] = max(min_val, min(max_val, new_val))
                
        else:
            return False
        
        return True