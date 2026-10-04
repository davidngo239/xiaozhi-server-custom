<template>
  <el-header class="header">
    <div class="header-container">
      <!-- Phần tử bên trái -->
      <div class="header-left" @click="handleRouter('home')">
        <img loading="lazy" alt="" src="@/assets/xiaozhi-logo.png" class="logo-img" />
        <img loading="lazy" alt="" :src="xiaozhiAiIcon" class="brand-img" />
      </div>

      <!-- Menu điều hướng ở giữa -->
      <div class="header-center">
        <div class="equipment-management" :class="{
          'active-tab':
            $route.path === '/home' ||
            $route.path === '/role-config' ||
            $route.path === '/device-management',
        }" @click="handleRouter('home')">
          <img loading="lazy" alt="" src="@/assets/header/robot.png" :style="{
            filter:
              $route.path === '/home' ||
                $route.path === '/role-config' ||
                $route.path === '/device-management'
                ? 'brightness(0) invert(1)'
                : 'None',
          }" />
          <span class="nav-text">{{ $t("header.smartManagement") }}</span>
        </div>
        <!-- Người dùng thông thường hiển thị bản sao giai điệu -->
        <div v-if="!userInfo.superAdmin && featureStatus.voiceClone" class="equipment-management"
          :class="{ 'active-tab': $route.path === '/voice-clone-management' }"
          @click="handleRouter('voiceCloneManagement')">
          <img loading="lazy" alt="" src="@/assets/header/voice.png" :style="{
            filter:
              $route.path === '/voice-clone-management'
                ? 'brightness(0) invert(1)'
                : 'None',
          }" />
          <span class="nav-text">{{ $t("header.voiceCloneManagement") }}</span>
        </div>

        <!-- Quản trị viên cấp cao hiển thị menu thả xuống bản sao bản vá -->
        <el-dropdown v-if="userInfo.superAdmin && featureStatus.voiceClone" trigger="click"
          class="equipment-management more-dropdown" :class="{
            'active-tab':
              $route.path === '/voice-clone-management' ||
              $route.path === '/voice-resource-management',
          }" @visible-change="handleVoiceCloneDropdownVisibleChange">
          <span class="el-dropdown-link">
            <img loading="lazy" alt="" src="@/assets/header/voice.png" :style="{
              filter:
                $route.path === '/voice-clone-management' ||
                  $route.path === '/voice-resource-management'
                  ? 'brightness(0) invert(1)'
                  : 'None',
            }" />
            <span class="nav-text">{{ $t("header.voiceCloneManagement") }}</span>
            <i class="el-icon-arrow-down" :class="{ 'rotate-down': voiceCloneDropdownVisible }"></i>
          </span>
          <el-dropdown-menu slot="dropdown">
            <el-dropdown-item @click.native="handleRouter('voiceCloneManagement')">
              {{ $t("header.voiceCloneManagement") }}
            </el-dropdown-item>
            <el-dropdown-item @click.native="handleRouter('voiceResourceManagement')">
              {{ $t("header.voiceResourceManagement") }}
            </el-dropdown-item>
          </el-dropdown-menu>
        </el-dropdown>

        <div v-if="userInfo.superAdmin" class="equipment-management"
          :class="{ 'active-tab': $route.path === '/model-config' }" @click="handleRouter('modelConfig')">
          <img loading="lazy" alt="" src="@/assets/header/model_config.png" :style="{
            filter:
              $route.path === '/model-config' ? 'brightness(0) invert(1)' : 'None',
          }" />
          <span class="nav-text">{{ $t("header.modelConfig") }}</span>
        </div>
        <div v-if="featureStatus.knowledgeBase" class="equipment-management"
          :class="{ 'active-tab': $route.path === '/knowledge-base-management' || $route.path === '/knowledge-file-upload' }"
          @click="handleRouter('knowledgeBaseManagement')">
          <img loading="lazy" alt="" src="@/assets/header/knowledge_base.png" :style="{
            filter:
              $route.path === '/knowledge-base-management' || $route.path === '/knowledge-file-upload' ? 'brightness(0) invert(1)' : 'None',
          }" />
          <span class="nav-text">{{ $t("header.knowledgeBase") }}</span>
        </div>
        <div v-if="featureStatus.addressBook" class="equipment-management"
          :class="{ 'active-tab': $route.path === '/address-book-management' }"
          @click="handleRouter('addressBookManagement')">
          <img loading="lazy" alt="" src="@/assets/header/address_book.png" :style="{
            filter:
              $route.path === '/address-book-management' ? 'brightness(0) invert(1)' : 'None',
          }" />
          <span class="nav-text">{{ $t("header.addressBook") }}</span>
        </div>
        <el-dropdown v-if="userInfo.superAdmin" trigger="click" class="equipment-management more-dropdown" :class="{
          'active-tab':
            $route.path === '/dict-management' ||
            $route.path === '/params-management' ||
            $route.path === '/provider-management' ||
            $route.path === '/server-side-management' ||
            $route.path === '/agent-template-management' ||
            $route.path === '/ota-management' ||
            $route.path === '/user-management' ||
            $route.path === '/feature-management' ||
            $route.path === '/replacement-word-management'
        }" @visible-change="handleParamDropdownVisibleChange">
          <span class="el-dropdown-link">
            <img loading="lazy" alt="" src="@/assets/header/param_management.png" :style="{
              filter:
                $route.path === '/dict-management' ||
                  $route.path === '/params-management' ||
                  $route.path === '/provider-management' ||
                  $route.path === '/server-side-management' ||
                  $route.path === '/agent-template-management' ||
                  $route.path === '/ota-management' ||
                  $route.path === '/user-management' ||
                  $route.path === '/feature-management' ||
                  $route.path === '/replacement-word-management'
                  ? 'brightness(0) invert(1)'
                  : 'None',
            }" />
            <span class="nav-text">{{ $t("header.paramDictionary") }}</span>
            <i class="el-icon-arrow-down" :class="{ 'rotate-down': paramDropdownVisible }"></i>
          </span>
          <el-dropdown-menu slot="dropdown">
            <el-dropdown-item @click.native="handleRouter('paramManagement')">
              {{ $t("header.paramManagement") }}
            </el-dropdown-item>
            <el-dropdown-item @click.native="handleRouter('userManagement')">
              {{ $t("header.userManagement") }}
            </el-dropdown-item>
            <el-dropdown-item @click.native="handleRouter('otaManagement')">
              {{ $t("header.otaManagement") }}
            </el-dropdown-item>
            <el-dropdown-item @click.native="handleRouter('dictManagement')">
              {{ $t("header.dictManagement") }}
            </el-dropdown-item>
            <el-dropdown-item @click.native="handleRouter('providerManagement')">
              {{ $t("header.providerManagement") }}
            </el-dropdown-item>
            <el-dropdown-item @click.native="handleRouter('agentTemplate')">
              {{ $t("header.agentTemplate") }}
            </el-dropdown-item>
            <el-dropdown-item @click.native="handleRouter('replacementWordManagement')">
              {{ $t("header.replacementWordManagement") }}
            </el-dropdown-item>
            <el-dropdown-item @click.native="handleRouter('serverSideManagement')">
              {{ $t("header.serverSideManagement") }}
            </el-dropdown-item>
            <el-dropdown-item @click.native="handleRouter('featureManagement')">
              {{ $t("header.featureManagement") }}
            </el-dropdown-item>
          </el-dropdown-menu>
        </el-dropdown>
      </div>

      <!-- Phần tử bên phải -->
      <div class="header-right">
        <img loading="lazy" alt="" src="@/assets/home/avatar.png" class="avatar-img" @click="handleAvatarClick" />
        <span class="el-user-dropdown" @click="handleAvatarClick">
          {{ userInfo.username || "Đang tải..." }}
          <i class="el-icon-arrow-down el-icon--right" :class="{ 'rotate-down': userMenuVisible }"></i>
        </span>
        <el-cascader :options="userMenuOptions" trigger="click" :props="cascaderProps"
          style="width: 0px; overflow: hidden" :show-all-levels="false" @change="handleCascaderChange"
          @visible-change="handleUserMenuVisibleChange" ref="userCascader">
          <template slot-scope="{ data }">
            <span>{{ data.label }}</span>
          </template>
        </el-cascader>
      </div>
    </div>

    <!-- Cửa sổ bật lên thay đổi mật khẩu -->
    <ChangePasswordDialog v-model="isChangePasswordDialogVisible" />
  </el-header>
