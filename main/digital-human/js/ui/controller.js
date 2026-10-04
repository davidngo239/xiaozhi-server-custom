// Mô-đun điều khiển giao diện người dùng
import { loadConfig, saveConfig } from '../config/manager.js?v=0205';
import { getAudioPlayer } from '../core/audio/player.js?v=0205';
import { getAudioRecorder } from '../core/audio/recorder.js?v=0205';
import { requestWakewordBridge, stopWakewordBridgeListener, startWakewordBridgeListener, getWakewordBridgeUrl, onNextBridgeConnected } from '../core/network/wakeword-bridge.js?v=0205';
import { getWebSocketHandler } from '../core/network/websocket.js?v=0205';
import { log } from '../utils/logger.js?v=0205';

// Lớp trình điều khiển giao diện người dùng
class UIController {
    constructor() {
        this.isEditing = false;
        this.visualizerCanvas = null;
        this.visualizerContext = null;
        this.audioStatsTimer = null;
        this.currentBackgroundIndex = localStorage.getItem('backgroundIndex') ? parseInt(localStorage.getItem('backgroundIndex')) : 0;
        this.backgroundImages = ['1.png', '2.png', '3.png'];
        this.dialBtnDisabled = false;
        this.isConnecting = false;
        this.lastWakewordDialTime = 0;

        // Bind methods
        this.init = this.init.bind(this);
        this.initEventListeners = this.initEventListeners.bind(this);
        this.updateDialButton = this.updateDialButton.bind(this);
        this.addChatMessage = this.addChatMessage.bind(this);
        this.switchBackground = this.switchBackground.bind(this);
        this.switchLive2DModel = this.switchLive2DModel.bind(this);
        this.showModal = this.showModal.bind(this);
        this.hideModal = this.hideModal.bind(this);
        this.switchTab = this.switchTab.bind(this);
        this.applyWakewordConfig = this.applyWakewordConfig.bind(this);
        this.handleApplyWakeword = this.handleApplyWakeword.bind(this);
        this.triggerWakewordDial = this.triggerWakewordDial.bind(this);
    }

    // Khởi tạo
    init() {
        console.log('UIController init started');

        this.visualizerCanvas = document.getElementById('audioVisualizer');
        if (this.visualizerCanvas) {
            this.visualizerContext = this.visualizerCanvas.getContext('2d');
            this.initVisualizer();
        }

        // Kiểm tra xem nút kết nối có tồn tại trong quá trình khởi tạo không
        const connectBtn = document.getElementById('connectBtn');
        console.log('connectBtn during init:', connectBtn);

        this.initEventListeners();
        this.startAudioStatsMonitor();
        loadConfig();

        // Register recording callback
        const audioRecorder = getAudioRecorder();
        audioRecorder.onRecordingStart = (seconds) => {
            this.updateRecordButtonState(true, seconds);
        };

        // Khởi tạo hiển thị trạng thái
        this.updateConnectionUI(false);
        // Apply saved background
        const backgroundContainer = document.querySelector('.background-container');
        if (backgroundContainer) {
            backgroundContainer.style.backgroundImage = `url('./images/${this.backgroundImages[this.currentBackgroundIndex]}')`;
        }

        this.updateDialButton(false);

        console.log('UIController init completed');
    }

    // Khởi tạo trình hiển thị
    initVisualizer() {
        if (this.visualizerCanvas) {
            this.visualizerCanvas.width = this.visualizerCanvas.clientWidth;
            this.visualizerCanvas.height = this.visualizerCanvas.clientHeight;
            this.visualizerContext.fillStyle = '#fafafa';
            this.visualizerContext.fillRect(0, 0, this.visualizerCanvas.width, this.visualizerCanvas.height);
        }
    }

