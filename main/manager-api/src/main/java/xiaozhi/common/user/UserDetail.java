package xiaozhi.common.user;

import java.io.Serializable;

import lombok.Data;

/**
 * Đăng nhập thông tin người dùng
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
@Data
public class UserDetail implements Serializable {
    private Long id;
    private String username;
    private Integer superAdmin;
    private String token;
    private Integer status;
}