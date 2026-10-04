import { getEnvBaseUrl } from './index'
import { toast } from './toast'

/**
 * Ví dụ sử dụng chức năng hook tải lên tệp
 * @example
 * const { đang tải, lỗi, dữ liệu, tiến trình, chạy } = useUpload<IUploadResult>(
 *   uploadUrl,
 *   {},
 *   {
 *     maxSize: 5, // Tối đa 5MB
 *     sourceType: ['album'], // Chỉ hỗ trợ lựa chọn từ album
 *     onProgress: (p) => console.log(`Tiến trình tải lên: ${p}%`),
 *     onSuccess: (res) => console.log('Tải lên thành công', res),
 *     onError: (err) => console.error('Tải lên không thành công', err),
 *   },
 * )
 */

/**
 * Cấu hình URL để tải tập tin lên
 */
export const uploadFileUrl = {
  /** Địa chỉ tải lên hình đại diện của người dùng (đọc động BaseURL hiện có hiệu lực) */
  get USER_AVATAR() {
    return `${getEnvBaseUrl()}/user/avatar`
  },
}

/**
 * Chức năng tải lên tệp phổ quát (hỗ trợ truyền trực tiếp vào đường dẫn tệp)
 * @param url Tải lên địa chỉ
 * @param filePath đường dẫn tệp cục bộ
 * @param formData Dữ liệu biểu mẫu bổ sung
 * @param options Tùy chọn tải lên
 */
export function useFileUpload<T = string>(url: string, filePath: string, formData: Record<string, any> = {}, options: Omit<UploadOptions, 'sourceType' | 'sizeType' | 'count'> = {}) {
  return useUpload<T>(
    url,
    formData,
    {
      ...options,
      sourceType: ['album'],
      sizeType: ['original'],
    },
    filePath,
  )
}

export interface UploadOptions {
  /** Số lượng hình ảnh tối đa có thể được chọn, mặc định là 1 */
  count?: number
  /** Kích thước của ảnh được chọn, ảnh gốc, ảnh nén */
  sizeType?: Array<'original' | 'compressed'>
  /** Chọn nguồn ảnh, album-album ảnh, camera-máy ảnh */
  sourceType?: Array<'album' | 'camera'>
  /** Giới hạn kích thước file, đơn vị: MB */
  maxSize?: number //
  /** Chức năng gọi lại tiến trình tải lên */
  onProgress?: (progress: number) => void
  /** Tải lên chức năng gọi lại thành công */
  onSuccess?: (res: Record<string, any>) => void
  /** Tải lên chức năng gọi lại thất bại */
  onError?: (err: Error | UniApp.GeneralCallbackResult) => void
  /** Tải lên chức năng gọi lại hoàn thành (bất kể thành công hay thất bại) */
  onComplete?: () => void
}

/**
 * Chức năng móc tải lên tập tin
 * @template T Kiểu dữ liệu được trả về sau khi tải lên thành công
 * @param url Tải lên địa chỉ
 * @param formData Dữ liệu biểu mẫu bổ sung
 * @param options Tùy chọn tải lên
 * @returns trạng thái tải lên và các đối tượng điều khiển
 */
export function useUpload<T = string>(url: string, formData: Record<string, any> = {}, options: UploadOptions = {},
  /** Truyền trực tiếp đường dẫn tệp, bỏ qua bộ chọn */
  directFilePath?: string) {
  /** Trạng thái tải lên */
  const loading = ref(false)
  /** Trạng thái lỗi tải lên */
  const error = ref(false)
  /** Dữ liệu phản hồi sau khi upload thành công */
  const data = ref<T>()
  /** Tiến trình tải lên (0-100) */
  const progress = ref(0)

  /** Giải cấu trúc các tùy chọn tải lên và đặt giá trị mặc định */
  const {
    /** Số lượng hình ảnh tối đa có thể được chọn */
    count = 1,
    /** Kích thước của hình ảnh đã chọn */
    sizeType = ['original', 'compressed'],
    /** Chọn nguồn ảnh */
    sourceType = ['album', 'camera'],
    /** Giới hạn kích thước tệp (MB) */
    maxSize = 10,
    /** Gọi lại tiến trình */
    onProgress,
    /** Gọi lại thành công */
    onSuccess,
    /** Gọi lại thất bại */
    onError,
    /** Gọi lại hoàn thành */
    onComplete,
  } = options

  /**
   * Kiểm tra xem kích thước tệp có vượt quá giới hạn không
   * @param size Kích thước tệp (byte)
   * @returns xem nó có vượt qua kiểm tra hay không
   */
  const checkFileSize = (size: number) => {
    const sizeInMB = size / 1024 / 1024
    if (sizeInMB > maxSize) {
      toast.warning(`文件大小不能超过${maxSize}MB`)
      return false
    }
    return true
  }
  /**
   * Lựa chọn và tải lên tập tin kích hoạt
   * Sử dụng các bộ chọn khác nhau tùy thuộc vào nền tảng:
   * - Chương trình mini WeChat sử dụng chooseMedia
   * - Các nền tảng khác sử dụng chooseImage
   */
  const run = () => {
    if (directFilePath) {
      // Sử dụng trực tiếp đường dẫn tệp đã truyền
      loading.value = true
      progress.value = 0
      uploadFile<T>({
        url,
        tempFilePath: directFilePath,
        formData,
        data,
        error,
        loading,
        progress,
        onProgress,
        onSuccess,
        onError,
        onComplete,
      })
      return
    }

    // #ifdef MP-WEIXIN
    // Sử dụng API chooseMedia trong môi trường chương trình mini WeChat
    uni.chooseMedia({
      count,
      mediaType: ['image'], // Chỉ hỗ trợ các loại hình ảnh
      sourceType,
      success: (res) => {
        const file = res.tempFiles[0]
        // Kiểm tra xem kích thước tệp có đáp ứng giới hạn không
        if (!checkFileSize(file.size))
          return

        // Bắt đầu tải lên
        loading.value = true
        progress.value = 0
        uploadFile<T>({
          url,
          tempFilePath: file.tempFilePath,
          formData,
          data,
          error,
          loading,
          progress,
          onProgress,
          onSuccess,
          onError,
          onComplete,
        })
      },
      fail: (err) => {
        console.error('选择媒体文件失败:', err)
        error.value = true
        onError?.(err)
      },
    })
    // #endif

    // #ifndef MP-WEIXIN
    // Sử dụng API chooseImage trong môi trường chương trình nhỏ không phải WeChat
    uni.chooseImage({
      count,
      sizeType,
      sourceType,
      success: (res) => {
        console.log('选择图片成功:', res)

        // Bắt đầu tải lên
        loading.value = true
        progress.value = 0
        uploadFile<T>({
          url,
          tempFilePath: res.tempFilePaths[0],
          formData,
          data,
          error,
          loading,
          progress,
          onProgress,
          onSuccess,
          onError,
          onComplete,
        })
      },
      fail: (err) => {
        console.error('选择图片失败:', err)
        error.value = true
        onError?.(err)
      },
    })
    // #endif
  }

  return { loading, error, data, progress, run }
}

