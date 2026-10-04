// Yêu cầu giới thiệu từng học phần
import admin from './module/admin.js'
import agent from './module/agent.js'
import device from './module/device.js'
import dict from './module/dict.js'
import model from './module/model.js'
import ota from './module/ota.js'
import timbre from "./module/timbre.js"
import user from './module/user.js'
import voiceClone from './module/voiceClone.js'
import voiceResource from './module/voiceResource.js'
import knowledgeBase from './module/knowledgeBase.js'
import correctWord from './module/correctWord.js'
import addressBook from './module/addressBook.js'



/**
 * địa chỉ giao diện
 * Tự động đọc và sử dụng tệp .env.development trong quá trình phát triển
 * Tự động đọc và sử dụng tệp .env.production trong quá trình biên dịch
 */
const DEV_API_SERVICE = process.env.VUE_APP_API_BASE_URL

/**
 * Trả về url giao diện theo môi trường phát triển
 * @returns {string}
 */
export function getServiceUrl() {
    return DEV_API_SERVICE
}

/** yêu cầu đóng gói dịch vụ */
export default {
    getServiceUrl,
    user,
    admin,
    agent,
    device,
    model,
    timbre,
    ota,
    dict,
    voiceResource,
    voiceClone,
    knowledgeBase,
    correctWord,
    addressBook
  }
