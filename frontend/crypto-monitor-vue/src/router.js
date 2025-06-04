import { createRouter, createWebHistory } from 'vue-router'
import MarketTable from './components/MarketTable.vue'
import EmaAlerts from './components/EmaAlerts.vue'
import ChangeAlerts from './components/ChangeAlerts.vue'
import OpenInterest from './components/OpenInterest.vue'
import PriceChange from './components/PriceChange.vue'
import TradeMonitor from './components/TradeMonitor.vue'

const routes = [
  { path: '/', component: MarketTable },
  { path: '/ema-alerts', component: EmaAlerts },
  { path: '/change-alerts', component: ChangeAlerts },
  { path: '/open-interest', component: OpenInterest }, // 新增路由
  { path: '/price-change', component: PriceChange },
  { path: '/trade-monitor', component: TradeMonitor } // 交易监控页面
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router // ✅ 这一行非常重要
