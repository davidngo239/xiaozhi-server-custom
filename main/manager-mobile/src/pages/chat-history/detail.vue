<route lang="jsonc" type="page">
{
  "layout": "default",
  "style": {
    "navigationStyle": "custom",
    "navigationBarTitleText": "Chi tiết trò chuyện"
  }
}
</route>

<script lang="ts" setup>
import type { ChatMessage, UserMessageContent } from '@/api/chat-history/types'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { getAudioId, getChatHistory } from '@/api/chat-history/chat-history'
import { t } from '@/i18n'
import { debounce, getEnvBaseUrl } from '@/utils'
import { toast } from '@/utils/toast'

defineOptions({
  name: 'ChatDetail',
})

// Lấy khoảng cách từ ranh giới màn hình tới vùng an toàn
let safeAreaInsets: any
let systemInfo: any

// #ifdef MP-WEIXIN
systemInfo = uni.getWindowInfo()
safeAreaInsets = systemInfo.safeArea
  ? {
      top: systemInfo.safeArea.top,
      right: systemInfo.windowWidth - systemInfo.safeArea.right,
      bottom: systemInfo.windowHeight - systemInfo.safeArea.bottom,
      left: systemInfo.safeArea.left,
    }
  : null
// #endif

// #ifndef MP-WEIXIN
systemInfo = uni.getSystemInfoSync()
safeAreaInsets = systemInfo.safeAreaInsets
// #endif

// Thông số trang
const sessionId = ref('')
const agentId = ref('')

// Thông tin đại lý (đơn giản hóa)
const currentAgent = computed(() => {
  return {
    id: agentId.value,
    agentName: t('chatHistory.assistantName'),
  }
})

// Dữ liệu trò chuyện
const messageList = ref<ChatMessage[]>([])
const loading = ref(false)

// Phát lại âm thanh liên quan
const audioContext = ref<UniApp.InnerAudioContext | null>(null)
const playingAudioId = ref<string | null>(null)
const expandedToolResults = ref({})

// Quay lại trang trước
function goBack() {
  uni.navigateBack()
}

// Tải lịch sử trò chuyện
async function loadChatHistory() {
  if (!sessionId.value || !agentId.value) {
    console.error('缺少必要参数')
    return
  }

  try {
    loading.value = true
    const response = await getChatHistory(agentId.value, sessionId.value)
    messageList.value = response
  }
  catch (error) {
    console.error('获取聊天记录失败:', error)
    toast.error(t('chatHistory.loadFailed'))
  }
  finally {
    loading.value = false
  }
}

// Phân tích nội dung tin nhắn của người dùng
function parseUserMessage(content: string): UserMessageContent | null {
  try {
    return JSON.parse(content)
  }
  catch {
    return null
  }
}

// Lấy nội dung hiển thị tin nhắn
function getMessageContent(message: ChatMessage): string {
  if (message.chatType === 1) {
    // Thông báo của người dùng cần phân tích cú pháp JSON
    const parsed = parseUserMessage(message.content)
    return parsed ? parsed.content : message.content
  }
  else {
    // Tin nhắn AI, hiển thị trực tiếp
    return message.content
  }
}

// Nhận tên người nói
function getSpeakerName(message: ChatMessage): string {
  if (message.chatType === 1) {
    const parsed = parseUserMessage(message.content)
    return parsed ? parsed.speaker : t('chatHistory.userName')
  }
  else {
    return currentAgent.value?.agentName || t('chatHistory.aiAssistantName')
  }
}

// Định dạng thời gian
function formatTime(timeStr: string) {
  if (!timeStr)
    return t('chatHistory.unknownTime')

  // Xử lý chuỗi thời gian để đảm bảo định dạng chính xác
  const date = new Date(timeStr.replace(' ', 'T')) // Chuyển đổi sang định dạng ISO
  const now = new Date()

  // Kiểm tra xem ngày có hợp lệ không
  if (Number.isNaN(date.getTime())) {
    return timeStr // Nếu phân tích cú pháp không thành công, chuỗi gốc sẽ được trả về trực tiếp.
  }

  const diff = now.getTime() - date.getTime()

  // chưa đầy 1 phút
  if (diff < 60000)
    return t('chatHistory.justNow')

  // chưa đầy 1 giờ
  if (diff < 3600000)
    return t('chatHistory.minutesAgo', { minutes: Math.floor(diff / 60000) })

  // Dưới 1 ngày (24 giờ)
  if (diff < 86400000)
    return t('chatHistory.hoursAgo', { hours: Math.floor(diff / 3600000) })

  // dưới 7 ngày
  if (diff < 604800000) {
    const days = Math.floor(diff / 86400000)
    return t('chatHistory.daysAgo', { days })
  }

  // Hơn 7 ngày, hiển thị ngày cụ thể
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const currentYear = now.getFullYear()

  // Nếu là năm hiện tại thì năm đó sẽ không hiển thị
  if (year === currentYear) {
    return `${month}-${day}`
  }

  return `${year}-${month}-${day}`
}

