export enum ResultEnum {
  Success = 0, // sự thành công
  Error = 400, // Lỗi
  Unauthorized = 401, // trái phép
  Forbidden = 403, // Bị cấm (trước đây bị cấm)
  NotFound = 404, // Không tìm thấy (trước đây là notFound)
  MethodNotAllowed = 405, // Phương thức không được phép (trước đây là phương thứcNotAllowed)
  RequestTimeout = 408, // Hết thời gian yêu cầu (trước đây là requestTimeout)
  InternalServerError = 500, // ServerError (trước đây là InternalServerError)
  NotImplemented = 501, // Chưa được triển khai (chưa được triển khai)
  BadGateway = 502, // Cổng xấu (là badGateway)
  ServiceUnavailable = 503, // Dịch vụ không khả dụng (trước đây là dịch vụKhông khả dụng)
  GatewayTimeout = 504, // Hết thời gian chờ cổng (trước đây là cổngTimeout)
  HttpVersionNotSupported = 505, // Phiên bản HTTP không được hỗ trợ (trước đây là httpVersionNotSupported)
  MixedContent = 600, // Lỗi nội dung hỗn hợp (trang HTTPS yêu cầu giao diện HTTP)
}
export enum ContentTypeEnum {
  JSON = 'application/json;charset=UTF-8',
  FORM_URLENCODED = 'application/x-www-form-urlencoded;charset=UTF-8',
  FORM_DATA = 'multipart/form-data;charset=UTF-8',
}
/**
 * Tạo thông tin lỗi tương ứng dựa trên mã trạng thái
 * @param {number|string} status mã trạng thái
 * @returns thông báo lỗi {string}
 */
export function ShowMessage(status: number | string): string {
  let message: string
  switch (status) {
    case 400:
      message = '请求错误(400)'
      break
    case 401:
      message = '未授权，请重新登录(401)'
      break
    case 403:
      message = '拒绝访问(403)'
      break
    case 404:
      message = '请求出错(404)'
      break
    case 408:
      message = '请求超时(408)'
      break
    case 500:
      message = '服务器错误(500)'
      break
    case 501:
      message = '服务未实现(501)'
      break
    case 502:
      message = '网络错误(502)'
      break
    case 503:
      message = '服务不可用(503)'
      break
    case 504:
      message = '网络超时(504)'
      break
    case 505:
      message = 'HTTP版本不受支持(505)'
      break
    case 600:
      message = '混合内容错误(600)'
      break
    default:
      message = `连接出错(${status})!`
  }
  return `${message}，请检查网络或联系管理员！`
}
