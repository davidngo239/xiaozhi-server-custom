// định nghĩa liệt kê

export enum TestEnum {
  A = '1',
  B = '2',
}

// uni.uploadTham số tải lên tệp
export interface IUniUploadFileOptions {
  file?: File
  files?: UniApp.UploadFileOptionFiles[]
  filePath?: string
  name?: string
  formData?: any
}
