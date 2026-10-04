import type {
  ChatMessage,
  ChatSessionsResponse,
  GetSessionsParams,
} from './types'
import { http } from '@/http/request/alova'

/**
 * Nhận danh sách phiên trò chuyện
 * @param agentId ID đại lý
 * @param params Thông số phân trang
 */
export function getChatSessions(agentId: string, params: GetSessionsParams) {
  return http.Get<ChatSessionsResponse>(`/agent/${agentId}/sessions`, {
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

/**
 * Nhận chi tiết lịch sử trò chuyện
 * @param agentId ID đại lý
 * @param sessionId ID phiên
 */
export function getChatHistory(agentId: string, sessionId: string) {
  return http.Get<ChatMessage[]>(`/agent/${agentId}/chat-history/${sessionId}`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: -1,
    },
  })
}

/**
 * Nhận ID tải xuống âm thanh
 * @param audioId ID âm thanh
 */
export function getAudioId(audioId: string) {
  return http.Post<string>(`/agent/audio/${audioId}`, {}, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
  })
}

/**
 * Lấy địa chỉ phát lại âm thanh
 * @param downloadId ID tải xuống
 */
export function getAudioPlayUrl(downloadId: string) {
  // Theo tài liệu yêu cầu, điều này trả về trực tiếp nhị phân, vì vậy chúng tôi xây dựng URL trực tiếp
  return `/agent/play/${downloadId}`
}
