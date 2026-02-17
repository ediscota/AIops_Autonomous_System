<template>
  <div class="app-container">
    <header class="dashboard-header">
      <h1>
        <i class="bi bi-rocket-takeoff"></i>
        AIOps Autonomous System
      </h1>
      <p>Real-time monitoring & Self-healing AI</p>
    </header>

    <main>
      <section class="metrics-section">
        <div v-if="loading" class="loading-message">
          <i class="bi bi-broadcast-pin"></i>
          Connecting to the cluster...
        </div>
        
        <div v-else class="metrics-grid">
          <MetricCard 
            v-for="(item, index) in metrics" 
            :key="index" 
            :metricData="item" 
            :thresholds="thresholds"  />
        </div>
      </section>

      <section class="ai-section">
        <AiPlannerCard />
      </section>
    </main>
  </div>
</template>

<script>
import axios from 'axios';
import MetricCard from './components/MetricCard.vue';
import AiPlannerCard from './components/AIPlannerCard.vue';

export default {
  name: 'App',
  components: {
    MetricCard,
    AiPlannerCard
  },
  data() {
    return {
      metrics: [],
      thresholds: {},
      loading: true,
      intervalId: null
    }
  },
  methods: {
    async fetchThresholds() {
      try {
        const res = await axios.get('http://localhost:8080/api/thresholds');
        this.thresholds = res.data;
        console.log("Thresholds loaded:", this.thresholds);
      } catch (error) {
        console.error("API Thresholds error:", error);
      }
    },
    async fetchMetrics() {
      try {
        const res = await axios.get('http://localhost:8080/api/metrics');
        this.metrics = res.data;
        this.loading = false;
      } catch (error) {
        console.error("API Metrics error:", error);
      }
    }
  },
  async mounted() {
    await this.fetchThresholds();
    this.fetchMetrics();
    this.intervalId = setInterval(this.fetchMetrics, 2000);
  },
  beforeUnmount() {
    clearInterval(this.intervalId);
  }
}
</script>

<style>
/* GLOBAL STYLES */
body {
  margin: 0;
  background-color: #f8f9fa;
  font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  color: #2c3e50;
}

.app-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.dashboard-header {
  text-align: center;
  margin-bottom: 3rem;
}

.dashboard-header h1 {
  color: #1e293b;
  margin-bottom: 0.5rem;
}

.dashboard-header p {
  color: #64748b;
  margin: 0;
}

/* CSS changes: Space BELOW the metrics to separate them from the AI */
.metrics-section {
  margin-bottom: 3rem;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
}

.loading-message {
  text-align: center;
  font-size: 1.2rem;
  color: #64748b;
  padding: 2rem;
}

/* The AI Section is now at the bottom, we don't obligatory need any margin, but it's not an issue to add some */
.ai-section {
  margin-bottom: 2rem;
}
</style>