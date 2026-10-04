package xiaozhi.modules.sys.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.Data;
import lombok.EqualsAndHashCode;
import xiaozhi.common.entity.BaseEntity;

/**
 * từ điển dữ liệu
 */
@Data
@EqualsAndHashCode(callSuper = false)
@TableName("sys_dict_data")
public class SysDictDataEntity extends BaseEntity {
    /**
     * ID loại từ điển
     */
    private Long dictTypeId;
    /**
     * thẻ từ điển
     */
    private String dictLabel;
    /**
     * Giá trị từ điển
     */
    private String dictValue;
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