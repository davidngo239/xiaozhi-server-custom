import type { Ref } from 'vue'
import { defineStore } from 'pinia'
import { ref } from 'vue'

// Các loại ngôn ngữ được hỗ trợ
export type Language = 'zh_CN' | 'en' | 'zh_TW' | 'de' | 'vi' | 'pt_BR'

export interface LangStore {
  currentLang: Ref<Language>
  changeLang: (lang: Language) => void
}

export const useLangStore = defineStore(
  'lang',
  (): LangStore => {
    // Nhận cài đặt ngôn ngữ từ bộ nhớ cục bộ, sử dụng cài đặt mặc định nếu không có
    const savedLang = uni.getStorageSync('app_language') as Language | null
    const currentLang = ref<Language>(savedLang || 'vi')

    // chuyển đổi ngôn ngữ
    const changeLang = (lang: Language) => {
      currentLang.value = lang
      // Lưu cài đặt ngôn ngữ vào bộ nhớ cục bộ
      uni.setStorageSync('app_language', lang)
    }

    return {
      currentLang,
      changeLang,
    }
  },
  {
    persist: {
      key: 'lang',
      serializer: {
        serialize: state => JSON.stringify(state.currentLang),
        deserialize: value => ({ currentLang: JSON.parse(value) }),
      },
    },
  },
)
