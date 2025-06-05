// src/api.js
import axios from 'axios'
import config from './config'

// 使用配置文件中的API基础URL
const API = axios.create({
  baseURL: config.apiBaseUrl,
  timeout: config.apiTimeout,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true  // 允许跨域请求携带凭证
})

// 请求拦截器
API.interceptors.request.use(
  config => {
    // 添加CORS相关头
    config.headers['X-Requested-With'] = 'XMLHttpRequest'
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
API.interceptors.response.use(
  response => {
    return response
  },
  error => {
    console.error('API请求错误:', error)
    // 如果是CORS错误，提供更详细的日志
    if (error.message && error.message.includes('Network Error')) {
      console.error('可能是CORS配置问题，请检查后端CORS设置')
      console.error('前端域名:', window.location.origin)
      console.error('后端API地址:', config.apiBaseUrl)
    }
    return Promise.reject(error)
  }
)

export default API

