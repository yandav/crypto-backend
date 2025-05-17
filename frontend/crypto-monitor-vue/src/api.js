// src/api.js
import axios from 'axios'

//http://127.0.0.1:5000
//https://crypto-backend-2.onrender.com
const API = axios.create({
  baseURL: 'https://crypto-backend-2.onrender.com', // 你的后端 Render 地址
})

export default API
