import BlockingQueue from '../../utils/blocking-queue.js?v=0205';
import { log } from '../../utils/logger.js?v=0205';

// Lớp bối cảnh phát lại luồng âm thanh
export class StreamingContext {
    constructor(opusDecoder, audioContext, sampleRate, channels, minAudioDuration) {
        this.opusDecoder = opusDecoder;
        this.audioContext = audioContext;

        // Thông số âm thanh
        this.sampleRate = sampleRate;
        this.channels = channels;
        this.minAudioDuration = minAudioDuration;

        // Khởi tạo hàng đợi và trạng thái
        this.queue = [];          // Hàng đợi PCM được giải mã. Đang chơi
        this.activeQueue = new BlockingQueue(); // Hàng đợi PCM được giải mã. sẵn sàng chơi
        this.pendingAudioBufferQueue = [];  // Hàng đợi bộ đệm đang chờ xử lý
        this.audioBufferQueue = new BlockingQueue();  // hàng đợi bộ đệm
        this.playing = false;     // đang chơi
        this.endOfStream = false; // Liệu tín hiệu kết thúc có được nhận hay không
        this.source = null;       // Nguồn âm thanh hiện tại
        this.totalSamples = 0;    // Tổng số mẫu tích lũy
        this.lastPlayTime = 0;    // Dấu thời gian phát lần cuối
        this.scheduledEndTime = 0; // Thời gian kết thúc của âm thanh theo lịch trình

        // Khởi tạo nút phân tích (để Live2D sử dụng)
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 256;
    }

    // Bảng âm thanh bộ nhớ đệm
    pushAudioBuffer(item) {
        this.audioBufferQueue.enqueue(...item);
    }

    // Lấy nhu cầu xử lý hàng đợi bộ đệm, luồng đơn: sẽ không có vấn đề bảo mật khi audioBufferQueue luôn được cập nhật.
    async getPendingAudioBufferQueue() {
        // Đợi dữ liệu đến và lấy nó
        const data = await this.audioBufferQueue.dequeue();
        // Gán giá trị cho hàng đợi đang chờ xử lý
        this.pendingAudioBufferQueue = data;
    }

    // Nhận hàng đợi PCM đã giải mã đang được phát, một luồng: sẽ không có vấn đề bảo mật nào xảy ra khi activeQueue luôn được cập nhật
    async getQueue(minSamples) {
        const num = minSamples - this.queue.length > 0 ? minSamples - this.queue.length : 1;

        // Đợi dữ liệu và lấy nó
        const tempArray = await this.activeQueue.dequeue(num);
        this.queue.push(...tempArray);
    }

    // Chuyển đổi dữ liệu âm thanh Int16 sang dữ liệu âm thanh Float32
    convertInt16ToFloat32(int16Data) {
        const float32Data = new Float32Array(int16Data.length);
        for (let i = 0; i < int16Data.length; i++) {
            // Chuyển đổi phạm vi [-32768,32767] thành [-1,1] và sử dụng thống nhất 32768.0 để tránh biến dạng không đối xứng
            float32Data[i] = int16Data[i] / 32768.0;
        }
        return float32Data;
    }

    // Lấy số gói cần giải mã
    getPendingDecodeCount() {
        return this.audioBufferQueue.length + this.pendingAudioBufferQueue.length;
    }

    // Lấy số lượng sample cần phát (quy đổi thành số gói, 960 mẫu mỗi gói)
    getPendingPlayCount() {
        // Đếm các mẫu đã có trong hàng đợi
        const queuedSamples = this.activeQueue.length + this.queue.length;

        // Đếm các mẫu đã được lên lịch nhưng chưa được phát (trong bộ đệm Web Audio)
        let scheduledSamples = 0;
        if (this.playing && this.scheduledEndTime) {
            const currentTime = this.audioContext.currentTime;
            const remainingTime = Math.max(0, this.scheduledEndTime - currentTime);
            scheduledSamples = Math.floor(remainingTime * this.sampleRate);
        }

        const totalSamples = queuedSamples + scheduledSamples;
        return Math.ceil(totalSamples / 960);
    }

    // Đã xóa toàn bộ bộ đệm âm thanh
    clearAllBuffers() {
        log('Đã xóa toàn bộ bộ đệm âm thanh', 'info');

        // Xóa tất cả hàng đợi (sử dụng phương thức clear để giữ tham chiếu đối tượng)
        this.audioBufferQueue.clear();
        this.pendingAudioBufferQueue = [];
        this.activeQueue.clear();
        this.queue = [];

        // Dừng nguồn âm thanh hiện đang phát
        if (this.source) {
            try {
                this.source.stop();
                this.source.disconnect();
            } catch (e) {
                // Bỏ qua các lỗi đã dừng
            }
            this.source = null;
        }

        // thiết lập lại trạng thái
        this.playing = false;
        this.scheduledEndTime = this.audioContext.currentTime;
        this.totalSamples = 0;

        log('Đã xóa bộ đệm âm thanh', 'success');
    }

