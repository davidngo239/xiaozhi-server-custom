package xiaozhi.modules.sys.vo;

import java.util.Date;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * Quản trị viên hiển thị VO của người dùng trong trang
 * @ zjy
 * 
 * @since 2025-3-25
 */
@Data
public class AdminPageUserVO {

    @Schema(description = "设备数量")
    private String deviceCount;

    @Schema(description = "手机号码")
    private String mobile;

    @Schema(description = "状态")
    private Integer status;

    @Schema(description = "用户id")
    private String userid;

    @Schema(description = "注册时间")
    private Date createDate;
}
