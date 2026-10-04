import type { UserInfo } from '@/api/auth'
import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getUserInfo as _getUserInfo,
} from '@/api/auth'

// trạng thái khởi tạo
const userInfoState: UserInfo & { avatar?: string, token?: string } = {
  id: 0,
  username: '',
  realName: '',
  email: '',
  mobile: '',
  status: 0,
  superAdmin: 0,
  avatar: '/static/images/default-avatar.png',
  token: '',
}

export const useUserStore = defineStore(
  'userInfo',
  () => {
    // Xác định thông tin người dùng
    const userInfo = ref<UserInfo & { avatar?: string, token?: string }>({ ...userInfoState })
    // Đặt thông tin người dùng
    const setUserInfo = (val: UserInfo & { avatar?: string, token?: string }) => {
      console.log('设置用户信息', val)
      // Nếu avatar trống thì dùng avatar mặc định
      if (!val.avatar) {
        val.avatar = userInfoState.avatar
      }
      else {
        val.avatar = 'https://oss.laf.run/ukw0y1-site/avatar.jpg?feige'
      }
      userInfo.value = val
    }
    const setUserAvatar = (avatar: string) => {
      userInfo.value.avatar = avatar
      console.log('设置用户头像', avatar)
      console.log('userInfo', userInfo.value)
    }
    // Xóa thông tin người dùng
    const removeUserInfo = () => {
      userInfo.value = { ...userInfoState }
      uni.removeStorageSync('userInfo')
      uni.removeStorageSync('token')
    }
    /**
     * Lấy thông tin người dùng
     */
    const getUserInfo = async () => {
      const userData = await _getUserInfo()
      setUserInfo(userData)
      return userData
    }
    /**
     * Đăng xuất và xóa thông tin người dùng
     */
    const logout = async () => {
      removeUserInfo()
    }

    return {
      userInfo,
      getUserInfo,
      setUserInfo,
      setUserAvatar,
      logout,
      removeUserInfo,
    }
  },
  {
    persist: {
      key: 'userInfo',
      serializer: {
        serialize: state => JSON.stringify(state.userInfo),
        deserialize: value => ({ userInfo: JSON.parse(value) }),
      },
    },
  },
)
