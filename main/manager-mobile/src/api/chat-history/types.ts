// Mục danh sách phiên trò chuyện
export interface ChatSession {
  sessionId: string
  createdAt: string
  chatCount: number
  title: string
}

// Phản hồi danh sách phiên trò chuyện
export interface ChatSessionsResponse {
  total: number
  list: ChatSession[]
}

// Tin nhắn trò chuyện
export interface ChatMessage {
  createdAt: string
  chatType: 1 | 2 | 3 // 1 là người dùng, 2 là AI, 3 là mô tả thông số
  content: string
  audioId: string | null
  macAddress: string
}

// Nội dung tin nhắn của người dùng (cần phân tích cú pháp JSON)
export interface UserMessageContent {
  speaker: string
  content: string
}

// Nhận thông số danh sách phiên trò chuyện
export interface GetSessionsParams {
  page: number
  limit: number
}

// Phát lại âm thanh liên quan
export interface AudioResponse {
  data: string // ID tải xuống âm thanh
}
