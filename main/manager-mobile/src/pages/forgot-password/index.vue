<route lang="jsonc" type="page">
{
  "layout": "default",
  "style": {
    "navigationStyle": "custom",
    "navigationBarTitleText": "ForgotPassword"
  }
}
</route>

<script lang="ts" setup>
import { onLoad } from '@dcloudio/uni-app'
import { computed, onMounted, ref } from 'vue'
// Giao diện API nhập
import { retrievePassword, sendSmsCode } from '@/api/auth'
// Nhập các chức năng liên quan đến quốc tế hóa
import { initI18n, t } from '@/i18n'
import { useConfigStore } from '@/store'
import { getEnvBaseUrl, sm2Encrypt } from '@/utils'
import { toast } from '@/utils/toast'

// Lấy khoảng cách từ ranh giới màn hình tới vùng an toàn
let safeAreaInsets
let systemInfo

// #ifdef MP-WEIXIN
// Ứng dụng WeChat sử dụng API mới
systemInfo = uni.getWindowInfo()
safeAreaInsets = systemInfo.safeArea
  ? {
      top: systemInfo.safeArea.top,
      right: systemInfo.windowWidth - systemInfo.safeArea.right,
      bottom: systemInfo.windowHeight - systemInfo.safeArea.bottom,
      left: systemInfo.safeArea.left,
    }
  : null
// #endif

// #ifndef MP-WEIXIN
// Các nền tảng khác tiếp tục sử dụng API uni
systemInfo = uni.getSystemInfoSync()
safeAreaInsets = systemInfo.safeAreaInsets
// #endif

// dữ liệu biểu mẫu
interface ForgotPasswordData {
  mobile: string
  captcha: string
  captchaId: string
  mobileCaptcha: string
  newPassword: string
  confirmPassword: string
  areaCode: string
}

const formData = ref<ForgotPasswordData>({
  mobile: '',
  captcha: '',
  captchaId: '',
  mobileCaptcha: '',
  newPassword: '',
  confirmPassword: '',
  areaCode: '+86',
})

// Hình ảnh mã xác minh
const captchaImage = ref('')
const loading = ref(false)

// Nhận cửa hàng cấu hình
const configStore = useConfigStore()

// Trạng thái của bảng hành động mã vùng
const showAreaCodeSheet = ref(false)
const selectedAreaCode = ref('+86')
// Đếm ngược mã xác minh SMS
const smsCountdown = ref(0)
const smsLoading = ref(false)
const areaCodeList = computed(() =>
  (configStore.config.mobileAreaList || []).map((item) => {
    return {
      value: item.key,
      label: `${item.name} (${item.key})`,
    }
  }),
)

const canSendMobileCaptcha = computed(() => {
  const mobile = formData.value.mobile
  const phoneRegex = /^1[3-9]\d{9}$/
  return phoneRegex.test(mobile) && smsCountdown.value === 0
})

// Khóa công khai SM2
const sm2PublicKey = computed(() => {
  return configStore.config.sm2PublicKey
})

// Mở cửa sổ bật lên chọn mã vùng
function openAreaCodeSheet() {
  showAreaCodeSheet.value = true
}

// Chọn mã vùng
function selectAreaCode(item: { value: string, label: string }) {
  selectedAreaCode.value = item.value
  formData.value.areaCode = item.value
  showAreaCodeSheet.value = false
}

// Đóng cửa sổ bật lên chọn mã vùng
function closeAreaCodeSheet() {
  showAreaCodeSheet.value = false
}

// Tạo UUID
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

// Nhận mã xác minh đồ họa
async function refreshCaptcha() {
  const uuid = generateUUID()
  formData.value.captchaId = uuid
  captchaImage.value = `${getEnvBaseUrl()}/user/captcha?uuid=${uuid}&t=${Date.now()}`
}

