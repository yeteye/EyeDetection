// main.js
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import axios from 'axios'

// 设置axios基本URL，根据实际部署环境可能需要修改
axios.defaults.baseURL = process.env.NODE_ENV === 'production' 
  ? '' 
  : 'http://localhost:5000';

const app = createApp(App)

app.use(ElementPlus)
app.mount('#app')