<template>
  <div class="metric-card">
    <div class="card-header">
      <div class="header-top">
        <span class="container-name">{{ formattedName }}</span>
        <span class="badge">{{ formattedCluster }}</span>
      </div>
    </div>

    <div class="card-body">
      <div 
        v-for="(value, key) in displayMetrics" 
        :key="key" 
        class="metric-row"
      >
        <span class="label">{{ formatLabel(key) }}</span>
        
        <span 
          class="value" 
          :class="getDynamicClass(key, value)"
          :title="thresholds[key] ? 'Threshold: ' + thresholds[key].threshold : ''"
        >
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
    metricData: { type: Object, required: true },
    thresholds: { type: Object, required: true }
  },
  computed: {
    // We use a Regex with the 'g' flag to replace every instance of dashes/underscores
    formattedName() {
      const name = this.metricData.container || "Unknown";
      return name
        .replace(/^container_/, "") // Removes the prefix only at the beginning
        .replace(/[-_]/g, " ") // Replaces every '-' or '_' with a space
        .toUpperCase();
    },

    formattedCluster() {
      const name = this.metricData.cluster || "Unknown";
      // It supports both strings like "cluster_0" and numbers
      const clusterStr = String(name);
      return clusterStr
        .replace(/^cluster_/, "CLUSTER ")
        .replace(/[-_]/g, " ")
        .toUpperCase();
    },

    displayMetrics() {
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
    formatLabel(key) {
      return key
        .replace(/_/g, " ") 
        .toUpperCase();
    },

    formatValue(key, value) {
      if (typeof value !== 'number') return value;

      const config = this.thresholds[key];
      const unit = (config && config.unit) ? ' ' + config.unit : '';
      
      // Instances are always Integers, the rest are float with 2 decimal values
      const formattedNum = key.includes('instances') ? Math.round(value) : value.toFixed(2);
      return `${formattedNum}${unit}`;
    },

    getDynamicClass(key, value) {
      // If the metric is Instances we use the neutral bagde style
      if (key.includes('instances')) return 'instance-badge-text';

      const config = this.thresholds[key];
      if (!config || config.threshold === undefined) return 'normal';

      const threshold = config.threshold;

      // Logic allined with the backend "Dead Zone"
      if (value > threshold) return 'critical';
      if (value > (threshold * 0.6)) return 'warning';
      if (value < (threshold * 0.2)) return 'under-usage'; 
      
      return 'normal'; // Between 20% and 60%
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
  color: #1e293b;
  font-size: 0.95rem;
}

.badge {
  background: #f1f5f9;
  color: #64748b;
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.05em;
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
  color: #94a3b8;
  font-size: 0.8rem;
  font-weight: 600;
}

.value {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-weight: 700;
  font-size: 0.9rem;
}

/* Color Palette based on the severity */
.normal { color: #10b981; }
.warning { color: #f59e0b; }   
.critical { color: #ef4444; }
.under-usage { color: #3b82f6; }

.instance-badge-text {
  background: #f8fafc;
  color: #475569;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
}
</style>