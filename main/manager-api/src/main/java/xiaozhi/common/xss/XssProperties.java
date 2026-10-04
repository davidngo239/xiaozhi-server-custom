package xiaozhi.common.xss;

import java.util.Collections;
import java.util.List;

import org.springframework.boot.context.properties.ConfigurationProperties;

import lombok.Data;

/**
 * Các mục cấu hình XSS
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
@Data
@ConfigurationProperties(prefix = "renren.xss")
public class XssProperties {
    /**
     * Có bật XSS hay không
     */
    private boolean enabled;
    /**
     * Danh sách URL bị loại trừ
     */
    private List<String> excludeUrls = Collections.emptyList();
}
