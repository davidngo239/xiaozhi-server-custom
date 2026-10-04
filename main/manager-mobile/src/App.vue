<script setup lang="ts">
import { onHide, onLaunch, onShow } from '@dcloudio/uni-app'
import { onMounted, watch } from 'vue'
import { usePageAuth } from '@/hooks/usePageAuth'
import { t } from '@/i18n'
import { useConfigStore } from '@/store'
import { useLangStore } from '@/store/lang'
import 'abortcontroller-polyfill/dist/abortcontroller-polyfill-only'

usePageAuth()

const configStore = useConfigStore()
const langStore = useLangStore()

onLaunch(() => {
  console.log('App Launch')
  // Nhận cấu hình công khai
  configStore.fetchPublicConfig().catch((error) => {
    console.error('获取公共配置失败:', error)
  })
})
onShow(() => {
  console.log('App Show')
  // Sử dụng setTimeout để trì hoãn việc thực thi và đảm bảo tabBar đã được khởi tạo
  setTimeout(() => {
    updateTabBarText()
  }, 100)
})

// Tự động cập nhật văn bản tabBar
function updateTabBarText() {
  try {
    // Đặt văn bản thanh tab trang chủ
    uni.setTabBarItem({
      index: 0,
      text: t('tabBar.home'),
      success: () => {},
      fail: (err) => {
        console.log('设置首页tabBar文本失败:', err)
      },
    })

    // Đặt văn bản tab mạng phân phối
    uni.setTabBarItem({
      index: 1,
      text: t('tabBar.deviceConfig'),
      success: () => {},
      fail: (err) => {
        console.log('设置配网tabBar文本失败:', err)
      },
    })

    // Đặt văn bản thanh tab hệ thống
    uni.setTabBarItem({
      index: 2,
      text: t('tabBar.settings'),
      success: () => {},
      fail: (err) => {
        console.log('设置系统tabBar文本失败:', err)
      },
    })
  }
  catch (error) {
    console.log('更新tabBar文本时出错:', error)
  }
}
// Lắng nghe các sự kiện chuyển đổi ngôn ngữ
onMounted(() => {
  // Theo dõi thay đổi ngôn ngữ và tự động cập nhật văn bản tabBar khi ngôn ngữ thay đổi
  watch(() => langStore.currentLang, () => {
    console.log('语言已切换，更新tabBar文本')
    // Cập nhật văn bản tabBar ngay sau khi chuyển đổi ngôn ngữ
    updateTabBarText()
  })
})

onHide(() => {
  console.log('App Hide')
})
</script>

<style lang="scss">
swiper,
scroll-view {
  flex: 1;
  height: 100%;
  overflow: hidden;
}

image {
  width: 100%;
  height: 100%;
  vertical-align: middle;
}
</style>
