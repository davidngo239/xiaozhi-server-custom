import type {
  Agent,
  AgentCreateData,
  AgentDetail,
  AgentSnapshot,
  AgentSnapshotPageParams,
  CorrectWordFile,
  ModelOption,
  PageData,
  RoleTemplate,
  TtsVoice,
} from './types'
import { http } from '@/http/request/alova'

// Nhận thông tin chi tiết đại lý
export function getAgentDetail(id: string) {
  return http.Get<AgentDetail>(`/agent/${id}`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// Nhận danh sách các mẫu vai trò
export function getRoleTemplates() {
  return http.Get<RoleTemplate[]>('/agent/template', {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// Nhận tùy chọn mô hình
export function getModelOptions(modelType: string, modelName: string = '') {
  return http.Get<ModelOption[]>('/models/names', {
    params: {
      modelType,
      modelName,
    },
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// Lấy danh sách đại lý
export function getAgentList() {
  return http.Get<Agent[]>('/agent/list', {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// Tạo một đại lý
export function createAgent(data: AgentCreateData) {
  return http.Post<string>('/agent', data, {
    meta: {
      ignoreAuth: false,
      toast: true,
    },
  })
}

// Xóa đại lý
export function deleteAgent(id: string) {
  return http.Delete(`/agent/${id}`, {
    meta: {
      ignoreAuth: false,
      toast: true,
    },
  })
}

// Nhận danh sách giai điệu TTS
export function getTTSVoices(ttsModelId: string, voiceName: string = '') {
  return http.Get<TtsVoice[]>(`/models/${ttsModelId}/voices`, {
    params: {
      voiceName,
    },
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// Cập nhật đại lý
export function updateAgent(id: string, data: Partial<AgentDetail> & { tagNames?: string[] }) {
  return http.Put(`/agent/${id}`, data, {
    meta: {
      ignoreAuth: false,
      toast: true,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// Nhận danh sách plugin
export function getPluginFunctions() {
  return http.Get<any[]>(`/models/provider/plugin/names`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// Nhận điểm truy cập mcp
export function getMcpAddress(agentId: string) {
  return http.Get<string>(`/agent/mcp/address/${agentId}`, {
    meta: {
      ignoreAuth: false,
      toast: false,
      isExposeError: true,
    },
  })
}

// Nhận công cụ mcp
export function getMcpTools(agentId: string) {
  return http.Get<string[]>(`/agent/mcp/tools/${agentId}`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// Nhận danh sách giọng nói
export function getVoicePrintList(agentId: string) {
  return http.Get<any[]>(`/agent/voice-print/list/${agentId}`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// Nhận bản ghi cuộc trò chuyện bằng giọng nói
export function getChatHistoryUser(agentId: string) {
  return http.Get<any[]>(`/agent/${agentId}/chat-history/user`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// Thêm loa voiceprint mới
export function createVoicePrint(data: { agentId: string, audioId: string, sourceName: string, introduce: string }) {
  return http.Post('/agent/voice-print', data, {
    meta: {
      ignoreAuth: false,
      toast: true,
    },
  })
}

// Nhận thẻ đại lý
export function getAgentTags(agentId: string) {
  return http.Get<any[]>(`/agent/${agentId}/tags`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// Cập nhật nhãn đại lý
export function updateAgentTags(agentId: string, data) {
  return http.Put(`/agent/${agentId}/tags`, data, {
    meta: {
      ignoreAuth: false,
      isExposeError: true,
    },
  })
}

// Nhận tất cả các ngôn ngữ
export function getAllLanguage(modelId: string) {
  return http.Get<TtsVoice[]>(`/models/${modelId}/voices`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

/**
 * Nhận ID phát lại tạm thời của âm thanh được nhân bản
 * @param cloneId bản sao ID bản ghi âm thanh
 */
export function getVoiceCloneAudioId(cloneId: string) {
  return http.Post<string>(`/voiceClone/audio/${cloneId}`, {}, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
  })
}

// Nhận danh sách các phiên bản lịch sử của đại lý
export function getAgentSnapshots(agentId: string, params: AgentSnapshotPageParams) {
  return http.Get<PageData<AgentSnapshot>>(`/agent/${agentId}/snapshots`, {
    params,
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// Nhận chi tiết phiên bản lịch sử của đại lý
export function getAgentSnapshot(agentId: string, snapshotId: string) {
  return http.Get<AgentSnapshot>(`/agent/${agentId}/snapshots/${snapshotId}`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// Khôi phục phiên bản lịch sử của đại lý
export function restoreAgentSnapshot(agentId: string, snapshotId: string, currentStateToken: string) {
  return http.Post(`/agent/${agentId}/snapshots/${snapshotId}/restore`, { currentStateToken }, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
  })
}

// Xóa phiên bản lịch sử của đại lý
export function deleteAgentSnapshot(agentId: string, snapshotId: string) {
  return http.Delete(`/agent/${agentId}/snapshots/${snapshotId}`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
  })
}

// Nhận tất cả các file word thay thế
export function getCorrectWordFiles() {
  return http.Get<CorrectWordFile[]>('/correct-word/file/select', {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}
