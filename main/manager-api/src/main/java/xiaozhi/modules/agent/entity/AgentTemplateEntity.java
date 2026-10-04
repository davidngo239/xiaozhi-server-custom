package xiaozhi.modules.agent.entity;

import java.io.Serializable;
import java.math.BigDecimal;
import java.util.Date;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import lombok.Data;

/**
 * Bảng mẫu cấu hình đại lý
 * 
 * @TableName ai_agent_template
 */
@TableName(value = "ai_agent_template")
@Data
public class AgentTemplateEntity implements Serializable {
    /**
     * Mã định danh duy nhất của đại lý
     */
    @TableId(type = IdType.ASSIGN_UUID)
    private String id;

    /**
     * mã hóa đại lý
     */
    private String agentCode;

    /**
     * Tên đại lý
     */
    private String agentName;

    /**
     * Nhận dạng mô hình nhận dạng giọng nói
     */
    private String asrModelId;

    /**
     * Logo phát hiện hoạt động giọng nói
     */
    private String vadModelId;

    /**
     * Mã định danh mô hình ngôn ngữ lớn
     */
    private String llmModelId;

    /**
     * Nhận dạng mô hình VLLM
     */
    private String vllmModelId;

    /**
     * Nhận dạng mô hình tổng hợp giọng nói
     */
    private String ttsModelId;

    /**
     * nhận dạng âm sắc
     */
    private String ttsVoiceId;

    /**
     * ngôn ngữ âm sắc
     */
    private String ttsLanguage;

    /**
     * khối lượng TTS
     */
    private Integer ttsVolume;

    /**
     * Tốc độ nói TTS
     */
    private Integer ttsRate;

    /**
     * giai điệu TTS
     */
    private Integer ttsPitch;

    /**
     * mã định danh mô hình bộ nhớ
     */
    private String memModelId;

    /**
     * Mã nhận dạng mô hình ý định
     */
    private String intentModelId;

    /**
     * Cấu hình bản ghi trò chuyện (0 không ghi, 1 chỉ ghi văn bản, 2 ghi văn bản và giọng nói)
     */
    private Integer chatHistoryConf;

    /**
     * Thông số cài đặt ký tự
     */
    private String systemPrompt;

    /**
     * Bộ nhớ tóm tắt
     */
    private String summaryMemory;
    /**
     * mã hóa ngôn ngữ
     */
    private String langCode;

    /**
     * ngôn ngữ tương tác
     */
    private String language;

    /**
     * Phân loại trọng lượng
     */
    private Integer sort;

    /**
     * ID người sáng tạo
     */
    private Long creator;

    /**
     * thời gian sáng tạo
     */
    private Date createdAt;

    /**
     * ID người cập nhật
     */
    private Long updater;

    /**
     * Thời gian cập nhật
     */
    private Date updatedAt;

    @TableField(exist = false)
    private static final long serialVersionUID = 1L;
}