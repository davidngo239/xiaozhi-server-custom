/**
 * Trình quản lý Live2D
 * Chịu trách nhiệm khởi tạo mô hình Live2D, điều khiển hoạt ảnh miệng và các chức năng khác
 */
class Live2DManager {
    constructor() {
        this.live2dApp = null;
        this.live2dModel = null;
        this.isTalking = false;
        this.mouthAnimationId = null;
        this.mouthParam = 'ParamMouthOpenY';
        this.audioContext = null;
        this.analyser = null;
        this.dataArray = null;
        this.lastEmotionActionTime = null;
        this.currentModelName = null;

        // Cấu hình cụ thể của model
        this.modelConfig = {
            'hiyori_pro_zh': {
                mouthParam: 'ParamMouthOpenY',
                mouthAmplitude: 1.0,
                mouthThresholds: { low: 0.3, high: 0.7 },
                motionMap: {
                    'FlickUp': 'FlickUp',
                    'FlickDown': 'FlickDown',
                    'Tap': 'Tap',
                    'Tap@Body': 'Tap@Body',
                    'Flick': 'Flick',
                    'Flick@Body': 'Flick@Body'
                }
            },
            'natori_pro_zh': {
                mouthParam: 'ParamMouthOpenY',
                mouthAmplitude: 1.0,
                mouthThresholds: { low: 0.1, high: 0.4 },
                mouthFormParam: 'ParamMouthForm',
                mouthFormAmplitude: 1.0,
                mouthForm2Param: 'ParamMouthForm2',
                mouthForm2Amplitude: 0.8,
                motionMap: {
                    'FlickUp': 'FlickUp',
                    'FlickDown': 'Flick@Body',
                    'Tap': 'Tap',
                    'Tap@Body': 'Tap@Head',
                    'Flick': 'Tap',
                    'Flick@Body': 'Flick@Body'
                }
            }
        };

        // Ánh xạ cảm xúc thành hành động
        this.emotionToActionMap = {
            'happy': 'FlickUp',      // Vui vẻ - hành động vuốt lên
            'laughing': 'FlickUp',   // Hành động vuốt gây cười
            'funny': 'FlickUp',      // Hài hước - hành động vuốt lên
            'sad': 'FlickDown',      // Buồn - hành động vuốt xuống
            'crying': 'FlickDown',   // Khóc - hành động vuốt xuống
            'angry': 'Tap@Body',     // Tức giận - hành động nhấp vào cơ thể
            'surprised': 'Tap',      // hành động nhấp chuột bất ngờ
            'neutral': 'Flick',      // Hành động vuốt bình thường
            'default': 'Flick@Body'  // Mặc định - hành động vuốt cơ thể
        };

        // Nhấp chuột một lần/hai lần để xác định cấu hình và trạng thái
        this._lastClickTime = 0;
        this._lastClickPos = { x: 0, y: 0 };
        this._singleClickTimer = null;
        this._doubleClickMs = 280; // Ngưỡng thời gian nhấp đúp (ms)
        this._doubleClickDist = 16; // Độ dịch chuyển tối đa được phép bằng cách nhấp đúp (px)
        // Quyết định trượt
        this._pointerDown = false;
        this._downPos = { x: 0, y: 0 };
        this._downTime = 0;
        this._downArea = 'Body';
        this._movedBeyondClick = false;
        this._swipeMinDist = 24; // Khoảng cách tối thiểu để kích hoạt trượt
    }