// Gửi mã xác minh qua SMS
async function handleSendSmsCode() {
  // Xác minh định dạng số điện thoại di động
  const phoneRegex = /^1[3-9]\d{9}$/
  if (!phoneRegex.test(formData.value.mobile)) {
    toast.warning(t('retrievePassword.inputCorrectMobile'))
    return
  }

  if (!formData.value.captcha) {
    toast.warning(t('retrievePassword.captchaRequired'))
    return
  }

  try {
    smsLoading.value = true
    // Chuyển đổi số điện thoại di động sang định dạng quốc tế
    const internationalPhone = formData.value.areaCode + formData.value.mobile
    // Gọi API để gửi mã xác minh qua SMS
    await sendSmsCode({
      phone: internationalPhone,
      captcha: formData.value.captcha,
      captchaId: formData.value.captchaId,
    })

    toast.success(t('retrievePassword.captchaSendSuccess'))

    // Bắt đầu đếm ngược
    smsCountdown.value = 60
    const timer = setInterval(() => {
      smsCountdown.value--
      if (smsCountdown.value <= 0) {
        clearInterval(timer)
      }
    }, 1000)
  }
  catch (error: any) {
    // Xử lý lỗi mã xác minh
    if (error.message.includes('请求错误[10067]')) {
      toast.warning(t('login.captchaError'))
    }
    // Không thể gửi và lấy lại mã xác minh đồ họa
    refreshCaptcha()
  }
  finally {
    smsLoading.value = false
  }
}

// đặt lại mật khẩu
async function handleResetPassword() {
  // xác nhận mẫu
  if (!formData.value.mobile) {
    toast.warning(t('retrievePassword.mobileRequired'))
    return
  }

  // Xác minh định dạng số điện thoại di động
  const phoneRegex = /^1[3-9]\d{9}$/
  if (!phoneRegex.test(formData.value.mobile)) {
    toast.warning(t('retrievePassword.inputCorrectMobile'))
    return
  }

  // Chuyển đổi số điện thoại di động sang định dạng quốc tế
  const internationalPhone = formData.value.areaCode + formData.value.mobile

  if (!formData.value.captcha) {
    toast.warning(t('retrievePassword.captchaRequired'))
    return
  }

  if (!formData.value.mobileCaptcha) {
    toast.warning(t('retrievePassword.mobileCaptchaRequired'))
    return
  }

  if (!formData.value.newPassword) {
    toast.warning(t('retrievePassword.newPasswordRequired'))
    return
  }

  if (!formData.value.confirmPassword) {
    toast.warning(t('retrievePassword.confirmNewPasswordRequired'))
    return
  }

  if (formData.value.newPassword !== formData.value.confirmPassword) {
    toast.warning(t('retrievePassword.passwordsNotMatch'))
    return
  }

  try {
    loading.value = true

    // Kiểm tra xem khóa công khai SM2 đã được cấu hình chưa
    if (!sm2PublicKey.value) {
      toast.warning(t('sm2.publicKeyNotConfigured'))
      return
    }

    // Mật khẩu được mã hóa
    let encryptedPassword
    try {
      // Ghép mã xác minh đồ họa và mật khẩu mới để mã hóa
      const captchaAndPassword = formData.value.captcha + formData.value.newPassword
      encryptedPassword = sm2Encrypt(sm2PublicKey.value, captchaAndPassword)
    }
    catch (error) {
      console.error('密码加密失败:', error)
      toast.warning(t('sm2.encryptionFailed'))
      return
    }

    // API đặt lại mật khẩu cuộc gọi
    await retrievePassword({
      phone: internationalPhone,
      code: formData.value.mobileCaptcha,
      password: encryptedPassword,
      captchaId: formData.value.captchaId,
    })

    toast.success(t('retrievePassword.passwordUpdateSuccess'))

    // Chuyển đến trang đăng nhập
    setTimeout(() => {
      uni.redirectTo({
        url: '/pages/login/index',
      })
    }, 1000)
  }
  catch (error: any) {
    // Xử lý lỗi mã xác minh
    if (error.message.includes('请求错误[10067]')) {
      toast.warning(t('login.captchaError'))
    }
    // Đặt lại không thành công và lấy lại mã xác minh
    refreshCaptcha()
  }
  finally {
    loading.value = false
  }
}

// Quay lại đăng nhập
function goBack() {
  uni.redirectTo({
    url: '/pages/login/index',
  })
}

// Nhận mã xác minh khi tải trang
onLoad(() => {
  refreshCaptcha()
})

