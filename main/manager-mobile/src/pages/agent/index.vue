<route lang="jsonc" type="page">
{
  "layout": "default",
  "style": {
    "navigationBarTitleText": "Trợ lý AI",
    "navigationStyle": "custom"
  }
}
</route>

<script lang="ts" setup>
import { onLoad } from '@dcloudio/uni-app'
import { onMounted, ref } from 'vue'
import CustomTabs from '@/components/custom-tabs/index.vue'
import { t } from '@/i18n'
import ChatHistory from '@/pages/chat-history/index.vue'
import DeviceManagement from '@/pages/device/index.vue'
import VoiceprintManagement from '@/pages/voiceprint/index.vue'
import AgentEdit from './edit.vue'

defineOptions({
  name: 'AgentIndex',
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

// ID đại lý
const currentAgentId = ref('default')

// tab hiện tại
const currentTab = ref('agent-config')

// Trạng thái làm mới và tải
const refreshing = ref(false)
const refresherEnabled = ref(false)

// tham chiếu thành phần phụ
const deviceRef = ref()
const chatRef = ref()
const voiceprintRef = ref()

// Cập nhật trạng thái bồi dưỡng
function updateRefresherEnabled(value: boolean) {
  refresherEnabled.value = value
}

// Cấu hình tab
const tabList = [
  {
    label: t('agent.roleConfig'),
    value: 'agent-config',
    icon: '/static/tabbar/robot.png',
    activeIcon: '/static/tabbar/robot_activate.png',
  },
  {
    label: t('agent.deviceManagement'),
    value: 'device-management',
    icon: '/static/tabbar/device.png',
    activeIcon: '/static/tabbar/device_activate.png',
  },
  {
    label: t('agent.chatHistory'),
    value: 'chat-history',
    icon: '/static/tabbar/chat.png',
    activeIcon: '/static/tabbar/chat_activate.png',
  },
  {
    label: t('agent.voiceprintManagement'),
    value: 'voiceprint-management',
    icon: '/static/tabbar/microphone.png',
    activeIcon: '/static/tabbar/microphone_activate.png',
  },
]

// Quay lại trang trước
function goBack() {
  uni.navigateBack()
}

// Xử lý chuyển đổi tab
function handleTabChange(item: any) {
  console.log('Tab changed:', item)
}

// Kéo xuống để làm mới
async function onRefresh() {
  // Trang chỉnh sửa ký tự không cần phải làm mới
  if (currentTab.value === 'agent-config') {
    return
  }

  refreshing.value = true

  try {
    switch (currentTab.value) {
      case 'device-management':
        if (deviceRef.value?.refresh) {
          await deviceRef.value.refresh()
        }
        break
      case 'chat-history':
        if (chatRef.value?.refresh) {
          await chatRef.value.refresh()
        }
        break
      case 'voiceprint-management':
        if (voiceprintRef.value?.refresh) {
          await voiceprintRef.value.refresh()
        }
        break
    }
  }
  catch (error) {
    console.error('刷新失败:', error)
  }
  finally {
    refreshing.value = false
  }
}

// Đang tải thêm
async function onLoadMore() {
  // Chỉ có lịch sử trò chuyện cần được tải thêm
  if (currentTab.value === 'chat-history' && chatRef.value?.loadMore) {
    await chatRef.value.loadMore()
  }
}

watch(() => currentTab.value, (newTab) => {
  updateRefresherEnabled(newTab !== 'agent-config')
})

// Nhận thông số trang
onLoad((options) => {
  if (options?.agentId) {
    currentAgentId.value = options.agentId
    console.log('接收到智能体ID:', options.agentId)
  }
})

onMounted(async () => {
  // Khởi tạo trang
})
</script>

<template>
  <view class="h-screen flex flex-col bg-[#f5f7fb]">
    <!-- Thanh điều hướng -->
    <wd-navbar :title="t('agent.pageTitle')" safe-area-inset-top>
      <template #left>
        <wd-icon name="arrow-left" size="18" @click="goBack" />
      </template>
    </wd-navbar>

    <!-- Tab tùy chỉnh -->
    <CustomTabs
      v-model="currentTab"
      :tab-list="tabList"
      @change="handleTabChange"
    />

    <!-- Khu vực cuộn nội dung chính -->
    <scroll-view
      scroll-y
      :style="{ height: `calc(100vh - ${safeAreaInsets?.top || 0}px - 180rpx)` }"
      class="box-border flex-1 bg-[#f5f7fb]"
      enable-back-to-top
      :refresher-enabled="refresherEnabled"
      :refresher-triggered="refreshing"
      @refresherrefresh="onRefresh"
      @scrolltolower="onLoadMore"
    >
      <!-- Nội dung tab -->
      <view class="flex-1">
        <AgentEdit
          v-if="currentTab === 'agent-config'"
          :agent-id="currentAgentId"
        />
        <DeviceManagement
          v-else-if="currentTab === 'device-management'"
          ref="deviceRef"
          :agent-id="currentAgentId"
        />
        <ChatHistory
          v-else-if="currentTab === 'chat-history'"
          ref="chatRef"
          :agent-id="currentAgentId"
        />
        <VoiceprintManagement
          v-else-if="currentTab === 'voiceprint-management'"
          ref="voiceprintRef"
          :agent-id="currentAgentId"
          @update-refresher-enabled="updateRefresherEnabled"
        />
      </view>
    </scroll-view>
  </view>
</template>

<style scoped>
</style>
