import { http } from '@/http/request/alova'

// Kiểu dữ liệu giao diện đăng nhập
export interface LoginData {
  username: string
  password: string
  captchaId: string
  areaCode?: string
  mobile?: string
}

// Kiểu dữ liệu phản hồi đăng nhập
export interface LoginResponse {
  token: string
  expire: number
  clientHash: string
}

// Kiểu dữ liệu phản hồi mã xác minh
export interface CaptchaResponse {
  captchaId: string
  captchaImage: string
}

// Nhận mã xác minh
export function getCaptcha(uuid: string) {
  return http.Get<string>('/user/captcha', {
    params: { uuid },
    meta: {
      ignoreAuth: true,
      toast: false,
    },
  })
}

// Đăng nhập người dùng
export function login(data: LoginData) {
  return http.Post<LoginResponse>('/user/login', data, {
    meta: {
      ignoreAuth: true,
      toast: true,
    },
  })
}

// Kiểu dữ liệu phản hồi thông tin người dùng
export interface UserInfo {
  id: number
  username: string
  realName: string
  email: string
  mobile: string
  status: number
  superAdmin: number
}

// Kiểu dữ liệu phản hồi cấu hình công khai
export interface PublicConfig {
  enableMobileRegister: boolean
  version: string
  year: string
  allowUserRegister: boolean
  mobileAreaList: Array<{
    name: string
    key: string
  }>
  beianIcpNum: string
  beianGaNum: string
  name: string
  sm2PublicKey: string
}

// Lấy thông tin người dùng
export function getUserInfo() {
  return http.Get<UserInfo>('/user/info', {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
  })
}

// Nhận cấu hình công khai
export function getPublicConfig() {
  return http.Get<PublicConfig>('/user/pub-config', {
    meta: {
      ignoreAuth: true,
      toast: false,
    },
  })
}

// Đăng ký kiểu dữ liệu
export interface RegisterData {
  username: string
  password: string
  captchaId: string
  areaCode: string
  mobile: string
  mobileCaptcha: string
}

// Gửi mã xác minh qua SMS
export function sendSmsCode(data: {
  phone: string
  captcha: string
  captchaId: string
}) {
  return http.Post('/user/smsVerification', data, {
    meta: {
      ignoreAuth: true,
      toast: false,
    },
  })
}

// Đăng ký người dùng
export function register(data: RegisterData) {
  return http.Post('/user/register', data, {
    meta: {
      ignoreAuth: true,
      toast: true,
    },
  })
}

// Quên kiểu dữ liệu mật khẩu
export interface ForgotPasswordData {
  phone: string
  code: string
  password: string
  captchaId: string
}

// Quên mật khẩu (lấy lại mật khẩu)
export function retrievePassword(data: ForgotPasswordData) {
  return http.Put('/user/retrieve-password', data, {
    meta: {
      ignoreAuth: true,
      toast: true,
    },
  })
}