// Phát âm thanh
const playAudio = debounce(async (audioId: string) => {
  if (!audioId) {
    toast.error(t('chatHistory.invalidAudioId'))
    return
  }

  try {
    // Nếu âm thanh khác đang phát, hãy dừng âm thanh đó trước
    if (audioContext.value) {
      audioContext.value.stop()
    }
    // Tạm dừng phát lại nếu ID âm thanh hiện tại giống với ID yêu cầu
    if (playingAudioId.value === audioId) {
      playingAudioId.value = null
      return
    }

    // Nhận ID tải xuống âm thanh
    const downloadId = await getAudioId(audioId)

    // Xây dựng địa chỉ phát lại âm thanh
    const baseUrl = getEnvBaseUrl()
    const audioUrl = `${baseUrl}/agent/play/${downloadId}`

    // Tạo bối cảnh âm thanh
    if (!audioContext.value) {
      audioContext.value = uni.createInnerAudioContext()
    }
    audioContext.value.src = audioUrl

    // Đặt trạng thái phát
    playingAudioId.value = audioId

    // Giám sát và phát lại đã hoàn tất
    audioContext.value.onEnded(() => {
      playingAudioId.value = null
      if (audioContext.value) {
        audioContext.value.destroy()
        audioContext.value = null
      }
    })

    // Theo dõi lỗi phát lại
    audioContext.value.onError((error) => {
      console.error('音频播放失败:', error)
      toast.error(t('chatHistory.audioPlayFailed'))
      playingAudioId.value = null
      if (audioContext.value) {
        audioContext.value.destroy()
        audioContext.value = null
      }
    })

    // Bắt đầu chơi
    audioContext.value.play()
  }
  catch (error) {
    console.error('播放音频失败:', error)
    toast.error(t('chatHistory.playAudioFailed'))
    playingAudioId.value = null
  }
}, 400)

function extractContentFromString(content: string) {
  if (!content || content.trim() === '') {
    return content
  }

  // Hãy thử phân tích thành JSON
  try {
    const jsonObj = JSON.parse(content)

    // Nếu là định dạng mảng (bao gồm văn bản và công cụ)
    if (Array.isArray(jsonObj)) {
      return jsonObj
    }

    // Nếu nó là một đối tượng và có trường nội dung
    if (jsonObj && typeof jsonObj === 'object' && jsonObj.content) {
      return jsonObj.content
    }
  }
  catch (e) {
    // Nếu nó không phải là JSON hợp lệ, hãy trả lại trực tiếp nội dung gốc.
  }

  // Nếu nó không ở định dạng JSON hoặc không có trường nội dung thì nội dung gốc sẽ được trả về trực tiếp.
  return content
}

function toggleToolResult(messageIndex, itemIndex) {
  const key = `${messageIndex}-${itemIndex}`
  expandedToolResults.value[key] = !expandedToolResults.value[key]
}

function isToolResultCollapsed(messageIndex, itemIndex) {
  const key = `${messageIndex}-${itemIndex}`
  // Gấp mặc định (true có nghĩa là gấp)
  return !expandedToolResults.value[key]
}

function getFirstLineText(text: string) {
  if (!text) {
    return ''
  }
  const firstLine = text.split('\n')[0]
  return firstLine.length < text.length ? `${firstLine}...` : text
}

onLoad((options) => {
  if (options?.sessionId && options?.agentId) {
    sessionId.value = options.sessionId
    agentId.value = options.agentId
  }
  else {
    console.error('缺少必要参数')
    toast.error(t('chatHistory.parameterError'))
  }
})

onShow(() => {
  loadChatHistory()
})

// Dọn dẹp tài nguyên âm thanh khi trang bị hủy
onUnload(() => {
  if (audioContext.value) {
    audioContext.value.stop()
    audioContext.value.destroy()
    audioContext.value = null
  }
})
</script>

