package xiaozhi.modules.sys.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.Data;
import lombok.EqualsAndHashCode;
import xiaozhi.common.entity.BaseEntity;

/**
 * loại từ điển
 */
@Data
@EqualsAndHashCode(callSuper = false)
@TableName("sys_dict_type")
public class SysDictTypeEntity extends BaseEntity {
    /**
     * Mã hóa kiểu từ điển
     */
    private String dictType;
    /**
     * Tên từ điển
     */
    private String dictName;
    /**
     * Bình luận
     */
    private String remark;
    /**
     * sắp xếp
     */
    private Integer sort;
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