package xiaozhi.modules.knowledge.rag;

import java.time.Duration;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.Map;

import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.client.SimpleClientHttpRequestFactory;

import java.text.SimpleDateFormat;
import java.util.TimeZone;
import java.util.Locale;
import java.net.URLEncoder;
import java.io.UnsupportedEncodingException;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.URI;
import java.io.OutputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.function.Consumer;

import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.extern.slf4j.Slf4j;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;

/**
 * Máy khách HTTP RAGFlow
 * Xử lý thống nhất giao tiếp HTTP, xác thực, thời gian chờ và phân tích lỗi
 */
@Slf4j
public class RAGFlowClient {

    private final String baseUrl;
    private final String apiKey;
    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    // Thời gian chờ mặc định (giây)
    private static final int DEFAULT_TIMEOUT = 30;

    public RAGFlowClient(String baseUrl, String apiKey) {
        this(baseUrl, apiKey, DEFAULT_TIMEOUT);
    }

    public RAGFlowClient(String baseUrl, String apiKey, int timeoutSeconds) {
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.apiKey = apiKey;
        this.objectMapper = new ObjectMapper();
        // [Củng cố] Tương thích với định dạng ngày RFC 1123 được RAGFlow trả về (ví dụ: Thứ Ba, ngày 10 tháng 2 năm 2026 10:27:35 GMT)
        this.objectMapper
                .setDateFormat(new SimpleDateFormat("EEE, dd MMM yyyy HH:mm:ss 'GMT'", Locale.US));
        this.objectMapper.setTimeZone(TimeZone.getTimeZone("GMT"));

        // Ưu tiên lấy RestTemplate Bean được gộp từ bối cảnh Spring (Vấn đề 3: Nhóm kết nối)
        RestTemplate pooledTemplate = null;
        try {
            pooledTemplate = xiaozhi.common.utils.SpringContextUtils.getBean(RestTemplate.class);
        } catch (Exception e) {
            log.warn("无法从 SpringContext 获取池化 RestTemplate，将退化为简单连接模式: {}", e.getMessage());
        }

        if (false) { // Force new RestTemplate for debugging
            this.restTemplate = pooledTemplate;
            log.debug("RAGFlowClient 已成功挂载全局池化 RestTemplate");
        } else {
            // Một giải pháp hoàn hảo: Định cấu hình thời gian chờ và tạo RestTemplate đơn giản
            log.info("RAGFlowClient 初始化: 使用独立 RestTemplate (Debug Mode)");
            SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
            factory.setConnectTimeout(timeoutSeconds * 1000);
            factory.setReadTimeout(timeoutSeconds * 1000);
            this.restTemplate = new RestTemplate(factory);
        }
    }

    /**
     * Gửi yêu cầu NHẬN
     */
    public Map<String, Object> get(String endpoint, Map<String, Object> queryParams) {
        String url = buildUrl(endpoint, queryParams);
        log.debug("GET {}", url);
        return execute(url, HttpMethod.GET, null);
    }

    /**
     * Gửi yêu cầu POST (JSON)
     */
    public Map<String, Object> post(String endpoint, Object body) {
        String url = buildUrl(endpoint, null);
        log.info("RAGFlow Client POST Request: URL={}, BodyType={}", url,
                body != null ? body.getClass().getName() : "null");
        try {
            return execute(url, HttpMethod.POST, body);
        } catch (Exception e) {
            log.error("RAGFlow Client POST Failed: URL={}", url, e);
            throw e;
        }
    }

    /**
     * Gửi yêu cầu XÓA
     */
    public Map<String, Object> delete(String endpoint, Object body) {
        String url = buildUrl(endpoint, null);
        log.debug("DELETE {}", url);
        return execute(url, HttpMethod.DELETE, body);
    }

    /**
     * Gửi yêu cầu PUT
     */
    public Map<String, Object> put(String endpoint, Object body) {
        String url = buildUrl(endpoint, null);
        log.debug("PUT {}", url);
        return execute(url, HttpMethod.PUT, body);
    }

    /**
     * Gửi yêu cầu nhiều phần (tải lên tệp)
     */
    public Map<String, Object> postMultipart(String endpoint, MultiValueMap<String, Object> parts) {
        String url = buildUrl(endpoint, null);
        log.debug("POST MULTIPART {}", url);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        headers.setBearerAuth(apiKey);
        // Để tránh tên tệp tiếng Trung bị cắt xén, một số môi trường có thể cần đặt Bộ ký tự, nhưng trong Multipart, nó thường được điều khiển bởi tiêu đề Phần.

        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(parts, headers);

        return doExecute(url, HttpMethod.POST, requestEntity);
    }

    private Map<String, Object> execute(String url, HttpMethod method, Object body) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setBearerAuth(apiKey);
        // Buộc UTF-8
        headers.setAcceptCharset(Collections.singletonList(StandardCharsets.UTF_8));

