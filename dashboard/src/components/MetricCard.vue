<template>
  <div class="metric-card">
    <div class="card-header">
      <div class="header-top">
        <span class="container-name">{{ formattedName }}</span>
        <span class="badge">{{ metricData.cluster }}</span>
      </div>
    </div>

    <div class="card-body">
      <div 
        v-for="(value, key) in displayMetrics" 
        :key="key" 
        class="metric-row"
      >
        <span class="label">{{ formatLabel(key) }}</span>
        
        <span class="value" :class="getDynamicClass(key, value)">
          {{ formatValue(key, value) }}
        </span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "MetricCard",
  props: {
    metricData: {
      type: Object,
      required: true
    }
  },
  computed: {
    // 1. Pulisce il nome del container
    formattedName() {
      const name = this.metricData.container || "Unknown";
      return name.replace("container_", "").replace("-", " ").toUpperCase();
    },

    // 2. Filtra le chiavi che NON sono metriche da mostrare
    displayMetrics() {
      // Lista di chiavi da ignorare (metadati del sistema)
      const ignoredKeys = ['cluster', 'container', 'host', 'topic', 'result', 'table', '_start', '_stop', '_time'];
      
      const metrics = {};
      for (const [key, value] of Object.entries(this.metricData)) {
        if (!ignoredKeys.includes(key)) {
          metrics[key] = value;
        }
      }
      return metrics;
    }
  },
  methods: {
    // Trasforma "service_time" in "Service Time"
    formatLabel(key) {
      return key
        .replace(/_/g, " ") // Sostituisce underscore con spazi
        .replace(/\b\w/g, l => l.toUpperCase()); // Capitalizza prima lettera
    },

    // Aggiunge unità di misura basandosi sul nome della chiave (euristico)
    formatValue(key, value) {
      if (typeof value !== 'number') return value;

      if (key.includes('cpu')) return value.toFixed(2) + ' %';
      if (key.includes('memory')) return value.toFixed(1) + ' MB';
      if (key.includes('time') || key.includes('latency')) return value.toFixed(2) + ' ms';
      if (key.includes('instances')) return Math.round(value); // Intero

      // Default per metriche sconosciute
      return value.toFixed(2);
    },

    // Logica colori dinamica (Semplificata perché il frontend non conosce le soglie del backend)
    // Se volessimo le soglie vere, dovremmo passarle via API.
    // Qui usiamo valori "di buon senso" o neutri per metriche sconosciute.
    getDynamicClass(key, value) {
      // Esempi di soglie hardcoded lato frontend solo per visualizzazione (OPZIONALE)
      // Se preferisci, puoi lasciare tutto 'normal' o colorare solo CPU/RAM.
      
      if (key.includes('cpu')) {
        if (value > 80) return 'critical';
        if (value > 50) return 'warning';
      }
      
      if (key.includes('memory')) {
        if (value > 3000) return 'critical'; // Esempio generico
        if (value > 2000) return 'warning';
      }

      if (key.includes('instances')) {
        return 'instance-badge-text'; // Classe speciale per istanze
      }

      return 'normal';
    }
  }
};
</script>

<style scoped>
.metric-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 1.2rem;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  border: 1px solid #f0f0f0;
}

.metric-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  border-bottom: 1px solid #eee;
  padding-bottom: 0.5rem;
}

.container-name {
  font-weight: 700;
  color: #2c3e50;
  font-size: 1rem;
}

.badge {
  background: #e0f2fe;
  color: #0369a1;
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.label {
  color: #64748b;
  font-size: 0.9rem;
}

.value {
  font-family: 'Consolas', monospace;
  font-weight: 600;
}

/* Colori Stati */
.normal { color: #334155; } /* Grigio scuro per default */
.warning { color: #f59e0b; }
.critical { color: #ef4444; font-weight: 800; }

/* Stile speciale per le istanze */
.instance-badge-text {
  background: #f1f5f9;
  color: #475569;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}
</style>