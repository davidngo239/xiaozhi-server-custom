package xiaozhi.modules.sys.utils;

import java.net.URI;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;

import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.socket.WebSocketHttpHeaders;
import org.springframework.web.socket.client.WebSocketClient;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;

public class WebSocketValidator {
    private static final Logger logger = LoggerFactory.getLogger(WebSocketValidator.class);

    // Biểu thức chính quy URL WebSocket
    private static final Pattern WS_URL_PATTERN = Pattern
            .compile("^wss?://[\\w.-]+(?:\\.[\\w.-]+)*(?::\\d+)?(?:/[\\w.-]*)*$");

    /**
     * Xác minh định dạng địa chỉ WebSocket
     * 
     * @param url Địa chỉ WebSocket
     * @return có hợp lệ không?
     */
    public static boolean validateUrlFormat(String url) {
        if (StringUtils.isBlank(url)) {
            return false;
        }
        return WS_URL_PATTERN.matcher(url.trim()).matches();
    }

    /**
     * Kiểm tra kết nối WebSocket
     * 
     * @param url Địa chỉ WebSocket
     * @return liệu nó có thể được kết nối không
     */
    public static boolean testConnection(String url) {
        if (!validateUrlFormat(url)) {
            return false;
        }

        try {
            WebSocketClient client = new StandardWebSocketClient();
            CompletableFuture<Boolean> future = new CompletableFuture<>();
            WebSocketHttpHeaders headers = new WebSocketHttpHeaders();

            client.execute(new WebSocketTestHandler(future), headers, URI.create(url));

            // Đợi tối đa 5 giây để có kết quả kết nối
            return future.get(5, TimeUnit.SECONDS);
        } catch (Exception e) {
            logger.error("WebSocket连接测试失败: {}", url, e);
            return false;
        }
    }
}