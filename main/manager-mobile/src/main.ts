import { VueQueryPlugin } from '@tanstack/vue-query'
import { createSSRApp } from 'vue'
import App from './App.vue'
// Nhập các chức năng liên quan đến quốc tế hóa
import { initI18n } from './i18n'

import { routeInterceptor } from './router/interceptor'
import store from './store'

import '@/style/index.scss'
import 'virtual:uno.css'

export function createApp() {
  const app = createSSRApp(App)
  app.use(store)
  app.use(routeInterceptor)
  app.use(VueQueryPlugin)

  // Khởi tạo quốc tế hóa
  initI18n()

  return {
    app,
  }
}
