// Mô-đun phát lại âm thanh
import BlockingQueue from '../../utils/blocking-queue.js?v=0205';
import { log } from '../../utils/logger.js?v=0205';
import { createStreamingContext } from './stream-context.js?v=0205';

// Lớp trình phát âm thanh
export class AudioPlayer {
    constructor() {
        // Thông số âm thanh
        this.SAMPLE_RATE = 16000;
        this.CHANNELS = 1;
        this.FRAME_SIZE = 960;
        this.MIN_AUDIO_DURATION = 0.12;

        // Trạng thái
        this.audioContext = null;
        this.opusDecoder = null;
        this.streamingContext = null;
        this.queue = new BlockingQueue();
        this.isPlaying = false;
    }

    // Nhận hoặc tạo AudioContext
    getAudioContext() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: this.SAMPLE_RATE,
                latencyHint: 'interactive'
            });
            log('Tạo ngữ cảnh âm thanh, tần số lấy mẫu: ' + this.SAMPLE_RATE + ' Hz', 'debug');
        }
        return this.audioContext;
    }

    // Đang khởi tạo bộ giải mã Opus
    async initOpusDecoder() {
        if (this.opusDecoder) return this.opusDecoder;

        try {
            if (typeof window.ModuleInstance === 'undefined') {
                if (typeof Module !== 'undefined') {
                    window.ModuleInstance = Module;
                    log('Dùng Module toàn cục làm ModuleInstance', 'info');
                } else {
                    throw new Error('Thư viện Opus chưa được tải, ModuleInstance và Module đều không tồn tại');
                }
            }

            const mod = window.ModuleInstance;

            this.opusDecoder = {
                channels: this.CHANNELS,
                rate: this.SAMPLE_RATE,
                frameSize: this.FRAME_SIZE,
                module: mod,
                decoderPtr: null,

                init: function () {
                    if (this.decoderPtr) return true;

                    const decoderSize = mod._opus_decoder_get_size(this.channels);
                    log(`Kích thước bộ giải mã Opus: ${decoderSize} byte`, 'debug');

                    this.decoderPtr = mod._malloc(decoderSize);
                    if (!this.decoderPtr) {
                        throw new Error("Không thể cấp bộ nhớ cho bộ giải mã");
                    }

                    const err = mod._opus_decoder_init(
                        this.decoderPtr,
                        this.rate,
                        this.channels
                    );

                    if (err < 0) {
                        this.destroy();
                        throw new Error(`Không thể khởi tạo bộ giải mã Opus: ${err}`);
                    }

                    log("Đã khởi tạo bộ giải mã Opus", 'success');
                    return true;
                },

                decode: function (opusData) {
                    if (!this.decoderPtr) {
                        if (!this.init()) {
                            throw new Error("Bộ giải mã chưa được khởi tạo và không thể khởi tạo");
                        }
                    }

                    try {
                        const mod = this.module;

                        const opusPtr = mod._malloc(opusData.length);
                        mod.HEAPU8.set(opusData, opusPtr);

                        const pcmPtr = mod._malloc(this.frameSize * 2);

                        const decodedSamples = mod._opus_decode(
                            this.decoderPtr,
                            opusPtr,
                            opusData.length,
                            pcmPtr,
                            this.frameSize,
                            0
                        );

                        if (decodedSamples < 0) {
                            mod._free(opusPtr);
                            mod._free(pcmPtr);
                            throw new Error(`Giải mã Opus thất bại: ${decodedSamples}`);
                        }

                        const decodedData = new Int16Array(decodedSamples);
                        for (let i = 0; i < decodedSamples; i++) {
                            decodedData[i] = mod.HEAP16[(pcmPtr >> 1) + i];
                        }

                        mod._free(opusPtr);
                        mod._free(pcmPtr);

                        return decodedData;
                    } catch (error) {
                        log(`Lỗi giải mã Opus: ${error.message}`, 'error');
                        return new Int16Array(0);
                    }
                },

                destroy: function () {
                    if (this.decoderPtr) {
                        this.module._free(this.decoderPtr);
                        this.decoderPtr = null;
                    }
                }
            };

            if (!this.opusDecoder.init()) {
                throw new Error("Không thể khởi tạo bộ giải mã Opus");
            }

            return this.opusDecoder;

        } catch (error) {
            log(`Không thể khởi tạo bộ giải mã Opus: ${error.message}`, 'error');
            this.opusDecoder = null;
            throw error;
        }
    }

    // Bật bộ đệm âm thanh
    async startAudioBuffering() {
        log("bắt đầuâm thanhbộ đệm...", 'info');

        this.initOpusDecoder().catch(error => {
            log(`Khởi tạo trước bộ giải mã Opus thất bại: ${error.message}`, 'warning');
        });

        const timeout = 400;
        while (true) {
            const packets = await this.queue.dequeue(
                6,
                timeout,
                (count) => {
                    log(`Hết thời gian chờ bộ đệm, hiện có ${count} gói; bắt đầu phát`, 'info');
                }
            );
            if (packets.length) {
                log(`Đã nhận ${packets.length} gói âm thanh vào bộ đệm, bắt đầu phát`, 'info');
                this.streamingContext.pushAudioBuffer(packets);
            }

            while (true) {
                const data = await this.queue.dequeue(99, 30);
                if (data.length) {
                    this.streamingContext.pushAudioBuffer(data);
                } else {
                    break;
                }
            }
        }
    }

    // Phát âm thanh đệm
    async playBufferedAudio() {
        try {
            this.audioContext = this.getAudioContext();

            if (!this.opusDecoder) {
                log('Đang khởi tạo bộ giải mã Opus...', 'info');
                try {
                    this.opusDecoder = await this.initOpusDecoder();
                    if (!this.opusDecoder) {
                        throw new Error('Không thể khởi tạo bộ giải mã');
                    }
                    log('Đã khởi tạo bộ giải mã Opus', 'success');
                } catch (error) {
                    log('Không thể khởi tạo bộ giải mã Opus: ' + error.message, 'error');
                    this.isPlaying = false;
                    return;
                }
            }

            if (!this.streamingContext) {
                this.streamingContext = createStreamingContext(
                    this.opusDecoder,
                    this.audioContext,
                    this.SAMPLE_RATE,
                    this.CHANNELS,
                    this.MIN_AUDIO_DURATION
                );
            }

            this.streamingContext.decodeOpusFrames();
            this.streamingContext.startPlaying();

        } catch (error) {
            log(`Lỗi phát âm thanh đã đưa vào bộ đệm: ${error.message}`, 'error');
            this.isPlaying = false;
            this.streamingContext = null;
        }
    }

    // Thêm dữ liệu âm thanh vào hàng đợi
    enqueueAudioData(opusData) {
        if (opusData.length > 0) {
            this.queue.enqueue(opusData);
        } else {
        log('Đã nhận khung âm thanh rỗng, có thể đây là tín hiệu kết thúc', 'warning');
            if (this.isPlaying && this.streamingContext) {
                this.streamingContext.endOfStream = true;
            }
        }
    }

    // Bộ giải mã tải trước
    async preload() {
        log('Đang tải trước bộ giải mã Opus...', 'info');
        try {
            await this.initOpusDecoder();
            log('Đã tải trước bộ giải mã Opus', 'success');
        } catch (error) {
            log(`Tải trước bộ giải mã Opus thất bại: ${error.message}; sẽ thử lại khi cần`, 'warning');
        }
    }

    // Khởi động hệ thống phát lại
    async start() {
        await this.preload();
        this.playBufferedAudio();
        this.startAudioBuffering();
    }

    // Nhận số liệu thống kê gói âm thanh
    getAudioStats() {
        if (!this.streamingContext) {
            return {
                pendingDecode: 0,
                pendingPlay: 0,
                totalPending: 0
            };
        }

        const pendingDecode = this.streamingContext.getPendingDecodeCount();
        const pendingPlay = this.streamingContext.getPendingPlayCount();

        return {
            pendingDecode,  // Số lượng gói được giải mã
            pendingPlay,    // Số lượng gói có thể chơi
            totalPending: pendingDecode + pendingPlay  // Tổng số gói hàng cần xử lý
        };
    }

    // Đã xóa toàn bộ bộ đệm âm thanh và ngừng phát
    clearAllAudio() {
        log('AudioPlayer: Đã xóa toàn bộ âm thanh', 'info');

        // Xóa hàng đợi nhận (sử dụng phương thức clear để giữ tham chiếu đối tượng)
        this.queue.clear();

        // Xóa tất cả bộ đệm trong ngữ cảnh luồng
        if (this.streamingContext) {
            this.streamingContext.clearAllBuffers();
        }

        log('AudioPlayer: Đã xóa âm thanh', 'success');
    }
}

// Tạo một singleton
let audioPlayerInstance = null;

export function getAudioPlayer() {
    if (!audioPlayerInstance) {
        audioPlayerInstance = new AudioPlayer();
    }
    return audioPlayerInstance;
}
