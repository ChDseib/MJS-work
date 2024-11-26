// src/main.js
import { createApp } from 'vue'
import App from './App.vue'

// 引入 Element Plus 及其样式
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

const app = createApp(App)

// 使用 Element Plus
app.use(ElementPlus)

app.mount('#app')