// Đảm bảo cấu hình được tải khi lắp thành phần
onMounted(async () => {
  if (!configStore.config.name) {
    try {
      await configStore.fetchPublicConfig()
    }
    catch (error) {
      console.error('获取配置失败:', error)
    }
  }
  // Khởi tạo quốc tế hóa
  initI18n()
})
</script>

<template>
  <view
    class="app-container box-border h-screen w-full"
    :style="{ paddingTop: `${safeAreaInsets?.top}px` }"
  >
    <view class="header">
      <view class="back-button" @click="goBack">
        <wd-icon name="arrow-left" custom-class="back-icon" />
      </view>
      <view class="logo-section">
        <wd-img :width="80" :height="80" round src="/static/logo.png" class="logo" />
        <text class="welcome-text">
          {{ t("retrievePassword.title") }}
        </text>
        <text class="subtitle">
          {{ t("retrievePassword.subtitle") }}
        </text>
      </view>
    </view>

    <view class="form-container">
      <view class="form">
        <!-- Nhập số điện thoại di động -->
        <view class="input-group">
          <view class="input-wrapper mobile-wrapper">
            <view class="area-code-selector" @click="openAreaCodeSheet">
              <text class="area-code-text">
                {{ selectedAreaCode }}
              </text>
              <wd-icon name="arrow-down" custom-class="area-code-arrow" />
            </view>
            <view class="mobile-input-wrapper">
              <wd-input
                v-model="formData.mobile"
                custom-class="styled-input"
                no-border
                :placeholder="t('retrievePassword.mobilePlaceholder')"
                type="number"
                :maxlength="11"
              />
            </view>
          </view>
        </view>

        <!-- Mã xác minh đồ họa -->
        <view class="input-group">
          <view class="input-wrapper captcha-wrapper">
            <wd-input
              v-model="formData.captcha"
              custom-class="styled-input"
              no-border
              :placeholder="t('retrievePassword.captchaPlaceholder')"
              :maxlength="6"
            />
            <view class="captcha-image" @click="refreshCaptcha">
              <image :src="captchaImage" class="captcha-img" />
            </view>
          </view>
        </view>

        <!-- Mã xác minh qua SMS -->
        <view class="input-group">
          <view class="input-wrapper sms-wrapper">
            <wd-input
              v-model="formData.mobileCaptcha"
              custom-class="styled-input"
              no-border
              :placeholder="t('retrievePassword.mobileCaptchaPlaceholder')"
              :maxlength="6"
            />
            <view class="sms-button" @click="handleSendSmsCode">
              <text class="sms-text">
                {{
                  smsCountdown > 0
                    ? `${smsCountdown}s`
                    : t("retrievePassword.getMobileCaptcha")
                }}
              </text>
            </view>
          </view>
        </view>

        <!-- Mật khẩu mới -->
        <view class="input-group">
          <view class="input-wrapper">
            <wd-input
              v-model="formData.newPassword"
              custom-class="styled-input"
              no-border
              :placeholder="t('retrievePassword.newPasswordPlaceholder')"
              show-password
              :maxlength="20"
            />
          </view>
        </view>

        <!-- Xác nhận mật khẩu mới -->
        <view class="input-group">
          <view class="input-wrapper">
            <wd-input
              v-model="formData.confirmPassword"
              custom-class="styled-input"
              no-border
              :placeholder="t('retrievePassword.confirmNewPasswordPlaceholder')"
              show-password
              :maxlength="20"
            />
          </view>
        </view>

        <!-- Nút đặt lại mật khẩu -->
        <view class="reset-btn" @click="handleResetPassword">
          {{ loading ? t("common.loading") : t("retrievePassword.resetButton") }}
        </view>

        <!-- Quay lại liên kết đăng nhập -->
        <view class="back-login-hint" @click="goBack">
          <text class="hint-text">
            {{ t("retrievePassword.goToLogin") }}
          </text>
        </view>
      </view>
    </view>

    <!-- Cửa sổ bật lên lựa chọn mã vùng -->
    <wd-action-sheet
      v-model="showAreaCodeSheet"
      :title="t('login.selectCountry')"
      :close-on-click-modal="true"
      @close="closeAreaCodeSheet"
    >
      <view class="area-code-sheet">
        <scroll-view scroll-y class="area-code-list">
          <view
            v-for="item in areaCodeList"
            :key="item.value"
            class="area-code-item"
            :class="{ selected: selectedAreaCode === item.value }"
            @click="selectAreaCode(item)"
          >
            <view class="area-info">
              <text class="area-name">
                {{ item.label }}
              </text>
            </view>
            <wd-icon
              v-if="selectedAreaCode === item.value"
              name="check"
              custom-class="check-icon"
            />
          </view>
        </scroll-view>
        <view class="sheet-footer">
          <wd-button
            type="primary"
            custom-class="confirm-btn"
            @click="closeAreaCodeSheet"
          >
            {{ t("login.confirm") }}
          </wd-button>
        </view>
      </view>
    </wd-action-sheet>
  </view>
