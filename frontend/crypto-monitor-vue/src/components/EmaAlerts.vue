<template>
  <div>
    <div class="alert-header">
      <h2>📈 EMA25 警报</h2>
      <div class="alert-info">
        <span>更新时间: {{ updateTime }}</span>
        <span>警报数量: {{ emaAlerts.length }}</span>
      </div>
    </div>

    <div class="alert-controls">
      <input
        v-model="searchKeyword"
        placeholder="搜索币种"
        class="search-box"
      />
    </div>

    <div class="data-note mb-4" v-if="emaAlerts.length === 0">
      <strong>暂无警报:</strong> 当前没有符合条件的EMA警报。系统会监控价格与EMA指标的关系，当出现交叉信号时会在此处显示。
    </div>

    <ul class="alert-list">
      <li v-for="alert in filteredAlerts" :key="alert" class="alert-item">
        {{ alert }}
      </li>
    </ul>

    <div class="alert-footer">
      <p class="alert-description">
        EMA警报基于价格与EMA25均线的关系，当价格突破或跌破EMA25均线时，系统会生成警报信号。
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import API from '../api'

const emaAlerts = ref([])
const updateTime = ref('--:--:--')
const searchKeyword = ref('')

const load = async () => {
  try {
    const res = await API.get('/api/data')
    emaAlerts.value = res.data.alerts.ema_alerts
    updateTime.value = new Date().toLocaleTimeString()
    console.log(`EMA警报已更新，共 ${emaAlerts.value.length} 条`)
  } catch (error) {
    console.error('加载EMA警报失败:', error)
  }
}

const filteredAlerts = computed(() => {
  if (!searchKeyword.value) return emaAlerts.value
  
  return emaAlerts.value.filter(alert => 
    alert.toLowerCase().includes(searchKeyword.value.toLowerCase())
  )
})

onMounted(() => {
  load()
  setInterval(load, 10000) // 每10秒刷新一次
})
</script>

<style scoped>
.alert-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.alert-info {
  display: flex;
  gap: 15px;
  font-size: 0.9em;
  color: #666;
}

.alert-controls {
  margin-bottom: 15px;
}

.search-box {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.alert-list {
  list-style-type: none;
  padding: 0;
  margin: 0;
}

.alert-item {
  padding: 10px;
  border-left: 3px solid #42b983;
  background-color: #f9f9f9;
  margin-bottom: 8px;
  border-radius: 0 4px 4px 0;
}

.alert-footer {
  margin-top: 20px;
  padding-top: 10px;
  border-top: 1px dashed #ddd;
}

.alert-description {
  font-size: 0.9em;
  color: #666;
  font-style: italic;
}

.data-note {
  padding: 10px;
  background-color: #fff3cd;
  border-left: 4px solid #ffc107;
  color: #856404;
  font-size: 0.9em;
  margin-bottom: 15px;
}

.mb-4 {
  margin-bottom: 1rem;
}
</style>