<template>
  <view class="h-screen flex flex-col bg-[#f5f7fb]">
    <!-- Nền thanh trạng thái -->
    <view class="w-full bg-white" :style="{ height: `${safeAreaInsets?.top}px` }" />

    <!-- Thanh điều hướng -->
    <wd-navbar :title="t('chatHistory.pageTitle')">
      <template #left>
        <wd-icon name="arrow-left" size="18" @click="goBack" />
      </template>
    </wd-navbar>

    <!-- Danh sách tin nhắn trò chuyện -->
    <scroll-view
      scroll-y
      :style="{ height: `calc(100vh - ${safeAreaInsets?.top || 0}px - 120rpx)` }"
      class="box-border flex-1 bg-[#f5f7fb] p-[20rpx]"
      :scroll-into-view="`message-${messageList.length - 1}`"
    >
      <view v-if="loading" class="flex flex-col items-center justify-center gap-[20rpx] p-[100rpx_0]">
        <wd-loading />
        <text class="text-[28rpx] text-[#65686f]">
          {{ t('chatHistory.loading') }}
        </text>
      </view>

      <view v-else class="flex flex-col gap-[20rpx]">
        <view
          v-for="(message, index) in messageList"
          :id="`message-${index}`"
          :key="index"
          class="w-full flex"
          :class="{
            'justify-end': message.chatType === 1,
            'justify-start': message.chatType === 2,
          }"
        >
          <view
            class="max-w-[80%] flex flex-col gap-[8rpx]"
            :class="{
              'items-end': message.chatType === 1,
              'items-start': message.chatType === 2,
              'tool-message': message.chatType === 3,
            }"
          >
            <!-- Bong bóng tin nhắn -->
            <view
              class="shadow-message break-words rounded-[20rpx] p-[24rpx] leading-[1.4]"
              :class="{
                'bg-[#336cff] text-white': message.chatType === 1,
                'bg-white text-[#232338] border border-[#eeeeee]': [2, 3].includes(message.chatType),
              }"
            >
              <template v-if="Array.isArray(extractContentFromString(message.content))">
                <div class="content-wrapper">
                  <div v-for="(item, idx) in extractContentFromString(message.content)" :key="idx">
                    <div v-if="item.type === 'text'" class="text-content">
                      {{ item.text }}
                    </div>
                    <div v-else-if="item.type === 'tool'" class="tool-call-text">
                      {{ item.text }}
                    </div>
                    <div v-else-if="item.type === 'tool_result'" class="tool-call-text">
                      <div v-if="item.text && item.text.length > 80" class="tool-result-wrapper">
                        <div v-if="isToolResultCollapsed(index, idx)" class="tool-result-collapsed">
                          {{ getFirstLineText(item.text) }}
                        </div>
                        <div v-else class="tool-result-expanded">
                          {{ item.text }}
                        </div>
                        <span class="tool-toggle-btn" @click="toggleToolResult(index, idx)">
                          <wd-icon :name="isToolResultCollapsed(index, idx) ? 'arrow-down' : 'arrow-up'" size="12" />
                        </span>
                      </div>
                      <div v-else>
                        {{ item.text }}
                      </div>
                    </div>
                  </div>
                </div>
              </template>
              <!-- Khu vực nội dung - sử dụng bố cục linh hoạt để căn chỉnh biểu tượng và văn bản -->
              <view v-else class="flex items-center gap-[12rpx]">
                <!-- Biểu tượng phát lại âm thanh -->
                <view
                  v-if="message.audioId"
                  class="flex-shrink-0 cursor-pointer transition-transform duration-200 active:scale-90"
                  :class="{
                    'text-white animate-pulse-audio': message.chatType === 1 && playingAudioId === message.audioId,
                    'text-[#ffd700]': message.chatType === 1 && playingAudioId === message.audioId && playingAudioId,
                    'text-[#336cff] animate-pulse-audio': message.chatType === 2 && playingAudioId === message.audioId,
                    'text-[#ff6b35]': message.chatType === 2 && playingAudioId === message.audioId && playingAudioId,
                    'text-white': message.chatType === 1 && playingAudioId !== message.audioId,
                    'text-[#336cff]': message.chatType === 2 && playingAudioId !== message.audioId,
                  }"
                  @click="playAudio(message.audioId)"
                >
                  <wd-icon
                    :name="playingAudioId === message.audioId ? 'pause-circle-filled' : 'play-circle-filled'"
                    size="20"
                  />
                </view>

                <!-- Vùng chứa nội dung tin nhắn -->
                <view class="min-w-0 flex-1">
                  <!-- Nội dung tin nhắn -->
                  <text class="block text-[28rpx]">
                    {{ getMessageContent(message) }}
                  </text>
                </view>
              </view>
            </view>

            <!-- Thông tin diễn giả -->
            <text
              class="mx-[12rpx] text-[22rpx] text-[#9d9ea3]"
              :class="{
                'text-right': message.chatType === 1,
                'text-left': message.chatType === 2,
              }"
            >
              {{ formatTime(message.createdAt) }}
            </text>
          </view>
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<style>
/* Các hiệu ứng đổ bóng và hoạt ảnh tùy chỉnh, các kiểu không thể được thể hiện bằng UnoCSS */
.shadow-message {
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.06);
}

@keyframes pulse-audio {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

.animate-pulse-audio {
  animation: pulse-audio 1.5s infinite;
}

.text-content {
  display: block;
  margin-bottom: 8rpx;
}

.tool-call-text {
  color: #1890ff;
  font-family: 'Courier New', monospace;
  font-weight: 500;
  font-size: 24rpx;
  display: block;
  margin-top: 8rpx;
}

.user-message .tool-call-text {
  color: #e6f7ff;
}

.tool-message .message-content {
  background-color: #f0f0f0;
}

.tool-result-wrapper {
  position: relative;
  padding-right: 40rpx;
}

.tool-result-collapsed {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tool-toggle-btn {
  position: absolute;
  right: 0;
  top: 0;
  cursor: pointer;
  color: #1890ff;
  font-size: 24rpx;
}
</style>
