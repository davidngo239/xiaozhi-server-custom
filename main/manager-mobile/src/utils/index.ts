import smCrypto from 'sm-crypto'
import { pages, subPackages } from '@/pages.json'

import { isMpWeixin } from './platform'

/**
 * Địa chỉ máy chủ thời gian chạy ghi đè khóa lưu trữ
 */
export const SERVER_BASE_URL_OVERRIDE_KEY = 'server_base_url_override'

/**
 * Đặt/xóa/lấy địa chỉ máy chủ được bảo vệ trong thời gian chạy
 */
export function setServerBaseUrlOverride(url: string) {
  uni.setStorageSync(SERVER_BASE_URL_OVERRIDE_KEY, url)
}

export function clearServerBaseUrlOverride() {
  uni.removeStorageSync(SERVER_BASE_URL_OVERRIDE_KEY)
}

export function getServerBaseUrlOverride(): string | null {
  const value = uni.getStorageSync(SERVER_BASE_URL_OVERRIDE_KEY)
  return value || null
}

export function getLastPage() {
  // getCurrentPages() có ít nhất 1 phần tử nên không cần phải đánh giá thêm
  // const lastPage = getCurrentPages().at(-1)
  // Cái ở trên sẽ báo lỗi khi đóng gói trong phiên bản Android thấp hơn, vì vậy hãy sử dụng cái sau thay thế [Mặc dù tôi đã thêm src/interceptions/prototype.ts nhưng nó vẫn báo lỗi]
  const pages = getCurrentPages()
  return pages[pages.length - 1]
}

/**
 * Nhận đường dẫn và redirectPath của tuyến trang hiện tại
 * đường dẫn như '/pages/login/index'
 * redirectPath chẳng hạn như '/pages/demo/base/route-interceptor'
 */
export function currRoute() {
  const lastPage = getLastPage()
  const currRoute = (lastPage as any).$page
  // console.log('lastPage.$page:', currRoute)
  // console.log('lastPage.$page.fullpath:', currRoute.fullPath)
  // console.log('lastPage.$page.options:', currRoute.options)
  // console.log('lastPage.options:', (lastPage as any).options)
  // Sau khi kiểm tra nhiều thiết bị đầu cuối, chỉ có fullPath là đáng tin cậy, còn các thiết bị khác là không đáng tin cậy.
  const { fullPath } = currRoute as { fullPath: string }
  // console.log(fullPath)
  // ví dụ: /pages/login/index?redirect=%2Fpages%2Fdemo%2Fbase%2Froute-interceptor (chương trình nhỏ)
  // eg: /pages/login/index?redirect=%2Fpages%2Froute-interceptor%2Findex%3Fname%3Dfeige%26age%3D30(h5)
  return getUrlObj(fullPath)
}

function ensureDecodeURIComponent(url: string) {
  if (url.startsWith('%')) {
    return ensureDecodeURIComponent(decodeURIComponent(url))
  }
  return url
}
/**
 * Phân tích url để lấy đường dẫn và truy vấn
 * Ví dụ: nhập url: /pages/login/index?redirect=%2Fpages%2Fdemo%2Fbase%2Froute-interceptor
 * Đầu ra: {path: /pages/login/index, query: {redirect: /pages/demo/base/route-interceptor}}
 */
export function getUrlObj(url: string) {
  const [path, queryStr] = url.split('?')
  // console.log(path, queryStr)

  if (!queryStr) {
    return {
      path,
      query: {},
    }
  }
  const query: Record<string, string> = {}
  queryStr.split('&').forEach((item) => {
    const [key, value] = item.split('=')
    // console.log(key, value)
    query[key] = ensureDecodeURIComponent(value) // Cần phải thống nhất DecodeURIComponent ở đây mới có thể tương thích với h5 và WeChat y
  })
  return { path, query }
}
/**
 * Nhận tất cả các trang cần đăng nhập, bao gồm gói chính và hợp đồng phụ
 * Thiết kế ở đây tổng quát hơn. Bạn có thể truyền chìa khóa làm cơ sở để phán đoán. Giá trị mặc định là needLogin, được sử dụng cùng với block-route.
 * Nếu khóa không được thông qua, điều đó có nghĩa là tất cả các trang. Nếu khóa được thông qua, điều đó có nghĩa là lọc theo khóa.
 */
