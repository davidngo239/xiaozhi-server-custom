// Mô-đun xử lý tin nhắn WebSocket
import { getConfig, saveConnectionUrls } from '../../config/manager.js?v=0205';
import { uiController } from '../../ui/controller.js?v=0205';
import { log } from '../../utils/logger.js?v=0205';
import { getAudioPlayer } from '../audio/player.js?v=0205';
import { getAudioRecorder } from '../audio/recorder.js?v=0205';
import { executeMcpTool, getMcpTools, setWebSocket as setMcpWebSocket } from '../mcp/tools.js?v=0205';
import { webSocketConnect } from './ota-connector.js?v=0205';

// Lớp xử lý WebSocket
export class WebSocketHandler {
    constructor() {
        this.websocket = null;
        this.onConnectionStateChange = null;
        this.onRecordButtonStateChange = null;
        this.onSessionStateChange = null;
        this.onSessionEmotionChange = null;
        this.onChatMessage = null; // Mới: Gọi lại tin nhắn trò chuyện
        this.currentSessionId = null;
        this.isRemoteSpeaking = false;
    }

    // Gửi tin nhắn bắt tay xin chào
    async sendHelloMessage() {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) return false;

        try {
            const config = getConfig();

            const helloMessage = {
                type: 'hello',
                device_id: config.deviceId,
                device_name: config.deviceName,
                device_mac: config.deviceMac,
                token: config.token,
                features: {
                    mcp: true,
                    emoji: config.emojiEnabled
                }
            };

            log('Đang gửi thông điệp bắt tay hello', 'info');
            this.websocket.send(JSON.stringify(helloMessage));

            return new Promise(resolve => {
                const timeout = setTimeout(() => {
                    log('chờhellophản hồiquá thời gian chờ', 'error');
                    log('Gợi ý: hãy nhấn nút "Kiểm tra xác thực" để chẩn đoán kết nối', 'info');
                    resolve(false);
                }, 5000);

                const onMessageHandler = (event) => {
                    try {
                        const response = JSON.parse(event.data);
                        if (response.type === 'hello' && response.session_id) {
                            log(`Máy chủ bắt tay thành công, ID phiên: ${response.session_id}`, 'success');
                            clearTimeout(timeout);
                            this.websocket.removeEventListener('message', onMessageHandler);
                            resolve(true);
                        }
                    } catch (e) {
                        // Bỏ qua các tin nhắn không phải JSON
                    }
                };

                this.websocket.addEventListener('message', onMessageHandler);
            });
        } catch (error) {
            log(`gửihellothông điệplỗi: ${error.message}`, 'error');
            return false;
        }
    }

    _sendWakeupMessages(sessionId) {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) return;

        // listen detect
        this.websocket.send(JSON.stringify({
            session_id: sessionId,
            type: 'listen',
            state: 'detect',
            text: 'Xin chào!'
        }));
        log('Gửi thông điệp listen detect, từ đánh thức: Xin chào!', 'info');

        // nghe bắt đầu: bắt đầu nghe
        this.websocket.send(JSON.stringify({
            session_id: sessionId,
            type: 'listen',
            state: 'start',
            mode: 'auto'
        }));
        log('gửilisten startthông điệp', 'info');
    }

    // Xử lý tin nhắn văn bản
    handleTextMessage(message) {
        if (message.type === 'hello') {
            log(`Máy chủ phản hồi: ${JSON.stringify(message, null, 2)}`, 'success');
            window.cameraAvailable = true;
            log('Kết nối thành công, camera đã sẵn sàng', 'success');
            uiController.updateDialButton(true);

            this._sendWakeupMessages(message.session_id);

            uiController.startAIChatSession();
        } else if (message.type === 'tts') {
            this.handleTTSMessage(message);
        } else if (message.type === 'audio') {
            log(`Nhận thông điệp điều khiển âm thanh: ${JSON.stringify(message)}`, 'info');
        } else if (message.type === 'stt') {
            log(`Kết quả nhận dạng: ${message.text}`, 'info');
            // Kiểm tra xem thiết bị có cần được ràng buộc không
            if (message.text && (message.text.includes('绑定') || message.text.includes('bind') || message.text.toLowerCase().includes('liên kết thiết bị'))) {
                log('Nhận hướng dẫn liên kết thiết bị, cập nhật trạng thái camera', 'warning');
                window.cameraAvailable = false;
                // ĐóngCamera
                if (typeof window.stopCamera === 'function') {
                    window.stopCamera();
                }
                // Cập nhật trạng thái nút Máy ảnh
                const cameraBtn = document.getElementById('cameraBtn');
                if (cameraBtn) {
                    cameraBtn.classList.remove('camera-active');
                    cameraBtn.querySelector('.btn-text').textContent = 'Camera';
                    cameraBtn.disabled = true;
                    cameraBtn.title = 'Vui lòng liên kết thiết bị bằng mã xác minh trước';
                }
            }
            // Hiển thị tin nhắn STT bằng cách gọi lại tin nhắn trò chuyện mới
            if (this.onChatMessage && message.text) {
                this.onChatMessage(message.text, true);
            }
        } else if (message.type === 'llm') {
            log(`Trợ lý trả lời: ${message.text}`, 'info');
            // Hiển thị câu trả lời LLM bằng cách gọi lại tin nhắn trò chuyện mới
            if (this.onChatMessage && message.text) {
                this.onChatMessage(message.text, false);
            }

            // Nếu bao gồm biểu tượng cảm xúc, hãy cập nhật biểu tượng cảm xúc sessionStatus và kích hoạt hành động Live2D
            if (message.text && /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/u.test(message.text)) {
                // Trích xuất biểu tượng cảm xúc
                const emojiMatch = message.text.match(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/u);
                if (emojiMatch && this.onSessionEmotionChange) {
                    this.onSessionEmotionChange(emojiMatch[0]);
                }

                // Kích hoạt hành động cảm xúc Live2D
                if (message.emotion) {
                    console.log(`Nhận thông điệp cảm xúc: emotion=${message.emotion}, text=${message.text}`);
                    this.triggerLive2DEmotionAction(message.emotion);
                }
            }

            // Chỉ thêm vào cuộc trò chuyện nếu văn bản không chỉ là biểu tượng cảm xúc
            // Kiểm tra xem còn nội dung hay không sau khi xóa biểu tượng cảm xúc khỏi văn bản
            const textWithoutEmoji = message.text ? message.text.replace(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu, '').trim() : '';
            if (textWithoutEmoji && this.onChatMessage) {
                this.onChatMessage(message.text, false);
            }
        } else if (message.type === 'mcp') {
            this.handleMCPMessage(message);
        } else {
            log(`Loại thông điệp không xác định: ${message.type}`, 'info');
            if (this.onChatMessage) {
                this.onChatMessage(`Loại thông điệp không xác định: ${message.type}\n${JSON.stringify(message, null, 2)}`, false);
            }
        }
    }

    // Xử lý tin nhắn TTS
    handleTTSMessage(message) {
        if (message.state === 'start') {
            log('Máy chủ bắt đầu gửi giọng nói', 'info');
            this.currentSessionId = message.session_id;
            this.isRemoteSpeaking = true;
            if (this.onSessionStateChange) {
                this.onSessionStateChange(true);
            }

            // Bắt đầu hoạt hình nói Live2D
            this.startLive2DTalking();
        } else if (message.state === 'sentence_start') {
            log(`Máy chủ gửi đoạn thoại: ${message.text}`, 'info');
            this.ttsSentenceCount = (this.ttsSentenceCount || 0) + 1;

            if (message.text && this.onChatMessage) {
                this.onChatMessage(message.text, false);
            }

            // Đảm bảo hoạt ảnh chạy ở đầu câu
            const live2dManager = window.chatApp?.live2dManager;
            if (live2dManager && !live2dManager.isTalking) {
                this.startLive2DTalking();
            }
        } else if (message.state === 'sentence_end') {
            log(`Đoạn thoại kết thúc: ${message.text}`, 'info');

            // Hoạt ảnh không bị xóa khi câu kết thúc, chờ câu tiếp theo hoặc cuối cùng dừng lại
        } else if (message.state === 'stop') {
            log('Máy chủ đã gửi xong giọng nói; đã xóa bộ đệm âm thanh', 'info');

            // Đã xóa toàn bộ bộ đệm âm thanh và ngừng phát
            const audioPlayer = getAudioPlayer();
            audioPlayer.clearAllAudio();

            this.isRemoteSpeaking = false;
            if (this.onRecordButtonStateChange) {
                this.onRecordButtonStateChange(false);
            }
            if (this.onSessionStateChange) {
                this.onSessionStateChange(false);
            }

            // Trì hoãn dừng hoạt ảnh nói Live2D để đảm bảo tất cả các câu đã phát xong
            setTimeout(() => {
                this.stopLive2DTalking();
                this.ttsSentenceCount = 0; // đặt lại bộ đếm
            }, 1000); // Trì hoãn 1 giây để đảm bảo hoàn thành tất cả các câu
        }
    }

    // Bắt đầu hoạt hình nói Live2D
    startLive2DTalking() {
        try {
            // Nhận phiên bản trình quản lý Live2D
            const live2dManager = window.chatApp?.live2dManager;
            if (live2dManager && live2dManager.live2dModel) {
                // Sử dụng nút phân tích của trình phát âm thanh
                live2dManager.startTalking();
                log('Đã khởi chạy hoạt ảnh nói chuyện Live2D', 'info');
            }
        } catch (error) {
            log(`Khởi chạy hoạt ảnh nói chuyện Live2D thất bại: ${error.message}`, 'error');
        }
    }

    // Dừng hoạt hình nói chuyện Live2D
    stopLive2DTalking() {
        try {
            const live2dManager = window.chatApp?.live2dManager;
            if (live2dManager) {
                live2dManager.stopTalking();
                log('Đã dừng hoạt ảnh nói chuyện Live2D', 'info');
            }
        } catch (error) {
            log(`Dừng hoạt ảnh nói chuyện Live2D thất bại: ${error.message}`, 'error');
        }
    }

    // Khởi tạo bộ phân tích âm thanh Live2D
    initializeLive2DAudioAnalyzer() {
        try {
            const live2dManager = window.chatApp?.live2dManager;
            if (live2dManager) {
                // Khởi tạo bộ phân tích âm thanh (sử dụng ngữ cảnh của trình phát âm thanh)
                if (live2dManager.initializeAudioAnalyzer()) {
                    log('Đã khởi tạo bộ phân tích âm thanh Live2D và kết nối với trình phát', 'success');
                } else {
                    log('Khởi tạo bộ phân tích âm thanh Live2D thất bại, sẽ dùng hoạt ảnh mô phỏng', 'warning');
                }
            }
        } catch (error) {
            log(`Khởi tạo bộ phân tích âm thanh Live2D thất bại: ${error.message}`, 'error');
        }
    }

    // Xử lý tin nhắn MCP
    handleMCPMessage(message) {
        const payload = message.payload || {};
        log(`Máy chủ gửi xuống: ${JSON.stringify(message)}`, 'info');

        if (payload.method === 'tools/list') {
            const tools = getMcpTools();

            const replyMessage = JSON.stringify({
                "session_id": message.session_id || "",
                "type": "mcp",
                "payload": {
                    "jsonrpc": "2.0",
                    "id": payload.id,
                    "result": {
                        "tools": tools
                    }
                }
            });
            log(`Máy khách báo cáo: ${replyMessage}`, 'info');
            this.websocket.send(replyMessage);
            log(`Trả lời danh sách công cụ MCP: ${tools.length} công cụ`, 'info');

        } else if (payload.method === 'tools/call') {
            const toolName = payload.params?.name;
            const toolArgs = payload.params?.arguments;

            log(`Gọi công cụ: ${toolName}; tham số: ${JSON.stringify(toolArgs)}`, 'info');

            executeMcpTool(toolName, toolArgs).then(result => {
                const replyMessage = JSON.stringify({
                    "session_id": message.session_id || "",
                    "type": "mcp",
                    "payload": {
                        "jsonrpc": "2.0",
                        "id": payload.id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": JSON.stringify(result)
                                }
                            ],
                            "isError": false
                        }
                    }
                });

                log(`Máy khách báo cáo: ${replyMessage}`, 'info');
                this.websocket.send(replyMessage);
            }).catch(error => {
                log(`Thực thi công cụ thất bại: ${error.message}`, 'error');
                const errorReply = JSON.stringify({
                    "session_id": message.session_id || "",
                    "type": "mcp",
                    "payload": {
                        "jsonrpc": "2.0",
                        "id": payload.id,
                        "error": {
                            "code": -32603,
                            "message": error.message
                        }
                    }
                });
                this.websocket.send(errorReply);
            });
        } else if (payload.method === 'initialize') {
            log(`nhậncông cụkhởi tạoyêu cầu: ${JSON.stringify(payload.params)}`, 'info');
            // Lưu địa chỉ giao diện phân tích trực quan
            const visionUrl = document.getElementById('visionUrl');
            const visionConfig = payload?.params?.capabilities?.vision;
            if (visionConfig && typeof visionConfig === 'object' && visionConfig.url && visionConfig.token) {
                const visionConfigStr = JSON.stringify(visionConfig);
                localStorage.setItem('xz_tester_vision', visionConfigStr);
                if (visionUrl) visionUrl.value = visionConfig.url;
            } else {
                localStorage.removeItem('xz_tester_vision');
                if (visionUrl) visionUrl.value = '';
            }

            const replyMessage = JSON.stringify({
                "session_id": message.session_id || "",
                "type": "mcp",
                "payload": {
                    "jsonrpc": "2.0",
                    "id": payload.id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "xiaozhi-web-test",
                            "version": "2.1.0"
                        }
                    }
                }
            });
            log('Trả lời xác nhận khởi tạo', 'info');
            this.websocket.send(replyMessage);
        } else {
            log(`Phương thức MCP không xác định: ${payload.method}`, 'warning');
        }
    }

    // Xử lý tin nhắn nhị phân
    async handleBinaryMessage(data) {
        try {
            let arrayBuffer;
            if (data instanceof ArrayBuffer) {
                arrayBuffer = data;
            } else if (data instanceof Blob) {
                arrayBuffer = await data.arrayBuffer();
                log(`Nhận dữ liệu âm thanh Blob, kích thước: ${arrayBuffer.byteLength} byte`, 'debug');
            } else {
                log(`Nhận dữ liệu nhị phân không xác định: ${typeof data}`, 'warning');
                return;
            }

            const opusData = new Uint8Array(arrayBuffer);
            const audioPlayer = getAudioPlayer();
            audioPlayer.enqueueAudioData(opusData);
        } catch (error) {
            log(`Xử lý thông điệp nhị phân gặp lỗi: ${error.message}`, 'error');
        }
    }

    // Kết nối với máy chủ WebSocket
    async connect() {
        const config = getConfig();
        log('Đang kiểm tra trạng thái OTA...', 'info');
        saveConnectionUrls();

        try {
            const otaUrl = document.getElementById('otaUrl').value.trim();
            const ws = await webSocketConnect(otaUrl, config);
            if (ws === undefined) {
                return false;
            }
            this.websocket = ws;

            // Loại dữ liệu nhị phân mà Cài đặt nhận được là ArrayBuffer
            this.websocket.binaryType = 'arraybuffer';

            // Phiên bản WebSocket của mô-đun Cài đặt MCP
            setMcpWebSocket(this.websocket);

            // Cài đặt WebSocket Ghi âm
            const audioRecorder = getAudioRecorder();
            audioRecorder.setWebSocket(this.websocket);

            this.setupEventHandlers();

            return true;
        } catch (error) {
            log(`kết nốilỗi: ${error.message}`, 'error');
            if (this.onConnectionStateChange) {
                this.onConnectionStateChange(false);
            }
            return false;
        }
    }

    // Cài đặt trình xử lý sự kiện
    setupEventHandlers() {
        this.websocket.onopen = async () => {
            const url = document.getElementById('serverUrl').value;
            log(`Đã kết nối đến máy chủ: ${url}`, 'success');

            if (this.onConnectionStateChange) {
                this.onConnectionStateChange(true);
            }

            // Sau khi Kết nối thành công, trạng thái mặc định là đang nghe
            this.isRemoteSpeaking = false;
            if (this.onSessionStateChange) {
                this.onSessionStateChange(false);
            }

            // Khởi tạo bộ phân tích âm thanh Live2D khi kết nối WebSocketConnect thành công
            this.initializeLive2DAudioAnalyzer();

            await this.sendHelloMessage();
        };

        this.websocket.onclose = () => {
            log('Đã Ngắt kết nối', 'info');

            if (this.onConnectionStateChange) {
                this.onConnectionStateChange(false);
            }

            const audioRecorder = getAudioRecorder();
            audioRecorder.stop();

            // ĐóngCamera
            if (typeof window.stopCamera === 'function') {
                window.stopCamera();
            }

            // Ẩn khu vực hiển thị Camera
            const cameraContainer = document.getElementById('cameraContainer');
            if (cameraContainer) {
                cameraContainer.classList.remove('active');
            }
        };

        this.websocket.onerror = (error) => {
            log(`Lỗi WebSocket: ${error.message || 'Lỗi không xác định'}`, 'error');
            uiController.addChatMessage(`⚠️ Lỗi WebSocket: ${error.message || 'Lỗi không xác định'}`, false);
            if (this.onConnectionStateChange) {
                this.onConnectionStateChange(false);
            }
        };

        this.websocket.onmessage = (event) => {
            try {
                if (typeof event.data === 'string') {
                    const message = JSON.parse(event.data);
                    this.handleTextMessage(message);
                } else {
                    this.handleBinaryMessage(event.data);
                }
            } catch (error) {
                log(`WebSocketthông điệpxử lýlỗi: ${error.message}`, 'error');
                // Hàm addMessage cũ không còn được sử dụng vì phần tử talkDiv không tồn tại
                // Thông báo lỗi sẽ được hiển thị bằng các phương tiện khác
            }
        };
    }

    // Ngắt kết nối
    disconnect() {
        if (!this.websocket) return;

        this.websocket.close();
        const audioRecorder = getAudioRecorder();
        audioRecorder.stop();

        // ĐóngCamera
        if (typeof window.stopCamera === 'function') {
            window.stopCamera();
        }

        // Ẩn khu vực hiển thị Camera
        const cameraContainer = document.getElementById('cameraContainer');
        if (cameraContainer) {
            cameraContainer.classList.remove('active');
        }
    }

    // Gửi tin nhắn văn bản
    sendTextMessage(text) {
        if (text === '' || !this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            return false;
        }

        try {
            // Nếu bên kia đang nói chuyện, trước tiên hãy gửi tin nhắn ngắt
            if (this.isRemoteSpeaking && this.currentSessionId) {
                const abortMessage = {
                    session_id: this.currentSessionId,
                    type: 'abort',
                    reason: 'wake_word_detected'
                };
                this.websocket.send(JSON.stringify(abortMessage));
                log('Gửi thông điệp ngắt lời', 'info');
            }

            const listenMessage = {
                type: 'listen',
                state: 'detect',
                text: text
            };

            this.websocket.send(JSON.stringify(listenMessage));
            log(`Gửi tin nhắn văn bản: ${text}`, 'info');

            return true;
        } catch (error) {
            log(`gửithông điệplỗi: ${error.message}`, 'error');
            return false;
        }
    }

    /**
     * Kích hoạt hành động cảm xúc Live2D
     * @param {string} emotion - Tên cảm xúc
     */
    triggerLive2DEmotionAction(emotion) {
        try {
            const live2dManager = window.chatApp?.live2dManager;
            if (live2dManager && typeof live2dManager.triggerEmotionAction === 'function') {
                live2dManager.triggerEmotionAction(emotion);
                log(`Kích hoạt biểu cảm Live2D: ${emotion}`, 'info');
            } else {
                log('Không thể kích hoạt biểu cảm Live2D: không tìm thấy trình quản lý hoặc phương thức không khả dụng', 'warning');
            }
        } catch (error) {
            log(`Kích hoạt biểu cảm Live2D thất bại: ${error.message}`, 'error');
        }
    }

    // Nhận phiên bản WebSocket
    getWebSocket() {
        return this.websocket;
    }

    // Kiểm tra xem đã kết nối chưa
    isConnected() {
        return this.websocket && this.websocket.readyState === WebSocket.OPEN;
    }
}

// Tạo một singleton
let wsHandlerInstance = null;

export function getWebSocketHandler() {
    if (!wsHandlerInstance) {
        wsHandlerInstance = new WebSocketHandler();
    }
    return wsHandlerInstance;
}
