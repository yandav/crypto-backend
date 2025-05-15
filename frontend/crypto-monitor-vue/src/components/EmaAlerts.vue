<template>
  <div>
    <h2>📈 EMA25 警报</h2>
    <ul>
      <li v-for="alert in emaAlerts" :key="alert">{{ alert }}</li>
    </ul>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const emaAlerts = ref([])

const load = async () => {
  const res = await axios.get('http://localhost:5000/api/data')
  emaAlerts.value = res.data.alerts.ema_alerts
}

onMounted(load)
</script>
