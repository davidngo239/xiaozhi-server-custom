// # Sau khi thực hiện `pnpm nâng cấp`, các phần phụ thuộc liên quan đến `uniapp` sẽ được nâng cấp
// # Sau khi nâng cấp, nhiều phần phụ thuộc vô dụng sẽ được tự động thêm vào, cần xóa để giảm kích thước của gói phụ thuộc.
// # Chỉ cần thực hiện lệnh sau

const { exec } = require('node:child_process')

// Xác định lệnh cần thực hiện
const dependencies = [
  '@dcloudio/uni-app-harmony',
  // VIỆC CẦN LÀM: Nếu bạn không cần applet cho một nền tảng nhất định, vui lòng xóa nó theo cách thủ công hoặc nhận xét nó.
  '@dcloudio/uni-mp-alipay',
  '@dcloudio/uni-mp-baidu',
  '@dcloudio/uni-mp-jd',
  '@dcloudio/uni-mp-kuaishou',
  '@dcloudio/uni-mp-lark',
  '@dcloudio/uni-mp-qq',
  '@dcloudio/uni-mp-toutiao',
  '@dcloudio/uni-mp-xhs',
  '@dcloudio/uni-quickapp-webview',
  // Mẫu i18n cần bình luận như sau
  'vue-i18n',
]

// Sử dụng exec để thực thi lệnh
exec(`pnpm un ${dependencies.join(' ')}`, (error, stdout, stderr) => {
  if (error) {
    // Nếu có lỗi thì in thông báo lỗi
    console.error(`执行出错: ${error}`)
    return
  }
  // In đầu ra bình thường
  console.log(`stdout: ${stdout}`)
  // Nếu có bất kỳ lỗi nào xảy ra, hãy in nó ra.
  console.error(`stderr: ${stderr}`)
})
