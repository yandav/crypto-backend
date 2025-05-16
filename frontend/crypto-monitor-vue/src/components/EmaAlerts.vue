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
import API from '../api'

const emaAlerts = ref([])

const load = async () => {
  const res = await API.get('/api/data')
  emaAlerts.value = res.data.alerts.ema_alerts
}

onMounted(load)
</script>
