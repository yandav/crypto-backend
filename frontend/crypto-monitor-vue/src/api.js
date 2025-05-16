// src/api.js
import axios from 'axios'

const API = axios.create({
  baseURL: 'https://crypto-backend-2.onrender.com', // 你的后端 Render 地址
})

export default API
