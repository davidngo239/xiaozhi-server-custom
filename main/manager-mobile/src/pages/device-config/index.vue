<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { t } from '@/i18n'
import UltrasonicConfig from './components/ultrasonic-config.vue'
import WifiConfig from './components/wifi-config.vue'
import WifiSelector from './components/wifi-selector.vue'

// định nghĩa kiểu
interface WiFiNetwork {
  ssid: string
  rssi: number
  authmode: number
  channel: number
}

// Loại mạng lưới phân phối
const configType = ref<'wifi' | 'ultrasonic'>('wifi')

// Trạng thái bộ chọn chế độ phân phối
const configTypeSelectorShow = ref(false)

// Tham khảo bộ chọn WiFi
const wifiSelectorRef = ref<InstanceType<typeof WifiSelector>>()

// Thông tin mạng WiFi đã chọn
const selectedWifiInfo = ref<{
  network: WiFiNetwork | null
  password: string
}>({
  network: null,
  password: '',
})

// Tùy chọn chế độ phân phối
const configTypeOptions = [
  {
    name: t('deviceConfig.wifiConfig'),
    value: 'wifi' as const,
  },
  // {
  //   name: t('deviceConfig.ultrasonicConfig'),
  //   value: 'ultrasonic' as const,
  // },
]

// Hiển thị bộ chọn chế độ phân phối
function showConfigTypeSelector() {
  configTypeSelectorShow.value = true
}

// Xác nhận bộ chọn chế độ phân phối
function onConfigTypeConfirm(item: { name: string, value: 'wifi' | 'ultrasonic' }) {
  configType.value = item.value
  configTypeSelectorShow.value = false
}

// Bộ chọn chế độ phân phối hủy bỏ
function onConfigTypeCancel() {
  configTypeSelectorShow.value = false
}

// Sự kiện lựa chọn mạng WiFi
function onNetworkSelected(network: WiFiNetwork | null, password: string) {
  selectedWifiInfo.value = { network, password }
}

// Sự kiện thay đổi trạng thái kết nối ESP32
function onConnectionStatusChange(connected: boolean) {
  console.log('ESP32连接状态:', connected)
}
// Đặt tiêu đề thanh điều hướng sau khi thành phần được gắn kết
onMounted(() => {
  uni.setNavigationBarTitle({
    title: t('deviceConfig.pageTitle'),
  })
})
</script>

<template>
  <view class="min-h-screen bg-[#f5f7fb]">
    <wd-navbar :title="t('deviceConfig.pageTitle')" safe-area-inset-top />

    <view class="box-border px-[20rpx]">
      <!-- Lựa chọn phương thức phân phối mạng -->
      <view class="pb-[20rpx] first:pt-[20rpx]">
        <text class="text-[32rpx] text-[#232338] font-bold">
          {{ t('deviceConfig.configMethod') }}
        </text>
      </view>

      <view class="mb-[24rpx] border border-[#eeeeee] rounded-[20rpx] bg-[#fbfbfb] p-[24rpx]" style="box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);">
        <view class="flex cursor-pointer items-center justify-between border border-[#eeeeee] rounded-[12rpx] bg-[#f5f7fb] p-[20rpx] transition-all duration-300 active:border-[#336cff] active:bg-[#eef3ff]" @click="showConfigTypeSelector">
          <text class="text-[28rpx] text-[#232338] font-medium">
            {{ t('deviceConfig.configMethod') }}
          </text>
          <text class="mx-[16rpx] flex-1 text-right text-[26rpx] text-[#65686f]">
            {{ configType === 'wifi' ? t('deviceConfig.wifiConfig') : t('deviceConfig.ultrasonicConfig') }}
          </text>
          <wd-icon name="arrow-right" custom-class="text-[20rpx] text-[#9d9ea3]" />
        </view>
      </view>

      <!-- Lựa chọn mạng WiFi -->
      <view class="pb-[20rpx]">
        <text class="text-[32rpx] text-[#232338] font-bold">
          {{ t('deviceConfig.networkConfig') }}
        </text>
      </view>

      <view class="mb-[24rpx] border border-[#eeeeee] rounded-[20rpx] bg-[#fbfbfb] p-[24rpx]" style="box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.04);">
        <wifi-selector
          ref="wifiSelectorRef"
          @network-selected="onNetworkSelected"
          @connection-status="onConnectionStatusChange"
        />
      </view>

      <!-- Vận hành mạng lưới phân phối -->
      <view v-if="selectedWifiInfo.network" class="flex-1">
        <!-- Các thành phần mạng phân phối WiFi -->
        <wifi-config
          v-if="configType === 'wifi'"
          :selected-network="selectedWifiInfo.network"
          :password="selectedWifiInfo.password"
        />

        <!-- Các thành phần mạng lưới phân phối siêu âm -->
        <ultrasonic-config
          v-else-if="configType === 'ultrasonic'"
          :selected-network="selectedWifiInfo.network"
          :password="selectedWifiInfo.password"
        />
      </view>
    </view>

    <!-- Bộ chọn chế độ phân phối -->
    <wd-action-sheet
      v-model="configTypeSelectorShow"
      :actions="configTypeOptions.map(item => ({ name: item.name, value: item.value }))"
      @close="onConfigTypeCancel"
      @select="({ item }) => onConfigTypeConfirm(item)"
    />
  </view>
</template>

<route lang="jsonc" type="page">
{
  "style": {
    "navigationBarTitleText": "Cấu hình thiết bị",
    "navigationStyle": "custom"
  }
}
</route>
