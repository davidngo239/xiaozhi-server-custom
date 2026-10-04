package xiaozhi.modules.sys.service;


import java.util.function.Consumer;

/**
 * Xác định lớp công cụ người dùng hệ thống để tránh phụ thuộc vòng tròn với các mô-đun người dùng
 * Nếu người dùng và thiết bị phụ thuộc lẫn nhau, người dùng cần lấy tất cả các thiết bị và thiết bị cần lấy tên người dùng của từng thiết bị.
 * @author zjy
 * @since 2025-4-2
 */
public interface SysUserUtilService {
    /**
     * Gán tên người dùng
     * @param userId userid
     * @param setter Phương pháp phân công
     */
    void assignUsername( Long userId, Consumer<String> setter);
}