export function getAllPages(key = 'needLogin') {
  // Gói chính được xử lý ở đây
  const mainPages = pages
    .filter(page => !key || page[key])
    .map(page => ({
      ...page,
      path: `/${page.path}`,
    }))

  // Hợp đồng phụ được xử lý ở đây
  const subPages: any[] = []
  subPackages.forEach((subPageObj) => {
    // console.log(subPageObj)
    const { root } = subPageObj

    subPageObj.pages
      .filter(page => !key || page[key])
      .forEach((page: { path: string } & Record<string, any>) => {
        subPages.push({
          ...page,
          path: `/${root}/${page.path}`,
        })
      })
  })
  const result = [...mainPages, ...subPages]
  // console.log(`getAllPages by ${key} result: `, result)
  return result
}

/**
 * Nhận tất cả các trang cần đăng nhập, bao gồm gói chính và hợp đồng phụ
 * Chỉ lấy mảng đường dẫn
 */
export const getNeedLoginPages = (): string[] => getAllPages('needLogin').map(page => page.path)

/**
 * Nhận tất cả các trang cần đăng nhập, bao gồm gói chính và hợp đồng phụ
 * Chỉ lấy mảng đường dẫn
 */
export const needLoginPages: string[] = getAllPages('needLogin').map(page => page.path)

/**
 * Theo môi trường hiện tại của applet WeChat, hãy xác định baseUrl cần lấy
 */
export function getEnvBaseUrl() {
  // Nếu có địa chỉ ghi đè do người dùng đặt, địa chỉ đó sẽ được trả về trước.
  const override = getServerBaseUrlOverride()
  if (override)
    return override

  // Địa chỉ cơ sở yêu cầu (mặc định đến từ env)
  let baseUrl = import.meta.env.VITE_SERVER_BASEURL

  // # Một số sinh viên có thể cần đặt địa chỉ tải lên theo quá trình phát triển, dùng thử và phát hành trong ứng dụng WeChat. Mã tham chiếu như sau.
  const VITE_SERVER_BASEURL__WEIXIN_DEVELOP = 'https://ukw0y1.laf.run'
  const VITE_SERVER_BASEURL__WEIXIN_TRIAL = 'https://ukw0y1.laf.run'
  const VITE_SERVER_BASEURL__WEIXIN_RELEASE = 'https://ukw0y1.laf.run'

  // Phân biệt môi trường applet WeChat
  if (isMpWeixin) {
    const {
      miniProgram: { envVersion },
    } = uni.getAccountInfoSync()

    switch (envVersion) {
      case 'develop':
        baseUrl = VITE_SERVER_BASEURL__WEIXIN_DEVELOP || baseUrl
        break
      case 'trial':
        baseUrl = VITE_SERVER_BASEURL__WEIXIN_TRIAL || baseUrl
        break
      case 'release':
        baseUrl = VITE_SERVER_BASEURL__WEIXIN_RELEASE || baseUrl
        break
    }
  }

  return baseUrl
}

/**
 * Theo môi trường hiện tại của ứng dụng WeChat, hãy xác định UPLOAD_BASEURL cần lấy
 */
export function getEnvBaseUploadUrl() {
  // Yêu cầu địa chỉ cơ sở
  let baseUploadUrl = import.meta.env.VITE_UPLOAD_BASEURL

  const VITE_UPLOAD_BASEURL__WEIXIN_DEVELOP = 'https://ukw0y1.laf.run/upload'
  const VITE_UPLOAD_BASEURL__WEIXIN_TRIAL = 'https://ukw0y1.laf.run/upload'
  const VITE_UPLOAD_BASEURL__WEIXIN_RELEASE = 'https://ukw0y1.laf.run/upload'

  // Phân biệt môi trường applet WeChat
  if (isMpWeixin) {
    const {
      miniProgram: { envVersion },
    } = uni.getAccountInfoSync()

    switch (envVersion) {
      case 'develop':
        baseUploadUrl = VITE_UPLOAD_BASEURL__WEIXIN_DEVELOP || baseUploadUrl
        break
      case 'trial':
        baseUploadUrl = VITE_UPLOAD_BASEURL__WEIXIN_TRIAL || baseUploadUrl
        break
      case 'release':
        baseUploadUrl = VITE_UPLOAD_BASEURL__WEIXIN_RELEASE || baseUploadUrl
        break
    }
  }

  return baseUploadUrl
}