</template>

<style lang="scss" scoped>
.app-container {
  background: linear-gradient(145deg, #f5f8fd, #6baaff, #9ebbfc, #f5f8fd);
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  min-height: 100vh;

  &::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
    animation: float 6s ease-in-out infinite;
  }
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0px) rotate(0deg);
  }
  50% {
    transform: translateY(-20px) rotate(180deg);
  }
}

.header {
  flex: 0 0 auto;
  min-height: 280rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 15% 0 40rpx 0;
  position: relative;

  .back-button {
    position: absolute;
    left: 30rpx;
    top: 50rpx;
    width: 60rpx;
    height: 60rpx;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.2);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    backdrop-filter: blur(10rpx);
    border: 1rpx solid rgba(255, 255, 255, 0.3);

    .back-icon {
      font-size: 32rpx;
      color: #ffffff;
    }
  }

  .logo-section {
    text-align: center;

    .logo {
      margin-bottom: 20rpx;
      box-shadow: 0 8rpx 32rpx rgba(0, 0, 0, 0.1);
    }

    .welcome-text {
      display: block;
      color: #ffffff;
      font-size: 40rpx;
      font-weight: 600;
      margin-bottom: 12rpx;
      text-shadow: 0 2rpx 4rpx rgba(0, 0, 0, 0.1);
    }

    .subtitle {
      display: block;
      color: rgba(255, 255, 255, 0.8);
      font-size: 26rpx;
      font-weight: 400;
    }
  }
}

