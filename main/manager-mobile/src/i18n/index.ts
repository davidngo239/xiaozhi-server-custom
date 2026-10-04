import type { Language } from '@/store/lang'
import { ref } from 'vue'
import { useLangStore } from '@/store/lang'

import de from './de'
import en from './en'
import pt_BR from './pt_BR'
import vi from './vi'
// Nhập file dịch cho từng ngôn ngữ
import zh_CN from './zh_CN'
import zh_TW from './zh_TW'

// Ánh xạ gói ngôn ngữ
const messages = {
  zh_CN,
  en,
  zh_TW,
  de,
  vi,
  pt_BR,
}

// Ngôn ngữ hiện tại
const currentLang = ref<Language>('vi')

// ngôn ngữ khởi tạo
export function initI18n() {
  const langStore = useLangStore()
  currentLang.value = langStore.currentLang
}

// chuyển đổi ngôn ngữ
export function changeLanguage(lang: Language) {
  currentLang.value = lang
  const langStore = useLangStore()
  langStore.changeLang(lang)
}

// Nhận văn bản dịch
export function t(key: string, params?: Record<string, string | number>): string {
  const langMessages = messages[currentLang.value]

  // Tìm tên khóa phẳng trực tiếp
  if (langMessages && typeof langMessages === 'object' && key in langMessages) {
    const value = langMessages[key]
    if (typeof value === 'string') {
      // Xử lý thay thế tham số
      if (params) {
        let result = value
        Object.entries(params).forEach(([paramKey, paramValue]) => {
          const regex = new RegExp(`\{${paramKey}\}`, 'g')
          result = result.replace(regex, String(paramValue))
        })
        return result
      }
      return value
    }
    return key
  }

  return key // Nếu không tìm thấy bản dịch tương ứng, hãy trả lại chính khóa đó
}

// Nhận ngôn ngữ hiện tại
export function getCurrentLanguage(): Language {
  return currentLang.value
}

// Nhận danh sách các ngôn ngữ được hỗ trợ
export function getSupportedLanguages(): { code: Language, name: string }[] {
  return [
    { code: 'zh_CN', name: '简体中文' },
    { code: 'en', name: 'English' },
    { code: 'zh_TW', name: '繁體中文' },
    { code: 'de', name: 'Deutsch' },
    { code: 'vi', name: 'Tiếng Việt' },
    { code: 'pt_BR', name: 'Português (Brasil)' },
  ]
}
