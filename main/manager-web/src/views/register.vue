<template>
  <div class="welcome" @keyup.enter="register">
    <el-container style="height: 100%;">
      <!-- Giữ nguyên tiêu đề -->
      <el-header>
        <div style="display: flex;align-items: center;margin-top: 15px;margin-left: 10px;gap: 10px;">
          <img loading="lazy" alt="" src="@/assets/xiaozhi-logo.png" style="width: 45px;height: 45px;" />
          <img loading="lazy" alt="" :src="xiaozhiAiIcon" style="height: 18px;" />
        </div>
      </el-header>
      <div class="login-person">
        <img loading="lazy" alt="" src="@/assets/login/register-person.png" style="width: 100%;" />
      </div>
      <el-main style="position: relative;">
        <div class="login-box">
          <!-- Sửa phần tiêu đề -->
          <div style="display: flex;align-items: center;gap: 20px;margin-bottom: 39px;padding: 0 30px;">
            <img loading="lazy" alt="" src="@/assets/login/hi.png" style="width: 34px;height: 34px;" />
            <div class="login-text">{{ $t('register.title') }}</div>
            <div class="login-welcome">
              {{ $t('register.welcome') }}
            </div>
          </div>

          <div style="padding: 0 30px;">
            <form @submit.prevent="register">
              <!-- Hộp nhập tên người dùng/số điện thoại di động -->
              <div class="input-box" v-if="!enableMobileRegister">
                <img loading="lazy" alt="" class="input-icon" src="@/assets/login/username.png" />
                <el-input v-model="form.username" :placeholder="$t('register.usernamePlaceholder')" />
              </div>

              <!-- Phần đăng ký số điện thoại di động -->
              <template v-if="enableMobileRegister">
                <div class="input-box">
                  <div style="display: flex; align-items: center; width: 100%;">
                    <el-select v-model="form.areaCode" style="width: 220px; margin-right: 10px;">
                      <el-option v-for="item in mobileAreaList" :key="item.key" :label="`${item.name} (${item.key})`"
                        :value="item.key" />
                    </el-select>
                    <el-input v-model="form.mobile" :placeholder="$t('register.mobilePlaceholder')" />
                  </div>
                </div>

                <div style="display: flex; align-items: center; margin-top: 20px; width: 100%; gap: 10px;">
                  <div class="input-box" style="width: calc(100% - 130px); margin-top: 0;">
                    <img loading="lazy" alt="" class="input-icon" src="@/assets/login/shield.png" />
                    <el-input v-model="form.captcha" :placeholder="$t('register.captchaPlaceholder')"
                      style="flex: 1;" />
                  </div>
                  <img loading="lazy" v-if="captchaUrl" :src="captchaUrl" alt="Mã xác minh"
                    style="width: 150px; height: 40px; cursor: pointer;" @click="fetchCaptcha" />
                </div>

                <!-- Mã xác minh điện thoại di động -->

                <div style="display: flex; align-items: center; margin-top: 20px; width: 100%; gap: 10px;">
                  <div class="input-box" style="width: calc(100% - 130px); margin-top: 0;">
                    <img loading="lazy" alt="" class="input-icon" src="@/assets/login/phone.png" />
                    <el-input v-model="form.mobileCaptcha" :placeholder="$t('register.mobileCaptchaPlaceholder')"
                      style="flex: 1;" maxlength="6" />
                  </div>
                  <el-button type="primary" class="send-captcha-btn" :disabled="!canSendMobileCaptcha"
                    @click="sendMobileCaptcha">
                    <span>
                      {{ countdown > 0 ? `${countdown}${$t('register.secondsLater')}` : $t('register.sendCaptcha') }}
                    </span>
                  </el-button>
                </div>
              </template>

              <!-- Ô nhập mật khẩu -->
              <div class="input-box">
                <img loading="lazy" alt="" class="input-icon" src="@/assets/login/password.png" />
                <el-input v-model="form.password" :placeholder="$t('register.passwordPlaceholder')" type="password"
                  show-password />
              </div>

              <!-- Thêm mật khẩu xác nhận mới -->
              <div class="input-box">
                <img loading="lazy" alt="" class="input-icon" src="@/assets/login/password.png" />
                <el-input v-model="form.confirmPassword" :placeholder="$t('register.confirmPasswordPlaceholder')"
                  type="password" show-password />
              </div>

              <!-- Phần mã xác minh vẫn giữ nguyên -->
              <div v-if="!enableMobileRegister"
                style="display: flex; align-items: center; margin-top: 20px; width: 100%; gap: 10px;">
                <div class="input-box" style="width: calc(100% - 130px); margin-top: 0;">
                  <img loading="lazy" alt="" class="input-icon" src="@/assets/login/shield.png" />
                  <el-input v-model="form.captcha" :placeholder="$t('register.captchaPlaceholder')" style="flex: 1;" />
                </div>
                <img loading="lazy" v-if="captchaUrl" :src="captchaUrl" alt="Mã xác minh"
                  style="width: 150px; height: 40px; cursor: pointer;" @click="fetchCaptcha" />
              </div>

              <!-- Sửa đổi liên kết dưới cùng -->
              <div style="font-weight: 400;font-size: 14px;text-align: left;color: #5778ff;margin-top: 20px;">
                <div style="cursor: pointer;" @click="goToLogin">{{ $t('register.goToLogin') }}</div>
              </div>
            </form>
          </div>

          <!-- Sửa đổi văn bản nút -->
          <div class="login-btn" @click="register">{{ $t('register.registerButton') }}</div>

          <!-- Giữ nguyên khai báo giao thức -->
          <div style="font-size: 14px;color: #979db1;">
            {{ $t('register.agreeTo') }}
            <div style="display: inline-block;color: #5778FF;cursor: pointer;" @click="openPage('/user-agreement.html')">{{ $t('register.userAgreement') }}</div>
            {{ $t('login.and') }}
            <div style="display: inline-block;color: #5778FF;cursor: pointer;" @click="openPage('/privacy-policy.html')">{{ $t('register.privacyPolicy') }}</div>
          </div>
        </div>
      </el-main>

      <!-- Giữ nguyên chân trang -->
      <el-footer>
        <version-footer />
      </el-footer>
    </el-container>
  </div>
