import Vue from 'vue'
import VueRouter from 'vue-router'

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    name: 'welcome',
    component: function () {
      return import('../views/login.vue')
    }
  },
  {
    path: '/role-config',
    name: 'RoleConfig',
    component: function () {
      return import('../views/roleConfig.vue')
    }
  },
  {
    path: '/voice-print',
    name: 'VoicePrint',
    component: function () {
      return import('../views/VoicePrint.vue')
    }
  },
  {
    path: '/login',
    name: 'login',
    component: function () {
      return import('../views/login.vue')
    }
  },
  {
    path: '/home',
    name: 'home',
    component: function () {
      return import('../views/home.vue')
    }
  },
  {
    path: '/register',
    name: 'Register',
    component: function () {
      return import('../views/register.vue')
    }
  },
  {
    path: '/retrieve-password',
    name: 'RetrievePassword',
    component: function () {
      return import('../views/retrievePassword.vue')
    }
  },
  // Định tuyến trang quản lý thiết bị
  {
    path: '/device-management',
    name: 'DeviceManagement',
    component: function () {
      return import('../views/DeviceManagement.vue')
    }
  },
  // Thêm lộ trình quản lý người dùng
  {
    path: '/user-management',
    name: 'UserManagement',
    component: function () {
      return import('../views/UserManagement.vue')
    }
  },
  {
    path: '/model-config',
    name: 'ModelConfig',
    component: function () {
      return import('../views/ModelConfig.vue')
    }
  },
  {
    path: '/params-management',
    name: 'ParamsManagement',
    component: function () {
      return import('../views/ParamsManagement.vue')
    },
    meta: {
      requiresAuth: true,
      title: 'Quản lý tham số'
    }
  },
  {
    path: '/knowledge-base-management',
    name: 'KnowledgeBaseManagement',
    component: function () {
      return import('../views/KnowledgeBaseManagement.vue')
    },
    meta: {
      requiresAuth: true,
      title: 'Quản lý kho tri thức'
    }
  },
  {
    path: '/server-side-management',
    name: 'ServerSideManager',
    component: function () {
      return import('../views/ServerSideManager.vue')
    },
    meta: {
      requiresAuth: true,
      title: 'Quản lý server'
    }
  },
  {
    path: '/ota-management',
    name: 'OtaManagement',
    component: function () {
      return import('../views/OtaManagement.vue')
    },
    meta: {
      requiresAuth: true,
      title: 'Quản lý OTA'
    }
  },
  {
    path: '/voice-resource-management',
    name: 'VoiceResourceManagement',
    component: function () {
      return import('../views/VoiceResourceManagement.vue')
    },
    meta: {
      requiresAuth: true,
      title: 'Kích hoạt tài nguyên giọng đọc'
    }
  },
  {
    path: '/voice-clone-management',
    name: 'VoiceCloneManagement',
    component: function () {
      return import('../views/VoiceCloneManagement.vue')
    },
    meta: {
      requiresAuth: true,
      title: 'Quản lý nhân bản giọng nói'
    }
  },
  {
    path: '/dict-management',
    name: 'DictManagement',
    component: function () {
      return import('../views/DictManagement.vue')
    }
  },
  {
    path: '/provider-management',
    name: 'ProviderManagement',
    component: function () {
      return import('../views/ProviderManagement.vue')
    }
  },
  // Thêm tuyến quản lý vai trò mặc định
  {
    path: '/agent-template-management',
    name: 'AgentTemplateManagement',
    component: function () {
      return import('../views/AgentTemplateManagement.vue')
    }
  },
  // Thêm mẫu để định cấu hình định tuyến nhanh chóng
  {
    path: '/template-quick-config',
    name: 'TemplateQuickConfig',
    component: function () {
      return import('../views/TemplateQuickConfig.vue')
    }
  },
  // Định tuyến trang cấu hình chức năng
  {
    path: '/feature-management',
    name: 'FeatureManagement',
    component: function () {
      return import('../views/FeatureManagement.vue')
    },
    meta: {
      requiresAuth: true,
      title: 'Cấu hình chức năng'
    }
  },
  // Quản lý từ thay thế
  {
    path: '/replacement-word-management',
    name: 'ReplacementWordManagement',
    component: function () {
      return import('../views/ReplacementWordManagement.vue')
    },
    meta: {
      requiresAuth: true,
      title: 'Quản lý từ thay thế'
    }
  },
  // Định tuyến trang quản lý sổ địa chỉ
  {
    path: '/address-book-management',
    name: 'AddressBookManagement',
    component: function () {
      return import('../views/AddressBookManagement.vue')
    },
    meta: {
      requiresAuth: true,
      title: 'Quản lý danh bạ'
    }
  },
]
const router = new VueRouter({
  base: process.env.VUE_APP_PUBLIC_PATH || '/',
  routes
})

// Thay vào đó, hãy xử lý việc điều hướng lặp đi lặp lại và làm mới trang
const originalPush = VueRouter.prototype.push
VueRouter.prototype.push = function push(location) {
  return originalPush.call(this, location).catch(err => {
    if (err.name === 'NavigationDuplicated') {
      // Nếu điều hướng lặp lại, hãy làm mới trang
      window.location.reload()
    } else {
      // Các lỗi khác ném bình thường
      throw err
    }
  })
}

// Các tuyến yêu cầu đăng nhập để truy cập
const protectedRoutes = ['home', 'RoleConfig', 'DeviceManagement', 'UserManagement', 'ModelConfig', 'KnowledgeBaseManagement', 'KnowledgeFileUpload', 'AddressBookManagement']

// bảo vệ tuyến đường
router.beforeEach((to, from, next) => {
  // Kiểm tra xem đó có phải là tuyến đường cần được bảo vệ không
  if (protectedRoutes.includes(to.name)) {
    // Nhận mã thông báo từ localStorage
    const token = localStorage.getItem('token')
    if (!token) {
      // Chưa đăng nhập, chuyển đến trang đăng nhập
      next({ name: 'login', query: { redirect: to.fullPath } })
      return
    }
  }
  next()
})

export default router