    // Nhận nút phân tích (để Live2D sử dụng)
    getAnalyser() {
        return this.analyser;
    }

    // Giải mã dữ liệu Opus sang PCM
    async decodeOpusFrames() {
        if (!this.opusDecoder) {
            log('Bộ giải mã Opus chưa được khởi tạo，Không thể giải mã', 'error');
            return;
        } else {
            log('Opusbộ giải mãkhởi động', 'info');
        }

        while (true) {
            let decodedSamples = [];
            for (const frame of this.pendingAudioBufferQueue) {
                try {
                    // Giải mã bằng bộ giải mã Opus
                    const frameData = this.opusDecoder.decode(frame);
                    if (frameData && frameData.length > 0) {
                        // Chuyển đổi sang Float32
                        const floatData = this.convertInt16ToFloat32(frameData);
                        // Sử dụng vòng lặp thay vì toán tử trải rộng
                        for (let i = 0; i < floatData.length; i++) {
                            decodedSamples.push(floatData[i]);
                        }
                    }
                } catch (error) {
                    log("Giải mã Opus thất bại: " + error.message, 'error');
                }
            }

            if (decodedSamples.length > 0) {
                // Sử dụng vòng lặp thay vì toán tử trải rộng
                for (let i = 0; i < decodedSamples.length; i++) {
                    this.activeQueue.enqueue(decodedSamples[i]);
                }
                this.totalSamples += decodedSamples.length;
            } else {
                log('Không có mẫu âm thanh nào được giải mã thành công', 'warning');
            }
            await this.getPendingAudioBufferQueue();
        }
    }

    // Bắt đầu phát âm thanh
    async startPlaying() {
        this.scheduledEndTime = this.audioContext.currentTime; // Theo dõi thời gian kết thúc của âm thanh đã lên lịch

        while (true) {
            // Bộ đệm ban đầu: đợi đủ mẫu trước khi bắt đầu phát lại
            const minSamples = this.sampleRate * this.minAudioDuration * 2;
            if (!this.playing && this.queue.length < minSamples) {
                await this.getQueue(minSamples);
            }
            this.playing = true;

            // Liên tục phát âm thanh trong hàng đợi, mỗi lần một đoạn nhỏ
            while (this.playing && this.queue.length > 0) {
                // Phát 120ms âm thanh mỗi lần (2 gói Opus)
                const playDuration = 0.12;
                const targetSamples = Math.floor(this.sampleRate * playDuration);
                const actualSamples = Math.min(this.queue.length, targetSamples);

                if (actualSamples === 0) break;

                const currentSamples = this.queue.splice(0, actualSamples);
                const audioBuffer = this.audioContext.createBuffer(this.channels, currentSamples.length, this.sampleRate);
                audioBuffer.copyToChannel(new Float32Array(currentSamples), 0);

                // Tạo nguồn âm thanh
                this.source = this.audioContext.createBufferSource();
                this.source.buffer = audioBuffer;

                // Lên lịch chính xác thời gian phát lại
                const currentTime = this.audioContext.currentTime;
                const startTime = Math.max(this.scheduledEndTime, currentTime);

                // Kết nối với máy phân tích và đầu ra
                this.source.connect(this.analyser);
                this.source.connect(this.audioContext.destination);

                log(`Đã lên lịch phát ${currentSamples.length} mẫu âm thanh, khoảng ${(currentSamples.length / this.sampleRate).toFixed(2)} giây`, 'debug');
                this.source.start(startTime);

                // Cập nhật thời gian dự kiến của đoạn âm thanh tiếp theo
                const duration = audioBuffer.duration;
                this.scheduledEndTime = startTime + duration;
                this.lastPlayTime = startTime;

                // Nếu không có đủ dữ liệu trong hàng đợi, hãy đợi dữ liệu mới
                if (this.queue.length < targetSamples) {
                    break;
                }
            }

            // chờ dữ liệu mới
            await this.getQueue(minSamples);
        }
    }
}

// Chức năng xuất xưởng để tạo các phiên bản streamingContext
export function createStreamingContext(opusDecoder, audioContext, sampleRate, channels, minAudioDuration) {
    return new StreamingContext(opusDecoder, audioContext, sampleRate, channels, minAudioDuration);
}
