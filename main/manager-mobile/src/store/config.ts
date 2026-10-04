import type { PublicConfig } from '@/api/auth'
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getPublicConfig } from '@/api/auth'

// trạng thái khởi tạo
const initialConfigState: PublicConfig = {
  enableMobileRegister: false,
  version: '',
  year: '',
  allowUserRegister: false,
  mobileAreaList: [],
  beianIcpNum: '',
  beianGaNum: '',
  sm2PublicKey: '',
  name: import.meta.env.VITE_APP_TITLE,
}

export const useConfigStore = defineStore(
  'config',
  () => {
    // Xác định cấu hình toàn cầu
    const config = ref<PublicConfig>({ ...initialConfigState })

    // Đặt thông tin cấu hình
    const setConfig = (val: PublicConfig) => {
      config.value = val
    }

    // Nhận cấu hình công khai
    const fetchPublicConfig = async () => {
      try {
        const configData = await getPublicConfig()
        console.log(configData)

        setConfig(configData)
        return configData
      }
      catch (error) {
        console.error('获取公共配置失败:', error)
        throw error
      }
    }

    // Đặt lại cấu hình
    const resetConfig = () => {
      config.value = { ...initialConfigState }
    }

    return {
      config,
      setConfig,
      fetchPublicConfig,
      resetConfig,
    }
  },
  {
    persist: {
      key: 'config',
      serializer: {
        serialize: state => JSON.stringify(state.config),
        deserialize: value => ({ config: JSON.parse(value) }),
      },
    },
  },
)
