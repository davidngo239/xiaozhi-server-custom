import { getServiceUrl } from '../api';
import RequestService from '../httpRequest';


export default {
    // Danh sách người dùng
    getUserList(params, callback) {
        const queryParams = new URLSearchParams({
            page: params.page,
            limit: params.limit,
            mobile: params.mobile
        }).toString();

        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/users?${queryParams}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('请求失败:', err)
                RequestService.reAjaxFun(() => {
                    this.getUserList(callback)
                })
            }).send()
    },
    // Xóa người dùng
    deleteUser(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/users/${id}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('删除失败:', err)
                RequestService.reAjaxFun(() => {
                    this.deleteUser(id, callback)
                })
            }).send()
    },
    // Đặt lại mật khẩu người dùng
    resetUserPassword(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/users/${id}`)
            .method('PUT')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('重置密码失败:', err)
                RequestService.reAjaxFun(() => {
                    this.resetUserPassword(id, callback)
                })
            }).send()
    },
    // Lấy danh sách tham số
    getParamsList(params, callback) {
        const queryParams = new URLSearchParams({
            page: params.page,
            limit: params.limit,
            paramCode: params.paramCode || ''
        }).toString();

        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/params/page?${queryParams}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取参数列表失败:', err)
                RequestService.reAjaxFun(() => {
                    this.getParamsList(params, callback)
                })
            }).send()
    },
    // lưu lại
    addParam(data, callback, failCallback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/params`)
            .method('POST')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail((err) => {
                RequestService.clearRequestTime()
                failCallback(err)
            })
            .networkFail((err) => {
                console.error('添加参数失败:', err)
                RequestService.reAjaxFun(() => {
                    this.addParam(data, callback)
                })
            }).send()
    },
    // sửa đổi
    updateParam(data, callback, failCallback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/params`)
            .method('PUT')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .fail((err) => {
                RequestService.clearRequestTime()
                failCallback(err)
            })
            .networkFail((err) => {
                console.error('更新参数失败:', err)
                RequestService.reAjaxFun(() => {
                    this.updateParam(data, callback)
                })
            }).send()
    },
    // Xóa
    deleteParam(ids, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/params/delete`)
            .method('POST')
            .data(ids)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res);
            })
            .networkFail((err) => {
                console.error('删除参数失败:', err)
                RequestService.reAjaxFun(() => {
                    this.deleteParam(ids, callback)
                })
            }).send()
    },
    // Nhận danh sách máy chủ ws
    getWsServerList(params, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/server/server-list`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                console.error('获取ws服务端列表失败:', err)
                RequestService.reAjaxFun(() => {
                    this.getWsServerList(params, callback)
                })
            }).send();
    },
    // Gửi lệnh hành động của máy chủ ws
    sendWsServerAction(data, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/admin/server/emit-action`)
            .method('POST')
            .data(data)
            .success((res) => {
                RequestService.clearRequestTime()
                callback(res)
            })
            .networkFail((err) => {
                RequestService.reAjaxFun(() => {
                    this.sendWsServerAction(data, callback)
                })
            }).send();
    }

}
