<template>
  <div>
    <h2>📊 市场总览</h2>

    <div class="status-info mb-4">
      <div class="data-status">
        <span>数据总数: {{ data.length }} 个交易对</span>
        <span>更新时间: {{ updateTime }}</span>
      </div>
    </div>

    <div class="controls">
      <!-- 搜索框 -->
      <input
        v-model="searchKeyword"
        placeholder="搜索币种（例如 BTCUSDT）"
        class="search-box"
      />
      
      <!-- 筛选选项 -->
      <div class="filter-options">
        <el-select v-model="fundingRateFilter" placeholder="资金费率筛选" clearable>
          <el-option label="全部" value=""></el-option>
          <el-option label="正费率" value="positive"></el-option>
          <el-option label="负费率" value="negative"></el-option>
          <el-option label="高费率 (>0.01%)" value="high"></el-option>
        </el-select>
        
        <el-select v-model="changeFilter" placeholder="涨跌幅筛选" clearable>
          <el-option label="全部" value=""></el-option>
          <el-option label="上涨" value="up"></el-option>
          <el-option label="下跌" value="down"></el-option>
          <el-option label="大涨 (>3%)" value="big-up"></el-option>
          <el-option label="大跌 (<-3%)" value="big-down"></el-option>
        </el-select>
      </div>
    </div>

    <!-- 表格 -->
    <table>
      <thead>
        <tr>
          <th @click="sortBy('symbol')">
            币种
            <span v-if="sortKey === 'symbol'" class="sort-indicator">{{ sortOrder > 0 ? '↑' : '↓' }}</span>
          </th>
          <th @click="sortBy('price')">
            价格
            <span v-if="sortKey === 'price'" class="sort-indicator">{{ sortOrder > 0 ? '↑' : '↓' }}</span>
          </th>
          <th @click="sortBy('change')">
            涨跌幅 (%)
            <span v-if="sortKey === 'change'" class="sort-indicator">{{ sortOrder > 0 ? '↑' : '↓' }}</span>
          </th>
          <th @click="sortBy('volume')">
            交易量
            <span v-if="sortKey === 'volume'" class="sort-indicator">{{ sortOrder > 0 ? '↑' : '↓' }}</span>
          </th>
          <th @click="sortBy('fundingRate')">
            资金费率
            <span v-if="sortKey === 'fundingRate'" class="sort-indicator">{{ sortOrder > 0 ? '↑' : '↓' }}</span>
          </th>
          <th @click="sortBy('ema25')">
            EMA25
            <span v-if="sortKey === 'ema25'" class="sort-indicator">{{ sortOrder > 0 ? '↑' : '↓' }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in paginatedData" :key="item.symbol">
          <td>{{ item.symbol }}</td>
          <td>{{ formatNumber(item.price) }}</td>
          <td :class="getChangeClass(item.change)">
            {{ formatChange(item.change) }}
          </td>
          <td>{{ formatLargeNumber(item.volume) }}</td>
          <td :class="getFundingRateClass(item.fundingRate)">
            {{ formatFundingRate(item.fundingRate) }}
          </td>
          <td>{{ item.ema25 ? formatNumber(item.ema25) : '-' }}</td>
        </tr>
      </tbody>
    </table>

    <!-- 分页控件 -->
    <div class="pagination">
      <button @click="prevPage" :disabled="page === 1">上一页</button>
      <span>第 {{ page }} 页 / 共 {{ totalPages }} 页</span>
      <button @click="nextPage" :disabled="page >= totalPages">下一页</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import API from '../api'
import { ElSelect, ElOption } from 'element-plus'

const data = ref([])
const page = ref(1)
const perPage = 10
const searchKeyword = ref('')
const sortKey = ref('')
const sortOrder = ref(1) // 1: 升序, -1: 降序
const updateTime = ref('--:--:--')

// 筛选选项
const fundingRateFilter = ref('')
const changeFilter = ref('')

// 加载数据
const loadData = async () => {
  try {
    const res = await API.get('/api/data')
    data.value = res.data.data
    updateTime.value = new Date().toLocaleTimeString()
    console.log(`市场数据已更新，共 ${data.value.length} 条记录`)
  } catch (error) {
    console.error('加载市场数据失败:', error)
  }
}

onMounted(() => {
  loadData()
  setInterval(loadData, 10000) // 每10秒刷新一次
})

// 筛选 + 排序数据
const filteredData = computed(() => {
  let result = data.value
  
  // 关键词搜索
  if (searchKeyword.value) {
    result = result.filter(item =>
      item.symbol.toLowerCase().includes(searchKeyword.value.toLowerCase())
    )
  }
  
  // 资金费率筛选
  if (fundingRateFilter.value) {
    switch (fundingRateFilter.value) {
      case 'positive':
        result = result.filter(item => item.fundingRate > 0)
        break
      case 'negative':
        result = result.filter(item => item.fundingRate < 0)
        break
      case 'high':
        result = result.filter(item => Math.abs(item.fundingRate) > 0.0001) // 0.01%
        break
    }
  }
  
  // 涨跌幅筛选
  if (changeFilter.value) {
    switch (changeFilter.value) {
      case 'up':
        result = result.filter(item => item.change > 0)
        break
      case 'down':
        result = result.filter(item => item.change < 0)
        break
      case 'big-up':
        result = result.filter(item => item.change > 3)
        break
      case 'big-down':
        result = result.filter(item => item.change < -3)
        break
    }
  }
  
  // 排序
  if (sortKey.value) {
    result = [...result].sort((a, b) => {
      const aValue = a[sortKey.value] ?? 0
      const bValue = b[sortKey.value] ?? 0
      return (aValue - bValue) * sortOrder.value
    })
  }
  
  return result
})

// 总页数
const totalPages = computed(() => {
  return Math.ceil(filteredData.value.length / perPage)
})

// 当前页的数据
const paginatedData = computed(() => {
  const start = (page.value - 1) * perPage
  return filteredData.value.slice(start, start + perPage)
})

// 切换页码
const prevPage = () => { if (page.value > 1) page.value-- }
const nextPage = () => { if (page.value < totalPages.value) page.value++ }

// 排序
const sortBy = (key) => {
  if (sortKey.value === key) {
    sortOrder.value = -sortOrder.value
  } else {
    sortKey.value = key
    sortOrder.value = 1
  }
}

// 格式化资金费率
const formatFundingRate = (rate) => {
  if (rate === null || rate === undefined) return '-'
  return (rate * 100).toFixed(4) + '%'
}

// 格式化涨跌幅
const formatChange = (change) => {
  if (change === null || change === undefined) return '-'
  return (change >= 0 ? '+' : '') + change.toFixed(2) + '%'
}

// 格式化数字
const formatNumber = (num) => {
  if (num === null || num === undefined) return '-'
  return num.toLocaleString(undefined, { maximumFractionDigits: 8 })
}

// 格式化大数字（交易量）
const formatLargeNumber = (num) => {
  if (num === null || num === undefined) return '-'
  if (num >= 1000000000) {
    return (num / 1000000000).toFixed(2) + 'B'
  } else if (num >= 1000000) {
    return (num / 1000000).toFixed(2) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(2) + 'K'
  }
  return num.toFixed(2)
}

// 获取涨跌幅的CSS类
const getChangeClass = (change) => {
  if (change === null || change === undefined) return ''
  if (change > 3) return 'high-positive'
  if (change > 0) return 'positive'
  if (change < -3) return 'high-negative'
  if (change < 0) return 'negative'
  return ''
}

// 获取资金费率的CSS类
const getFundingRateClass = (rate) => {
  if (rate === null || rate === undefined) return ''
  if (rate > 0.0001) return 'high-positive'
  if (rate > 0) return 'positive'
  if (rate < -0.0001) return 'high-negative'
  if (rate < 0) return 'negative'
  return ''
}
</script>

<style>
.status-info {
  background-color: #f9f9f9;
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 15px;
}

.data-status {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
}

.controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.filter-options {
  display: flex;
  gap: 10px;
}

.search-box {
  width: 300px;
  padding: 0.5rem;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1rem;
}

th, td {
  padding: 0.6rem;
  border: 1px solid #ccc;
  text-align: center;
}

th {
  cursor: pointer;
  position: relative;
}

th:hover {
  background-color: #f0f0f0;
}

.sort-indicator {
  margin-left: 5px;
  font-weight: bold;
}

.positive {
  color: #4caf50;
}

.high-positive {
  color: #2e7d32;
  font-weight: bold;
}

.negative {
  color: #f44336;
}

.high-negative {
  color: #c62828;
  font-weight: bold;
}

.pagination {
  text-align: center;
  margin-top: 1rem;
}

button {
  margin: 0 0.5rem;
  padding: 0.4rem 1rem;
}

.mb-4 {
  margin-bottom: 1rem;
}
</style>