</template>

<script>
import i18n, { changeLanguage } from "@/i18n";
import featureManager from "@/utils/featureManager"; // Giới thiệu lớp công cụ quản lý hàm
import { mapActions, mapState } from "vuex";
import ChangePasswordDialog from "./ChangePasswordDialog.vue"; // Giới thiệu thành phần bật lên thay đổi mật khẩu

export default {
  name: "HeaderBar",
  components: {
    ChangePasswordDialog,
  },
  props: ["devices"], // Nhận danh sách thiết bị thành phần cha mẹ
  data() {
    return {
      search: "",
      isChangePasswordDialogVisible: false, // Điều khiển hiển thị cửa sổ pop-up đổi mật khẩu
      paramDropdownVisible: false,
      voiceCloneDropdownVisible: false,
      userMenuVisible: false, // Thêm trạng thái hiển thị menu người dùng
      menuVisibleTimer: null, // Menu hiển thị hẹn giờ để tránh kích hoạt sớm
      // Cấu hình tầng
      cascaderProps: {
        expandTrigger: "click",
        value: "value",
        label: "label",
        children: "children",
      },
      // Cấu hình trang nhảy
      routerPaths: {
        home: "/home",
        modelConfig: "/model-config",
        knowledgeBaseManagement: "/knowledge-base-management",
        addressBookManagement: "/address-book-management",
        voiceCloneManagement: "/voice-clone-management",
        voiceResourceManagement: "/voice-resource-management",
        paramManagement: "/params-management",
        userManagement: "/user-management",
        otaManagement: "/ota-management",
        dictManagement: "/dict-management",
        providerManagement: "/provider-management",
        agentTemplate: "/agent-template-management",
        replacementWordManagement: "/replacement-word-management",
        serverSideManagement: "/server-side-management",
        featureManagement: "/feature-management",
      }
    };
  },
  computed: {
    ...mapState({
      featureStatus: (state) => ({
        voiceClone: state.pubConfig.systemWebMenu?.features?.voiceClone?.enabled, // Trạng thái chức năng sao chép âm thanh
        knowledgeBase: state.pubConfig.systemWebMenu?.features?.knowledgeBase?.enabled, // Trạng thái chức năng cơ sở kiến thức
        addressBook: state.pubConfig.systemWebMenu?.features?.addressBook?.enabled, // Trạng thái chức năng sổ địa chỉ
      }),
      userInfo: (state) => state.userInfo,
    }),
    // Nhận ngôn ngữ hiện tại
    currentLanguage() {
      return i18n.locale || "zh_CN";
    },
    // Lấy văn bản hiển thị ngôn ngữ hiện tại
    currentLanguageText() {
      const currentLang = this.currentLanguage;
      switch (currentLang) {
        case "zh_CN":
          return this.$t("language.zhCN");
        case "zh_TW":
          return this.$t("language.zhTW");
        case "en":
          return this.$t("language.en");
        case "de":
          return this.$t("language.de");
        case "vi":
          return this.$t("language.vi");
        case "pt_BR":
          return this.$t("language.ptBR");
        default:
          return this.$t("language.zhCN");
      }
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
        case "pt_BR":
          return require("@/assets/xiaozhi-ai_en.png");
        default:
          return require("@/assets/xiaozhi-ai.png");
      }
    },
    // Tùy chọn menu người dùng
    userMenuOptions() {
      return [
        {
          label: this.currentLanguageText,
          value: "language",
          children: [
            {
              label: this.$t("language.zhCN"),
              value: "zh_CN",
            },
            {
              label: this.$t("language.zhTW"),
              value: "zh_TW",
            },
            {
              label: this.$t("language.en"),
              value: "en",
            },
            {
              label: this.$t("language.de"),
              value: "de",
            },
            {
              label: this.$t("language.vi"),
              value: "vi",
            },
            {
              label: this.$t("language.ptBR"),
              value: "pt_BR",
            },
          ],
        },
        {
          label: this.$t("header.changePassword"),
          value: "changePassword",
        },
        {
          label: this.$t("header.logout"),
          value: "logout",
        },
      ];
    },
  },
  async mounted() {
    // Đợi featureManager được khởi tạo trước khi tải trạng thái tính năng.
    await this.loadFeatureStatus();
  },
  methods: {
    handleRouter(type) {
      this.$router.push(this.routerPaths[type]);
    },
    // Tải trạng thái chức năng
    async loadFeatureStatus() {
      // Đợi quá trình khởi tạo featureManager hoàn tất
      await featureManager.waitForInitialization();
    },
    // Hiển thị cửa sổ pop-up đổi mật khẩu
    showChangePasswordDialog() {
      this.isChangePasswordDialogVisible = true;
      // Đã thêm: Đặt lại trạng thái hiển thị của menu người dùng sau khi hiển thị cửa sổ bật lên thay đổi mật khẩu.
      this.userMenuVisible = false;
    },
    // Đăng xuất
    async handleLogout() {
      try {
        // Gọi hành động đăng xuất của Vuex
        await this.logout();
        this.$message.success({
          message: this.$t("message.success"),
          showClose: true,
        });
      } catch (error) {
        console.error("退出登录失败:", error);
        this.$message.error({
          message: this.$t("message.error"),
          showClose: true,
        });
      }
    },
    // Lắng nghe những thay đổi ở trạng thái hiển thị của menu thả xuống từ điển tham số
    handleParamDropdownVisibleChange(visible) {
      this.paramDropdownVisible = visible;
    },

    // Theo dõi sự thay đổi trạng thái hiển thị của menu thả xuống bản sao bản vá
    handleVoiceCloneDropdownVisibleChange(visible) {
      this.voiceCloneDropdownVisible = visible;
    },
    // Thêm khóa vào dữ liệu để buộc hiển thị lại thành phần
    // Xử lý các thay đổi lựa chọn Cascader
    handleCascaderChange(value) {
      if (!value || value.length === 0) {
        return;
      }

      const action = value[value.length - 1];

      // Xử lý chuyển đổi ngôn ngữ
      if (value.length === 2 && value[0] === "language") {
        this.changeLanguage(action);
      } else {
        // Xử lý các hoạt động khác
        switch (action) {
          case "changePassword":
            this.showChangePasswordDialog();
            break;
          case "logout":
            this.handleLogout();
            break;
        }
      }

      // Xóa lựa chọn ngay sau khi thao tác hoàn tất
      setTimeout(() => {
        this.completeResetCascader();
      }, 300);
    },

    // chuyển đổi ngôn ngữ
    changeLanguage(lang) {
      changeLanguage(lang);
      this.$message.success({
        message: this.$t("message.success"),
        showClose: true,
      });
      // Đã thêm: Đặt lại trạng thái hiển thị menu người dùng sau khi chuyển đổi ngôn ngữ
      this.userMenuVisible = false;
    },

    // Đặt lại hoàn toàn bộ chọn xếp tầng
    completeResetCascader() {
      if (this.$refs.userCascader) {
        try {
          // Hãy thử mọi cách có thể để xóa lựa chọn
          // 1. Thử sử dụng phương thức clearValue do thành phần cung cấp
          if (this.$refs.userCascader.clearValue) {
            this.$refs.userCascader.clearValue();
          }

          // 2. Xóa trực tiếp thuộc tính bên trong
          if (this.$refs.userCascader.$data) {
            this.$refs.userCascader.$data.selectedPaths = [];
            this.$refs.userCascader.$data.displayLabels = [];
            this.$refs.userCascader.$data.inputValue = "";
            this.$refs.userCascader.$data.checkedValue = [];
            this.$refs.userCascader.$data.showAllLevels = false;
          }

          // 3. Thao tác DOM để xóa trạng thái đã chọn
          const menuElement = this.$refs.userCascader.$refs.menu;
          if (menuElement && menuElement.$el) {
            const activeItems = menuElement.$el.querySelectorAll(
              ".el-cascader-node.is-active"
            );
            activeItems.forEach((item) => item.classList.remove("is-active"));

            const checkedItems = menuElement.$el.querySelectorAll(
              ".el-cascader-node.is-checked"
            );
            checkedItems.forEach((item) => item.classList.remove("is-checked"));
          }

          console.log("Cascader values cleared");
        } catch (error) {
          console.error("清空选择值失败:", error);
        }
      }
    },

    // Nhấp vào hình đại diện để kích hoạt menu thả xuống tầng
    handleAvatarClick() {
      if (this.$refs.userCascader) {
        // Chuyển đổi chế độ hiển thị menu
        this.userMenuVisible = !this.userMenuVisible;

        // Xóa giá trị lựa chọn khi đóng menu
        if (!this.userMenuVisible) {
          this.completeResetCascader();
        }

        // Trực tiếp đặt trạng thái hiển thị và ẩn của menu
        try {
          // Hãy thử sử dụng phương thức TottleDropDownVisible
          this.$refs.userCascader.toggleDropDownVisible(this.userMenuVisible);
        } catch (error) {
          // Nếu phương thức chuyển đổi không thành công, hãy thử đặt thuộc tính trực tiếp
          if (this.$refs.userCascader.$refs.menu) {
            this.$refs.userCascader.$refs.menu.showMenu(this.userMenuVisible);
          } else {
            console.error("Cannot access menu component");
          }
        }
      }
    },

    // Xử lý các thay đổi về khả năng hiển thị của menu người dùng
    handleUserMenuVisibleChange(visible) {
      if (this.menuVisibleTimer) return;
      this.menuVisibleTimer = setTimeout(() => {
        this.userMenuVisible = visible;
        clearTimeout(this.menuVisibleTimer);
        this.menuVisibleTimer = null;
      }, 100);

      // Nếu menu bị đóng, giá trị lựa chọn cũng phải bị xóa
      if (!visible) {
        this.completeResetCascader();
      }
    },

    // Sử dụng mapActions để giới thiệu hành động đăng xuất của Vuex
    ...mapActions(["logout"]),
  },
};
</script>

