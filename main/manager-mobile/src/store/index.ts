import { createPinia } from 'pinia'
import { createPersistedState } from 'pinia-plugin-persistedstate' // Tính kiên trì của dữ liệu

const store = createPinia()
store.use(
  createPersistedState({
    storage: {
      getItem: uni.getStorageSync,
      setItem: uni.setStorageSync,
    },
  }),
)

export default store

export * from './config'
export * from './plugin'
export * from './provider'
export * from './speedPitch'
// Xuất khẩu thống nhất các mô-đun
export * from './user'