/**
 * Giao diện tùy chọn upload file
 * @template T Kiểu dữ liệu được trả về sau khi tải lên thành công
 */
interface UploadFileOptions<T> {
  /** Tải lên địa chỉ */
  url: string
  /** Đường dẫn tệp tạm thời */
  tempFilePath: string
  /** Dữ liệu biểu mẫu bổ sung */
  formData: Record<string, any>
  /** Dữ liệu phản hồi sau khi upload thành công */
  data: Ref<T | undefined>
  /** Trạng thái lỗi tải lên */
  error: Ref<boolean>
  /** Trạng thái tải lên */
  loading: Ref<boolean>
  /** Tiến trình tải lên (0-100) */
  progress: Ref<number>
  /** Gọi lại tiến trình tải lên */
  onProgress?: (progress: number) => void
  /** Tải lên gọi lại thành công */
  onSuccess?: (res: Record<string, any>) => void
  /** Tải lên lệnh gọi lại thất bại */
  onError?: (err: Error | UniApp.GeneralCallbackResult) => void
  /** Tải lên lệnh gọi lại hoàn thành */
  onComplete?: () => void
}

/**
 * Thực hiện tải tập tin lên
 * @template T Kiểu dữ liệu được trả về sau khi tải lên thành công
 * @param options Tùy chọn tải lên
 */
function uploadFile<T>({
  url,
  tempFilePath,
  formData,
  data,
  error,
  loading,
  progress,
  onProgress,
  onSuccess,
  onError,
  onComplete,
}: UploadFileOptions<T>) {
  try {
    // Tạo tác vụ tải lên
    const uploadTask = uni.uploadFile({
      url,
      filePath: tempFilePath,
      name: 'file', // Khóa tương ứng với tập tin
      formData,
      header: {
        // Trong môi trường H5, không cần thiết lập Content-Type theo cách thủ công, cho phép trình duyệt tự động xử lý định dạng nhiều phần.
        // #ifndef H5
        'Content-Type': 'multipart/form-data',
        // #endif
      },
      // Đảm bảo tên tệp là hợp pháp
      success: (uploadFileRes) => {
        console.log('上传文件成功:', uploadFileRes)
        try {
          // Phân tích dữ liệu phản hồi
          const { data: _data } = JSON.parse(uploadFileRes.data)
          // Tải lên thành công
          data.value = _data as T
          onSuccess?.(_data)
        }
        catch (err) {
          // Lỗi phân tích phản hồi
          console.error('解析上传响应失败:', err)
          error.value = true
          onError?.(new Error('上传响应解析失败'))
        }
      },
      fail: (err) => {
        // Yêu cầu tải lên không thành công
        console.error('上传文件失败:', err)
        error.value = true
        onError?.(err)
      },
      complete: () => {
        // Thực hiện bất kể thành công hay thất bại
        loading.value = false
        onComplete?.()
      },
    })

    // Theo dõi tiến trình tải lên
    uploadTask.onProgressUpdate((res) => {
      progress.value = res.progress
      onProgress?.(res.progress)
    })
  }
  catch (err) {
    // Không tạo được tác vụ tải lên
    console.error('创建上传任务失败:', err)
    error.value = true
    loading.value = false
    onError?.(new Error('创建上传任务失败'))
  }
}
