package xiaozhi.modules.sys.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.Data;
import lombok.EqualsAndHashCode;
import xiaozhi.common.entity.BaseEntity;

/**
 * Quản lý thông số
 */
@Data
@EqualsAndHashCode(callSuper = false)
@TableName("sys_params")
public class SysParamsEntity extends BaseEntity {
    /**
     * Mã hóa thông số
     */
    private String paramCode;
    /**
     * Giá trị tham số
     */
    private String paramValue;
    /**
     * Kiểu giá trị: chuỗi chuỗi, số-số, boolean-Boolean, mảng mảng
     */
    private String valueType;
    /**
     * Loại 0: Tham số hệ thống 1: Tham số phi hệ thống
     */
    private Integer paramType;
    /**
     * Bình luận
     */
    private String remark;
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