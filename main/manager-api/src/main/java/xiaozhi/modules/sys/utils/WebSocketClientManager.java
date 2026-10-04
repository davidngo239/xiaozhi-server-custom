package xiaozhi.modules.sys.utils;

import java.io.Closeable;
import java.io.IOException;
import java.net.URI;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Consumer;
import java.util.function.Predicate;

import org.springframework.util.StopWatch;
import org.springframework.web.socket.BinaryMessage;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketHttpHeaders;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;
import org.springframework.web.socket.handler.AbstractWebSocketHandler;

import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.utils.DateUtils;

/**
 * WebSocketClientResource: hỗ trợ chế độ dùng thử với tài nguyên
 */
@Slf4j
public class WebSocketClientManager implements Closeable {
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    // Nhóm luồng xử lý callback dùng chung
    private static final ExecutorService CALLBACK_EXECUTOR = Executors
            .newFixedThreadPool(Runtime.getRuntime().availableProcessors(), new ThreadFactory() {
                private final AtomicInteger cnt = new AtomicInteger();

                public Thread newThread(Runnable r) {
                    Thread t = new Thread(r, "ws-callback-" + cnt.getAndIncrement());
                    t.setDaemon(true);
                    return t;
                }
            });

    private volatile WebSocketSession session;
    private final BlockingQueue<String> textMessageQueue;
    private final BlockingQueue<byte[]> binaryMessageQueue;
    private final CompletableFuture<Void> errorFuture;
    private final long maxSessionDuration;
    private final TimeUnit maxSessionDurationUnit;

    private volatile Consumer<String> onText;
    private volatile Consumer<byte[]> onBinary;
    private volatile Consumer<Throwable> onError;

    private final int queueCapacity;

    // Hàm tạo riêng, chỉ được gọi bởi Builder
    private WebSocketClientManager(Builder b) {
        this.maxSessionDuration = b.maxSessionDuration;
        this.maxSessionDurationUnit = b.maxSessionDurationUnit;
        this.queueCapacity = b.queueCapacity;
        this.textMessageQueue = new LinkedBlockingQueue<>(queueCapacity);
        this.binaryMessageQueue = new LinkedBlockingQueue<>(queueCapacity);
        this.errorFuture = new CompletableFuture<>();
    }

    public static WebSocketClientManager build(Builder b)
            throws InterruptedException, ExecutionException, TimeoutException, IOException {
        WebSocketClientManager ws = new WebSocketClientManager(b);
        StandardWebSocketClient client = new StandardWebSocketClient();
        CompletableFuture<WebSocketSession> future = client.execute(ws.new InternalHandler(b.uri), b.headers,
                URI.create(b.uri));
        WebSocketSession sess = future.get(b.connectTimeout, b.connectUnit);
        if (sess == null || !sess.isOpen()) {
            throw new IOException("握手失败或会话未打开");
        }
        // Đặt bộ đệm
        sess.setTextMessageSizeLimit(b.bufferSize);
        sess.setBinaryMessageSizeLimit(b.bufferSize);
        ws.session = sess;
        return ws;
    }


    /**
     * Gửi văn bản
     */
    public void sendText(String text) throws IOException {
        session.sendMessage(new TextMessage(text));
    }

    public void sendBinary(byte[] data) throws IOException {
        session.sendMessage(new BinaryMessage(data));
    }

    public void sendJson(Object payload) throws IOException {
        String json = OBJECT_MAPPER.writeValueAsString(payload);
        session.sendMessage(new TextMessage(json));
    }

    private <T> List<T> listenerCustom(
            BlockingQueue<T> queue,
            Predicate<T> predicate)
            throws InterruptedException, TimeoutException, ExecutionException {
        List<T> collected = new ArrayList<>();
        long deadline = System.currentTimeMillis() + maxSessionDurationUnit.toMillis(maxSessionDuration);

        while (true) {
            if (errorFuture.isDone()) {
                errorFuture.get();
            }

            long remaining = deadline - System.currentTimeMillis();
            if (remaining <= 0) {
                throw new TimeoutException("等待批量消息超时");
            }

            T msg = queue.poll(remaining, TimeUnit.MILLISECONDS);
            if (msg == null) {
                throw new TimeoutException("等待批量消息超时");
            }

            collected.add(msg);
            if (predicate.test(msg)) {
                break;
            }
        }
        close();
        return collected;
    }

