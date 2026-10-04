import { log } from '../../utils/logger.js?v=0205';


// Kiểm tra xem thư viện Opus đã được tải chưa
export function checkOpusLoaded() {
    try {
        // Kiểm tra xem Mô-đun có tồn tại không (biến toàn cục được thư viện cục bộ xuất)
        if (typeof Module === 'undefined') {
            throw new Error('Thư viện Opus chưa được tải, đối tượng Module không tồn tại');
        }

        // Trước tiên hãy thử sử dụng Module.instance (dòng cuối cùng của phương thức xuất libopus.js)
        if (typeof Module.instance !== 'undefined' && typeof Module.instance._opus_decoder_get_size === 'function') {
            // Thay thế đối tượng Module toàn cầu bằng đối tượng Module.instance
            window.ModuleInstance = Module.instance;
            log('Đã tải thư viện Opus (dùng Module.instance)', 'success');

            // Ẩn trạng thái sau 3 giây
            const statusElement = document.getElementById('scriptStatus');
            if (statusElement) statusElement.style.display = 'none';
            return;
        }

        // Nếu không có Module.instance, hãy kiểm tra chức năng Mô-đun chung
        if (typeof Module._opus_decoder_get_size === 'function') {
            window.ModuleInstance = Module;
            log('Đã tải thư viện Opus (dùng Module toàn cục)', 'success');

            // Ẩn trạng thái sau 3 giây
            const statusElement = document.getElementById('scriptStatus');
            if (statusElement) statusElement.style.display = 'none';
            return;
        }

        throw new Error('Không tìm thấy hàm giải mã Opus, cấu trúc Module có thể không đúng');
    } catch (err) {
        log(`Tải thư viện Opus thất bại. Kiểm tra tệp libopus.js: ${err.message}`, 'error');
    }
}


// Tạo bộ mã hóa Opus
let opusEncoder = null;
export function initOpusEncoder() {
    try {
        if (opusEncoder) {
            return opusEncoder; // Đã khởi tạo
        }

        if (!window.ModuleInstance) {
            log('Không thể tạo bộ mã hóa Opus: ModuleInstance không khả dụng', 'error');
            return;
        }

        // Khởi tạo bộ mã hóa Opus
        const mod = window.ModuleInstance;
        const sampleRate = 16000; // Tốc độ lấy mẫu 16kHz
        const channels = 1;       // đơn sắc
        const application = 2048; // OPUS_APPLICATION_VOIP = 2048

        // Tạo bộ mã hóa
        opusEncoder = {
            channels: channels,
            sampleRate: sampleRate,
            frameSize: 960, // 60ms @ 16kHz = 60 * 16 = 960 samples
            maxPacketSize: 4000, // Kích thước gói tối đa
            module: mod,

            // Khởi tạo bộ mã hóa
            init: function () {
                try {
                    // Nhận kích thước bộ mã hóa
                    const encoderSize = mod._opus_encoder_get_size(this.channels);
                    log(`Kích thước bộ mã hóa Opus: ${encoderSize} byte`, 'info');

                    // phân bổ bộ nhớ
                    this.encoderPtr = mod._malloc(encoderSize);
                    if (!this.encoderPtr) {
                        throw new Error("Không thể cấp bộ nhớ cho bộ mã hóa");
                    }

                    // Khởi tạo bộ mã hóa
                    const err = mod._opus_encoder_init(
                        this.encoderPtr,
                        this.sampleRate,
                        this.channels,
                        application
                    );

                    if (err < 0) {
                        throw new Error(`Không thể khởi tạo bộ mã hóa Opus: ${err}`);
                    }

                    // Cài đặt tốc độ bit (16kbps)
                    mod._opus_encoder_ctl(this.encoderPtr, 4002, 16000); // OPUS_SET_BITRATE

                    // Độ phức tạp của cài đặt (0-10, chất lượng cao hơn thì tốt hơn nhưng sử dụng nhiều CPU hơn)
                    mod._opus_encoder_ctl(this.encoderPtr, 4010, 5);     // OPUS_SET_COMPLEXITY

                    // Cài đặt sử dụng DTX (không truyền khung im lặng)
                    mod._opus_encoder_ctl(this.encoderPtr, 4016, 1);     // OPUS_SET_DTX

                    log("Đã khởi tạo bộ mã hóa Opus", 'success');
                    return true;
                } catch (error) {
                    if (this.encoderPtr) {
                        mod._free(this.encoderPtr);
                        this.encoderPtr = null;
                    }
                    log(`Không thể khởi tạo bộ mã hóa Opus: ${error.message}`, 'error');
                    return false;
                }
            },

            // Mã hóa dữ liệu PCM sang Opus
            encode: function (pcmData) {
                if (!this.encoderPtr) {
                    if (!this.init()) {
                        return null;
                    }
                }

                try {
                    const mod = this.module;

                    // Cấp phát bộ nhớ cho dữ liệu PCM
                    const pcmPtr = mod._malloc(pcmData.length * 2); // 2 byte/int16

                    // Sao chép dữ liệu PCM sang HEAP
                    for (let i = 0; i < pcmData.length; i++) {
                        mod.HEAP16[(pcmPtr >> 1) + i] = pcmData[i];
                    }

                    // Cấp phát bộ nhớ cho đầu ra
                    const outPtr = mod._malloc(this.maxPacketSize);

                    // Mã hóa
                    const encodedLen = mod._opus_encode(
                        this.encoderPtr,
                        pcmPtr,
                        this.frameSize,
                        outPtr,
                        this.maxPacketSize
                    );

                    if (encodedLen < 0) {
                        throw new Error(`Mã hóa Opus thất bại: ${encodedLen}`);
                    }

                    // Sao chép dữ liệu được mã hóa
                    const opusData = new Uint8Array(encodedLen);
                    for (let i = 0; i < encodedLen; i++) {
                        opusData[i] = mod.HEAPU8[outPtr + i];
                    }

                    // bộ nhớ trống
                    mod._free(pcmPtr);
                    mod._free(outPtr);

                    return opusData;
                } catch (error) {
                    log(`Mã hóa Opus gặp lỗi: ${error.message}`, 'error');
                    return null;
                }
            },

            // Phá hủy bộ mã hóa
            destroy: function () {
                if (this.encoderPtr) {
                    this.module._free(this.encoderPtr);
                    this.encoderPtr = null;
                }
            }
        };

        opusEncoder.init();
        return opusEncoder;
    } catch (error) {
        log(`tạoOpusbộ mã hóathất bại: ${error.message}`, 'error');
        return false;
    }
}
