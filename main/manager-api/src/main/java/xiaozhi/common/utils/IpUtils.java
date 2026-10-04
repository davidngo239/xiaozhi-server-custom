package xiaozhi.common.utils;

import org.apache.commons.lang3.StringUtils;

import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;

/**
 * địa chỉ IP
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
@Slf4j
public class IpUtils {
    /**
     * Nhận địa chỉ IP
     * <p>
     * Nếu bạn sử dụng phần mềm proxy ngược như Nginx, bạn không thể lấy địa chỉ IP thông qua request.getRemoteAddr()
     * Nếu proxy ngược nhiều cấp được sử dụng, giá trị của X-Forwarded-For không chỉ là một mà là một chuỗi địa chỉ IP. Chuỗi IP hợp lệ không xác định đầu tiên trong X-Forwarded-For là địa chỉ IP thực.
     */
    public static String getIpAddr(HttpServletRequest request) {
        String unknown = "unknown";
        String ip = null;
        try {
            ip = request.getHeader("x-forwarded-for");
            if (StringUtils.isEmpty(ip) || unknown.equalsIgnoreCase(ip)) {
                ip = request.getHeader("Proxy-Client-IP");
            }
            if (StringUtils.isEmpty(ip) || ip.length() == 0 || unknown.equalsIgnoreCase(ip)) {
                ip = request.getHeader("WL-Proxy-Client-IP");
            }
            if (StringUtils.isEmpty(ip) || unknown.equalsIgnoreCase(ip)) {
                ip = request.getHeader("HTTP_CLIENT_IP");
            }
            if (StringUtils.isEmpty(ip) || unknown.equalsIgnoreCase(ip)) {
                ip = request.getHeader("HTTP_X_FORWARDED_FOR");
            }
            if (StringUtils.isEmpty(ip) || unknown.equalsIgnoreCase(ip)) {
                ip = request.getRemoteAddr();
            }
        } catch (Exception e) {
            log.error("IPUtils ERROR ", e);
        }

        return ip;
    }

}
