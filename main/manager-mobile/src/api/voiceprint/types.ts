// Loại phản hồi thông tin giọng nói
export interface VoicePrint {
  id: string
  audioId: string
  sourceName: string
  introduce: string
  createDate: string
}

// Loại bản ghi cuộc trò chuyện bằng giọng nói
export interface ChatHistory {
  content: string
  audioId: string
}

// Tạo kiểu dữ liệu loa
export interface CreateSpeakerData {
  agentId: string
  audioId: string
  sourceName: string
  introduce: string
}

// Các loại phản hồi chung
export interface ApiResponse<T = any> {
  code: number
  msg: string
  data: T
}
