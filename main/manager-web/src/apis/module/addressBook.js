import { getServiceUrl } from '../api';
import RequestService from '../httpRequest';

export default {
  /**
   * Lấy danh sách sổ địa chỉ thiết bị
   */
  getAddressBookList(macAddress, callback) {
    RequestService.sendRequest()
      .url(`${getServiceUrl()}/device/address-book/${macAddress}`)
      .method('GET')
      .success((res) => {
        RequestService.clearRequestTime();
        callback(res);
      })
      .networkFail(() => {
        RequestService.reAjaxFun(() => {
          this.getAddressBookList(macAddress, callback);
        });
      }).send();
  },

  /**
   * Cập nhật bí danh sổ địa chỉ thiết bị
   */
  updateAlias(data, callback) {
    RequestService.sendRequest()
      .url(`${getServiceUrl()}/device/address-book/alias`)
      .method('PUT')
      .data(data)
      .success((res) => {
        RequestService.clearRequestTime();
        callback(res);
      })
      .networkFail(() => {
        RequestService.reAjaxFun(() => {
          this.updateAlias(data, callback);
        });
      }).send();
  },

  /**
   * Cập nhật quyền sổ địa chỉ thiết bị
   */
  updatePermission(data, callback) {
    RequestService.sendRequest()
      .url(`${getServiceUrl()}/device/address-book/permission`)
      .method('PUT')
      .data(data)
      .success((res) => {
        RequestService.clearRequestTime();
        callback(res);
      })
      .networkFail(() => {
        RequestService.reAjaxFun(() => {
          this.updatePermission(data, callback);
        });
      }).send();
  }
};