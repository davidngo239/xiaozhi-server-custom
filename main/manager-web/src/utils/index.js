import { Message } from 'element-ui'
import router from '../router'
import Constant from '../utils/constant'

/**
 * Xác định xem người dùng đã đăng nhập hay chưa
 */
export function checkUserLogin(fn) {
    let token = localStorage.getItem(Constant.STORAGE_KEY.TOKEN)
    let userType = localStorage.getItem(Constant.STORAGE_KEY.USER_TYPE)
    if (isNull(token) || isNull(userType)) {
        goToPage('console', true)
        return
    }
    if (fn) {
        fn()
    }
}

/**
 * Xác định xem nó có trống không
 * @param data
 * @returns {boolean}
 */
export function isNull(data) {
    if (data === undefined) {
        return true
    } else if (data === null) {
        return true
    } else if (typeof data === 'string' && (data.length === 0 || data === '' || data === 'undefined' || data === 'null')) {
        return true
    } else if ((data instanceof Array) && data.length === 0) {
        return true
    }
    return false
}

/**
 * Bản án không trống rỗng
 * @param data
 * @returns {boolean}
 */
export function isNotNull(data) {
    return !isNull(data)
}

/**
 * Hiển thị thông báo màu đỏ hàng đầu
 * @param msg
 */
export function showDanger(msg) {
    if (isNull(msg)) {
        return
    }
    Message({
        message: msg,
        type: 'error',
        showClose: true
    })
}

/**
 * Hiển thị thông báo màu cam hàng đầu
 * @param msg
 */
export function showWarning(msg) {
    if (isNull(msg)) {
        return
    }
    Message({
        message: msg,
        type: 'warning',
        showClose: true
    });
}



/**
 * Hiển thị thông báo màu xanh lá cây hàng đầu
 * @param msg
 */
export function showSuccess(msg) {
    Message({
        message: msg,
        type: 'success',
        showClose: true
    })
}



/**
 * Nhảy trang
 * @param path
 * @param isRepalce
 */
export function goToPage(path, isRepalce) {
    if (isRepalce) {
        router.replace(path)
    } else {
        router.push(path)
    }
}

/**
 * Lấy tên trang vue hiện tại
 * @param path
 * @param isRepalce
 */
export function getCurrentPage() {
    let hash = location.hash.replace('#', '')
    if (hash.indexOf('?') > 0) {
        hash = hash.substring(0, hash.indexOf('?'))
    }
    return hash
}

/**
 * Tạo số ngẫu nhiên từ [min,max]
 * @param min
 * @param max
 * @returns {number}
 */
export function randomNum(min, max) {
    return Math.round(Math.random() * (max - min) + min)
}


/**
 * Nhận uuid
 */
export function getUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        return (c === 'x' ? (Math.random() * 16 | 0) : ('r&0x3' | '0x8')).toString(16)
    })
}


/**
 * Xác minh định dạng số điện thoại di động
 * @param {string} mobile Số điện thoại di động
 * @param {string} areaCode mã vùng
 * @returns {boolean}
 */
