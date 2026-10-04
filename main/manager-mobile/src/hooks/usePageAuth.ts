import { onLoad } from '@dcloudio/uni-app'
import { useUserStore } from '@/store'
import { needLoginPages as _needLoginPages, getNeedLoginPages } from '@/utils'

const loginRoute = import.meta.env.VITE_LOGIN_URL
const isDev = import.meta.env.DEV
function isLogined() {
  const userStore = useUserStore()
  return !!userStore.userInfo.username
}
// Kiểm tra xem trang hiện tại có yêu cầu đăng nhập không
export function usePageAuth() {
  onLoad((options) => {
    // Nhận đường dẫn trang hiện tại
    const pages = getCurrentPages()
    const currentPage = pages[pages.length - 1]
    const currentPath = `/${currentPage.route}`

    // Lấy danh sách các trang yêu cầu đăng nhập
    let needLoginPages: string[] = []
    if (isDev) {
      needLoginPages = getNeedLoginPages()
    }
    else {
      needLoginPages = _needLoginPages
    }

    // Kiểm tra xem trang hiện tại có yêu cầu đăng nhập không
    const isNeedLogin = needLoginPages.includes(currentPath)
    if (!isNeedLogin) {
      return
    }

    const hasLogin = isLogined()
    if (hasLogin) {
      return true
    }

    // Xây dựng URL chuyển hướng
    const queryString = Object.entries(options || {})
      .map(([key, value]) => `${key}=${encodeURIComponent(String(value))}`)
      .join('&')

    const currentFullPath = queryString ? `${currentPath}?${queryString}` : currentPath
    const redirectRoute = `${loginRoute}?redirect=${encodeURIComponent(currentFullPath)}`

    // Chuyển hướng đến trang đăng nhập
    uni.redirectTo({ url: redirectRoute })
  })
}