        HttpEntity<Object> requestEntity = new HttpEntity<>(body, headers);
        return doExecute(url, method, requestEntity);
    }

    private Map<String, Object> doExecute(String url, HttpMethod method, HttpEntity<?> requestEntity) {
        try {
            ResponseEntity<String> response = restTemplate.exchange(url, method, requestEntity, String.class);

            if (!response.getStatusCode().is2xxSuccessful()) {
                log.error("RAGFlow API Error Status: {}", response.getStatusCode());
                throw new RenException(ErrorCode.RAG_API_ERROR, "HTTP " + response.getStatusCode());
            }

            String responseBody = response.getBody();
            if (responseBody == null) {
                throw new RenException(ErrorCode.RAG_API_ERROR, "Empty Response");
            }

            @SuppressWarnings("unchecked")
            Map<String, Object> map = objectMapper.readValue(responseBody, Map.class);

            Integer code = (Integer) map.get("code");
            if (code != null && code != 0) {
                String msg = (String) map.get("message");
                log.error("RAGFlow Business Error: code={}, msg={}", code, msg);
                throw new RenException(ErrorCode.RAG_API_ERROR, msg != null ? msg : "Unknown RAGFlow Error");
            }

            // Trả về trường dữ liệu hoặc toàn bộ bản đồ nếu dữ liệu không tồn tại (thường RAGFlow trả về code=0, data=... tùy theo tình huống)
            // Xử lý tương thích: Nếu người gọi bên ngoài cần kiểm tra mã, nó đã được kiểm tra tại đây.
            // Chúng ta có nên trả lại một bản đồ được bao bọc bằng mã một cách thống nhất hay chỉ trả về dữ liệu?
            // Theo báo cáo phân tích, logic cũ kiểm tra code==0 rồi lấy dữ liệu.
            // Ở đây chúng tôi trả lại toàn bộ Bản đồ và để Bộ điều hợp quyết định cách lấy nó hay chúng tôi chỉ loại bỏ nó ở đây?
            // Đề xuất: Để linh hoạt, hãy trả lại Bản đồ đầy đủ nhưng đưa ra lỗi mã!=0 ở lớp Máy khách.
            return map;

        } catch (RenException re) {
            throw re;
        } catch (Exception e) {
            log.error("RAGFlow Client Execute Error! URL: {}, Method: {}, Body Type: {}", url, method,
                    requestEntity.getBody() != null ? requestEntity.getBody().getClass().getName() : "null");
            log.error("Full exception stack trace: ", e);
            throw new RenException(ErrorCode.RAG_API_ERROR, "Request Failed: " + e.getMessage());
        }
    }

    private String buildUrl(String endpoint, Map<String, Object> queryParams) {
        StringBuilder sb = new StringBuilder(baseUrl);
        if (!endpoint.startsWith("/")) {
            sb.append("/");
        }
        sb.append(endpoint);

        if (queryParams != null && !queryParams.isEmpty()) {
            sb.append("?");
            queryParams.forEach((k, v) -> {
                if (v != null) {
                    try {
                        sb.append(k).append("=")
                                .append(URLEncoder.encode(v.toString(),
                                        StandardCharsets.UTF_8.name()))
                                .append("&");
                    } catch (UnsupportedEncodingException e) {
                        log.warn("参数编码失败: k={}, v={}", k, v);
                        sb.append(k).append("=").append(v).append("&");
                    }
                }
            });
            // Xóa & cuối cùng
            sb.setLength(sb.length() - 1);
        }
        return sb.toString();
    }

    /**
     * Gửi yêu cầu POST phát trực tuyến (SSE)
     * Được triển khai bằng Java 21 HttpClient
     *
     * @param endpoint điểm cuối API
     * @param body Nội dung yêu cầu
     * @param onData Gọi lại dữ liệu (được gọi khi mỗi hàng dữ liệu được nhận)
     */
    public void postStream(String endpoint, Object body, Consumer<String> onData) {
        try {
            String url = buildUrl(endpoint, null);
            log.debug("POST STREAM {}", url);

            String jsonBody = objectMapper.writeValueAsString(body);

            HttpClient httpClient = HttpClient.newBuilder()
                    .connectTimeout(Duration.ofSeconds(DEFAULT_TIMEOUT))
                    .build();

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .header("Content-Type", "application/json")
                    .header("Authorization", "Bearer " + apiKey)
                    .POST(HttpRequest.BodyPublishers.ofString(jsonBody, StandardCharsets.UTF_8))
                    .build();

            // Gửi yêu cầu và xử lý phản hồi phát trực tuyến
            httpClient.send(request, HttpResponse.BodyHandlers.ofInputStream())
                    .body()
                    .transferTo(new OutputStream() {
                        private final ByteArrayOutputStream buffer = new ByteArrayOutputStream();

                        @Override
                        public void write(int b) throws IOException {
                            if (b == '\n') {
                                String line = buffer.toString(StandardCharsets.UTF_8);
                                if (!line.trim().isEmpty()) {
                                    onData.accept(line);
                                }
                                buffer.reset();
                            } else {
                                buffer.write(b);
                            }
                        }
                    });

        } catch (Exception e) {
            log.error("RAGFlow Stream Request Error", e);
            throw new RenException(ErrorCode.RAG_API_ERROR, "Stream Request Failed: " + e.getMessage());
        }
    }
}
