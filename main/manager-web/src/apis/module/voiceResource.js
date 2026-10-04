import { getServiceUrl } from '../api';
import RequestService from '../httpRequest';

export default {
    // Truy vấn tài nguyên âm sắc theo trang
    getVoiceResourceList(params, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/voiceResource`)
            .method('GET')
            .data(params)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取音色资源列表失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getVoiceResourceList(params, callback);
                });
            }).send();
    },
    // Nhận thông tin tài nguyên âm sắc riêng lẻ
    getVoiceResourceInfo(id, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/voiceResource/${id}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取音色资源信息失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getVoiceResourceInfo(id, callback);
                });
            }).send();
    },
    // Tiết kiệm tài nguyên giai điệu
    saveVoiceResource(entity, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/voiceResource`)
            .method('POST')
            .data(entity)
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('保存音色资源失败:', err);
                RequestService.reAjaxFun(() => {
                    this.saveVoiceResource(entity, callback);
                });
            }).send();
    },
    // Xóa tài nguyên âm thanh
    deleteVoiceResource(ids, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/voiceResource/${ids}`)
            .method('DELETE')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('删除音色资源失败:', err);
                RequestService.reAjaxFun(() => {
                    this.deleteVoiceResource(ids, callback);
                });
            }).send();
    },
    // Lấy danh sách tài nguyên âm sắc dựa trên ID người dùng
    getVoiceResourceByUserId(userId, callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/voiceResource/user/${userId}`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取用户音色资源列表失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getVoiceResourceByUserId(userId, callback);
                });
            }).send();
    },
    // Nhận danh sách nền tảng TTS
    getTtsPlatformList(callback) {
        RequestService.sendRequest()
            .url(`${getServiceUrl()}/voiceResource/ttsPlatforms`)
            .method('GET')
            .success((res) => {
                RequestService.clearRequestTime();
                callback(res);
            })
            .networkFail((err) => {
                console.error('获取TTS平台列表失败:', err);
                RequestService.reAjaxFun(() => {
                    this.getTtsPlatformList(callback);
                });
            }).send();
    }
}
