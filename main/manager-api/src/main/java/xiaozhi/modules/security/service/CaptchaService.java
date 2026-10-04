package xiaozhi.modules.security.service;

import java.io.IOException;

import jakarta.servlet.http.HttpServletResponse;

/**
 * Mã xác minh
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
public interface CaptchaService {

    /**
     * Mã xác minh hình ảnh
     */
    void create(HttpServletResponse response, String uuid) throws IOException;

    /**
     * Xác thực mã xác minh
     * 
     * @param uuid   uuid
     * @param code xác minh mã
     * @param delete có xóa mã xác minh không
     * @return true: thành công sai: thất bại
     */
    boolean validate(String uuid, String code, Boolean delete);

    /**
     * Gửi mã xác minh qua SMS
     * 
     * @param phone thoại điện thoại di động
     */
    void sendSMSValidateCode(String phone);

    /**
     * Xác minh mã xác minh SMS
     * 
     * @param phone thoại điện thoại di động
     * @param code xác minh mã
     * @param delete có xóa mã xác minh không
     * @return true: thành công sai: thất bại
     */
    boolean validateSMSValidateCode(String phone, String code, Boolean delete);
}
