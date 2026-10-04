/**
 * trạng thái thanh tab, thêm storageSync để đảm bảo đúng trang tabbar khi làm mới trình duyệt
 * Sử dụng trạng thái đơn giản phản ứng thay vì trạng thái toàn cầu pinia
 */
export const tabbarStore = reactive({
  curIdx: uni.getStorageSync('app-tabbar-index') || 0,
  setCurIdx(idx: number) {
    this.curIdx = idx
    uni.setStorageSync('app-tabbar-index', idx)
  },
})
