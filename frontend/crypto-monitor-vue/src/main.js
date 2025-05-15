import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css' // ✅ 引入 Element Plus 样式

const app = createApp(App)
app.use(router)
app.use(ElementPlus) // ✅ 引入 Element Plus 插件
app.mount('#app')
