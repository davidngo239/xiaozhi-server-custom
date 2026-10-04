package xiaozhi.modules.agent.entity;

import java.io.Serializable;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * Bảng ánh xạ duy nhất giữa Tác nhân và trình cắm
 * 
 * @TableName ai_agent_plugin_mapping
 */
@Data
@TableName(value = "ai_agent_plugin_mapping")
@Schema(description = "Agent与插件的唯一映射表")
public class AgentPluginMapping implements Serializable {
    /**
     * khóa chính
     */
    @TableId(type = IdType.ASSIGN_ID)
    @Schema(description = "映射信息主键ID")
    private Long id;

    /**
     * ID đại lý
     */
    @Schema(description = "智能体ID")
    private String agentId;

    /**
     * Mã plugin
     */
    @Schema(description = "插件ID")
    private String pluginId;

    /**
     * Định dạng tham số trình cắm (Json)
     */
    @Schema(description = "插件参数(Json)格式")
    private String paramInfo;

    // Trường dự phòng, được sử dụng để tạo điều kiện thuận lợi cho việc kiểm tra Provider_code của trình cắm khi truy vấn trình cắm dựa trên ID. Để biết chi tiết, hãy xem tệp xml lớp dao.
    @TableField(exist = false)
    @Schema(description = "插件provider_code, 对应表ai_model_provider")
    private String providerCode;

    @TableField(exist = false)
    private static final long serialVersionUID = 1L;
}