    // Khởi tạo trình xử lý sự kiện
    initEventListeners() {
        // Nút cài đặt
        const settingsBtn = document.getElementById('settingsBtn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => {
                this.showModal('settingsModal');
            });
        }

        // Nút chuyển đổi nền
        const backgroundBtn = document.getElementById('backgroundBtn');
        if (backgroundBtn) {
            backgroundBtn.addEventListener('click', this.switchBackground);
        }

        // Sự kiện thay đổi chọn mô hình
        const modelSelect = document.getElementById('live2dModelSelect');
        if (modelSelect) {
            modelSelect.addEventListener('change', () => {
                this.switchLive2DModel();
            });
        }

        // Nút chuyển đổi máy ảnh
        const cameraSwitch = document.getElementById('cameraSwitch');
        const cameraSwitchMask = document.getElementById('cameraSwitchMask');
        if (cameraSwitchMask) {
            cameraSwitchMask.addEventListener('click', () => {
                const isCameraActive = cameraSwitch.classList.contains('active');
                if (isCameraActive) {
                    window.switchCamera();
                }
            })
        }

        // Nút quay số
        const dialBtn = document.getElementById('dialBtn');
        if (dialBtn) {
            dialBtn.addEventListener('click', () => {
                dialBtn.disabled = true;
                this.dialBtnDisabled = true;
                setTimeout(() => {
                    dialBtn.disabled = false;
                    this.dialBtnDisabled = false;
                }, 3000);

                const wsHandler = getWebSocketHandler();
                const isConnected = wsHandler.isConnected();

                if (isConnected) {
                    wsHandler.disconnect();
                    this.updateDialButton(false);
                    if (cameraSwitch) cameraSwitch.classList.remove('active');
                    this.addChatMessage('Disconnected, see you next time~😊', false);
                } else {
                    // Kiểm tra xem URL OTA đã được điền chưa
                    const otaUrlInput = document.getElementById('otaUrl');
                    if (!otaUrlInput || !otaUrlInput.value.trim()) {
                        // Nếu URL OTA không được điền, hãy hiển thị chế độ cài đặt và chuyển sang tab thiết bị
                        this.showModal('settingsModal');
                        this.switchTab('device');
                        this.addChatMessage('Please fill in OTA server URL', false);
                        return;
                    }

                    // Start connection process
                    this.handleConnect();
                }
            });
        }

        // Nút chụp ảnh
        const cameraBtn = document.getElementById('cameraBtn');
        let cameraTimer = null;
        if (cameraBtn) {
            cameraBtn.addEventListener('click', () => {
                if (cameraTimer) {
                    clearTimeout(cameraTimer);
                    cameraTimer = null;
                }
                cameraTimer = setTimeout(() => {
                    const cameraContainer = document.getElementById('cameraContainer');
                    if (!cameraContainer) {
                        log('Không tìm thấy vùng chứa camera', 'warning');
                        return;
                    }

                    const isActive = cameraContainer.classList.contains('active');
                    if (isActive) {
                        // ĐóngCamera
                        if (typeof window.stopCamera === 'function') {
                            if (cameraSwitch) cameraSwitch.classList.remove('active');
                            window.stopCamera();
                        }
                        cameraContainer.classList.remove('active');
                        cameraBtn.classList.remove('camera-active');
                        cameraBtn.querySelector('.btn-text').textContent = 'Camera';
                        log('camera đã tắt', 'info');
                    } else {
                        // Mở máy ảnh
                        if (typeof window.startCamera === 'function') {
                            window.startCamera().then(success => {
                                if (success) {
                                    cameraBtn.classList.add('camera-active');
                                    cameraBtn.querySelector('.btn-text').textContent = 'Đóng';
                                } else {
                                    this.addChatMessage('⚠️ Không thể bật camera. Kiểm tra quyền truy cập của trình duyệt', false);
                                }
                            }).catch(error => {
                                log(`khởi độngcamerasự cố: ${error.message}`, 'error');
                            });
                        } else {
                            log('Chưa định nghĩa hàm startCamera', 'warning');
                        }
                    }
                }, 300);
            });
        }

        // Nút ghi
        const recordBtn = document.getElementById('recordBtn');
        if (recordBtn) {
            let recordTimer = null;
            recordBtn.addEventListener('click', () => {
                if (recordTimer) {
                    clearTimeout(recordTimer);
                    recordTimer = null;
                }
                recordTimer = setTimeout(() => {
                    const audioRecorder = getAudioRecorder();
                    if (audioRecorder.isRecording) {
                        audioRecorder.stop();
                        // Khôi phục nút ghi về trạng thái bình thường
                        recordBtn.classList.remove('recording');
                        recordBtn.querySelector('.btn-text').textContent = 'Ghi âm';
                    } else {
                        // Cập nhật trạng thái nút để ghi
                        recordBtn.classList.add('recording');
                        recordBtn.querySelector('.btn-text').textContent = 'Đang ghi âm';

                        // Bắt đầu ghi, cập nhật trạng thái nút sau khi trì hoãn
                        setTimeout(() => {
                            audioRecorder.start();
                        }, 100);
                    }
                }, 300);
            });
        }

        // Trình nghe sự kiện nhập cuộc trò chuyện
        const chatIpt = document.getElementById('chatIpt');
        if (chatIpt) {
            const wsHandler = getWebSocketHandler();
            chatIpt.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    if (e.target.value) {
                        wsHandler.sendTextMessage(e.target.value);
                        e.target.value = '';
                        return;
                    }
                }
            });
        }

        // Nút đóng
        const closeButtons = document.querySelectorAll('.close-btn');
        closeButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const modal = e.target.closest('.modal');
                if (modal) {
                    if (modal.id === 'settingsModal') {
                        saveConfig();
                    }
                    this.hideModal(modal.id);
                }
            });
        });

        // Settings tab switch
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        const applyWakewordBtn = document.getElementById('applyWakewordBtn');
        if (applyWakewordBtn) {
            applyWakewordBtn.addEventListener('click', this.handleApplyWakeword);
        }

        // Nhấp vào nền hộp phương thức Đóng (chỉ dành cho các hộp phương thức cụ thể Tắt chức năng này)
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    // settingsModal, mcpToolModal, mcpPropertyModal chỉ có thể truy cập được bằng cách nhấn XĐóng
                    const nonClosableModals = ['settingsModal', 'mcpToolModal', 'mcpPropertyModal'];
                    if (nonClosableModals.includes(modal.id)) {
                        return; // Tắt tính năng nhấp vào nền Đóng
                    }
                    this.hideModal(modal.id);
                }
            });
        });

        // Thêm nút công cụ MCP
        const addMCPToolBtn = document.getElementById('addMCPToolBtn');
        if (addMCPToolBtn) {
            addMCPToolBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.addMCPTool();
            });
        }

        // Nút kết nối và nút gửi không bị loại bỏ, có thể thêm vào nút quay số sau
    }

    // Cập nhật giao diện trạng thái kết nối
    updateConnectionUI(isConnected) {
        const connectionStatus = document.getElementById('connectionStatus');
        const statusDot = document.querySelector('.status-dot');

        if (connectionStatus) {
            if (isConnected) {
                connectionStatus.textContent = 'Đã kết nối';
                if (statusDot) {
                    statusDot.className = 'status-dot status-connected';
                }
            } else {
                connectionStatus.textContent = 'Ngoại tuyến';
                if (statusDot) {
                    statusDot.className = 'status-dot status-disconnected';
                }
            }
        }
    }

    // Cập nhật trạng thái nút quay số
    updateDialButton(isConnected) {
        const dialBtn = document.getElementById('dialBtn');
        const recordBtn = document.getElementById('recordBtn');
        const cameraBtn = document.getElementById('cameraBtn');

        if (dialBtn) {
            if (isConnected) {
                dialBtn.classList.add('dial-active');
                dialBtn.querySelector('.btn-text').textContent = 'Ngắt kết nối';
                // Cập nhật biểu tượng nút quay số để gác máy
                dialBtn.querySelector('svg').innerHTML = `
                    <path d="M12,9C10.4,9 9,10.4 9,12C9,13.6 10.4,15 12,15C13.6,15 15,13.6 15,12C15,10.4 13.6,9 12,9M12,17C9.2,17 7,14.8 7,12C7,9.2 9.2,7 12,7C14.8,7 17,9.2 17,12C17,14.8 14.8,17 12,17M12,4.5C7,4.5 2.7,7.6 1,12C2.7,16.4 7,19.5 12,19.5C17,19.5 21.3,16.4 23,12C21.3,7.6 17,4.5 12,4.5Z"/>
                `;
            } else {
                dialBtn.classList.remove('dial-active');
                dialBtn.querySelector('.btn-text').textContent = 'Kết nối';
                // Khôi phục biểu tượng nút quay số
                dialBtn.querySelector('svg').innerHTML = `
                    <path d="M6.62,10.79C8.06,13.62 10.38,15.94 13.21,17.38L15.41,15.18C15.69,14.9 16.08,14.82 16.43,14.93C17.55,15.3 18.75,15.5 20,15.5A1,1 0 0,1 21,16.5V20A1,1 0 0,1 20,21A17,17 0 0,1 3,4A1,1 0 0,1 4,3H7.5A1,1 0 0,1 8.5,4C8.5,5.25 8.7,6.45 9.07,7.57C9.18,7.92 9.1,8.31 8.82,8.59L6.62,10.79Z"/>
                `;
            }
        }

        // Cập nhật trạng thái nút camera - đặt lại về mặc định khi bị ngắt kết nối
        if (cameraBtn && !isConnected) {
            const cameraContainer = document.getElementById('cameraContainer');
            if (cameraContainer && cameraContainer.classList.contains('active')) {
                cameraContainer.classList.remove('active');
            }
            cameraBtn.classList.remove('camera-active');
            cameraBtn.querySelector('.btn-text').textContent = 'Camera';
            cameraBtn.disabled = true;
            cameraBtn.title = 'Vui lòng kết nối server trước';
            // ĐóngCamera
            if (typeof window.stopCamera === 'function') {
                window.stopCamera();
            }
        }

        // Cập nhật trạng thái nút camera - bật khi được kết nối và có camera
        if (cameraBtn && isConnected) {
            if (window.cameraAvailable) {
                cameraBtn.disabled = false;
                cameraBtn.title = 'Bật/tắt camera';
            } else {
                cameraBtn.disabled = true;
                cameraBtn.title = 'Vui lòng liên kết thiết bị bằng mã xác minh trước';
            }
        }

        // Cập nhật trạng thái nút ghi
        if (recordBtn) {
            const microphoneAvailable = window.microphoneAvailable !== false;
            if (isConnected && microphoneAvailable) {
                recordBtn.disabled = false;
                recordBtn.title = 'Bắt đầu ghi âm';
                // Khôi phục nút ghi về trạng thái bình thường
                recordBtn.querySelector('.btn-text').textContent = 'Ghi âm';
                recordBtn.classList.remove('recording');
            } else {
                recordBtn.disabled = true;
                if (!microphoneAvailable) {
                    recordBtn.title = window.isHttpNonLocalhost ? 'Truy cập qua HTTP nên không thể ghi âm, chỉ có thể trò chuyện bằng văn bản' : 'Micro không khả dụng';
                } else {
                    recordBtn.title = 'Vui lòng kết nối server trước';
                }
                // Khôi phục nút ghi về trạng thái bình thường
                recordBtn.querySelector('.btn-text').textContent = 'Ghi âm';
                recordBtn.classList.remove('recording');
            }
        }
    }

    // Cập nhật trạng thái nút ghi
    updateRecordButtonState(isRecording, seconds = 0) {
        const recordBtn = document.getElementById('recordBtn');
        if (recordBtn) {
            if (isRecording) {
                recordBtn.querySelector('.btn-text').textContent = `Đang ghi âm`;
                recordBtn.classList.add('recording');
            } else {
                recordBtn.querySelector('.btn-text').textContent = 'Ghi âm';
                recordBtn.classList.remove('recording');
            }
            // Chỉ bật nút khi có micrô
            recordBtn.disabled = window.microphoneAvailable === false;
        }
    }

    /**
     * Cập nhật trạng thái sẵn có của micrô
     * @param {boolean} isAvailable - Whether microphone is available
     * @param {boolean} isHttpNonLocalhost - Whether it is HTTP non-localhost access
     */
    updateMicrophoneAvailability(isAvailable, isHttpNonLocalhost) {
        const recordBtn = document.getElementById('recordBtn');
        if (!recordBtn) return;
        if (!isAvailable) {
            // Tắt nút ghi
            recordBtn.disabled = true;
            // Cập nhật văn bản và tiêu đề của nút
            recordBtn.querySelector('.btn-text').textContent = 'Ghi âm';
            recordBtn.title = isHttpNonLocalhost ? 'Truy cập qua HTTP nên không thể ghi âm, chỉ có thể trò chuyện bằng văn bản' : 'Micro không khả dụng';

        } else {
            // Nếu được kết nối, hãy bật nút ghi
            const wsHandler = getWebSocketHandler();
            if (wsHandler && wsHandler.isConnected()) {
                recordBtn.disabled = false;
                recordBtn.title = 'Bắt đầu ghi âm';
            }
        }
    }

    // Thêm tin nhắn trò chuyện
    addChatMessage(content, isUser = false) {
        const chatStream = document.getElementById('chatStream');
        if (!chatStream) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${isUser ? 'user' : 'ai'}`;
        messageDiv.innerHTML = `<div class="message-bubble">${content}</div>`;
        chatStream.appendChild(messageDiv);

        // Scroll to bottom
        chatStream.scrollTop = chatStream.scrollHeight;
    }

    // Switch background
    switchBackground() {
        this.currentBackgroundIndex = (this.currentBackgroundIndex + 1) % this.backgroundImages.length;
        const backgroundContainer = document.querySelector('.background-container');
        if (backgroundContainer) {
            backgroundContainer.style.backgroundImage = `url('./images/${this.backgroundImages[this.currentBackgroundIndex]}')`;
        }
        localStorage.setItem('backgroundIndex', this.currentBackgroundIndex);
    }

    // Chuyển đổi mô hình Live2D
    switchLive2DModel() {
        const modelSelect = document.getElementById('live2dModelSelect');
        if (!modelSelect) {
            console.error('Không tìm thấy danh sách chọn mô hình.');
            return;
        }

        const selectedModel = modelSelect.value;
        const app = window.chatApp;

        if (app && app.live2dManager) {
            app.live2dManager.switchModel(selectedModel)
                .then(success => {
                    if (success) {
                        this.addChatMessage(`Đã chuyển sang mô hình: ${selectedModel}`, false);
                    } else {
                        this.addChatMessage('Không thể đổi mô hình', false);
                    }
                })
                .catch(error => {
                    console.error('Lỗi khi chuyển mô hình:', error);
                    this.addChatMessage('Lỗi khi đổi mô hình', false);
                });
        } else {
            this.addChatMessage('Bộ quản lý Live2D chưa được khởi tạo', false);
        }
    }

    // Show modal
    showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'flex';
        }
    }

    // Hide modal
    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
        }
    }

    // Switch tab
    switchTab(tabName) {
        // Xóa lớp đang hoạt động khỏi tất cả các tab
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');

        tabBtns.forEach(btn => btn.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));

        // Activate selected tab
        const activeTabBtn = document.querySelector(`[data-tab="${tabName}"]`);
        const activeTabContent = document.getElementById(`${tabName}Tab`);

        if (activeTabBtn && activeTabContent) {
            activeTabBtn.classList.add('active');
            activeTabContent.classList.add('active');
        }
    }

    applyWakewordConfig(config = {}) {
        const wakewordEnabledInput = document.getElementById('wakewordEnabled');
        const wakewordListInput = document.getElementById('wakewordList');

        if (!wakewordEnabledInput || !wakewordListInput) {
            return;
        }

        const wakeWords = Array.isArray(config.wakeWords)
            ? config.wakeWords.filter(item => typeof item === 'string' && item.trim())
            : [];

        wakewordEnabledInput.value = config.enabled === false ? 'false' : 'true';
        wakewordListInput.value = wakeWords.join('\n');
        saveConfig();
    }

    async handleApplyWakeword() {
        const wakewordEnabledInput = document.getElementById('wakewordEnabled');
        const wakewordListInput = document.getElementById('wakewordList');
        const wakewordWsUrlInput = document.getElementById('wakewordWsUrl');
        if (!wakewordEnabledInput || !wakewordListInput) {
            return;
        }

        const wakeWords = wakewordListInput.value
            .split(/\r?\n/u)
            .map(item => item.trim())
            .filter(Boolean)
            .filter((item, index, items) => items.indexOf(item) === index);

        const payload = {
            enabled: wakewordEnabledInput.value !== 'false',
            wakeWords,
        };

        if (payload.enabled && payload.wakeWords.length === 0) {
            this.addChatMessage('Cần nhập ít nhất một từ đánh thức khi bật tính năng này.', false);
            return;
        }

        const applyWakewordBtn = document.getElementById('applyWakewordBtn');
        if (applyWakewordBtn) {
            applyWakewordBtn.disabled = true;
            applyWakewordBtn.textContent = 'Đang áp dụng...';
        }

        try {
            // Lưu địa chỉ vào localStorage
            if (wakewordWsUrlInput && wakewordWsUrlInput.value.trim()) {
                localStorage.setItem('xz_tester_wakewordWsUrl', wakewordWsUrlInput.value.trim());
            }

            // So sánh địa chỉ mới với địa chỉ kết nối hiện tại
            const newWsUrl = localStorage.getItem('xz_tester_wakewordWsUrl');
            const currentWsUrl = getWakewordBridgeUrl();
            const urlChanged = newWsUrl !== currentWsUrl;

            if (urlChanged) {
                // Địa chỉ đã thay đổi, vui lòng xác nhận trước
                const shouldRestart = window.confirm('Địa chỉ đã thay đổi. Tiếp tục để ngắt kết nối cũ và kết nối lại?');
                if (!shouldRestart) {
                    // Khôi phục địa chỉ cũ trong localStorage
                    localStorage.setItem('xz_tester_wakewordWsUrl', currentWsUrl);
                    this.addChatMessage('Đã hủy thay đổi địa chỉ.', false);
                    return;
                }

                // Ngắt kết nối cũ
                stopWakewordBridgeListener();

                // Bắt đầu kết nối mới (tự động sử dụng địa chỉ mới)
                startWakewordBridgeListener();

                // v.v. bridge_connected
                await new Promise((resolve, reject) => {
                    const timeout = setTimeout(() => {
                        reject(new Error('Kết nối tới server mới quá thời gian chờ'));
                    }, 5000);

                    onNextBridgeConnected(() => {
                        clearTimeout(timeout);
                        resolve();
                    });
                });

                // Gửi cấu hình và khởi động lại
                await requestWakewordBridge('set_wakeword_config', payload);
                this.applyWakewordConfig(payload);
                await requestWakewordBridge('restart_wakeword_service');
                this.addChatMessage('Đã lưu cấu hình từ đánh thức. Dịch vụ đang khởi động lại.', false);
            } else {
                // Địa chỉ không thay đổi: thao tác trực tiếp trên kết nối hiện tại
                const response = await requestWakewordBridge('set_wakeword_config', payload);
                this.applyWakewordConfig(response.payload || payload);

                const shouldRestart = window.confirm('Đã lưu từ đánh thức. Khởi động lại dịch vụ ngay để áp dụng?');
                if (!shouldRestart) {
                    this.addChatMessage('Đã lưu cấu hình. Bạn có thể khởi động lại dịch vụ sau để áp dụng.', false);
                    return;
                }

                await requestWakewordBridge('restart_wakeword_service');
                this.addChatMessage('Đã lưu cấu hình từ đánh thức. Dịch vụ đang khởi động lại.', false);
            }
        } catch (error) {
            this.addChatMessage(`Không thể áp dụng từ đánh thức: ${error.message}`, false);
        } finally {
            if (applyWakewordBtn) {
                applyWakewordBtn.disabled = false;
                applyWakewordBtn.textContent = 'Áp dụng từ đánh thức';
            }
        }
    }

    // Bắt đầu phiên trò chuyện AI sau khi kết nối
    startAIChatSession() {
        this.addChatMessage('Kết nối thành công, bắt đầu trò chuyện nhé! 😊', false);
        // Kiểm tra tính khả dụng của micrô và hiển thị thông báo lỗi nếu cần
        if (!window.microphoneAvailable) {
            if (window.isHttpNonLocalhost) {
                this.addChatMessage('⚠️ Truy cập qua HTTP nên không thể ghi âm, chỉ có thể trò chuyện bằng văn bản', false);
            } else {
                this.addChatMessage('⚠️ Micro không khả dụng. Kiểm tra quyền truy cập; hiện chỉ có thể trò chuyện bằng văn bản', false);
            }
        }
        // Chỉ bắt đầu ghi âm nếu có micrô
        if (window.microphoneAvailable) {
            const recordBtn = document.getElementById('recordBtn');
            if (recordBtn) {
                recordBtn.click();
            }
        }
        // Chỉ khởi động camera nếu camera có sẵn (có mã xác minh)
        if (window.cameraAvailable && typeof window.startCamera === 'function') {
            window.startCamera().then(success => {
                if (success) {
                    const cameraBtn = document.getElementById('cameraBtn');
                    if (cameraBtn) {
                        cameraBtn.classList.add('camera-active');
                        cameraBtn.querySelector('.btn-text').textContent = 'Đóng';
                    }
                } else {
                    this.addChatMessage('⚠️ Không thể bật camera, trình duyệt có thể đã từ chối quyền truy cập', false);
                }
            }).catch(error => {
                log(`khởi độngcamerasự cố: ${error.message}`, 'error');
            });
        }
    }

    // Xử lý nút kết nối bấm
    async handleConnect() {
        const wsHandler = getWebSocketHandler();
        if (this.isConnecting || (wsHandler && wsHandler.isConnected())) {
            log('Đã có kết nối hoặc đang kết nối, bỏ qua yêu cầu lần này', 'info');
            return;
        }

        this.isConnecting = true;
        console.log('handleConnect called');

        try {
            // Chuyển sang tab cài đặt thiết bị
            this.switchTab('device');

            // Đợi cập nhật DOM
            await new Promise(resolve => setTimeout(resolve, 50));

            const otaUrlInput = document.getElementById('otaUrl');

            console.log('otaUrl element:', otaUrlInput);

            if (!otaUrlInput || !otaUrlInput.value) {
                this.addChatMessage('Vui lòng nhập địa chỉ server OTA', false);
                return;
            }

            const otaUrl = otaUrlInput.value;
            console.log('otaUrl value:', otaUrl);

            // Cập nhật trạng thái nút quay số để kết nối
            const dialBtn = document.getElementById('dialBtn');
            if (dialBtn) {
                dialBtn.classList.add('dial-active');
                dialBtn.querySelector('.btn-text').textContent = 'Đang kết nối...';
                dialBtn.disabled = true;
            }

            // Hiển thị thông báo kết nối
            this.addChatMessage('Đang kết nối server...', false);

            const chatIpt = document.getElementById('chatIpt');
            if (chatIpt) {
                chatIpt.style.display = 'flex';
            }

            // Lấy phiên bản bộ xử lý WebSocket
            // Đăng ký gọi lại trạng thái kết nối TRƯỚC KHI kết nối
            wsHandler.onConnectionStateChange = (isConnected) => {
                this.updateConnectionUI(isConnected);
                this.updateDialButton(isConnected);
            };

            // Đăng ký tin nhắn trò chuyện gọi lại TRƯỚC KHI kết nối
            wsHandler.onChatMessage = (text, isUser) => {
                this.addChatMessage(text, isUser);
            };

            // Đăng ký gọi lại trạng thái nút ghi TRƯỚC KHI kết nối
            wsHandler.onRecordButtonStateChange = (isRecording) => {
                const recordBtn = document.getElementById('recordBtn');
                if (recordBtn) {
                    if (isRecording) {
                        recordBtn.classList.add('recording');
                        recordBtn.querySelector('.btn-text').textContent = 'Đang ghi âm';
                    } else {
                        recordBtn.classList.remove('recording');
                        recordBtn.querySelector('.btn-text').textContent = 'Ghi âm';
                    }
                }
            };

            const isConnected = await wsHandler.connect();

            if (isConnected) {
                // Kiểm tra tính khả dụng của micrô (kiểm tra lại sau khi kết nối)
                const { checkMicrophoneAvailability } = await import('../core/audio/recorder.js?v=0205');
                const micAvailable = await checkMicrophoneAvailability();

                if (!micAvailable) {
                    const isHttp = window.isHttpNonLocalhost;
                    if (isHttp) {
                        this.addChatMessage('⚠️ Truy cập qua HTTP nên không thể ghi âm, chỉ có thể trò chuyện bằng văn bản', false);
                    }
                    // Cập nhật trạng thái toàn cầu
                    window.microphoneAvailable = false;
                }

                // Cập nhật trạng thái nút quay số
                const dialBtn = document.getElementById('dialBtn');
                if (dialBtn) {
                    if (!this.dialBtnDisabled) {
                        dialBtn.disabled = false;
                    }
                    dialBtn.querySelector('.btn-text').textContent = 'Ngắt kết nối';
                    dialBtn.classList.add('dial-active');
                }

                this.hideModal('settingsModal');
            } else {
                throw new Error('Kết nối OTA thất bại');
            }
        } catch (error) {
            console.error('Connection error details:', {
                message: error.message,
                stack: error.stack,
                name: error.name
            });

            // Hiển thị thông báo lỗi
            const errorMessage = error.message.includes('Cannot set properties of null')
                ? 'Kết nối thất bại. Vui lòng kiểm tra kết nối thiết bị'
                : `Kết nối thất bại: ${error.message}`;

            this.addChatMessage(errorMessage, false);

            // Khôi phục trạng thái nút quay số
            const dialBtn = document.getElementById('dialBtn');
            if (dialBtn) {
                if (!this.dialBtnDisabled) {
                    dialBtn.disabled = false;
                }
                dialBtn.querySelector('.btn-text').textContent = 'Kết nối';
                dialBtn.classList.remove('dial-active');
                console.log('Dial button state restored successfully');
            }
        } finally {
            this.isConnecting = false;
        }
    }

    async triggerWakewordDial(wakeWord = 'Từ đánh thức') {
        const wsHandler = getWebSocketHandler();
        const now = Date.now();

        if (wsHandler && wsHandler.isConnected()) {
            log('Trang đã kết nối, bỏ qua kết nối tự động', 'info');
            return false;
        }

        if (this.isConnecting || this.dialBtnDisabled) {
            log('Trang đang kết nối, bỏ qua yêu cầu đánh thức lặp lại', 'info');
            return false;
        }

        if (now - this.lastWakewordDialTime < 3000) {
            log('Đánh thức liên tục quá nhanh, bỏ qua kết nối tự động lần này', 'warning');
            return false;
        }

        this.lastWakewordDialTime = now;
        this.addChatMessage(`Phát hiện từ đánh thức “${wakeWord}”, đang chuẩn bị kết nối server...`, false);
        await this.handleConnect();
        return true;
    }

    // Add MCP tool
    addMCPTool() {
        const mcpToolsList = document.getElementById('mcpToolsList');
        if (!mcpToolsList) return;

        const toolId = `mcp-tool-${Date.now()}`;
        const toolDiv = document.createElement('div');
        toolDiv.className = 'properties-container';
        toolDiv.innerHTML = `
            <div class="property-item">
                <input type="text" placeholder="Tên công cụ" value="Công cụ mới">
                <input type="text" placeholder="Mô tả công cụ" value="Mô tả công cụ">
                <button class="remove-property" onclick="uiController.removeMCPTool('${toolId}')">Xóa</button>
            </div>
        `;

        mcpToolsList.appendChild(toolDiv);
    }

    // Remove MCP tool
    removeMCPTool(toolId) {
        const toolElement = document.getElementById(toolId);
        if (toolElement) {
            toolElement.remove();
        }
    }

    // Cập nhật hiển thị thống kê âm thanh
    updateAudioStats() {
        const audioPlayer = getAudioPlayer();
        if (!audioPlayer) return;

        const stats = audioPlayer.getAudioStats();
        // Ở đây có thể thêm logic cập nhật UI thống kê âm thanh
    }

    // Bắt đầu giám sát thống kê âm thanh
    startAudioStatsMonitor() {
        // Cập nhật số liệu thống kê âm thanh cứ sau 100 mili giây
        this.audioStatsTimer = setInterval(() => {
            this.updateAudioStats();
        }, 100);
    }

    // Dừng màn hình thống kê âm thanh
    stopAudioStatsMonitor() {
        if (this.audioStatsTimer) {
            clearInterval(this.audioStatsTimer);
            this.audioStatsTimer = null;
        }
    }

    // Vẽ dạng sóng trình hiển thị âm thanh
    drawVisualizer(dataArray) {
        if (!this.visualizerContext || !this.visualizerCanvas) return;

        this.visualizerContext.fillStyle = '#fafafa';
        this.visualizerContext.fillRect(0, 0, this.visualizerCanvas.width, this.visualizerCanvas.height);

        const barWidth = (this.visualizerCanvas.width / dataArray.length) * 2.5;
        let barHeight;
        let x = 0;

        for (let i = 0; i < dataArray.length; i++) {
            barHeight = dataArray[i] / 2;

            // Tạo màu gradient: từ tím sang xanh lam sang xanh lục
            const gradient = this.visualizerContext.createLinearGradient(0, 0, 0, this.visualizerCanvas.height);
            gradient.addColorStop(0, '#8e44ad');
            gradient.addColorStop(0.5, '#3498db');
            gradient.addColorStop(1, '#1abc9c');

            this.visualizerContext.fillStyle = gradient;
            this.visualizerContext.fillRect(x, this.visualizerCanvas.height - barHeight, barWidth, barHeight);
            x += barWidth + 1;
        }
    }

    // Cập nhật giao diện người dùng trạng thái phiên
    updateSessionStatus(isSpeaking) {
        // Ở đây có thể thêm logic cập nhật giao diện người dùng trạng thái phiên
        // Ví dụ: cập nhật trạng thái chuyển động miệng của mô hình Live2D
    }

    // Cập nhật cảm xúc phiên
    updateSessionEmotion(emoji) {
        // Ở đây có thể thêm logic cập nhật cảm xúc
        // Ví dụ: hiển thị biểu tượng cảm xúc trong chỉ báo trạng thái
    }
}

// Tạo cá thể đơn lẻ
export const uiController = new UIController();

// Xuất lớp để sử dụng mô-đun
export { UIController };
