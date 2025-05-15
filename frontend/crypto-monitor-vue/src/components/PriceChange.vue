<template>
  <div>
    <el-input v-model="filterText" placeholder="搜索币种" class="mb-2" />

    <el-table :data="paginatedData" stripe style="width: 100%">
      <el-table-column prop="symbol" label="币种" sortable />
      <el-table-column prop="price" label="当前价格" sortable />

      <el-table-column label="1分钟涨跌" :sortable="true"
        :sort-method="(a, b) => a.change['1m'] - b.change['1m']">
        <template #default="scope">{{ format(scope.row.change['1m']) }}</template>
      </el-table-column>

      <el-table-column label="2分钟涨跌" :sortable="true"
        :sort-method="(a, b) => a.change['2m'] - b.change['2m']">
        <template #default="scope">{{ format(scope.row.change['2m']) }}</template>
      </el-table-column>

      <el-table-column label="5分钟涨跌" :sortable="true"
        :sort-method="(a, b) => a.change['5m'] - b.change['5m']">
        <template #default="scope">{{ format(scope.row.change['5m']) }}</template>
      </el-table-column>

      <el-table-column label="20分钟涨跌" :sortable="true"
        :sort-method="(a, b) => a.change['20m'] - b.change['20m']">
        <template #default="scope">{{ format(scope.row.change['20m']) }}</template>
      </el-table-column>

      <el-table-column label="40分钟涨跌" :sortable="true"
        :sort-method="(a, b) => a.change['40m'] - b.change['40m']">
        <template #default="scope">{{ format(scope.row.change['40m']) }}</template>
      </el-table-column>

      <el-table-column label="1小时涨跌" :sortable="true"
        :sort-method="(a, b) => a.change['1h'] - b.change['1h']">
        <template #default="scope">{{ format(scope.row.change['1h']) }}</template>
      </el-table-column>
    </el-table>

    <div class="mt-4 text-center">
      <el-pagination
        background
        layout="prev, pager, next"
        :page-size="pageSize"
        :total="filteredData.length"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const data = ref([])
const filterText = ref('')
const currentPage = ref(1)
const pageSize = 20

const fetchData = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:5000/api/price_change')
    data.value = res.data.data
  } catch (e) {
    ElMessage.error('获取失败')
  }
}

const filteredData = computed(() =>
  data.value.filter(item =>
    item.symbol.toLowerCase().includes(filterText.value.toLowerCase())
  )
)

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredData.value.slice(start, start + pageSize)
})

const handlePageChange = (page) => {
  currentPage.value = page
}

const format = (val) => (val >= 0 ? '+' : '') + val.toFixed(2) + '%'

onMounted(() => {
  fetchData()
  setInterval(fetchData, 30000)
})
</script>
