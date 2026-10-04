import type { Device, FirmwareType } from './types'
import { http } from '@/http/request/alova'

/**
 * Nhận danh sách các loại thiết bị
 */
export function getFirmwareTypes() {
  return http.Get<FirmwareType[]>('/admin/dict/data/type/FIRMWARE_TYPE')
}

/**
 * Lấy danh sách các thiết bị bị ràng buộc
 * @param agentId ID đại lý
 */
export function getBindDevices(agentId: string) {
  return http.Get<Device[]>(`/device/bind/${agentId}`, {
    meta: {
      ignoreAuth: false,
      toast: false,
    },
    cacheFor: {
      expire: 0,
    },
  })
}

/**
 * Thêm thiết bị
 * @param agentId ID đại lý
 * @param code Mã xác minh
 */
export function bindDevice(agentId: string, code: string) {
  return http.Post(`/device/bind/${agentId}/${code}`, null)
}

/**
 * Thêm thiết bị theo cách thủ công
 * @param agentId ID đại lý
 * @param board Loại thiết bị
 * @param appVersion Phiên bản phần mềm
 * @param macAddress Địa chỉ MAC
 */
export function bindDeviceManual(data: {
  agentId: string
  board: string
  appVersion: string
  macAddress: string
}) {
  return http.Post('/device/manual-add', data)
}

/**
 * Đặt công tắc nâng cấp OTA của thiết bị
 * @param deviceId ID thiết bị (địa chỉ MAC)
 * @param autoUpdate Có tự động nâng cấp 0|1 không
 */
export function updateDeviceAutoUpdate(deviceId: string, autoUpdate: number) {
  return http.Put(`/device/update/${deviceId}`, {
    autoUpdate,
  })
}

/**
 * Hủy liên kết thiết bị
 * @param deviceId ID thiết bị (địa chỉ MAC)
 */
export function unbindDevice(deviceId: string) {
  return http.Post('/device/unbind', {
    deviceId,
  })
}
