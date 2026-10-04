import type { AgentFunction, PluginDefinition } from '@/api/agent/types'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const usePluginStore = defineStore(
  'plugin',
  () => {
    // Tất cả các plugin có sẵn
    const allFunctions = ref<PluginDefinition[]>([])

    // Cấu hình plug-in của tác nhân hiện tại
    const currentFunctions = ref<AgentFunction[]>([])

    // ID đại lý hiện đã được chỉnh sửa
    const currentAgentId = ref('')

    // Thiết lập tất cả các plugin có sẵn
    const setAllFunctions = (functions: PluginDefinition[]) => {
      allFunctions.value = functions
    }

    // Đặt cấu hình trình cắm của tác nhân hiện tại
    const setCurrentFunctions = (functions: AgentFunction[]) => {
      currentFunctions.value = functions
    }

    // Đặt ID đại lý hiện tại
    const setCurrentAgentId = (agentId: string) => {
      currentAgentId.value = agentId
    }

    // Cập nhật cấu hình plugin (được gọi khi lưu)
    const updateFunctions = (functions: AgentFunction[]) => {
      currentFunctions.value = functions
    }

    // Xóa dữ liệu
    const clear = () => {
      allFunctions.value = []
      currentFunctions.value = []
      currentAgentId.value = ''
    }

    return {
      allFunctions,
      currentFunctions,
      currentAgentId,
      setAllFunctions,
      setCurrentFunctions,
      setCurrentAgentId,
      updateFunctions,
      clear,
    }
  },
  {
    persist: false, // Không kiên trì, tải lại mỗi lần vào trang
  },
)
