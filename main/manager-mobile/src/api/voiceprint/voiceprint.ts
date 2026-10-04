import type {
  ChatHistory,
  CreateSpeakerData,
  VoicePrint,
} from './types'
import { http } from '@/http/request/alova'

// Nhận danh sách giọng nói
export function getVoicePrintList(agentId: string) {
  return http.Get<VoicePrint[]>(`/agent/voice-print/list/${agentId}`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// Lấy bản ghi cuộc trò chuyện bằng giọng nói (được sử dụng để chọn vectơ giọng nói)
export function getChatHistory(agentId: string) {
  return http.Get<ChatHistory[]>(`/agent/${agentId}/chat-history/user`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

// Thêm loa mới
export function createVoicePrint(data: CreateSpeakerData) {
  return http.Post<null>('/agent/voice-print', data, {
    meta: {
      ignoreAuth: false,
      toast: true,
    },
  })
}

// Xóa giọng nói
export function deleteVoicePrint(id: string) {
  return http.Delete<null>(`/agent/voice-print/${id}`, {
    meta: {
      ignoreAuth: false,
      toast: true,
    },
  })
}

// Cập nhật thông tin giọng nói
export function updateVoicePrint(data: VoicePrint) {
  return http.Put<null>('/agent/voice-print', data, {
    meta: {
      ignoreAuth: false,
      toast: true,
    },
  })
}

// Nhận ID tải xuống âm thanh
export function getAudioDownloadId(audioId: string) {
  return http.Post<string>(`/agent/audio/${audioId}`, {}, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
  })
}