<style lang="scss" scoped>
.header {
  background: linear-gradient(180deg, #dfeafe, #eff4ff);
  height: 63px !important;
  min-width: 900px;
  overflow: visible;
}

.header-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
  padding: 0 10px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 130px;
  cursor: pointer;
}

.logo-img {
  width: 42px;
  height: 42px;
}

.brand-img {
  height: 20px;
}

.header-center {
  display: flex;
  align-items: center;
  gap: 25px;
  background: white;
  border-radius: 30px;
  box-shadow: 0 0 6px 0px #cfe1fb;
  padding: 4px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 7px;
  justify-content: flex-end;
}

.equipment-management {
  padding: 8px 16px;
  border-radius: 30px;
  display: flex;
  justify-content: center;
  font-size: 16px;
  font-weight: 500;
  gap: 7px;
  color: #6c79a8;
  margin-left: 1px;
  align-items: center;
  transition: all 0.3s ease;
  cursor: pointer;
  flex-shrink: 0;
  position: relative;
}

.equipment-management.active-tab {
  color: #fff !important;
  background: linear-gradient(90deg, #2983fe 0%, #5251fc 100%);
  box-shadow: 0 1px 8px rgba(41, 131, 254, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.3);
  position: relative;
  overflow: hidden;
}

.equipment-management.active-tab::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 50%;
  background: linear-gradient(to bottom, rgba(255, 255, 255, 0.4) 0%, rgba(255, 255, 255, 0) 100%);
  pointer-events: none;
}

