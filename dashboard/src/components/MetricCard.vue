<template>
  <div class="metric-card">
    <div class="card-header">
      <div class="header-top">
        <span class="container-name">{{ formattedName }}</span>
        <span class="badge">{{ metricData.cluster }}</span>
      </div>
    </div>

    <div class="card-body">
      <div class="metric-row">
        <span class="label">CPU Usage</span>
        <span class="value" :class="getThresholdClass(metricData.cpu, 10)">
          {{ metricData.cpu.toFixed(2) }} %
        </span>
      </div>

      <div class="metric-row">
        <span class="label">Memory</span>
        <span class="value" :class="getThresholdClass(metricData.memory, 150)">
          {{ metricData.memory.toFixed(1) }} MB
        </span>
      </div>

      <div class="metric-row">
        <span class="label">Service Time</span>
        <span class="value" :class="getThresholdClass(metricData.service_time, 60)">
          {{ metricData.service_time.toFixed(2) }} ms
        </span>
      </div>

      <div class="metric-row">
        <span class="label">Instances</span>
        <span class="value instance-badge">
          {{ metricData.instances }}
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
    // Pulisce il nome: "container_auth-service" -> "Auth Service"
    formattedName() {
      const name = this.metricData.container || "Unknown";
      return name.replace("container_", "").replace("-", " ").toUpperCase();
    }
  },
  methods: {
    // Ritorna una classe CSS se il valore supera la soglia
    getThresholdClass(value, threshold) {
      if (value > threshold) return "critical";
      if (value > threshold * 0.8) return "warning";
      return "normal";
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

/* Classi per lo stato */
.normal { color: #10b981; }
.warning { color: #f59e0b; }
.critical { color: #ef4444; font-weight: 800; }

.instance-badge {
  background: #f3f4f6;
  padding: 2px 8px;
  border-radius: 4px;
  color: #374151;
}
</style>