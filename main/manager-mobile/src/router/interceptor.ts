/**
 * bởi Feige vào ngày 2024-03-06
 * Chặn tuyến đường, thường là chặn đăng nhập
 * Bạn có thể thiết lập danh sách trắng định tuyến hoặc danh sách đen, tùy thuộc vào nhu cầu mà doanh nghiệp của bạn cần.
 * Tôi nghĩ hầu hết mọi người ở đây đều có thể vào theo ý muốn nên tôi sử dụng danh sách đen.
 */
import { useUserStore } from '@/store'
import { needLoginPages as _needLoginPages, getLastPage, getNeedLoginPages } from '@/utils'

// Kiểm tra việc cần làm
const loginRoute = import.meta.env.VITE_LOGIN_URL

function isLogined() {
  const userStore = useUserStore()
  return !!userStore.userInfo.username
}

const isDev = import.meta.env.DEV

// Trình chặn đăng nhập danh sách đen - (áp dụng cho hầu hết các trang không yêu cầu đăng nhập, nhưng một số ít trang yêu cầu đăng nhập)
const navigateToInterceptor = {
  // Lưu ý rằng URL ở đây bắt đầu bằng '/', chẳng hạn như '/pages/index/index', khác với đường dẫn trong 'pages.json'
  // Thêm xử lý các đường dẫn tương đối, BY netizen @ideal
  invoke({ url }: { url: string }) {
    // console.log(url) // /pages/route-interceptor/index?name=feige&age=30
    let path = url.split('?')[0]
    console.log('页面变动')

    // Xử lý đường dẫn tương đối
    if (!path.startsWith('/')) {
      const currentPath = getLastPage().route
      const normalizedCurrentPath = currentPath.startsWith('/') ? currentPath : `/${currentPath}`
      const baseDir = normalizedCurrentPath.substring(0, normalizedCurrentPath.lastIndexOf('/'))
      path = `${baseDir}/${path}`
    }

    let needLoginPages: string[] = []
    // Để ngăn BUG xảy ra trong quá trình phát triển, hãy tải nó ở đây mọi lúc. Môi trường sản xuất có thể được di chuyển ra ngoài chức năng để có hiệu suất tốt hơn
    if (isDev) {
      needLoginPages = getNeedLoginPages()
    }
    else {
      needLoginPages = _needLoginPages
    }
    const isNeedLogin = needLoginPages.includes(path)
    if (!isNeedLogin) {
      return true
    }
    const hasLogin = isLogined()
    if (hasLogin) {
      return true
    }
    const redirectRoute = `${loginRoute}?redirect=${encodeURIComponent(url)}`
    uni.navigateTo({ url: redirectRoute })
    return false
  },
}

export const routeInterceptor = {
  install() {
    uni.addInterceptor('navigateTo', navigateToInterceptor)
    uni.addInterceptor('reLaunch', navigateToInterceptor)
    uni.addInterceptor('redirectTo', navigateToInterceptor)
    uni.addInterceptor('switchTab', navigateToInterceptor)
  },
}