    /**
     * Khởi tạo Live2D
     */
    async initializeLive2D() {
        try {
            const canvas = document.getElementById('live2d-stage');

            // để sử dụng nội bộ
            window.PIXI = PIXI;

            this.live2dApp = new PIXI.Application({
                view: canvas,
                height: window.innerHeight,
                width: window.innerWidth,
                resolution: window.devicePixelRatio,
                autoDensity: true,
                antialias: true,
                backgroundAlpha: 0,
            });

            // Tải mô hình Live2D - tự động phát hiện thư mục hiện tại và thích ứng với các môi trường khác nhau
            // Lấy đường dẫn thư mục chứa file HTML hiện tại
            const currentPath = window.location.pathname;
            const lastSlashIndex = currentPath.lastIndexOf('/');
            const basePath = currentPath.substring(0, lastSlashIndex + 1);

            // Đọc mô hình được chọn cuối cùng từ localStorage hoặc sử dụng mặc định nếu không có
            const savedModelName = localStorage.getItem('live2dModel') || 'hiyori_pro_zh';
            const modelFileMap = {
                'hiyori_pro_zh': 'hiyori_pro_t11.model3.json',
                'natori_pro_zh': 'natori_pro_t06.model3.json'
            };
            const modelFileName = modelFileMap[savedModelName] || 'hiyori_pro_t11.model3.json';
            const modelPath = basePath + 'resources/' + savedModelName + '/runtime/' + modelFileName;

            this.live2dModel = await PIXI.live2d.Live2DModel.from(modelPath);
            this.live2dApp.stage.addChild(this.live2dModel);

            // Lưu tên model hiện tại
            this.currentModelName = savedModelName;

            // Cập nhật hiển thị hộp thả xuống
            const modelSelect = document.getElementById('live2dModelSelect');
            if (modelSelect) {
                modelSelect.value = savedModelName;
            }

            // Cài đặt tên tham số miệng dành riêng cho kiểu máy
            if (this.modelConfig[savedModelName]) {
                this.mouthParam = this.modelConfig[savedModelName].mouthParam || 'ParamMouthOpenY';
            }

            // Cài đặt thuộc tính mô hình
            this.live2dModel.scale.set(0.33);
            this.live2dModel.x = (window.innerWidth - this.live2dModel.width) * 0.5;
            this.live2dModel.y = -50;

            // Kích hoạt tương tác và lắng nghe các lần nhấp chuột (đầu/thân, v.v.)

            this.live2dModel.interactive = true;


            this.live2dModel.on('doublehit', (args) => {
                const area = Array.isArray(args) ? args[0] : args;

                // Kích hoạt hành động nhấp đúp
                if (area === 'Body') {
                    this.motion('Flick@Body');
                } else if (area === 'Head' || area === 'Face') {
                    this.motion('Flick');
                }

                const app = window.chatApp;
                const payload = JSON.stringify({ type: 'live2d', event: 'doublehit', area });
                if (app && app.dataChannel && app.dataChannel.readyState === 'open') {
                    app.dataChannel.send(payload);
                }

            });

            this.live2dModel.on('singlehit', (args) => {
                const area = Array.isArray(args) ? args[0] : args;

                // kích hoạt hành động nhấp chuột
                if (area === 'Body') {
                    this.motion('Tap@Body');
                } else if (area === 'Head' || area === 'Face') {
                    this.motion('Tap');
                }

                const app = window.chatApp;
                const payload = JSON.stringify({ type: 'live2d', event: 'singlehit', area });
                if (app && app.dataChannel && app.dataChannel.readyState === 'open') {
                    app.dataChannel.send(payload);
                }

            });

            this.live2dModel.on('swipe', (args) => {
                const area = Array.isArray(args) ? args[0] : args;
                const dir = Array.isArray(args) ? args[1] : undefined;

                // kích hoạt hành động trượt
                if (area === 'Body') {
                    if (dir === 'up') {
                        this.motion('FlickUp');
                    } else if (dir === 'down') {
                        this.motion('FlickDown');
                    }
                } else if (area === 'Head' || area === 'Face') {
                    if (dir === 'up') {
                        this.motion('FlickUp');
                    } else if (dir === 'down') {
                        this.motion('FlickDown');
                    }
                }

                const app = window.chatApp;
                const payload = JSON.stringify({ type: 'live2d', event: 'swipe', area, dir });
                if (app && app.dataChannel && app.dataChannel.readyState === 'open') {
                    app.dataChannel.send(payload);
                }

            });

            // Điểm mấu chốt: Vùng nhấn "đầu/thân" được tùy chỉnh + phân biệt nhấp chuột một lần/hai lần/vuốt
            this.live2dModel.on('pointerdown', (event) => {
                try {
                    const global = event.data.global;
                    const bounds = this.live2dModel.getBounds();
                    // Chỉ được xác định khi lần nhấp nằm trong phạm vi hiển thị của mô hình
                    if (!bounds || !bounds.contains(global.x, global.y)) return;

                    const relX = (global.x - bounds.x) / (bounds.width || 1);
                    const relY = (global.y - bounds.y) / (bounds.height || 1);
                    let area = '';
                    // Ngưỡng thực nghiệm: 20% phía trên của hình chữ nhật nhìn thấy được của mô hình được coi là vùng "đầu"
                    if (relX >= 0.4 && relX <= 0.6) {
                        if (relY <= 0.15) {
                            area = 'Head';
                        } else if (relY <= 0.23) {
                            area = 'Face';
                        } else {
                            area = 'Body';
                        }
                    }
                    if (area === '') {
                        return;
                    }

                    // Ghi lại trạng thái ép để phán đoán trượt
                    this._pointerDown = true;
                    this._downPos = { x: global.x, y: global.y };
                    this._downTime = performance.now();
                    this._downArea = area;
                    this._movedBeyondClick = false;

                    const now = performance.now();
                    const dt = now - (this._lastClickTime || 0);
                    const dx = global.x - (this._lastClickPos?.x || 0);
                    const dy = global.y - (this._lastClickPos?.y || 0);
                    const dist = Math.hypot(dx, dy);

                    // Xác nhận lần nhấn: chỉ thực hiện phán đoán nhấp chuột đơn/đôi khi nhấp chuột vào mô hình
                    if (this._lastClickTime && dt <= this._doubleClickMs && dist <= this._doubleClickDist) {
                        // Được xác định là nhấp đúp: Hủy sự kiện nhấp chuột sẽ được kích hoạt
                        if (this._singleClickTimer) {
                            clearTimeout(this._singleClickTimer);
                            this._singleClickTimer = null;
                        }
                        if (typeof this.live2dModel.emit === 'function') {
                            this.live2dModel.emit('doublehit', [area]);
                        }
                        this._lastClickTime = 0;
                        this._pointerDown = false; // Nhấp đúp để hoàn tất và đặt lại trạng thái
                        return;
                    }

                    // Có thể nhấp chuột: ghi lại và trì hoãn xác nhận
                    this._lastClickTime = now;
                    this._lastClickPos = { x: global.x, y: global.y };
                    if (this._singleClickTimer) {
                        clearTimeout(this._singleClickTimer);
                        this._singleClickTimer = null;
                    }
                    this._singleClickTimer = setTimeout(() => {
                        // Nếu chuyển động vượt quá ngưỡng trong thời gian chờ, nó sẽ không còn được coi là nhấp chuột nữa.
                        if (!this._movedBeyondClick && typeof this.live2dModel.emit === 'function') {
                            this.live2dModel.emit('singlehit', [area]);
                        }
                        this._singleClickTimer = null;
                        this._lastClickTime = 0;
                    }, this._doubleClickMs);
                } catch (e) {
                    // Bỏ qua các ngoại lệ trong phán đoán lượt truy cập tùy chỉnh để tránh ảnh hưởng đến quy trình chính
                }
            });

            // Chuyển động của con trỏ: dùng để xác định xem có nên nâng cấp từ "click" lên "slide" hay không
            this.live2dModel.on('pointermove', (event) => {
                try {
                    if (!this._pointerDown) return;
                    const global = event.data.global;
                    const dx = global.x - this._downPos.x;
                    const dy = global.y - this._downPos.y;
                    const dist = Math.hypot(dx, dy);

                    // Sử dụng _doubleClickDist làm ngưỡng xác định lần nhấp/vuốt
                    if (dist > this._doubleClickDist) {
                        this._movedBeyondClick = true;
                        // Nếu vượt quá ngưỡng nhấp chuột, tính năng kích hoạt nhấp chuột có thể bị Hủy
                        if (this._singleClickTimer) {
                            clearTimeout(this._singleClickTimer);
                            this._singleClickTimer = null;
                        }
                        this._lastClickTime = 0;
                    }
                } catch (e) {
                    // Bỏ qua các ngoại lệ trong xác định chuyển động
                }
            });

            // Con trỏ được nâng lên: xác nhận xem nó có trượt không
            const handlePointerUp = (event) => {
                try {
                    if (!this._pointerDown) return;
                    const global = (event && event.data && event.data.global) ? event.data.global : { x: this._downPos.x, y: this._downPos.y };
                    const dx = global.x - this._downPos.x;
                    const dy = global.y - this._downPos.y;
                    const dist = Math.hypot(dx, dy);

                    // Vuốt: Nếu vượt quá khoảng cách trượt tối thiểu, sự kiện vuốt sẽ được kích hoạt (mang hướng và diện tích)
                    if (this._movedBeyondClick && dist >= this._swipeMinDist) {
                        if (typeof this.live2dModel.emit === 'function') {
                            const dir = Math.abs(dx) >= Math.abs(dy)
                                ? (dx > 0 ? 'right' : 'left')
                                : (dy > 0 ? 'down' : 'up');
                            this.live2dModel.emit('swipe', [this._downArea, dir]);
                        }
                        // Chấm dứt: không còn cho phép kích hoạt nhấp chuột/nhấp đúp chuột
                        if (this._singleClickTimer) {
                            clearTimeout(this._singleClickTimer);
                            this._singleClickTimer = null;
                        }
                        this._lastClickTime = 0;
                    }
                } catch (e) {
                    // Bỏ qua các trường hợp ngoại lệ khi xác định mức tăng
                }
                finally {
                    this._pointerDown = false;
                    this._movedBeyondClick = false;
                }
            };

            this.live2dModel.on('pointerup', handlePointerUp);
            this.live2dModel.on('pointerupoutside', handlePointerUp);

            // Thêm trình nghe thay đổi kích thước cửa sổ để giữ mô hình ở giữa và dưới cùng của Canvas
            window.addEventListener('resize', () => {
                if (this.live2dModel) {
                    // Tính toán lại vị trí mô hình bằng kích thước cửa sổ thực tế
                    this.live2dModel.x = (window.innerWidth - this.live2dModel.width) * 0.5;
                    this.live2dModel.y = -50;
                }
            });

        } catch (err) {
            console.error('Tải mô hình Live2D thất bại:', err);
        }
    }

