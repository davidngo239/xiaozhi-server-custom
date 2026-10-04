import type { Ref } from 'vue'

interface IUseRequestOptions<T> {
  /** Có thực hiện ngay không */
  immediate?: boolean
  /** Dữ liệu khởi tạo */
  initialData?: T
}

interface IUseRequestReturn<T> {
  loading: Ref<boolean>
  error: Ref<boolean | Error>
  data: Ref<T | undefined>
  run: () => Promise<T | undefined>
}

/**
 * useRequest là một hook yêu cầu tùy chỉnh để xử lý các yêu cầu và phản hồi không đồng bộ.
 * @param func Một hàm thực hiện các yêu cầu không đồng bộ và trả về Promise chứa dữ liệu phản hồi.
 * @param options Đối tượng {ngay lập tức, dữ liệu ban đầu} chứa các tùy chọn yêu cầu.
 * @param options.immediate Có thực hiện yêu cầu ngay lập tức hay không, mặc định là sai.
 * @param options.initialData dữ liệu khởi tạo, mặc định là không xác định.
 * @returns trả về một đối tượng {loading, error, data, run}, chứa trạng thái tải được yêu cầu, thông tin lỗi, dữ liệu phản hồi và chức năng kích hoạt yêu cầu theo cách thủ công.
 */
export default function useRequest<T>(
  func: () => Promise<IResData<T>>,
  options: IUseRequestOptions<T> = { immediate: false },
): IUseRequestReturn<T> {
  const loading = ref(false)
  const error = ref(false)
  const data = ref<T | undefined>(options.initialData) as Ref<T | undefined>
  const run = async () => {
    loading.value = true
    return func()
      .then((res) => {
        data.value = res.data
        error.value = false
        return data.value
      })
      .catch((err) => {
        error.value = err
        throw err
      })
      .finally(() => {
        loading.value = false
      })
  }

  options.immediate && run()
  return { loading, error, data, run }
}