</template>

<script>
import Api from '@/apis/api';
import VersionFooter from '@/components/VersionFooter.vue';
import { getUUID, goToPage, showDanger, showSuccess, sm2Encrypt, validateMobile } from '@/utils';
import { mapState } from 'vuex';
import i18n from '@/i18n';

// Chức năng chuyển đổi ngôn ngữ nhập khẩu

export default {
  name: 'register',
  components: {
    VersionFooter
  },
  computed: {
    ...mapState({
      allowUserRegister: state => state.pubConfig.allowUserRegister,
      enableMobileRegister: state => state.pubConfig.enableMobileRegister,
      mobileAreaList: state => state.pubConfig.mobileAreaList,
      sm2PublicKey: state => state.pubConfig.sm2PublicKey,
    }),
    // Nhận ngôn ngữ hiện tại
    currentLanguage() {
      return i18n.locale || "zh_CN";
    },
    // Nhận biểu tượng xiaozhi-ai tương ứng theo ngôn ngữ hiện tại
    xiaozhiAiIcon() {
      const currentLang = this.currentLanguage;
      switch (currentLang) {
        case "zh_CN":
          return require("@/assets/xiaozhi-ai.png");
        case "zh_TW":
          return require("@/assets/xiaozhi-ai_zh_TW.png");
        case "en":
          return require("@/assets/xiaozhi-ai_en.png");
        case "de":
          return require("@/assets/xiaozhi-ai_de.png");
        case "vi":
          return require("@/assets/xiaozhi-ai_vi.png");
        default:
          return require("@/assets/xiaozhi-ai.png");
      }
    },
    canSendMobileCaptcha() {
      return this.countdown === 0 && validateMobile(this.form.mobile, this.form.areaCode);
    }
  },
  data() {
    return {
      form: {
        username: '',
        password: '',
        confirmPassword: '',
        captcha: '',
        captchaId: '',
        areaCode: '+86',
        mobile: '',
        mobileCaptcha: ''
      },
      captchaUrl: '',
      countdown: 0,
      timer: null,
    }
  },
  mounted() {
    this.$store.dispatch('fetchPubConfig').then(() => {
      if (!this.allowUserRegister) {
        showDanger(this.$t('register.notAllowRegister'));
        setTimeout(() => {
          goToPage('/login');
        }, 1500);
      }
    });
    this.fetchCaptcha();
  },
  methods: {
    openPage(url) {
      const lang = this.$i18n ? this.$i18n.locale : 'vi';
      if (lang === 'vi') {
        url = url.replace('.html', '-vi.html');
      } else if (!lang.startsWith('zh')) {
        url = url.replace('.html', '-en.html');
      }
      window.open(url, '_blank');
    },
    // Cách lấy mã xác minh tái sử dụng
    fetchCaptcha() {
      this.form.captchaId = getUUID();
      Api.user.getCaptcha(this.form.captchaId, (res) => {
        if (res.status === 200) {
          const blob = new Blob([res.data], { type: res.data.type });
          this.captchaUrl = URL.createObjectURL(blob);

        } else {
          console.error('验证码加载异常:', error);
          showDanger(this.$t('register.captchaLoadFailed'));
        }
      });
    },

    // Đóng gói logic xác thực đầu vào
    validateInput(input, message) {
      if (!input.trim()) {
        showDanger(message);
        return false;
      }
      return true;
    },

    // Gửi mã xác minh điện thoại di động
    sendMobileCaptcha() {
      if (!validateMobile(this.form.mobile, this.form.areaCode)) {
        showDanger(this.$t('register.inputCorrectMobile'));
        return;
      }

      // Xác minh mã xác minh đồ họa
      if (!this.validateInput(this.form.captcha, this.$t('register.inputCaptcha'))) {
        this.fetchCaptcha();
        return;
      }

      // Xóa bộ tính giờ cũ có thể tồn tại
      if (this.timer) {
        clearInterval(this.timer);
        this.timer = null;
      }

      // Bắt đầu đếm ngược
      this.countdown = 60;
      this.timer = setInterval(() => {
        if (this.countdown > 0) {
          this.countdown--;
        } else {
          clearInterval(this.timer);
          this.timer = null;
        }
      }, 1000);

      // Gọi giao diện gửi mã xác minh
      Api.user.sendSmsVerification({
        phone: this.form.areaCode + this.form.mobile,
        captcha: this.form.captcha,
        captchaId: this.form.captchaId
      }, (res) => {
        showSuccess(this.$t('register.captchaSendSuccess'));
      }, (err) => {
        showDanger(err.data.msg || this.$t('register.captchaSendFailed'));
        this.countdown = 0;
        this.fetchCaptcha();
      });
    },

    // Logic đăng ký
    async register() {
      if (this.enableMobileRegister) {
        // Xác minh đăng ký số điện thoại di động
        if (!validateMobile(this.form.mobile, this.form.areaCode)) {
          showDanger(this.$t('register.inputCorrectMobile'));
          return;
        }
        if (!this.form.mobileCaptcha) {
          showDanger(this.$t('register.requiredMobileCaptcha'));
          return;
        }
      } else {
        // Xác minh đăng ký tên người dùng
        if (!this.validateInput(this.form.username, this.$t('register.requiredUsername'))) {
          return;
        }
      }

      // Xác minh mật khẩu
      if (!this.validateInput(this.form.password, this.$t('register.requiredPassword'))) {
        return;
      }
      if (this.form.password !== this.form.confirmPassword) {
        showDanger(this.$t('register.passwordsNotMatch'))
        return
      }
      // Xác minh mã xác minh
      if (!this.validateInput(this.form.captcha, this.$t('register.requiredCaptcha'))) {
        return;
      }
      // Mã hóa
      let encryptedPassword;
      try {
        // Nối mã xác minh và mật khẩu
        const captchaAndPassword = this.form.captcha + this.form.password;
        encryptedPassword = sm2Encrypt(this.sm2PublicKey, captchaAndPassword);
      } catch (error) {
        console.error("密码加密失败:", error);
        showDanger(this.$t('sm2.encryptionFailed'));
        return;
      }

      let plainUsername;
      if (this.enableMobileRegister) {
        plainUsername = this.form.areaCode + this.form.mobile;
      } else {
        plainUsername = this.form.username;
      }

      // Chuẩn bị dữ liệu đăng ký
      const registerData = {
        username: plainUsername,
        password: encryptedPassword,
        captchaId: this.form.captchaId,
        mobileCaptcha: this.form.mobileCaptcha
      };

      Api.user.register(registerData, ({ data }) => {
        showSuccess(this.$t('register.registerSuccess'))
        goToPage('/login')
      }, (err) => {
        showDanger(err.data.msg || this.$t('register.registerFailed'))
        if (err.data != null && err.data.msg != null && err.data.msg.indexOf('图形验证码') > -1) {
          this.fetchCaptcha()
        }
      })
    },

    goToLogin() {
      goToPage('/login')
    }
  },
  beforeDestroy() {
    if (this.timer) {
      clearInterval(this.timer);
    }
  }
}
</script>

<style lang="scss" scoped>
@import './auth.scss';

.send-captcha-btn {
  margin-right: -5px;
  min-width: 100px;
  height: 40px;
  line-height: 40px;
  border-radius: 4px;
  font-size: 14px;
  background: rgb(87, 120, 255);
  border: none;
  padding: 0px;

  &:disabled {
    background: #c0c4cc;
    cursor: not-allowed;
  }
}
</style>