    /**
     * Khởi tạo bộ phân tích âm thanh - sử dụng nút phân tích của trình phát âm thanh
     */
    initializeAudioAnalyzer() {
        try {
            // Nhận phiên bản trình phát âm thanh
            const audioPlayer = window.chatApp?.audioPlayer;
            if (!audioPlayer) {
                console.warn('Trình phát âm thanh chưa được khởi tạo, không thể lấy nút phân tích');
                return false;
            }

            // Nhận bối cảnh âm thanh của trình phát âm thanh
            this.audioContext = audioPlayer.getAudioContext();
            if (!this.audioContext) {
                console.warn('Không thể lấy ngữ cảnh âm thanh của trình phát');
                return false;
            }

            // Tạo nút phân tích
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;
            this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);

            return true;
        } catch (error) {
            console.error('Khởi tạo bộ phân tích âm thanh thất bại:', error);
            return false;
        }
    }

    /**
     * Kết nối với nút đầu ra của trình phát âm thanh
     */
    connectToAudioPlayer() {
        try {
            // Nhận bối cảnh phát trực tuyến của trình phát âm thanh
            const audioPlayer = window.chatApp?.audioPlayer;
            if (!audioPlayer || !audioPlayer.streamingContext) {
                console.warn('Trình phát âm thanh hoặc ngữ cảnh luồng chưa được khởi tạo');
                return false;
            }

            // Nhận bối cảnh phát trực tuyến của trình phát âm thanh
            const streamingContext = audioPlayer.streamingContext;

            // Nhận nút phân tích
            const analyser = streamingContext.getAnalyser();
            if (!analyser) {
                console.warn('Trình phát chưa tạo nút phân tích âm thanh, không thể kết nối');
                return false;
            }

            // Sử dụng nút phân tích của trình phát âm thanh
            this.analyser = analyser;
            this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
            return true;
        } catch (error) {
            console.error('Kết nối với trình phát âm thanh thất bại:', error);
            return false;
        }
    }

    /**
     * vòng lặp hoạt hình miệng
     */
    animateMouth() {
        if (!this.isTalking) return;
        if (!this.live2dModel) return;
        const internal = this.live2dModel && this.live2dModel.internalModel;
        if (internal && internal.coreModel) {
            const coreModel = internal.coreModel;

            let mouthOpenY = 0;
            let mouthForm = 0;
            let mouthForm2 = 0;
            let average = 0;

            if (this.analyser && this.dataArray) {
                this.analyser.getByteFrequencyData(this.dataArray);
                average = this.dataArray.reduce((a, b) => a + b) / this.dataArray.length;

                const normalizedVolume = average / 255;

                // Nhận ngưỡng dành riêng cho mô hình
                let lowThreshold = 0.3;
                let highThreshold = 0.7;
                if (this.currentModelName && this.modelConfig[this.currentModelName]) {
                    lowThreshold = this.modelConfig[this.currentModelName].mouthThresholds?.low || 0.3;
                    highThreshold = this.modelConfig[this.currentModelName].mouthThresholds?.high || 0.7;
                }

                // Ánh xạ sử dụng các ngưỡng dành riêng cho từng mô hình
                let minOpenY = 0.1;
                if (this.currentModelName && this.modelConfig[this.currentModelName]) {
                    minOpenY = this.modelConfig[this.currentModelName].mouthMinOpenY || 0.1;
                }

                if (normalizedVolume < lowThreshold) {
                    mouthOpenY = minOpenY + Math.pow(normalizedVolume / lowThreshold, 1.5) * (0.4 - minOpenY);
                } else if (normalizedVolume < highThreshold) {
                    mouthOpenY = 0.4 + (normalizedVolume - lowThreshold) / (highThreshold - lowThreshold) * 0.4;
                } else {
                    mouthOpenY = 0.8 + Math.pow((normalizedVolume - highThreshold) / (1 - highThreshold), 1.2) * 0.2;
                }

                // Áp dụng biên độ đóng và mở miệng dành riêng cho từng mô hình
                let amplitudeMultiplier = 1.0;
                let maxOpenY = 2.5;
                if (this.currentModelName && this.modelConfig[this.currentModelName]) {
                    amplitudeMultiplier = this.modelConfig[this.currentModelName].mouthAmplitude;
                    maxOpenY = this.modelConfig[this.currentModelName].maxOpenY || 2.5;
                }
                mouthOpenY = mouthOpenY * amplitudeMultiplier;
                mouthOpenY = Math.min(Math.max(mouthOpenY, 0), maxOpenY);

                // Tính toán các thông số hình dạng miệng (chỉ dành cho các dòng máy hỗ trợ thay đổi hình dạng miệng)
                if (this.currentModelName && this.modelConfig[this.currentModelName]?.mouthFormParam) {
                    const config = this.modelConfig[this.currentModelName];
                    const formAmplitude = config.mouthFormAmplitude || 0.5;
                    const form2Amplitude = config.mouthForm2Amplitude || 0;

                    // Hình dạng miệng thay đổi theo âm lượng:
                    // Âm lượng thấp: hình dạng miệng thiên về ký tự "một" (giá trị âm)
                    // Âm lượng lớn: hình dạng miệng thiên về ký tự "o" (giá trị dương)
                    // Khi âm lượng = 0: hình dạng miệng = 0 (trạng thái tự nhiên)
                    mouthForm = (normalizedVolume - 0.5) * 2 * formAmplitude;
                    mouthForm = Math.max(-formAmplitude, Math.min(formAmplitude, mouthForm));

                    // Tham số hình dạng miệng thứ hai (natori duy nhất)
                    if (config.mouthForm2Param) {
                        mouthForm2 = (normalizedVolume - 0.3) * 2 * form2Amplitude;
                        mouthForm2 = Math.max(-form2Amplitude, Math.min(form2Amplitude, mouthForm2));
                    }
                }

                // Nhật ký gỡ lỗi: thông số miệng đầu ra
                console.log(`[Live2D] Mô hình: ${this.currentModelName || 'unknown'}, âm lượng: ${average?.toFixed(0)}, OpenY: ${mouthOpenY.toFixed(3)}, Form: ${mouthForm.toFixed(3)}, Form2: ${mouthForm2.toFixed(3)}`);
            }

            // Cài đặt thông số đóng mở miệng
            coreModel.setParameterValueById(this.mouthParam, mouthOpenY);

            // Cài đặt thông số hình dạng miệng (chỉ dành cho những mẫu máy hỗ trợ thay đổi hình dạng miệng)
            if (this.currentModelName && this.modelConfig[this.currentModelName]?.mouthFormParam) {
                const config = this.modelConfig[this.currentModelName];
                const formParam = config.mouthFormParam;
                coreModel.setParameterValueById(formParam, mouthForm);

                // Cài đặt tham số hình miệng thứ hai (natori duy nhất)
                if (config.mouthForm2Param) {
                    coreModel.setParameterValueById(config.mouthForm2Param, mouthForm2);
                }
            }

            coreModel.update();
        }
        this.mouthAnimationId = requestAnimationFrame(() => this.animateMouth());
    }

    /**
     * Bắt đầu nói chuyện hoạt hình
     */
    startTalking() {
        if (this.isTalking || !this.live2dModel) return;

        // Đảm bảo bộ phân tích âm thanh được khởi tạo
        if (!this.analyser) {
            if (!this.initializeAudioAnalyzer()) {
                console.warn('Khởi tạo bộ phân tích âm thanh thất bại, sẽ dùng hoạt ảnh mô phỏng');
                // Bắt đầu hoạt ảnh (sử dụng dữ liệu mô phỏng) ngay cả khi máy phân tích Khởi tạo thất bại
                this.isTalking = true;
                this.animateMouth();
                return;
            }
        }

        // Kết nối với đầu ra của trình phát âm thanh
        if (!this.connectToAudioPlayer()) {
            console.warn('Không thể kết nối đầu ra trình phát, sẽ dùng hoạt ảnh mô phỏng');
        }

        this.isTalking = true;
        this.animateMouth();
    }

    /**
     * ngừng nói chuyện hoạt hình
     */
    stopTalking() {
        this.isTalking = false;
        if (this.mouthAnimationId) {
            cancelAnimationFrame(this.mouthAnimationId);
            this.mouthAnimationId = null;
        }

        // Đặt lại thông số miệng
        if (this.live2dModel) {
            const internal = this.live2dModel.internalModel;
            if (internal && internal.coreModel) {
                const coreModel = internal.coreModel;
                coreModel.setParameterValueById(this.mouthParam, 0);
                coreModel.update();
            }
        }
    }

    /**
     * Kích hoạt hành động dựa trên cảm xúc
     * @param {string} emotion - Tên cảm xúc
     */
    triggerEmotionAction(emotion) {
        if (!this.live2dModel) return;

        // Thêm điều khiển thời gian làm mát để tránh kích hoạt quá thường xuyên
        const now = Date.now();
        if (this.lastEmotionActionTime && now - this.lastEmotionActionTime < 5000) { // Thời gian hồi chiêu 5 giây
            return;
        }

        // Nhận hành động tương ứng dựa trên cảm xúc
        const action = this.emotionToActionMap[emotion] || this.emotionToActionMap['default'];

        // Kích hoạt hành động và ghi lại thời gian
        this.motion(action);
        this.lastEmotionActionTime = now;
    }



    /**
     * Kích hoạt mô hình hành động (Chuyển động)
     * @param {string} name - Tên nhóm hành động, chẳng hạn như 'TapBody', 'FlickUp', 'Idle', v.v.
     */
    motion(name) {
        try {
            if (!this.live2dModel) return;

            // Lấy tên hành động tương ứng dựa trên mô hình hiện tại
            let actualMotionName = name;
            if (this.currentModelName && this.modelConfig[this.currentModelName]) {
                const motionMap = this.modelConfig[this.currentModelName].motionMap;
                actualMotionName = motionMap[name] || name;
            }

            this.live2dModel.motion(actualMotionName);
        } catch (error) {
            console.error('Kích hoạt chuyển động thất bại:', error);
        }
    }

    /**
     * Cài đặt sự kiện tương tác mô hình
     */
    setupModelInteractions() {
        if (!this.live2dModel) return;

        this.live2dModel.interactive = true;

        this.live2dModel.on('doublehit', (args) => {
            const area = Array.isArray(args) ? args[0] : args;

            if (area === 'Body') {
                this.motion('Flick@Body');
            } else if (area === 'Head' || area === 'Face') {
                this.motion('Flick');
            }

            const app = window.chatApp;
            const payload = JSON.stringify({ type: 'live2d', event: 'doublehit', area });
            if (app && app.dataChannel && app.dataChannel.readyState === 'open') {
                app.dataChannel.send(payload);
            }
        });

        this.live2dModel.on('singlehit', (args) => {
            const area = Array.isArray(args) ? args[0] : args;

            if (area === 'Body') {
                this.motion('Tap@Body');
            } else if (area === 'Head' || area === 'Face') {
                this.motion('Tap');
            }

            const app = window.chatApp;
            const payload = JSON.stringify({ type: 'live2d', event: 'singlehit', area });
            if (app && app.dataChannel && app.dataChannel.readyState === 'open') {
                app.dataChannel.send(payload);
            }
        });

        this.live2dModel.on('swipe', (args) => {
            const area = Array.isArray(args) ? args[0] : args;
            const dir = Array.isArray(args) ? args[1] : undefined;

            if (area === 'Body') {
                if (dir === 'up') {
                    this.motion('FlickUp');
                } else if (dir === 'down') {
                    this.motion('FlickDown');
                }
            }

            const app = window.chatApp;
            const payload = JSON.stringify({ type: 'live2d', event: 'swipe', area, dir });
            if (app && app.dataChannel && app.dataChannel.readyState === 'open') {
                app.dataChannel.send(payload);
            }
        });

        this.live2dModel.on('pointerdown', (event) => {
            try {
                const global = event.data.global;
                const bounds = this.live2dModel.getBounds();
                if (!bounds || !bounds.contains(global.x, global.y)) return;

                const relX = (global.x - bounds.x) / (bounds.width || 1);
                const relY = (global.y - bounds.y) / (bounds.height || 1);
                let area = '';

                if (relX >= 0.4 && relX <= 0.6) {
                    if (relY <= 0.15) {
                        area = 'Head';
                    } else if (relY >= 0.7) {
                        area = 'Body';
                    }
                }

                if (!area) return;

                const now = Date.now();
                const dt = now - (this._lastClickTime || 0);
                const dx = global.x - (this._lastClickPos?.x || 0);
                const dy = global.y - (this._lastClickPos?.y || 0);
                const dist = Math.hypot(dx, dy);

                if (this._lastClickTime && dt <= this._doubleClickMs && dist <= this._doubleClickDist) {
                    if (this._singleClickTimer) {
                        clearTimeout(this._singleClickTimer);
                        this._singleClickTimer = null;
                    }

                    this.live2dModel.emit('doublehit', area);
                    this._lastClickTime = null;
                    this._lastClickPos = null;
                } else {
                    this._lastClickTime = now;
                    this._lastClickPos = { x: global.x, y: global.y };

                    this._singleClickTimer = setTimeout(() => {
                        this._singleClickTimer = null;
                        this.live2dModel.emit('singlehit', area);
                    }, this._doubleClickMs);
                }
            } catch (e) {
                console.warn('Xử lý pointerdown gặp lỗi:', e);
            }
        });
    }

    /**
     * Dọn dẹp tài nguyên
     */
    destroy() {
        this.stopTalking();

        // Làm sạch máy phân tích âm thanh
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
        this.analyser = null;
        this.dataArray = null;

        // Làm sạch ứng dụng Live2D
        if (this.live2dApp) {
            this.live2dApp.destroy(true);
            this.live2dApp = null;
        }
        this.live2dModel = null;
    }

    /**
     * Chuyển đổi mô hình Live2D
     * @param {string} modelName - tên thư mục mô hình, chẳng hạn như 'hiyori_pro_zh', 'natori_pro_zh'
     * @returns {Promise<boolean>} - Việc chuyển đổi có thành công hay không
     */
    async switchModel(modelName) {
        try {
            // Nhận ánh xạ tên tệp mô hình
            const modelFileMap = {
                'hiyori_pro_zh': 'hiyori_pro_t11.model3.json',
                'natori_pro_zh': 'natori_pro_t06.model3.json',
                'chitose': 'chitose.model3.json',
                'haru_greeter_pro_jp': 'haru_greeter_t05.model3.json'
            };

            const modelFileName = modelFileMap[modelName];
            if (!modelFileName) {
                console.error('Tên mô hình không xác định:', modelName);
                return false;
            }

            // Nhận đường dẫn cơ sở
            const currentPath = window.location.pathname;
            const lastSlashIndex = currentPath.lastIndexOf('/');
            const basePath = currentPath.substring(0, lastSlashIndex + 1);
            const modelPath = basePath + 'resources/' + modelName + '/runtime/' + modelFileName;

            // Nếu mô hình đã tồn tại, hãy xóa nó trước
            if (this.live2dModel) {
                this.live2dApp.stage.removeChild(this.live2dModel);
                this.live2dModel.destroy();
                this.live2dModel = null;
            }

            // hiển thị trạng thái tải
            const app = window.chatApp;
            if (app) {
                app.setModelLoadingStatus(true);
            }

            // Tải mô hình mới
            this.live2dModel = await PIXI.live2d.Live2DModel.from(modelPath);
            this.live2dApp.stage.addChild(this.live2dModel);

            // Cài đặt thuộc tính mô hình
            this.live2dModel.scale.set(0.33);
            this.live2dModel.x = (window.innerWidth - this.live2dModel.width) * 0.5;
            this.live2dModel.y = -50;

            // Buộc lại các sự kiện tương tác
            this.setupModelInteractions();

            // Ẩn trạng thái tải
            if (app) {
                app.setModelLoadingStatus(false);
            }

            // Lưu tên model hiện tại
            this.currentModelName = modelName;

            // Cài đặt tên tham số miệng dành riêng cho kiểu máy
            if (this.modelConfig[modelName]) {
                this.mouthParam = this.modelConfig[modelName].mouthParam || 'ParamMouthOpenY';
            }

            // Lưu vào localStorage
            localStorage.setItem('live2dModel', modelName);

            // Cập nhật hiển thị hộp thả xuống
            const modelSelect = document.getElementById('live2dModelSelect');
            if (modelSelect) {
                modelSelect.value = modelName;
            }

            console.log('Đã chuyển mô hình:', modelName);
            return true;
        } catch (error) {
            console.error('Chuyển mô hình thất bại:', error);
            const app = window.chatApp;
            if (app) {
                app.setModelLoadingStatus(false);
            }
            return false;
        }
    }


}

// Xuất phiên bản toàn cầu
window.Live2DManager = Live2DManager;
