import type { TabBar } from '@uni-helper/vite-plugin-uni-pages'

type FgTabBarItem = TabBar['list'][0] & {
  icon: string
  iconType: 'uiLib' | 'unocss' | 'iconfont'
}

/**
 * Chiến lược lựa chọn thanh tab. Để có phần giới thiệu chi tiết hơn, hãy xem tệp tabbar.md.
 * 0: 'NO_TABBAR' `Không có thanh tab`
 * 1: 'NATIVE_TABBAR' `Thanh tab hoàn toàn gốc`
 * 2: 'CUSTOM_TABBAR_WITH_CACHE' `Thanh tab được tùy chỉnh với bộ đệm`
 * 3: 'CUSTOM_TABBAR_WITHOUT_CACHE' `Không có thanh tab tùy chỉnh bộ đệm`
 *
 * Lời nhắc ấm áp: Sau khi bất kỳ mã nào trong tệp này được thay đổi, nó cần phải được chạy lại, nếu không pages.json sẽ không được cập nhật và sẽ xảy ra lỗi.
 */
export const TABBAR_MAP = {
  NO_TABBAR: 0,
  NATIVE_TABBAR: 1,
  CUSTOM_TABBAR_WITH_CACHE: 2,
  CUSTOM_TABBAR_WITHOUT_CACHE: 3,
}
// VIỆC CẦN LÀM: Chuyển đổi chiến lược sử dụng thanh tabbar tại đây
export const selectedTabbarStrategy = TABBAR_MAP.NATIVE_TABBAR

// Khi được chọnTabbarStrategy==NATIVE_TABBAR(1), cần phải điền vào iconPath và selectedIconPath
// Khi được chọnTabbarStrategy==CUSTOM_TABBAR(2,3), cần phải điền vào biểu tượng và loại biểu tượng
// Khi được chọnTabbarStrategy==NO_TABBAR(0), tabbarList không có hiệu lực
export const tabbarList: FgTabBarItem[] = [
  {
    iconPath: 'static/tabbar/robot.png',
    selectedIconPath: 'static/tabbar/robot_activate.png',
    pagePath: 'pages/index/index',
    text: '首页',
    icon: 'home',
    // Khi chọn biểu tượng đi kèm với khung giao diện người dùng, iconType là uiLib
    iconType: 'uiLib',
  },
  {
    iconPath: 'static/tabbar/network.png',
    selectedIconPath: 'static/tabbar/network_activate.png',
    pagePath: 'pages/device-config/index',
    text: '配网',
    icon: 'i-carbon-network-3',
    iconType: 'uiLib',
  },
  {
    iconPath: 'static/tabbar/system.png',
    selectedIconPath: 'static/tabbar/system_activate.png',
    pagePath: 'pages/settings/index',
    text: '系统',
    icon: 'i-carbon-settings',
    iconType: 'uiLib',
  },
]

// NATIVE_TABBAR(1) và CUSTOM_TABBAR_WITH_CACHE(2) yêu cầu bộ đệm ẩn thanh tab
export const cacheTabbarEnable = selectedTabbarStrategy === TABBAR_MAP.NATIVE_TABBAR
  || selectedTabbarStrategy === TABBAR_MAP.CUSTOM_TABBAR_WITH_CACHE

const _tabbar: TabBar = {
  // Chỉ ứng dụng WeChat mới hỗ trợ tùy chỉnh. Ứng dụng và H5 không có hiệu lực
  custom: selectedTabbarStrategy === TABBAR_MAP.CUSTOM_TABBAR_WITH_CACHE,
  color: '#e6e6e6',
  selectedColor: '#667dea',
  backgroundColor: '#fff',
  borderStyle: 'black',
  height: '50px',
  fontSize: '10px',
  iconWidth: '24px',
  spacing: '3px',
  list: tabbarList as unknown as TabBar['list'],
}

// 0 và 1 cần hiển thị các cấu hình khác nhau của thanh tab dưới cùng để tận dụng bộ nhớ đệm
export const tabBar = cacheTabbarEnable ? _tabbar : undefined
