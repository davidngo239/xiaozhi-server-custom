package xiaozhi.modules.security.entity;

import java.io.Serializable;
import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.Data;

/**
 * Mã thông báo người dùng hệ thống
 */
@Data
@TableName("sys_user_token")
public class SysUserTokenEntity implements Serializable {

    /**
     * id
     */
    @TableId
    private Long id;
    /**
     * ID người dùng
     */
    private Long userId;
    /**
     * mã thông báo người dùng
     */
    private String token;
    /**
     * Thời gian hết hạn
     */
    private Date expireDate;
    /**
     * Thời gian cập nhật
     */
    private Date updateDate;
    /**
     * thời gian sáng tạo
     */
    @TableField(fill = FieldFill.INSERT)
    private Date createDate;

}