.form-container {
  padding: 0 40rpx 40rpx 40rpx;
  flex: 1;
  display: flex;
  align-items: flex-start;

  .form {
    width: 100%;
    background: rgba(255, 255, 255, 0.95);
    border-radius: 24rpx;
    padding: 40rpx 30rpx 30rpx 30rpx;
    backdrop-filter: blur(10rpx);
    box-shadow: 0 20rpx 60rpx rgba(0, 0, 0, 0.1);
    border: 1rpx solid rgba(255, 255, 255, 0.2);
    max-height: calc(100vh - 350rpx);
    overflow-y: auto;

    .input-group {
      margin-bottom: 24rpx;

      .input-wrapper {
        position: relative;
        background: #f8f9fa;
        border-radius: 16rpx;
        padding: 20rpx 16rpx;
        border: 2rpx solid #e9ecef;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;

        &:focus-within {
          border-color: #667eea;
          background: #ffffff;
          box-shadow: 0 0 0 6rpx rgba(102, 126, 234, 0.1);
        }

        &.mobile-wrapper {
          padding: 0;
          background: transparent;
          border: none;
          display: flex;
          gap: 20rpx;

          .area-code-selector {
            flex: 0 0 160rpx;
            background: #f8f9fa;
            border-radius: 16rpx;
            padding: 20rpx 16rpx;
            border: 2rpx solid #e9ecef;
            height: 45rpx;
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            transition: all 0.3s ease;

            &:hover {
              border-color: #667eea;
              background: #ffffff;
              box-shadow: 0 0 0 6rpx rgba(102, 126, 234, 0.1);
            }

            .area-code-text {
              font-size: 28rpx;
              color: #333333;
              font-weight: 500;
            }

            :deep(.area-code-arrow) {
              font-size: 24rpx;
              color: #999999;
              transition: transform 0.3s ease;
            }
          }

          .mobile-input-wrapper {
            flex: 1;
            background: #f8f9fa;
            border-radius: 16rpx;
            padding: 20rpx 16rpx;
            border: 2rpx solid #e9ecef;
            transition: all 0.3s ease;

            &:focus-within {
              border-color: #667eea;
              background: #ffffff;
              box-shadow: 0 0 0 6rpx rgba(102, 126, 234, 0.1);
            }
          }
        }

        &.captcha-wrapper {
          .captcha-image {
            margin-left: 20rpx;
            width: 150rpx;
            height: 60rpx;
            border-radius: 8rpx;
            overflow: hidden;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #e9ecef;
            border: 1rpx solid #ddd;

            .captcha-img {
              width: 100%;
              height: 100%;
            }
          }
        }

        &.sms-wrapper {
          .sms-button {
            margin-left: 20rpx;
            width: 180rpx;
            height: 60rpx;
            border-radius: 12rpx;
            background: #667eea;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;

            &:active {
              background: #5a6fd8;
              transform: scale(0.98);
            }

            .sms-text {
              font-size: 24rpx;
              color: #ffffff;
              font-weight: 500;
            }
          }
        }

        :deep(.styled-input) {
          background: transparent !important;
          border: none !important;
          outline: none !important;
          font-size: 32rpx;
          color: #333333;
          flex: 1;

          &::placeholder {
            color: #999999;
            font-size: 28rpx;
          }
        }
      }
    }

    .reset-btn {
      width: 100%;
      height: 80rpx;
      border: none;
      border-radius: 16rpx;
      font-size: 30rpx;
      font-weight: 600;
      color: #ffffff;
      margin-bottom: 30rpx;
      box-shadow: 0 8rpx 24rpx rgba(102, 126, 234, 0.3);
      transition: all 0.3s ease;
      background-color: var(--wot-button-primary-bg-color, var(--wot-color-theme, #4d80f0));
      text-align: center;
      line-height: 80rpx;

      &:active {
        transform: translateY(2rpx);
        box-shadow: 0 4rpx 12rpx rgba(102, 126, 234, 0.3);
      }

      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }
    }

    .back-login-hint {
      text-align: center;

      .hint-text {
        color: #667eea;
        font-size: 26rpx;
        font-weight: 500;
        cursor: pointer;

        &:hover {
          text-decoration: underline;
        }
      }
    }
  }
}

// Kiểu cửa sổ bật lên lựa chọn mã vùng
.area-code-sheet {
  background: #ffffff;
  border-radius: 24rpx 24rpx 0 0;
  overflow: hidden;

  .sheet-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 40rpx 40rpx 20rpx 40rpx;
    border-bottom: 1rpx solid #f0f0f0;

    .sheet-title {
      font-size: 36rpx;
      font-weight: 600;
      color: #333333;
    }

    :deep(.close-icon) {
      font-size: 32rpx;
      color: #999999;
      cursor: pointer;
      padding: 10rpx;

      &:hover {
        color: #333333;
      }
    }
  }

  .area-code-list {
    max-height: 60vh;
    padding: 0 40rpx;

    .area-code-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 32rpx 0;
      border-bottom: 1rpx solid #f8f9fa;
      cursor: pointer;
      transition: background-color 0.3s ease;

      &:hover {
        background-color: #f8f9fa;
      }

      &.selected {
        background-color: rgba(102, 126, 234, 0.05);

        .area-name {
          color: #667eea;
          font-weight: 500;
        }

        .area-code {
          color: #667eea;
        }
      }

      .area-info {
        display: flex;
        flex-direction: column;
        gap: 8rpx;

        .area-name {
          font-size: 32rpx;
          color: #333333;
        }

        .area-code {
          font-size: 28rpx;
          color: #666666;
        }
      }

      :deep(.check-icon) {
        font-size: 32rpx;
        color: #667eea;
      }
    }
  }

  .sheet-footer {
    padding: 30rpx 40rpx 40rpx 40rpx;
    border-top: 1rpx solid #f0f0f0;

    :deep(.confirm-btn) {
      width: 100%;
      height: 88rpx;
      border-radius: 16rpx;
      font-size: 32rpx;
      font-weight: 600;
    }
  }
}
</style>
