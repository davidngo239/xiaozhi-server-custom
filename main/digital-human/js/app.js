// Lối vào ứng dụng chính
import { checkOpusLoaded, initOpusEncoder } from './core/audio/opus-codec.js?v=0205';
import { getAudioPlayer } from './core/audio/player.js?v=0205';
import { checkMicrophoneAvailability, isHttpNonLocalhost } from './core/audio/recorder.js?v=0205';
import { initMcpTools } from './core/mcp/tools.js?v=0205';
import { startWakewordBridgeListener } from './core/network/wakeword-bridge.js?v=0205';
import { uiController } from './ui/controller.js?v=0205';
import { log } from './utils/logger.js?v=0205';

// Chức năng trợ giúp: Chuyển đổi dữ liệu Base64 sang Blob
function dataURItoBlob(dataURI) {
    const byteString = atob(dataURI.split(',')[1]);
    const mimeString = dataURI.split(',')[0].split(':')[1].split(';')[0];
    const ab = new ArrayBuffer(byteString.length);
    const ia = new Uint8Array(ab);
    for (let i = 0; i < byteString.length; i++) {
        ia[i] = byteString.charCodeAt(i);
    }
    return new Blob([ab], { type: mimeString });
}

// Lớp ứng dụng
class App {
    constructor() {
        this.uiController = null;
        this.audioPlayer = null;
        this.live2dManager = null;
        this.cameraStream = null;
        this.currentFacingMode = 'user';
    }

    // Khởi tạo ứng dụng
    async init() {
        log('Đang Đang khởi tạo ứng dụng...', 'info');
        // Khởi tạo bộ điều khiển UI
        this.uiController = uiController;
        this.uiController.init();
        // Kiểm tra thư viện Opus
        checkOpusLoaded();
        // Khởi tạo bộ mã hóa Opus
        initOpusEncoder();
        // Khởi tạo trình phát âm thanh
        this.audioPlayer = getAudioPlayer();
        await this.audioPlayer.start();
        // Khởi tạo công cụ MCP
        initMcpTools();
        // Khởi tạo tính năng nghe sự kiện đánh thức cục bộ
        startWakewordBridgeListener();
        // Kiểm tra tính khả dụng của Micro
        await this.checkMicrophoneAvailability();
        // Kiểm tra tính khả dụng của máy ảnh
        this.checkCameraAvailability();
        // Khởi tạo Live2D
        await this.initLive2D();
        // Khởi tạo máy ảnh
        this.initCamera();
        // Tắt trạng thái đang tải
        this.setModelLoadingStatus(false);
        log('Đã khởi tạo ứng dụng', 'success');
    }

    // Khởi tạo Live2D
    async initLive2D() {
        try {
            // Kiểm tra xem Live2DManager đã được tải chưa
            if (typeof window.Live2DManager === 'undefined') {
                throw new Error('Live2DManager chưa được tải. Kiểm tra thứ tự nạp script');
            }
            this.live2dManager = new window.Live2DManager();
            await this.live2dManager.initializeLive2D();
            // Cập nhật trạng thái giao diện người dùng
            const live2dStatus = document.getElementById('live2dStatus');
            if (live2dStatus) {
                live2dStatus.textContent = '● Đã tải';
                live2dStatus.className = 'status loaded';
            }
            log('Đã khởi tạo Live2D', 'success');
        } catch (error) {
            log(`Khởi tạo Live2D thất bại: ${error.message}`, 'error');
            // Cập nhật trạng thái giao diện người dùng
            const live2dStatus = document.getElementById('live2dStatus');
            if (live2dStatus) {
                live2dStatus.textContent = '● Không thể tải';
                live2dStatus.className = 'status error';
            }
        }
    }

    // Cài đặt trạng thái tải mô hình
    setModelLoadingStatus(isLoading) {
        const modelLoading = document.getElementById('modelLoading');
        if (modelLoading) {
            modelLoading.style.display = isLoading ? 'flex' : 'none';
        }
    }

    /**
     * Kiểm tra tính khả dụng của Micro
     * Được gọi khi ứng dụng được khởi tạo để kiểm tra xem Micro có khả dụng hay không và cập nhật trạng thái UI
     */
    async checkMicrophoneAvailability() {
        try {
            const isAvailable = await checkMicrophoneAvailability();
            const isHttp = isHttpNonLocalhost();
            // Lưu trạng thái sẵn có vào biến toàn cục
            window.microphoneAvailable = isAvailable;
            window.isHttpNonLocalhost = isHttp;
            // Cập nhật giao diện người dùng
            if (this.uiController) {
                this.uiController.updateMicrophoneAvailability(isAvailable, isHttp);
            }
            log(`Kiểm tra micro hoàn tất: ${isAvailable ? 'khả dụng' : 'không khả dụng'}`, isAvailable ? 'success' : 'warning');
        } catch (error) {
            log(`kiểm tramicrotính khả dụngthất bại: ${error.message}`, 'error');
            // Cài đặt mặc định không có sẵn
            window.microphoneAvailable = false;
            window.isHttpNonLocalhost = isHttpNonLocalhost();
            if (this.uiController) {
                this.uiController.updateMicrophoneAvailability(false, window.isHttpNonLocalhost);
            }
        }
    }