export function validateMobile(mobile, areaCode) {
    // Xóa tất cả các ký tự không phải số
    const cleanMobile = mobile.replace(/\D/g, '');

    // Sử dụng các quy tắc xác thực khác nhau dựa trên các mã vùng khác nhau
    switch (areaCode) {
        case '+86': // Trung Quốc đại lục
            return /^1[3-9]\d{9}$/.test(cleanMobile);
        case '+852': // Hồng Kông, Trung Quốc
            return /^[569]\d{7}$/.test(cleanMobile);
        case '+853': // Ma Cao, Trung Quốc
            return /^6\d{7}$/.test(cleanMobile);
        case '+886': // Đài Loan, Trung Quốc
            return /^9\d{8}$/.test(cleanMobile);
        case '+1': // Hoa Kỳ/Canada
            return /^[2-9]\d{9}$/.test(cleanMobile);
        case '+44': // Vương quốc Anh
            return /^7[1-9]\d{8}$/.test(cleanMobile);
        case '+81': // Nhật Bản
            return /^[7890]\d{8}$/.test(cleanMobile);
        case '+82': // Hàn Quốc
            return /^1[0-9]\d{7}$/.test(cleanMobile);
        case '+65': // singapore
            return /^[89]\d{7}$/.test(cleanMobile);
        case '+61': // Úc
            return /^[4578]\d{8}$/.test(cleanMobile);
        case '+49': // nước Đức
            return /^1[5-7]\d{8}$/.test(cleanMobile);
        case '+33': // Pháp
            return /^[67]\d{8}$/.test(cleanMobile);
        case '+39': // Ý
            return /^3[0-9]\d{8}$/.test(cleanMobile);
        case '+34': // Tây Ban Nha
            return /^[6-9]\d{8}$/.test(cleanMobile);
        case '+55': // Brazil
            return /^[1-9]\d{10}$/.test(cleanMobile);
        case '+91': // Ấn Độ
            return /^[6-9]\d{9}$/.test(cleanMobile);
        case '+971': // Các tiểu vương quốc Ả Rập thống nhất
            return /^[5]\d{8}$/.test(cleanMobile);
        case '+966': // Ả Rập Saudi
            return /^[5]\d{8}$/.test(cleanMobile);
        case '+880': // Bangladesh
            return /^1[3-9]\d{8}$/.test(cleanMobile);
        case '+234': // nigeria
            return /^[789]\d{9}$/.test(cleanMobile);
        case '+254': // Kenya
            return /^[17]\d{8}$/.test(cleanMobile);
        case '+255': // tanzania
            return /^[67]\d{8}$/.test(cleanMobile);
        case '+7': // Kazakhstan
            return /^[67]\d{9}$/.test(cleanMobile);
        default:
            // Các số quốc tế khác: tối thiểu 5 chữ số, tối đa 15 chữ số
            return /^\d{5,15}$/.test(cleanMobile);
    }
}


/**
 * Tạo cặp khóa SM2 (định dạng hex)
 * @returns {Object} Đối tượng chứa khóa chung và khóa riêng
 */
export function generateSm2KeyPairHex() {
    // Tạo cặp khóa SM2 bằng thư viện sm-crypto
    const sm2 = require('sm-crypto').sm2;
    const keypair = sm2.generateKeyPairHex();
    
    return {
        publicKey: keypair.publicKey,
        privateKey: keypair.privateKey,
        clientPublicKey: keypair.publicKey, // Khóa công khai của khách hàng
        clientPrivateKey: keypair.privateKey // Khóa riêng của khách hàng
    };
}

/**
 * Mã hóa khóa công khai SM2
 * @param {string} publicKey Khóa công khai (định dạng hex)
 * @param {string} plainText văn bản thuần túy
 * @returns {string} Văn bản mã hóa được mã hóa (định dạng thập lục phân)
 */
export function sm2Encrypt(publicKey, plainText) {
    if (!publicKey) {
        throw new Error('Khóa công khai không được là null hoặc undefined');
    }
    
    if (!plainText) {
        throw new Error('Văn bản cần mã hóa không được để trống');
    }
    
    const sm2 = require('sm-crypto').sm2;
    // Mã hóa SM2, thêm tiền tố 04 để biểu thị khóa chung không nén
    const encrypted = sm2.doEncrypt(plainText, publicKey, 1);
    // Chuyển đổi sang định dạng thập lục phân (phù hợp với phần phụ trợ, thêm tiền tố 04)
    const result = "04" + encrypted;
    
    return result;
}

/**
 * Giải mã khóa riêng SM2
 * @param {string} privateKey Khóa riêng (định dạng hex)
 * @param {string} cipherText Bản mã (định dạng hex)
 * @returns {string} văn bản gốc đã được giải mã
 */
export function sm2Decrypt(privateKey, cipherText) {
    const sm2 = require('sm-crypto').sm2;
    // Xóa tiền tố 04 (phù hợp với phần phụ trợ)
    const dataWithoutPrefix = cipherText.startsWith("04") ? cipherText.substring(2) : cipherText;
    // giải mã SM2
    return sm2.doDecrypt(dataWithoutPrefix, privateKey, 1);
}

/**
 * Chức năng chống rung
 * @param {Function} fn Chức năng chống rung
 * @param {number} delay Thời gian trễ (mili giây), mặc định 500ms
 * @param {boolean} immediate Có thực thi ngay lập tức hay không, mặc định là sai
 * @returns Chức năng {Function} sau khi xử lý chống rung
 */
export function debounce(fn, delay = 500, immediate = false) {
    let timer = null;
    
    return function (...args) {
        const context = this;
        
        if (timer) {
            clearTimeout(timer);
        }
        
        if (immediate && !timer) {
            fn.apply(context, args);
        }
        
        timer = setTimeout(() => {
            if (!immediate) {
                fn.apply(context, args);
            }
            timer = null;
        }, delay);
    };
}