    private <T> List<T> listenerCustomWithoutClose(
            BlockingQueue<T> queue,
            Predicate<T> predicate)
            throws InterruptedException, TimeoutException, ExecutionException {
        List<T> collected = new ArrayList<>();
        long deadline = System.currentTimeMillis() + maxSessionDurationUnit.toMillis(maxSessionDuration);

        while (true) {
            if (errorFuture.isDone()) {
                errorFuture.get();
            }

            long remaining = deadline - System.currentTimeMillis();
            if (remaining <= 0) {
                throw new TimeoutException("等待批量消息超时");
            }

            T msg = queue.poll(remaining, TimeUnit.MILLISECONDS);
            if (msg == null) {
                throw new TimeoutException("等待批量消息超时");
            }

            collected.add(msg);
            if (predicate.test(msg)) {
                break;
            }
        }
        // Không gọi close(), giữ kết nối mở
        return collected;
    }

    /**
     * Nhận nhiều tin nhắn một cách đồng bộ cho đến khi vị từ đúng hoặc một ngoại lệ được đưa ra sau khi hết thời gian chờ;
     * 
     * @return Trả về danh sách tất cả các tin nhắn trong thời gian nghe
     */
    public List<String> listener(Predicate<String> predicate)
            throws InterruptedException, TimeoutException, ExecutionException {
        return listenerCustom(textMessageQueue, predicate);
    }

    /**
     * Nhận nhiều tin nhắn một cách đồng bộ cho đến khi vị từ đúng hoặc một ngoại lệ được đưa ra sau khi hết thời gian chờ;
     * Không tự động đóng kết nối, phù hợp với các tình huống cần gửi nhiều tin nhắn trên cùng một kết nối
     * 
     * @return Trả về danh sách tất cả các tin nhắn trong thời gian nghe
     */
    public List<String> listenerWithoutClose(Predicate<String> predicate)
            throws InterruptedException, TimeoutException, ExecutionException {
        return listenerCustomWithoutClose(textMessageQueue, predicate);
    }

    public List<byte[]> listenerBinary(Predicate<byte[]> predicate)
            throws InterruptedException, TimeoutException, ExecutionException {
        return listenerCustom(binaryMessageQueue, predicate);
    }

    /**
     * Đăng ký gọi lại bằng văn bản
     */
    public WebSocketClientManager onText(Consumer<String> c) {
        this.onText = c;
        return this;
    }

    /**
     * Đăng ký gọi lại nhị phân
     */
    public WebSocketClientManager onBinary(Consumer<byte[]> c) {
        this.onBinary = c;
        return this;
    }

    /**
     * Đăng ký gọi lại lỗi
     */
    public WebSocketClientManager onError(Consumer<Throwable> c) {
        this.onError = c;
        return this;
    }

    /**
     * Đóng phiên, thử với tài nguyên/cuối cùng được gọi tự động
     */
    @Override
    public void close() {
        try {
            if (session != null && session.isOpen()) {
                session.close(CloseStatus.NORMAL);
            }
        } catch (IOException ignored) {
        }
        textMessageQueue.clear();
        binaryMessageQueue.clear();
        errorFuture.completeExceptionally(new IOException("WebSocket 已关闭"));
    }

    private class InternalHandler extends AbstractWebSocketHandler {
        private final String targetUri;
        private final StopWatch stopWatch;

        InternalHandler(String targetUri) {
            this.targetUri = targetUri;
            this.stopWatch = new StopWatch();
        }

        /**
         * Gọi lại khi kết nối được thiết lập
         */
        @Override
        public void afterConnectionEstablished(WebSocketSession session) {
            // lưu phiên
            WebSocketClientManager.this.session = session;
            this.stopWatch.start();
            log.info("ws连接成功, 目标URI: {}, 连接时间: {}", targetUri,
                    DateUtils.getDateTimeNow(DateUtils.DATE_TIME_MILLIS_PATTERN));
        }

