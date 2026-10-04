import type { uniappRequestAdapter } from '@alova/adapter-uniapp'
import type { IResponse } from './types'
import type { Language } from '@/store/lang'
import AdapterUniapp from '@alova/adapter-uniapp'
import { createAlova } from 'alova'
import { createServerTokenAuthentication } from 'alova/client'
import VueHook from 'alova/vue'
import { getEnvBaseUrl } from '@/utils'
import { toast } from '@/utils/toast'
import { ContentTypeEnum, ResultEnum, ShowMessage } from './enum'

// Ánh xạ ngôn ngữ, được sử dụng để đặt tiêu đề Ngôn ngữ chấp nhận
const langMap: Record<Language, string> = {
  zh_CN: 'zh-CN',
  en: 'en-US',
  zh_TW: 'zh-TW',
  de: 'de',
  vi: 'vi',
  pt_BR: 'pt-BR',
}

/**
 * Tạo phiên bản yêu cầu
 */
const { onAuthRequired, onResponseRefreshToken } = createServerTokenAuthentication<
  typeof VueHook,
  typeof uniappRequestAdapter
>({
  refreshTokenOnError: {
    isExpired: (error) => {
      return error.response?.status === ResultEnum.Unauthorized
    },
    handler: async () => {
      try {
        // await authLogin();
      }
      catch (error) {
        // Chuyển sang trang đăng nhập
        await uni.reLaunch({ url: '/pages/login/index' })
        throw error
      }
    },
  },
})

/**
 * ví dụ yêu cầu alova
 */
const alovaInstance = createAlova({
  baseURL: getEnvBaseUrl(),
  ...AdapterUniapp(),
  timeout: 5000,
  statesHook: VueHook,

  beforeRequest: onAuthRequired((method) => {
    // h5 tự động lấy baseURL mới nhất và đảm bảo rằng địa chỉ máy chủ do người dùng đặt được sử dụng
    const currentBaseUrl = getEnvBaseUrl()
    if (currentBaseUrl !== method.baseURL) {
      method.baseURL = currentBaseUrl
    }

    // Kiểm tra lỗi nội dung hỗn hợp (trang HTTPS yêu cầu giao diện HTTP)
    const currentProtocol = typeof window !== 'undefined' && window.location.protocol
    const requestProtocol = method.baseURL?.split(':')[0]
    const currentLang = langMap[uni.getStorageSync('app_language') as Language || 'vi']
    if (currentProtocol === 'https:' && requestProtocol === 'http') {
      const errorMessage = '无法配置http协议地址,请检查接口地址'
      throw new Error(errorMessage)
    }

    // Đặt loại nội dung mặc định
    method.config.headers = {
      'Content-Type': ContentTypeEnum.JSON,
      'Accept': 'application/json, text/plain, */*',
      'Accept-language': currentLang,
      ...method.config.headers,
    }

    const { config } = method
    const ignoreAuth = config.meta?.ignoreAuth
    console.log('ignoreAuth===>', ignoreAuth)

    // Xử lý thông tin xác thực
    if (!ignoreAuth) {
      const authInfo = JSON.parse(uni.getStorageSync('token') || '{}')
      if (!authInfo.token) {
        // Chuyển đến trang đăng nhập
        uni.reLaunch({ url: '/pages/login/index' })
        throw new Error('[请求错误]：未登录')
      }
      // Thêm tiêu đề ủy quyền
      method.config.headers.Authorization = `Bearer ${authInfo.token}`
    }

    // Xử lý tên miền động
    if (config.meta?.domain) {
      method.baseURL = config.meta.domain
      console.log('当前域名', method.baseURL)
    }
  }),

  responded: onResponseRefreshToken((response, method) => {
    const { config } = method
    const { requestType } = config
    const {
      statusCode,
      data: rawData,
      errMsg,
    } = response as UniNamespace.RequestSuccessCallbackResult

    console.log(response)

    // Xử lý các loại yêu cầu đặc biệt (tải lên/tải xuống)
    if (requestType === 'upload' || requestType === 'download') {
      return response
    }

    // Xử lý lỗi mã trạng thái HTTP
    if (statusCode !== 200) {
      const errorMessage = ShowMessage(statusCode) || `HTTP请求错误[${statusCode}]`
      console.error('errorMessage===>', errorMessage)
      toast.error(errorMessage)
      throw new Error(`${errorMessage}：${errMsg}`)
    }

    // Xử lý lỗi logic nghiệp vụ
    const { code, msg, data } = rawData as IResponse
    if (code !== ResultEnum.Success) {
      // Kiểm tra xem mã thông báo có hợp lệ không
      if (code === ResultEnum.Unauthorized) {
        // Xóa mã thông báo và chuyển đến trang đăng nhập
        uni.removeStorageSync('token')
        uni.reLaunch({ url: '/pages/login/index' })
        throw new Error(`请求错误[${code}]：${msg}`)
      }

      if (config.meta?.isExposeError) {
        return Promise.reject(msg)
      }

      if (config.meta?.toast !== false) {
        toast.warning(msg)
      }
      throw new Error(`请求错误[${code}]：${msg}`)
    }
    // Xử lý phản hồi thành công và trả lại dữ liệu kinh doanh
    return data
  }),
})

export const http = alovaInstance
