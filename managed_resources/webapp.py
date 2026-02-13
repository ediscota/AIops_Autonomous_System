import random

class Container:
    def __init__(self, name, cluster_id, metric_configs):
        self.name = name
        self.cluster_id = cluster_id
        self.status = "RUNNING"
        self.metric_configs = metric_configs # Salviamo la config per i limiti
        
        # Inizializzazione dinamica delle metriche dal config
        self.metrics = {} 
        for metric_name, config in metric_configs.items():
            self.metrics[metric_name] = float(config.get('initial', 0))

    def tick(self):
        if self.status == "CRASHED":
            for key in self.metrics:
                self.metrics[key] = 0
            return

        # Aggiornamento generico per tutte le metriche
        for name, value in self.metrics.items():
            cfg = self.metric_configs[name]
            noise = float(cfg.get('noise', 0))
            
            # Caso speciale: Instances non varia a caso
            if name == 'instances':
                continue
                
            # Calcolo variazione random
            change = random.uniform(-noise, noise)
            new_val = value + change
            
            # Applicazione limiti min/max
            min_val = float(cfg.get('min', 0))
            max_val = float(cfg.get('max', 10000))
            self.metrics[name] = max(min_val, min(max_val, new_val))

        # LOGICA RELAZIONALE (Questa è difficile da mettere in config puro)
        # Esempio: Se CPU alta -> Service Time aumenta
        # Possiamo parametrizzarla ma lasciarla nel codice per leggibilità
        if self.metrics.get('cpu', 0) > 75:
             # Sovrascriviamo la logica random base per il service_time in caso di stress
             self.metrics['service_time'] = max(self.metrics['service_time'], 200)

    def restart(self):
        print(f"[{self.name}] Restarting...")
        self.status = "RUNNING"
        # Reset ai valori iniziali da config
        for name, cfg in self.metric_configs.items():
            self.metrics[name] = float(cfg.get('initial', 0))

    def kill(self):
        print(f"[{self.name}] Killed!")
        self.status = "CRASHED"
        for key in self.metrics:
            self.metrics[key] = 0


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
        severity = action_payload.get("severity", "warning")
        
        container = next((c for c in self.containers if c.name == target), None)
        if not container: return False

        multiplier = 2 if severity == "critical" else 1

        if action == "restart":
            container.restart()
        elif action == "kill":
            container.kill()
        elif action in ["scale_up", "scale_down"]:
            # LOGICA GENERICA DI SCALING
            print(f"[Cluster {self.cluster_id}] Executing {action} on {target}")
            
            for name, val in container.metrics.items():
                cfg = container.metric_configs[name]
                
                # Leggiamo dal config quanto deve cambiare questa metrica
                # Esempio: cpu ha scale_up_delta = -10
                key = f"{action}_delta" # diventa "scale_up_delta" o "scale_down_delta"
                delta = float(cfg.get(key, 0)) * multiplier
                
                # Applichiamo il delta
                new_val = val + delta
                
                # Rispettiamo i limiti
                min_val = float(cfg.get('min', 0))
                max_val = float(cfg.get('max', 10000))
                container.metrics[name] = max(min_val, min(max_val, new_val))
                
        else:
            return False
        
        return True