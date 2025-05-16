<template>
  <div>
    <h2>📊 市场总览</h2>

    <!-- 搜索框 -->
    <input
      v-model="searchKeyword"
      placeholder="搜索币种（例如 BTCUSDT）"
      class="search-box"
    />

    <!-- 表格 -->
    <table>
      <thead>
        <tr>
          <th @click="sortBy('symbol')">币种</th>
          <th @click="sortBy('price')">价格</th>
          <th @click="sortBy('change')">涨跌幅 (%)</th>
          <th @click="sortBy('volume')">交易量</th>
          <th @click="sortBy('fundingRate')">资金费率</th>
          <th @click="sortBy('ema25')">EMA25</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in paginatedData" :key="item.symbol">
          <td>{{ item.symbol }}</td>
          <td>{{ item.price }}</td>
          <td :class="{ positive: item.change > 0, negative: item.change < 0 }">
            {{ item.change }}
          </td>
          <td>{{ item.volume }}</td>
          <td>{{ formatFundingRate(item.fundingRate) }}</td>
          <td>{{ item.ema25 }}</td>
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

const data = ref([])
const page = ref(1)
const perPage = 10
const searchKeyword = ref('')
const sortKey = ref('')
const sortOrder = ref(1) // 1: 升序, -1: 降序

// 加载数据
const loadData = async () => {
  const res = await API.get('/api/data')
  data.value = res.data.data
}

onMounted(() => {
  loadData()
  setInterval(loadData, 30000)
})

// 筛选 + 排序数据
const filteredData = computed(() => {
  let result = data.value
  if (searchKeyword.value) {
    result = result.filter(item =>
      item.symbol.toLowerCase().includes(searchKeyword.value.toLowerCase())
    )
  }
  if (sortKey.value) {
    result = [...result].sort((a, b) => {
      return (a[sortKey.value] - b[sortKey.value]) * sortOrder.value
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

//看着是 0 的，现在会变成 0.0128%、-0.0150% 等真实数值，方便你筛选判断
const formatFundingRate = (rate) => {
  if (rate === null || rate === undefined) return '-'
  return (rate * 100).toFixed(4) + '%'
}
</script>

<style>
.search-box {
  width: 300px;
  padding: 0.5rem;
  margin-bottom: 1rem;
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
  cursor: pointer;
}
th:hover {
  background-color: #f0f0f0;
}
.positive {
  color: green;
}
.negative {
  color: red;
}
.pagination {
  text-align: center;
  margin-top: 1rem;
}
button {
  margin: 0 0.5rem;
  padding: 0.4rem 1rem;
}
</style>
