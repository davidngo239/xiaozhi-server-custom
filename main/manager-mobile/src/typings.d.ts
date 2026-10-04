// Các loại được sử dụng trên toàn cầu được đặt ở đây.

declare global {
  interface IResData<T> {
    code: number
    msg: string
    data: T
  }

  // uni.uploadTham số tải lên tệp
  interface IUniUploadFileOptions {
    file?: File
    files?: UniApp.UploadFileOptionFiles[]
    filePath?: string
    name?: string
    formData?: any
  }

  interface IUserInfo {
    nickname?: string
    avatar?: string
    /** Openid của WeChat, không phải WeChat không có trường này */
    openid?: string
    token?: string
  }
}

export {} // Ngăn ngừa ô nhiễm mô-đun
