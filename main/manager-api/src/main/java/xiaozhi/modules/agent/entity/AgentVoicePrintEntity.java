package xiaozhi.modules.agent.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.Data;

/**
 * Bảng in giọng nói thông minh
 *
 * @author zjy
 */
@TableName(value = "ai_agent_voice_print")
@Data
public class AgentVoicePrintEntity {
    /**
     * id khóa chính
     */
    @TableId(type = IdType.ASSIGN_UUID)
    private String id;
    /**
     * id đại lý liên kết
     */
    private String agentId;
    /**
     * id âm thanh được liên kết
     */
    private String audioId;
    /**
     * Tên của người có giọng nói đến từ
     */
    private String sourceName;
    /**
     * Người mô tả nguồn gốc của giọng nói
     */
    private String introduce;

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
