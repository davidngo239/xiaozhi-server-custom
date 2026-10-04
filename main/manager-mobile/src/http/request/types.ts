// Dạng phản hồi chung
export interface IResponse<T = any> {
  code: number | string
  data: T
  msg: string
  status: string | number
}

// Tham số yêu cầu phân trang
export interface PageParams {
  page: number
  pageSize: number
  [key: string]: any
}

// Dữ liệu phản hồi được phân trang
export interface PageResult<T> {
  list: T[]
  total: number
  page: number
  pageSize: number
}
