import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  base: './', // 这样打包后的资源可以在任何路径下正常加载
  server: {
    proxy: {
      // 开发时代理API请求到后端
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    // 生产环境优化
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: process.env.NODE_ENV === 'production', // 仅在生产环境移除console
        drop_debugger: true // 移除debugger
      }
    },
    // 分割代码块
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['vue', 'vue-router'],
          'element-plus': ['element-plus'],
          'echarts': ['echarts']
        },
        // 优化静态资源输出
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: 'assets/[ext]/[name]-[hash].[ext]'
      }
    },
    // 启用源码映射，便于调试生产问题
    sourcemap: process.env.VITE_ENABLE_SOURCEMAP === 'true'
  },
  // 针对Vercel部署的优化
  optimizeDeps: {
    include: ['vue', 'vue-router', 'axios', 'element-plus', 'echarts']
  }
})
