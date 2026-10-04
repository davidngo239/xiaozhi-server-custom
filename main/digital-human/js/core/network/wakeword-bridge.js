import { uiController } from '../../ui/controller.js?v=0205';
import { log } from '../../utils/logger.js?v=0205';

let wakewordSocket = null;
let reconnectTimer = null;
let reconnectAttempts = 0;
let shouldReconnect = true;
let wakewordRequestSeq = 0;
let onNextBridgeConnectedCallback = null;

const pendingWakewordRequests = new Map();

export function startWakewordBridgeListener() {
    if (wakewordSocket) {
        return wakewordSocket;
    }

    shouldReconnect = true;
    log('Đang kết nối cầu nối sự kiện đánh thức cục bộ...', 'info');
    tryConnect();
    return wakewordSocket;
}

function tryConnect() {
    const bridgeUrl = buildWakewordBridgeUrl();

    try {
        wakewordSocket = new WebSocket(bridgeUrl);
        wakewordSocket.onopen = () => {
            reconnectAttempts = 0;
            log(`Đã kết nối cầu nối sự kiện đánh thức cục bộ: ${bridgeUrl}`, 'success');
            // Kết nối thành công tự động Lưu địa chỉ, sau khi làm mới vẫn có thể ghi nhớ
            localStorage.setItem('xz_tester_wakewordWsUrl', bridgeUrl);
            const urlInput = document.getElementById('wakewordWsUrl');
            if (urlInput) urlInput.value = bridgeUrl;
        };

        wakewordSocket.onerror = () => {
            log(`Kết nối cầu nối sự kiện đánh thức cục bộ thất bại: ${bridgeUrl}`, 'error');
        };

        wakewordSocket.onmessage = async (event) => {
            try {
                const message = parseWakewordBridgeMessage(event.data);
                if (message.requestId && pendingWakewordRequests.has(message.requestId)) {
                    settleWakewordRequest(message);
                    return;
                }

                if (message.success === false) {
                    log(`Cầu nối sự kiện đánh thức cục bộ báo lỗi: ${message.error || 'Lỗi không xác định'}`, 'error');
                    return;
                }

                if (message.type === 'bridge_connected') {
                    log('Bộ theo dõi đánh thức cục bộ đã sẵn sàng', 'info');
                    if (onNextBridgeConnectedCallback) {
                        const cb = onNextBridgeConnectedCallback;
                        onNextBridgeConnectedCallback = null;
                        cb(message);
                    }
                    return;
                }

                if (message.type === 'service_ready') {
                    log('Dịch vụ đánh thức cục bộ đã khởi động', 'info');
                    return;
                }

                if (message.type === 'wakeword_config') {
                    uiController.applyWakewordConfig(message.payload || {});
                    log('Đã đồng bộ danh sách từ đánh thức cục bộ', 'info');
                    return;
                }

                if (message.type === 'service_stopping') {
                    log('Dịch vụ đánh thức cục bộ đang dừng', 'warning');
                    return;
                }

                if (message.type === 'wake_word_detected') {
                    const wakeWord = message.payload?.wake_word || 'Từ đánh thức';
                log(`Đã nhận sự kiện đánh thức cục bộ: ${wakeWord}`, 'info');
                    await uiController.triggerWakewordDial(wakeWord);
                }
            } catch (error) {
                log(`Phân tích sự kiện đánh thức cục bộ thất bại: ${error.message}`, 'error');
            }
        };

        wakewordSocket.onclose = () => {
            if (wakewordSocket) {
                wakewordSocket = null;
            }

            rejectAllWakewordRequests('Kết nối sự kiện đánh thức cục bộ đã ngắt');

            if (!shouldReconnect) {
                return;
            }

            if (reconnectTimer) {
                return;
            }

            reconnectAttempts += 1;
            const delay = Math.min(1000 * reconnectAttempts, 5000);
            log(`Cầu nối đánh thức cục bộ sẽ kết nối lại sau ${delay} ms: ${bridgeUrl}`, 'warning');
            reconnectTimer = window.setTimeout(() => {
                reconnectTimer = null;
                tryConnect();
            }, delay);
        };

        return wakewordSocket;
    } catch (error) {
        log(`khởi độngcục bộđánh thứctheo dõithất bại: ${error.message}`, 'error');
        return null;
    }
}

export function stopWakewordBridgeListener() {
    shouldReconnect = false;

    if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }

    if (!wakewordSocket) {
        return;
    }

    wakewordSocket.onclose = null;
    wakewordSocket.close();
    wakewordSocket = null;
}

export function sendWakewordBridgeMessage(type, payload = {}, requestId = null) {
    if (!wakewordSocket || wakewordSocket.readyState !== WebSocket.OPEN) {
        log('Chưa kết nối sự kiện đánh thức cục bộ，Không thể gửithông điệp', 'warning');
        return false;
    }

    wakewordSocket.send(JSON.stringify({
        type,
        requestId,
        payload,
    }));
    return true;
}

export function requestWakewordBridge(type, payload = {}, timeout = 5000) {
    const requestId = `wakeword-${Date.now()}-${++wakewordRequestSeq}`;

    return new Promise((resolve, reject) => {
        const timer = window.setTimeout(() => {
            pendingWakewordRequests.delete(requestId);
            reject(new Error('Dịch vụ đánh thức cục bộ phản hồi quá thời gian chờ'));
        }, timeout);

        pendingWakewordRequests.set(requestId, { resolve, reject, timer });

        if (!sendWakewordBridgeMessage(type, payload, requestId)) {
            window.clearTimeout(timer);
            pendingWakewordRequests.delete(requestId);
            reject(new Error('Chưa kết nối sự kiện đánh thức cục bộ'));
        }
    });
}

export function getWakewordBridgeUrl() {
    if (wakewordSocket && wakewordSocket.url) {
        return wakewordSocket.url;
    }
    return buildWakewordBridgeUrl();
}

export function onNextBridgeConnected(callback) {
    onNextBridgeConnectedCallback = callback;
}

function buildWakewordBridgeUrl() {
    const configured = localStorage.getItem('xz_tester_wakewordWsUrl');
    if (configured && configured.trim()) {
        return configured.trim();
    }
    return 'ws://127.0.0.1:8006/wakeword-ws';
}

function parseWakewordBridgeMessage(rawData) {
    const message = JSON.parse(rawData);
    return {
        type: message.type || '',
        requestId: message.requestId || null,
        success: message.success !== false,
        payload: message.payload || {},
        error: message.error || null,
    };
}

function settleWakewordRequest(message) {
    const pendingRequest = pendingWakewordRequests.get(message.requestId);
    if (!pendingRequest) {
        return;
    }

    window.clearTimeout(pendingRequest.timer);
    pendingWakewordRequests.delete(message.requestId);

    if (message.success === false) {
        pendingRequest.reject(new Error(message.error || 'Dịch vụ đánh thức cục bộ trả về lỗi'));
        return;
    }

    pendingRequest.resolve(message);
}

function rejectAllWakewordRequests(errorMessage) {
    pendingWakewordRequests.forEach((pendingRequest) => {
        window.clearTimeout(pendingRequest.timer);
        pendingRequest.reject(new Error(errorMessage));
    });
    pendingWakewordRequests.clear();
}