/**
 * Tạo cặp khóa SM2 (định dạng hex)
 * @returns đối tượng {object} chứa khóa chung và khóa riêng
 */
export function generateSm2KeyPairHex() {
  // Tạo cặp khóa SM2 bằng thư viện sm-crypto
  const sm2 = smCrypto.sm2
  const keypair = sm2.generateKeyPairHex()

  return {
    publicKey: keypair.publicKey,
    privateKey: keypair.privateKey,
    clientPublicKey: keypair.publicKey, // Khóa công khai của khách hàng
    clientPrivateKey: keypair.privateKey, // Khóa riêng của khách hàng
  }
}

/**
 * Mã hóa khóa công khai SM2
 * @param {string} publicKey Khóa công khai (định dạng hex)
 * @param {string} plainText văn bản thuần túy
 * @returns {string} Văn bản mã hóa được mã hóa (định dạng thập lục phân)
 */
export function sm2Encrypt(publicKey: string, plainText: string): string {
  if (!publicKey) {
    throw new Error('公钥不能为null或undefined')
  }

  if (!plainText) {
    throw new Error('明文不能为空')
  }

  const sm2 = smCrypto.sm2
  // Mã hóa SM2, thêm tiền tố 04 để biểu thị khóa chung không nén
  const encrypted = sm2.doEncrypt(plainText, publicKey, 1)
  // Chuyển đổi sang định dạng thập lục phân (phù hợp với phần phụ trợ, thêm tiền tố 04)
  const result = `04${encrypted}`

  return result
}

/**
 * Giải mã khóa riêng SM2
 * @param {string} privateKey Khóa riêng (định dạng hex)
 * @param {string} cipherText Bản mã (định dạng hex)
 * @returns {string} văn bản gốc đã được giải mã
 */
export function sm2Decrypt(privateKey: string, cipherText: string): string {
  const sm2 = smCrypto.sm2
  // Xóa tiền tố 04 (phù hợp với phần phụ trợ)
  const dataWithoutPrefix = cipherText.startsWith('04') ? cipherText.substring(2) : cipherText
  // giải mã SM2
  return sm2.doDecrypt(dataWithoutPrefix, privateKey, 1)
}

type AnyFunction = (...args: any[]) => any

interface DebouncedFunction extends AnyFunction {
  cancel: () => void
}

/**
 * Chức năng chống rung
 * @param fn Chức năng chống rung
 * @param delay Thời gian trễ (mili giây), mặc định 500ms
 * @param immediate Có thực thi ngay lập tức hay không, mặc định là sai
 * Chức năng @returns sau khi xử lý chống rung
 */
export function debounce<T extends AnyFunction>(
  fn: T,
  delay = 500,
  immediate = false,
): DebouncedFunction {
  let timer: ReturnType<typeof setTimeout> | null = null

  const debounced = function (this: any, ...args: Parameters<T>) {
    if (timer) {
      clearTimeout(timer)
    }

    if (immediate && !timer) {
      fn.apply(this, args)
    }

    timer = setTimeout(() => {
      if (!immediate) {
        fn.apply(this, args)
      }
      timer = null
    }, delay)
  } as DebouncedFunction

  debounced.cancel = () => {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  return debounced
}

type DeepCloneTarget = string | number | boolean | null | undefined | object

/**
 * phương pháp sao chép sâu
 * @param target Mục tiêu cần sao chép
 * @returns đối tượng mới sau khi sao chép
 */
export function deepClone<T extends DeepCloneTarget>(target: T): T {
  if (target === null || typeof target !== 'object') {
    return target
  }

  if (target instanceof Date) {
    return new Date(target.getTime()) as any
  }

  if (Array.isArray(target)) {
    return target.map(item => deepClone(item)) as any
  }

  if (target instanceof Object) {
    const clonedObj = {} as T
    for (const key in target) {
      if (Object.prototype.hasOwnProperty.call(target, key)) {
        (clonedObj as any)[key] = deepClone((target as any)[key])
      }
    }
    return clonedObj
  }

  return target
}
