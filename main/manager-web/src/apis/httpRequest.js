import Fly from 'flyio/dist/npm/fly';
import store from '../store/index';
import Constant from '../utils/constant';
import { goToPage, isNotNull, showDanger, showWarning } from '../utils/index';
import i18n from '../i18n/index';
import { localizeSystemText } from '../i18n/systemText';

const fly = new Fly()
// Đặt thời gian chờ
fly.config.timeout = 30000

/**
 * Yêu cầu đóng gói dịch vụ
 */
export default {
    sendRequest,
    reAjaxFun,
    clearRequestTime
}

function sendRequest() {
    return {
        _sucCallback: null,
        _failCallback: null,
        _networkFailCallback: null,
        _method: 'GET',
        _data: {},
        _header: { 'content-type': 'application/json; charset=utf-8' },
        _url: '',
        _responseType: undefined, // Đã thêm trường loại phản hồi
        'send'() {
            // Đặt tiêu đề yêu cầu ngôn ngữ
            const currentLang = i18n.locale;
            // Chuyển đổi định dạng mã ngôn ngữ, chuyển đổi zh_CN sang zh-CN
            let acceptLanguage = currentLang.replace('_', '-');
            // Thêm mã vùng mặc định cho tiếng Anh
            if (acceptLanguage === 'en') {
                acceptLanguage = 'en-US';
            } else if (acceptLanguage === 'vi') {
                acceptLanguage = 'vi-VN';
            }
            this._header['Accept-Language'] = acceptLanguage;
            
            if (isNotNull(store.getters.getToken)) {
                this._header.Authorization = 'Bearer ' + (JSON.parse(store.getters.getToken)).token
            }

            // In thông tin yêu cầu
            fly.request(this._url, this._data, {
                method: this._method,
                headers: this._header,
                responseType: this._responseType
            }).then((res) => {
                const error = httpHandlerError(res, this._failCallback, this._networkFailCallback);
                if (error) {
                    return
                }

                if (this._sucCallback) {
                    this._sucCallback(res)
                }
            }).catch((res) => {
                // Phản hồi lỗi in
                console.log('catch', res)
                httpHandlerError(res, this._failCallback, this._networkFailCallback)
            })
            return this
        },
        'success'(callback) {
            this._sucCallback = callback
            return this
        },
        'fail'(callback) {
            this._failCallback = callback
            return this
        },
        'networkFail'(callback) {
            this._networkFailCallback = callback
            return this
        },
        'url'(url) {
            if (url) {
                url = url.replaceAll('$', '/')
            }
            this._url = url
            return this
        },
        'data'(data) {
            this._data = data
            return this
        },
        'method'(method) {
            this._method = method
            return this
        },
        'header'(header) {
            this._header = header
            return this
        },
        'showLoading'(showLoading) {
            this._showLoading = showLoading
            return this
        },
        'async'(flag) {
            this.async = flag
        },
        // Đã thêm phương pháp cài đặt loại
        'type'(responseType) {
            this._responseType = responseType;
            return this;
        }
    }
}

/**
 * Info trả về thông tin sau khi yêu cầu được hoàn thành
 * chức năng gọi lại failedCallback
 * chức năng gọi lại networkFailCallback
 */
// Thêm chức năng xử lý lỗi đăng nhập
function httpHandlerError(info, failCallback, networkFailCallback) {
    if (info.data && typeof info.data.msg === 'string') {
        info.data.msg = localizeSystemText(info.data.msg, i18n.locale);
    }

    /** Nếu yêu cầu thành công, hãy thoát khỏi chức năng này. Bạn có thể xác định xem yêu cầu có thành công hay không dựa trên yêu cầu của dự án. Điều được đánh giá ở đây là khi trạng thái là 200 là thành công */
    let networkError = false
    if (info.status === 200) {
        if (info.data.code === 'success' || info.data.code === 0 || info.data.code === undefined) {
            return networkError
        } else if (info.data.code === 401) {
            store.commit('clearAuth');
            goToPage(Constant.PAGE.LOGIN, true);
            return true
        } else {
            // Sử dụng trực tiếp các tin nhắn được quốc tế hóa do chương trình phụ trợ trả về
            let errorMessage = info.data.msg;
            
            if (failCallback) {
                failCallback(info)
            } else {
                showDanger(errorMessage)
            }
            return true
        }
    }
    if (networkFailCallback) {
        networkFailCallback(info)
    } else {
        showDanger(`Yêu cầu mạng gặp lỗi [${info.status}]`)
    }
    return true
}

let requestTime = 0
let reAjaxSec = 2

function reAjaxFun(fn) {
    let nowTimeSec = new Date().getTime() / 1000
    if (requestTime === 0) {
        requestTime = nowTimeSec
    }
    let ajaxIndex = parseInt((nowTimeSec - requestTime) / reAjaxSec)
    if (ajaxIndex > 10) {
        showWarning('Không thể kết nối tới server')
    } else {
        showWarning('Đang kết nối tới server (' + ajaxIndex + ')')
    }
    if (ajaxIndex < 10 && fn) {
        setTimeout(() => {
            fn()
        }, reAjaxSec * 1000)
    }
}

function clearRequestTime() {
    requestTime = 0
}