.equipment-management img {
  width: 15px;
  height: 13px;
}

.avatar-img {
  width: 21px;
  height: 21px;
  flex-shrink: 0;
  cursor: pointer;
}

.el-user-dropdown {
  cursor: pointer;
}

/* Kiểu văn bản điều hướng - hỗ trợ ngắt dòng tiếng Trung và tiếng Anh */
.nav-text {
  white-space: normal;
  text-align: center;
  line-height: 1.2;
}

.el-dropdown-link {
  display: flex;
  align-items: center;
  gap: 7px;
}

/* Điều chỉnh đáp ứng */
@media (max-width: 1200px) {
  .header-center {
    gap: 14px;
  }

  .equipment-management {
    min-width: 80px;
    font-size: 10px;
  }
}

.equipment-management.more-dropdown {
  position: relative;
}

.equipment-management.more-dropdown .el-dropdown-menu {
  position: absolute;
  right: 0;
  min-width: 120px;
  margin-top: 5px;
}

.el-dropdown-menu__item {
  min-width: 60px;
  padding: 8px 20px;
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}

/* Thêm kiểu xoay tam giác ngược */
.rotate-down {
  transform: rotate(180deg);
  transition: transform 0.3s ease;
}

.el-icon-arrow-down {
  transition: transform 0.3s ease;
}
</style>
