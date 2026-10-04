package xiaozhi.common.entity;

import java.io.Serializable;
import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;

import lombok.Data;

/**
 * Lớp thực thể cơ bản, tất cả các thực thể cần kế thừa
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
@Data
public abstract class BaseEntity implements Serializable {
    /**
     * id
     */
    @TableId
    private Long id;
    /**
     * Người sáng tạo
     */
    @TableField(fill = FieldFill.INSERT)
    private Long creator;
    /**
     * thời gian sáng tạo
     */
    @TableField(fill = FieldFill.INSERT)
    private Date createDate;
}