    // Kiểm tra tính khả dụng của máy ảnh
    checkCameraAvailability() {
        window.cameraAvailable = true;
        log('Đã kiểm tra camera: mã xác minh mặc định đã được liên kết', 'success');
    }

    // Khởi tạo máy ảnh
    async initCamera() {
        const cameraContainer = document.getElementById('cameraContainer');
        const cameraVideo = document.getElementById('cameraVideo');
        const cameraSwitch = document.getElementById('cameraSwitch');
        const cameraSwitchMask = document.getElementById('cameraSwitchMask');
        const dialBtn = document.getElementById('dialBtn');

        if (!cameraContainer || !cameraVideo) {
            log('Không tìm thấy thành phần camera, bỏ qua khởi tạo', 'warning');
            return Promise.resolve(false);
        }

        let isDragging = false;
        let currentX, currentY, initialX, initialY;
        let xOffset = 0, yOffset = 0;

        cameraContainer.addEventListener('mousedown', dragStart);
        document.addEventListener('mousemove', drag);
        document.addEventListener('mouseup', dragEnd);
        cameraContainer.addEventListener('touchstart', dragStart, { passive: false });
        document.addEventListener('touchmove', drag, { passive: false });
        document.addEventListener('touchend', dragEnd);

        function dragStart(e) {
            if (e.type === 'touchstart') {
                initialX = e.touches[0].clientX - xOffset;
                initialY = e.touches[0].clientY - yOffset;
            } else {
                initialX = e.clientX - xOffset;
                initialY = e.clientY - yOffset;
            }
            isDragging = true;
            cameraContainer.classList.add('dragging');
        }

        function drag(e) {
            if (isDragging) {
                e.preventDefault();
                if (e.type === 'touchmove') {
                    currentX = e.touches[0].clientX - initialX;
                    currentY = e.touches[0].clientY - initialY;
                } else {
                    currentX = e.clientX - initialX;
                    currentY = e.clientY - initialY;
                }
                xOffset = currentX;
                yOffset = currentY;
                cameraContainer.style.transform = `translate3d(${currentX}px, ${currentY}px, 0)`;
            }
        }

        function dragEnd() {
            initialX = currentX;
            initialY = currentY;
            isDragging = false;
            cameraContainer.classList.remove('dragging');
        }

        return new Promise((resolve) => {
            window.startCamera = async () => {
                try {
                    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                        log('Trình duyệt không hỗ trợ API camera', 'warning');
                        return false;
                    }
                    log('Đang yêu cầu quyền camera...', 'info');
                    this.cameraStream = await navigator.mediaDevices.getUserMedia({
                        video: { width: 180, height: 240, facingMode: this.currentFacingMode },
                        audio: false
                    });
                    cameraVideo.srcObject = this.cameraStream;
                    const devices = await navigator.mediaDevices.enumerateDevices();
                    const videoDevices = devices.filter(device => device.kind === 'videoinput');
                    if (videoDevices.length > 1) {
                        if (cameraSwitch) cameraSwitch.classList.add('active'); 
                    }
                    cameraContainer.classList.add('active');

                    // Tình huống ngắt kết nối khi chuyển đổi
                    const hasActive = dialBtn.classList.contains('dial-active');
                    if (!hasActive) {
                        cameraContainer.classList.remove('active');
                        cameraSwitch.classList.remove('active');
                        window.stopCamera();
                    }
                    log('camera đã bật', 'success');
                    return true;
                } catch (error) {
                    log(`khởi độngcamerathất bại: ${error.name} - ${error.message}`, 'error');
                    if (error.name === 'NotAllowedError') {
                        log('Quyền camera bị từ chối. Kiểm tra cài đặt trình duyệt', 'warning');
                    } else if (error.name === 'NotFoundError') {
                        log('Không tìm thấy camera', 'warning');
                    } else if (error.name === 'NotReadableError') {
                        log('camera đang được ứng dụng khác sử dụng', 'warning');
                    }
                    return false;
                }
            };

            window.stopCamera = () => {
                if (this.cameraStream) {
                    this.cameraStream.getTracks().forEach(track => track.stop());
                    this.cameraStream = null;
                    cameraVideo.srcObject = null;
                    log('camera đã tắt', 'info');
                }
            };

            window.switchCamera = async() => {
                if (window.switchCameraTimer) return;
                if (this.cameraStream) {
                    const currentTransform = window.getComputedStyle(cameraContainer).transform;
                    const originalTransform = currentTransform === 'none' ? 'translate(0px, 0px)' : currentTransform;
                    cameraContainer.style.setProperty('--original-transform', originalTransform);
                    cameraContainer.classList.add('flip');
                    if (cameraSwitchMask) cameraSwitchMask.style.opacity = 0; 
                    this.currentFacingMode = this.currentFacingMode === 'user' ? 'environment' : 'user';
                    window.stopCamera();
                    window.startCamera();
                    
                    window.switchCameraTimer = setTimeout(() => {
                        if (this.currentFacingMode === 'user') {
                            cameraVideo.style.transform = 'scaleX(-1)';
                        } else {
                            cameraVideo.style.transform = 'scaleX(1)';
                        }
                        window.switchCameraTimer = null;
                        cameraContainer.classList.remove('flip');
                        cameraContainer.style.removeProperty('--original-transform');
                        if (cameraSwitchMask) cameraSwitchMask.style.opacity = 1; 
                    }, 500);
                }
            };

            window.takePhoto = (question = 'Mô tả những vật thể bạn nhìn thấy') => {
                return new Promise(async (resolve) => {
                    const canvas = document.createElement('canvas');
                    const video = cameraVideo;

                    if (!video || video.readyState !== video.HAVE_ENOUGH_DATA) {
                        log('Không thể chụp ảnh: camera chưa sẵn sàng', 'warning');
                        resolve({
                            success: false,
                            error: 'Camera chưa sẵn sàng. Kiểm tra kết nối và bật camera'
                        });
                        return;
                    }

                    canvas.width = video.videoWidth || 180;
                    canvas.height = video.videoHeight || 240;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

                    const photoData = canvas.toDataURL('image/jpeg', 0.8);
                    log(`Chụp ảnh thành công, dung lượng dữ liệu ảnh: ${photoData.length}`, 'success');

                    try {
                        const xz_tester_vision = localStorage.getItem('xz_tester_vision');
                        if (xz_tester_vision) {
                            let visionInfo = null;

                            try {
                                visionInfo = JSON.parse(xz_tester_vision);
                            } catch (err) {
                                throw new Error(`Không thể phân tích cấu hình hình ảnh`);
                            }

                            const { url, token } = visionInfo || {};
                            if (!url || !token) {
                                throw new Error('Không thể phân tích hình ảnh: cấu hình thiếu địa chỉ API (url) hoặc token');
                            }

                            log(`Đang gửi ảnh đến API phân tích hình ảnh: ${url}`, 'info');

                            const deviceId = document.getElementById('deviceMac')?.value || '';
                            const clientId = document.getElementById('clientId')?.value || 'web_test_client';

                            const formData = new FormData();
                            formData.append('question', question);
                            formData.append('image', dataURItoBlob(photoData), 'photo.jpg');

                            const response = await fetch(url, {
                                method: 'POST',
                                body: formData,
                                headers: {
                                    'Device-Id': deviceId,
                                    'Client-Id': clientId,
                                    'Authorization': `Bearer ${token}`
                                }
                            });

                            if (!response.ok) {
                                throw new Error(`HTTP error! status: ${response.status}`);
                            }

                            const analysisResult = await response.json();
                            log(`phân tích hình ảnhhoàn tất: ${JSON.stringify(analysisResult).substring(0, 200)}...`, 'success');

                            resolve({
                                success: true,
                                message: question,
                                photo_data: photoData,
                                photo_width: canvas.width,
                                photo_height: canvas.height,
                                vision_analysis: analysisResult
                            });
                        } else {
                            log('Chưa cấu hình dịch vụ phân tích hình ảnh', 'warning');
                        }
                    } catch (error) {
                        log(`phân tích hình ảnhthất bại: ${error.message}`, 'error');
                        resolve({
                            success: true,
                            message: question,
                            photo_data: photoData,
                            photo_width: canvas.width,
                            photo_height: canvas.height,
                            vision_analysis: {
                                success: false,
                                error: error.message,
                                fallback: 'Không thể kết nối dịch vụ phân tích hình ảnh'
                            }
                        });
                    }
                });
            };

            log('Đã khởi tạo camera', 'success');
            resolve(true);
        });
    }
}

// Tạo và khởi chạy ứng dụng
const app = new App();
// Hiển thị các phiên bản ứng dụng trên toàn cầu để các mô-đun khác truy cập
window.chatApp = app;
document.addEventListener('DOMContentLoaded', () => {
    // Khởi tạo ứng dụng
    app.init();
});
export default app;
