/// <reference type="vite/client" />
/// <reference types="vite-svg-loader" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'

  const component: DefineComponent<{}, {}, any>
  export default component
}

interface ImportMetaEnv {
  /** Tiêu đề trang web, tên ứng dụng */
  readonly VITE_APP_TITLE: string
  /** Số cổng dịch vụ */
  readonly VITE_SERVER_PORT: string
  /** Địa chỉ giao diện phụ trợ */
  readonly VITE_SERVER_BASEURL: string
  /** H5 có yêu cầu đại lý không */
  readonly VITE_APP_PROXY: 'true' | 'false'
  /** H5 có cần proxy không? Nếu vậy thì có tiền tố */
  readonly VITE_APP_PROXY_PREFIX: string // Thông thường /api
  /** Tải lên địa chỉ hình ảnh */
  readonly VITE_UPLOAD_BASEURL: string
  /** Có xóa bảng điều khiển không */
  readonly VITE_DELETE_CONSOLE: string
  // Nhiều biến môi trường hơn...
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare const __VITE_APP_PROXY__: 'true' | 'false'
declare const __UNI_PLATFORM__: 'app' | 'h5' | 'mp-alipay' | 'mp-baidu' | 'mp-kuaishou' | 'mp-lark' | 'mp-qq' | 'mp-tiktok' | 'mp-weixin' | 'mp-xiaochengxu'
