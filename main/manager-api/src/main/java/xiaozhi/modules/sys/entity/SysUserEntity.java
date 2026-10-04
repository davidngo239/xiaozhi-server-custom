package xiaozhi.modules.sys.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.Data;
import lombok.EqualsAndHashCode;
import xiaozhi.common.entity.BaseEntity;

/**
 * người dùng hệ thống
 */
@Data
@EqualsAndHashCode(callSuper = false)
@TableName("sys_user")
public class SysUserEntity extends BaseEntity {
    /**
     * Tên người dùng
     */
    private String username;
    /**
     * Mật khẩu
     */
    private String password;
    /**
     * Quản trị viên cấp cao 0: Không 1: Có
     */
    private Integer superAdmin;
    /**
     * Trạng thái 0: Vô hiệu hóa 1: Bình thường
     */
    private Integer status;
    /**
     * Trình cập nhật
     */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private Long updater;
    /**
     * Thời gian cập nhật
     */
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private Date updateDate;

}