        /**
         * Xử lý tin nhắn văn bản
         */
        @Override
        protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
            String payload = message.getPayload();
            // Tham gia vào đội
            textMessageQueue.offer(payload);
            // Gọi lại onText đã được người dùng đăng ký
            if (onText != null) {
                CALLBACK_EXECUTOR.submit(() -> onText.accept(payload));
            }
        }

        /**
         * Xử lý tin nhắn nhị phân
         */
        @Override
        protected void handleBinaryMessage(WebSocketSession session, BinaryMessage message) throws Exception {
            ByteBuffer buf = message.getPayload();
            byte[] data = new byte[buf.remaining()];
            buf.get(data);
            // Tham gia vào đội
            binaryMessageQueue.offer(data);
            // Gọi lại onBinary đã được người dùng đăng ký
            if (onBinary != null) {
                CALLBACK_EXECUTOR.submit(() -> onBinary.accept(data));
            }
        }

        /**
         * Gọi lại khi xảy ra lỗi truyền tải
         */
        @Override
        public void handleTransportError(WebSocketSession session, Throwable exception) throws Exception {
            super.handleTransportError(session, exception);
            // Giữ nguyên logic ban đầu: hoàn thành errorFuture, gọi lại onError, đóng phiên, thông báo không đồng bộ về lỗi kết nối
            errorFuture.completeExceptionally(exception);
            if (onError != null) {
                CALLBACK_EXECUTOR.submit(() -> onError.accept(exception));
            }
            session.close(CloseStatus.SERVER_ERROR);
        }

        /**
         * Gọi lại khi kết nối bị đóng
         */
        @Override
        public void afterConnectionClosed(WebSocketSession session, CloseStatus status) throws Exception {
            super.afterConnectionClosed(session, status);
            if (stopWatch.isRunning()) {
                stopWatch.stop();
            }
            log.info("ws连接关闭, 目标URI: {}, 关闭时间: {}, 连接总时长: {}s,断开原因：{}",
                    targetUri, DateUtils.getDateTimeNow(DateUtils.DATE_TIME_MILLIS_PATTERN),
                    DateUtils.millsToSecond(stopWatch.getTotalTimeMillis()),status);
        }

    }

    public static class Builder {
        private String uri; // URI WS đích
        private long connectTimeout = 3; // Yêu cầu thời gian chờ kết nối
        private TimeUnit connectUnit = TimeUnit.SECONDS; // Đơn vị thời gian chờ kết nối yêu cầu
        private long maxSessionDuration = 5; // Thời gian kết nối tối đa, mặc định 5 giây
        private TimeUnit maxSessionDurationUnit = TimeUnit.SECONDS; // Đơn vị thời gian kết nối tối đa
        private int queueCapacity = 100; // dung lượng hàng đợi tin nhắn
        private int bufferSize = 8 * 1024; //8kb mặc định
        private WebSocketHttpHeaders headers; // Tiêu đề yêu cầu

        /**
         * URI WS đích
         */
        public Builder uri(String uri) {
            this.uri = Objects.requireNonNull(uri);
            return this;
        }

        public Builder headers(WebSocketHttpHeaders h) {
            this.headers = h;
            return this;
        }

        public Builder connectTimeout(long t, TimeUnit u) {
            this.connectTimeout = t;
            this.connectUnit = u;
            return this;
        }

        public Builder maxSessionDuration(long t, TimeUnit u) {
            this.maxSessionDuration = t;
            this.maxSessionDurationUnit = u;
            return this;
        }

        public Builder queueCapacity(int c) {
            this.queueCapacity = c;
            return this;
        }
        public Builder bufferSize(int c) {
            this.bufferSize = c;
            return this;
        }

        public WebSocketClientManager build()
                throws InterruptedException, ExecutionException, TimeoutException, IOException {
            return WebSocketClientManager.build(this);
        }

    }
}
